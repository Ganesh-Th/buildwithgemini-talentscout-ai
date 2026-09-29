"""Image generation service for TalentScout AI.

Generates promotional banners and visuals for tech events and job opportunities
using gemini-3.1-flash-lite-image in the global region.
Saves the artifact into tool_context and uploads directly to Cloud Storage.
"""

import re
import time
from typing import Any
from google import genai
from google.adk.tools import ToolContext
from google.cloud import storage
from google.genai import types

# Hardcoded project and bucket strings as required for Agent Platform
PROJECT_ID = "qwiklabs-gcp-03-70611c3d6bad"
BUCKET_NAME = "talentscout-ai-media-qwiklabs-gcp-03-70611c3d6bad"
MODEL_NAME = "gemini-3.1-flash-lite-image"
LOCATION = "global"

_genai_client = None
_storage_client = None


def _get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION,
        )
    return _genai_client


def _get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=PROJECT_ID)
    return _storage_client


async def generate_opportunity_image(
    prompt: str,
    item_title: str = "opportunity",
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Generate an image banner for a tech job posting or event in the agent's domain.

    Uses the gemini-3.1-flash-lite-image model in the global region.
    Saves the image into the session artifacts panel via tool_context.save_artifact,
    and uploads the image bytes directly to Cloud Storage, returning its public HTTPS URL.

    Args:
        prompt: Description of the visual banner or badge to generate (e.g. 'A futuristic conference banner with neural networks and code lines for AI Engineer World Fair').
        item_title: Short title or slug of the job or event used for naming the artifact and Cloud Storage object.
        tool_context: Context provided by ADK to record artifacts in the session.

    Returns:
        A dictionary containing the public HTTPS URL, object name, artifact filename, and status.
    """
    try:
        client = _get_genai_client()
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"

        if response.parts:
            for part in response.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break

        if not image_bytes:
            return {"error": "Model did not return valid image data."}

        sanitized_title = re.sub(r"[^a-zA-Z0-9_\-]", "_", item_title.strip().lower())
        timestamp = int(time.time())
        ext = "png" if "png" in mime_type else "jpg"
        filename = f"{sanitized_title}_{timestamp}.{ext}"
        object_name = f"banners/{filename}"

        # 1. Save with tool_context.save_artifact for Playground Artifacts panel
        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                await tool_context.save_artifact(
                    filename=filename,
                    artifact=types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                )
            except Exception as e:
                # In standalone testing without an artifact service, log and continue
                print(f"[Warning] tool_context.save_artifact skipped: {e}")

        # 2. Upload image bytes directly to Cloud Storage (no local file path returned)
        storage_client = _get_storage_client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(object_name)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{object_name}"

        return {
            "status": "success",
            "public_url": public_url,
            "object_name": object_name,
            "artifact_filename": filename,
            "mime_type": mime_type,
            "message": f"Image successfully generated and uploaded to public Cloud Storage: {public_url}",
        }
    except Exception as e:
        return {"error": f"Failed to generate image: {str(e)}"}
