"""Video generation service for TalentScout AI.

Generates promotional videos and event teasers for tech opportunities and conferences
using Google's Omni model (gemini-omni-flash-preview) in the global region.
Saves the video artifact into tool_context and uploads directly to Cloud Storage.
"""

import base64
import logging
import re
import time
from typing import Any
from google import genai
from google.adk.tools import ToolContext
from google.cloud import storage
from google.genai import types

logger = logging.getLogger(__name__)

# Hardcoded project and bucket strings as required for Agent Platform
PROJECT_ID = "qwiklabs-gcp-03-70611c3d6bad"
BUCKET_NAME = "talentscout-ai-media-qwiklabs-gcp-03-70611c3d6bad"
MODEL_NAME = "gemini-omni-flash-preview"
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


async def generate_opportunity_video(
    prompt: str,
    item_title: str = "opportunity",
    duration: str = "5s",
    aspect_ratio: str = "16:9",
    tool_context: ToolContext = None,
) -> dict[str, Any]:
    """Generate a short promotional teaser video for a tech event, conference, or job highlight in the agent's domain.

    Uses Google's Omni model (gemini-omni-flash-preview) in the global region.
    Saves the video into the session artifacts panel via tool_context.save_artifact,
    and uploads the video bytes directly to public Cloud Storage, returning its public HTTPS URL.

    Args:
        prompt: Description of the video scene, motion, and visual theme (e.g. 'A dynamic 5-second teaser featuring futuristic neural network connections and glowing code typography for AI Engineer World Fair').
        item_title: Short title or slug of the job or event used for naming the artifact and Cloud Storage object.
        duration: Length of the video ('3s' to '10s'). Default is '5s'.
        aspect_ratio: Video aspect ratio ('16:9' landscape or '9:16' portrait). Default is '16:9'.
        tool_context: Context provided by ADK to record artifacts in the session.

    Returns:
        A dictionary containing the public HTTPS URL, object name, artifact filename, duration, and status.
    """
    try:
        client = _get_genai_client()

        # Normalize duration between 3s and 10s as supported by gemini-omni-flash-preview
        dur_str = duration.strip().lower()
        if not dur_str.endswith("s"):
            dur_str = f"{dur_str}s"

        interaction = client.interactions.create(
            model=MODEL_NAME,
            input=[{"type": "text", "text": prompt}],
            response_format=[{
                "type": "video",
                "aspect_ratio": aspect_ratio if aspect_ratio in ["16:9", "9:16"] else "16:9",
                "duration": dur_str,
            }],
        )

        video_bytes = None
        mime_type = "video/mp4"

        # Extract video data from output_video property or steps
        output_vid = getattr(interaction, "output_video", None)
        if output_vid:
            data = getattr(output_vid, "data", None)
            if data:
                video_bytes = base64.b64decode(data) if isinstance(data, (str, bytes)) else data
            if getattr(output_vid, "mime_type", None):
                mime_type = output_vid.mime_type

        if not video_bytes and hasattr(interaction, "steps"):
            for step in interaction.steps or []:
                if getattr(step, "type", None) == "model_output":
                    for item in getattr(step, "content", []) or []:
                        if getattr(item, "type", None) == "video":
                            data = getattr(item, "data", None)
                            if data:
                                video_bytes = base64.b64decode(data) if isinstance(data, (str, bytes)) else data
                            if getattr(item, "mime_type", None):
                                mime_type = item.mime_type
                            break

        if not video_bytes:
            return {"error": "Model did not return valid video data."}

        sanitized_title = re.sub(r"[^a-zA-Z0-9_\-]", "_", item_title.strip().lower())
        timestamp = int(time.time())
        filename = f"{sanitized_title}_{timestamp}.mp4"
        object_name = f"videos/{filename}"

        # 1. Save with tool_context.save_artifact for Playground Artifacts panel
        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                await tool_context.save_artifact(
                    filename=filename,
                    artifact=types.Part.from_bytes(data=video_bytes, mime_type=mime_type),
                )
            except Exception as e:
                logger.warning("tool_context.save_artifact skipped: %s", e)

        # 2. Upload video bytes directly to public Cloud Storage (no local file path returned)
        storage_client = _get_storage_client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(object_name)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{object_name}"

        return {
            "status": "success",
            "public_url": public_url,
            "object_name": object_name,
            "artifact_filename": filename,
            "mime_type": mime_type,
            "duration": dur_str,
            "message": f"Video successfully generated and uploaded to public Cloud Storage: {public_url}",
        }
    except Exception as e:
        return {"error": f"Failed to generate video: {str(e)}"}
