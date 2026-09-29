# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.code_executors import AgentEngineSandboxCodeExecutor

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from app.a2ui_utils import a2ui_callback

from app.firestore_service import (
    search_jobs,
    add_job_posting,
    search_tech_events,
    add_tech_event,
    calculate_resume_match,
)
from app.external_api import fetch_live_tech_jobs
from app.maps_service import geocode_address, find_nearby_places
from app.image_service import generate_opportunity_image
from app.video_service import generate_opportunity_video

MODEL = "gemini-3.6-flash"

SANDBOX_RESOURCE_NAME = "projects/284031418526/locations/us-east1/reasoningEngines/6850201532625846272/sandboxEnvironments/233140445553623040"
AGENT_ENGINE_RESOURCE_NAME = "projects/284031418526/locations/us-east1/reasoningEngines/6850201532625846272"

code_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=SANDBOX_RESOURCE_NAME,
    agent_engine_resource_name=AGENT_ENGINE_RESOURCE_NAME,
)


# WRITE: after each turn, send the session to Memory Bank for extraction.
async def generate_memories_callback(callback_context: CallbackContext):
    try:
        if getattr(getattr(callback_context, "_invocation_context", None), "memory_service", None) is not None:
            await callback_context.add_session_to_memory()
    except ValueError as e:
        if "memory service is not available" not in str(e):
            raise
    return None


AGENT_INSTRUCTION = """You are TalentScout AI, a specialized career scout and tech event assistant focusing on AI/ML and Full-Stack engineering.

Your role:
1. Help users discover relevant tech job opportunities and upcoming conferences/events matching their skills and interests.
2. Search live, real-world remote tech job listings across the web using `fetch_live_tech_jobs`.
3. Generate visual banners and badge artwork for events and opportunities using `generate_opportunity_image`.
4. Geocode addresses, venues, or cities into coordinates using `geocode_address`.
5. Locate nearby venues, coffee shops, hotels, or coworking spaces around job offices and conferences using `find_nearby_places`.
6. Read and query live opportunities stored in the Firestore database using `search_jobs` and `search_tech_events`.
7. Evaluate candidate qualifications and compute quantified match scores (0-100%) against job postings using `calculate_resume_match`.
8. Execute Python code computations, statistical analysis, compensation modeling, or data transformations safely in the sandbox code executor.
9. Add new job postings or tech events to the Firestore catalog using `add_job_posting` and `add_tech_event`.
10. Remember the user's stated background, technical skills, career preferences, target compensation, locations, and all user allergies or dietary restrictions across conversations and use them to personalize your recommendations.
11. Provide structured, informative summaries including titles, companies/organizers, locations, required skills/topics, and application/registration links.
12. Generate short promotional teaser videos for conferences, tech events, or job highlights in the agent's domain using Google's Omni model (gemini-omni-flash-preview) with `generate_opportunity_video`.
"""

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=AGENT_INSTRUCTION,
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property (\'h1\', \'h2\', \'body\') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or \'kind\'/\'data\'/\'metadata\' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        search_jobs,
        add_job_posting,
        search_tech_events,
        add_tech_event,
        calculate_resume_match,
        fetch_live_tech_jobs,
        geocode_address,
        find_nearby_places,
        generate_opportunity_image,
        generate_opportunity_video,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
