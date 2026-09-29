"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.

Why A2A: agents-cli 1.1.0 (GA) deploys ADK agents to Agent Runtime as A2A agents
and no longer registers the reasoning-engine operation schema the old
`agent_engines.get(...).stream_query()` path relied on (operation_schemas() comes
back empty). The container serves the A2A protocol over the Agent Engine HTTP
passthrough, so this proxy fetches the agent's card and sends messages with the
a2a-sdk client (the same path `agents-cli run --mode a2a` uses). This works for
both A2A and plain ADK 1.1.0 deployments (the container serves A2A either way).

Run:
  pip install -r requirements.txt
  export AGENT_ENGINE_RESOURCE_NAME="projects/.../locations/.../reasoningEngines/..."
  export AGENT_DIRECTORY="app"   # your agent's app directory (agents-cli-manifest.yaml)
  python main.py                 # -> http://localhost:8080
"""

import os
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/284031418526/locations/us-east1/reasoningEngines/8687670180593008640",
)
# The agent's app directory (matches agent_directory in agents-cli-manifest.yaml).
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
# Location is embedded in the resource name: projects/<p>/locations/<loc>/reasoningEngines/<id>.
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

# A2A endpoint for an Agent Runtime deployment, via the Agent Engine HTTP
# passthrough. The card lives at the well-known path under this base.
A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

# The agent tags its A2UI data parts with this mime type.
_A2UI_MIME = "application/json+a2ui"

# One set of ADC credentials, refreshed per request (access tokens expire ~1h).
_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    # Always return JSON so the browser never receives a plain-text 500 page
    # (which shows up in the chat as "Unexpected token 'I', "Internal S"... is
    # not valid JSON"). Any server-side failure now surfaces as a readable
    # message in the chat bubble instead.
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}
# Cache the agent card after the first fetch.
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card = AgentCard(**resp.json())
        # Agent Runtime does not serve a public card URL, so point the client at
        # the passthrough base for message sends.
        card.url = A2A_BASE
        _card = card
    return _card


def _extract_parts(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for the chat UI.

    Text parts pass through as {"kind": "text"}. A2UI data parts (tagged
    application/json+a2ui) become {"kind": "a2ui", "data": <message>} so the UI
    renders the card; each data part is one A2UI message (beginRendering or
    surfaceUpdate).
    """
    out: list[dict] = []
    for p in parts:
        root = getattr(p, "root", p)
        if isinstance(root, TextPart) and getattr(root, "text", None):
            out.append({"kind": "text", "text": root.text})
        elif getattr(root, "data", None) is not None:
            data_val = root.data
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if isinstance(data_val, dict):
                inner_meta = data_val.get("metadata")
                if isinstance(inner_meta, dict) and inner_meta.get("mimeType"):
                    mime = inner_meta.get("mimeType")
                if "data" in data_val:
                    data_val = data_val["data"]
            if mime == _A2UI_MIME:
                out.append({"kind": "a2ui", "data": data_val})
        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id")
    session_id = body.get("session_id") or "default"
    
    # Enforce sign in: only authenticated users can use the AI bot
    if not user_id:
        return JSONResponse(
            status_code=401,
            content={
                "parts": [{"kind": "text", "text": "Authentication required. Please sign in with Google to chat with TalentScout AI."}]
            }
        )
    parts: list[dict] = []

    # Map user + session to context ID
    context_key = f"{user_id}:{session_id}"

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        factory = ClientFactory(
            ClientConfig(
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text=message))],
            context_id=_contexts.get(context_key),
        )

        last_task = None
        got_artifact_update = False
        async for event in a2a_client.send_message(msg):
            if not isinstance(event, tuple):
                continue
            task, update = event
            if task is not None:
                last_task = task
                if getattr(task, "context_id", None):
                    _contexts[context_key] = task.context_id
            if isinstance(update, TaskArtifactUpdateEvent):
                got_artifact_update = True
                parts.extend(_extract_parts(update.artifact.parts))

        # Non-streaming fallback: pull parts from the final task's artifacts.
        if not got_artifact_update and last_task is not None:
            for artifact in getattr(last_task, "artifacts", None) or []:
                parts.extend(_extract_parts(artifact.parts))

    if not parts:
        # The turn produced no text or UI (e.g. the agent only ran tools, or a
        # tool stalled). Be honest rather than silent.
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]

    # Asynchronously record turn in Firestore chat history for this user & session
    try:
        import time
        import urllib.parse
        creds, project = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        fs_headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json"
        }
        safe_uid = urllib.parse.quote(user_id, safe="")
        safe_sid = urllib.parse.quote(session_id, safe="")
        fs_url = f"https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents/chat_history/{safe_uid}/sessions/{safe_sid}/messages"
        
        # Extract reply text
        reply_texts = [p.get("text", "") for p in parts if p.get("kind") == "text" or p.get("text")]
        reply_summary = "\n".join(filter(None, reply_texts)) or "(Rich UI card)"

        # Save turn
        now_ts = time.time()
        turn_data = {
            "fields": {
                "user_message": {"stringValue": message[:2000]},
                "agent_reply": {"stringValue": reply_summary[:3000]},
                "timestamp": {"doubleValue": now_ts}
            }
        }
        async with httpx.AsyncClient(timeout=5.0) as fs_client:
            await fs_client.post(fs_url, json=turn_data, headers=fs_headers)
            
            # Also update session metadata doc for listing sessions
            meta_url = f"https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents/chat_history/{safe_uid}/sessions/{safe_sid}"
            meta_data = {
                "fields": {
                    "session_id": {"stringValue": session_id},
                    "title": {"stringValue": message[:60].strip() or "Conversation"},
                    "updated_at": {"doubleValue": now_ts}
                }
            }
            await fs_client.patch(meta_url, json=meta_data, headers=fs_headers)
    except Exception as e:
        print("Warning: failed to persist chat turn in Firestore:", e)

    return JSONResponse({"parts": parts, "session_id": session_id})


@app.get("/chat/sessions")
async def list_chat_sessions(user_id: str):
    """Retrieve list of conversation threads/sessions for the user."""
    if not user_id:
        return JSONResponse(status_code=400, content={"ok": False, "error": "user_id required"})

    try:
        import urllib.parse
        creds, project = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        fs_headers = {"Authorization": f"Bearer {creds.token}"}
        safe_uid = urllib.parse.quote(user_id, safe="")
        fs_url = f"https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents/chat_history/{safe_uid}/sessions?pageSize=50"

        async with httpx.AsyncClient(timeout=10.0) as fs_client:
            resp = await fs_client.get(fs_url, headers=fs_headers)
            if resp.status_code != 200:
                return JSONResponse({"ok": True, "sessions": []})

            docs_payload = resp.json().get("documents", [])
            sessions = []
            for d in docs_payload:
                doc_name = d.get("name", "").split("/")[-1]
                fields = d.get("fields", {})
                sid = fields.get("session_id", {}).get("stringValue", doc_name)
                title = fields.get("title", {}).get("stringValue", "Conversation")
                updated_at = fields.get("updated_at", {}).get("doubleValue", 0.0)
                sessions.append({
                    "session_id": sid,
                    "title": title,
                    "updated_at": updated_at
                })
            sessions.sort(key=lambda x: x.get("updated_at", 0.0), reverse=True)
            return JSONResponse({"ok": True, "sessions": sessions})
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@app.get("/chat/history")
async def get_chat_history(user_id: str, session_id: str = "default"):
    """Retrieve stored chat history messages for a specific session from Firestore."""
    if not user_id:
        return JSONResponse(status_code=400, content={"ok": False, "error": "user_id required"})

    try:
        import urllib.parse
        creds, project = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        fs_headers = {"Authorization": f"Bearer {creds.token}"}
        safe_uid = urllib.parse.quote(user_id, safe="")
        safe_sid = urllib.parse.quote(session_id, safe="")
        fs_url = f"https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents/chat_history/{safe_uid}/sessions/{safe_sid}/messages?pageSize=50"

        async with httpx.AsyncClient(timeout=10.0) as fs_client:
            resp = await fs_client.get(fs_url, headers=fs_headers)
            if resp.status_code != 200:
                # Fallback to old flat collection structure if needed
                old_url = f"https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents/chat_history/{safe_uid}/messages?pageSize=30"
                old_resp = await fs_client.get(old_url, headers=fs_headers)
                if old_resp.status_code == 200:
                    docs_payload = old_resp.json().get("documents", [])
                else:
                    return JSONResponse({"ok": True, "history": []})
            else:
                docs_payload = resp.json().get("documents", [])

            history = []
            for d in docs_payload:
                fields = d.get("fields", {})
                user_msg = fields.get("user_message", {}).get("stringValue", "")
                agent_reply = fields.get("agent_reply", {}).get("stringValue", "")
                ts = fields.get("timestamp", {}).get("doubleValue", 0.0)
                if user_msg or agent_reply:
                    history.append({
                        "user_message": user_msg,
                        "agent_reply": agent_reply,
                        "timestamp": ts
                    })
            # Sort by timestamp ascending
            history.sort(key=lambda x: x.get("timestamp", 0.0))
            return JSONResponse({"ok": True, "history": history})
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


# Authentication endpoints
GOOGLE_OAUTH_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID",
    "284031418526-ph8a2s8ccokq3jjh9kduq71bl9k47kne.apps.googleusercontent.com"
)

@app.get("/auth/config")
async def auth_config():
    """Return Google Client ID enabling the official Google Identity Services button."""
    return JSONResponse({
        "google_client_id": GOOGLE_OAUTH_CLIENT_ID
    })


@app.post("/auth/google")
async def auth_google(req: Request):
    """Verify Google ID token or fallback profile."""
    body = await req.json()
    credential = body.get("credential")
    client_id = GOOGLE_OAUTH_CLIENT_ID
    
    if credential:
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as auth_requests
            id_info = id_token.verify_oauth2_token(
                credential, auth_requests.Request(), audience=client_id if client_id else None
            )
            user_id = id_info.get("email") or id_info.get("sub")
            return JSONResponse({
                "ok": True,
                "user": {
                    "id": user_id,
                    "email": id_info.get("email", ""),
                    "name": id_info.get("name", "Google User"),
                    "picture": id_info.get("picture", "")
                }
            })
        except Exception as e:
            return JSONResponse(status_code=401, content={"ok": False, "error": f"Invalid Google token: {e}"})
    return JSONResponse(status_code=400, content={"ok": False, "error": "Google credential token required."})


# Resume Upload and Parsing using Gemini Multimodal
@app.post("/resume/upload")
async def upload_resume(req: Request):
    """Receive uploaded resume (PDF or text), parse skills, role, and experience using Gemini."""
    try:
        body = await req.json()
        filename = body.get("filename", "resume.pdf")
        mime_type = body.get("mime_type", "application/pdf")
        b64_data = body.get("data")
        user_id = body.get("user_id")

        if not b64_data:
            return JSONResponse(status_code=400, content={"ok": False, "error": "No file content provided"})

        # Call Gemini 2.5 Flash Multimodal to analyze and extract resume contents
        creds, project = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)

        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json"
        }

        prompt_text = (
            "Analyze this resume carefully. Extract:\n"
            "1. Candidate Name and current/target Role\n"
            "2. Location / City / Country (if specified)\n"
            "3. Core Technical Skills and tools\n"
            "4. Years of experience and recent job titles\n"
            "5. A concise 2-sentence professional summary for job matching.\n"
            "Format the response cleanly and concisely."
        )

        gemini_url = f"https://us-east1-aiplatform.googleapis.com/v1/projects/{project}/locations/us-east1/publishers/google/models/gemini-2.5-flash:generateContent"
        
        parts_payload = []
        if mime_type.startswith("text/") or filename.endswith((".txt", ".md")):
            import base64
            decoded_text = base64.b64decode(b64_data).decode("utf-8", errors="ignore")
            parts_payload = [{"text": f"Resume Content:\n{decoded_text}\n\n{prompt_text}"}]
        else:
            parts_payload = [
                {"inlineData": {"mimeType": mime_type, "data": b64_data}},
                {"text": prompt_text}
            ]

        payload = {"contents": [{"role": "user", "parts": parts_payload}]}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(gemini_url, json=payload, headers=headers)
            if resp.status_code != 200:
                return JSONResponse(status_code=500, content={"ok": False, "error": f"Gemini parsing failed: {resp.text[:300]}"})

            gemini_res = resp.json()
            extracted_analysis = gemini_res["candidates"][0]["content"]["parts"][0]["text"]

            return JSONResponse({
                "ok": True,
                "filename": filename,
                "summary": extracted_analysis
            })
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": f"Upload failed: {str(e)}"})


# Serve the chat UI (keep this mount last so /chat and /auth win).
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
