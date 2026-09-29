# TalentScout AI

> An autonomous career scout and tech event assistant specialized in AI/ML and Full-Stack engineering, built with Google's Agent Development Kit (ADK) and deployed on Google Cloud.

![TalentScout AI Demo](demo.gif)

---

## Overview

**TalentScout AI** helps software engineers, researchers, and tech professionals navigate the rapidly evolving AI/ML landscape. It discovers live remote job opportunities, queries curated databases of tech conferences, evaluates resume-to-job match percentages, finds venues around conferences, remembers user preferences across sessions, and generates custom multimodal visual media (promotional banners and teaser videos).

---

## Implemented Capabilities & Tools

Every capability listed below is implemented in this repository and wired to live tools in `app/`:

| Capability | Implementing Tool / Module | Description |
|---|---|---|
| **Live Remote Job Search** | `fetch_live_tech_jobs` (`app/external_api.py`) | Queries live engineering job postings across the web via the Remotive Jobs API with location, tag, and seniority filtering. |
| **Curated Job Catalog** | `search_jobs`, `add_job_posting` (`app/firestore_service.py`) | Searches and manages structured job listings in Google Cloud Firestore. |
| **Tech Conferences & Events** | `search_tech_events`, `add_tech_event` (`app/firestore_service.py`) | Discovers upcoming AI summits, hackathons, and developer conferences stored in Firestore. |
| **Resume & Skill Match Analysis** | `calculate_resume_match` (`app/firestore_service.py`) | Compares candidate skills against job requirements, calculating quantified match percentages, matching skills, and missing prerequisites. |
| **Secure Code Execution** | `AgentEngineSandboxCodeExecutor` (`app/agent.py`) | Safely executes Python code in an isolated Vertex AI Agent Engine Sandbox environment for compensation modeling, statistical analysis, and data transformation. |
| **Location & Venue Discovery** | `geocode_address`, `find_nearby_places` (`app/maps_service.py`) | Resolves venue locations with Google Maps Geocoding API and discovers nearby coffee shops, coworking spaces, and hotels with Google Maps Places API. |
| **Multimodal Image Generation** | `generate_opportunity_image` (`app/image_service.py`) | Uses `gemini-3.1-flash-lite-image` to generate promotional banners and event artwork, directly uploading bytes to Google Cloud Storage and returning a public HTTPS URL. |
| **Multimodal Video Generation** | `generate_opportunity_video` (`app/video_service.py`) | Uses Google's Omni model (`gemini-omni-flash-preview`) in the `global` region to produce promotional teaser videos, saving artifacts to the ADK session panel and uploading bytes to Google Cloud Storage. |
| **Cross-Session Long-Term Memory** | `PreloadMemoryTool`, `generate_memories_callback` (`app/agent.py`) | Persists candidate preferences, technical background, career goals, and dietary restrictions/allergies across conversations using Vertex AI Memory Bank. |
| **Rich A2UI Card Rendering** | `A2uiSchemaManager`, `a2ui_callback` (`app/a2ui_utils.py`) | Emits structured A2UI v0.8 Basic Catalog components (Cards, Columns, Rows, Text, Images) for clean visual presentation in chat interfaces. |

### Planned / Not Yet Implemented

The following features were outlined during initial brainstorming but are not yet implemented in the codebase:
- **Automated Email Dispatcher (`send_digest_email`)**: Direct email delivery of customized job digests (*planned, not yet implemented*).
- **Scheduled Background Digest Triggering**: Cloud Scheduler cron trigger for automated daily/weekly scans (*planned, not yet implemented*).

---

## Google Cloud Architecture & Services

- **Reasoning Model**: Google Gemini (`gemini-3.6-flash`) for multi-step reasoning, tool orchestration, and A2UI generation.
- **Agent Platform / Runtime**: Deployed via `agents-cli` to Vertex AI Agent Runtime with A2A (Agent-to-Agent) protocol support.
- **Vertex AI Memory Bank**: Managed memory service maintaining cross-session user context and personalized attributes.
- **Vertex AI Code Sandbox**: Isolated container sandbox environment for executing arbitrary Python computations.
- **Google Cloud Firestore**: Scalable NoSQL document database indexing jobs, events, and skill requirements.
- **Google Cloud Storage**: Public bucket hosting generated banners, event graphics, and video teasers.
- **Google Maps Platform**: Geocoding and Places API integration for physical event and office location discovery.
- **Cloud Run**: Hosts the custom chat web interface and FastAPI reverse proxy communicating with Agent Engine via A2A.

---

## Project Structure

```
talentscout-ai/
├── app/
│   ├── agent.py               # Root agent definition, system prompt, and tool registration
│   ├── a2ui_utils.py          # A2UI callback and schema integration for rich UI cards
│   ├── firestore_service.py   # Firestore queries for jobs, events, and resume matching
│   ├── external_api.py        # Live job search via Remotive API
│   ├── maps_service.py        # Google Maps Geocoding and Places integration
│   ├── image_service.py       # Gemini image generation and Cloud Storage upload
│   ├── video_service.py       # Gemini Omni video generation, artifact saving, and GCS upload
│   ├── fast_api_app.py        # ADK FastAPI backend wrapper
│   └── app_utils/             # Initialization and helper utilities
├── frontend/
│   ├── main.py                # FastAPI proxy connecting browser to deployed agent over A2A
│   ├── Dockerfile             # Container definition for Cloud Run deployment
│   ├── requirements.txt       # Frontend proxy dependencies
│   └── static/
│       └── index.html         # Custom chat UI with A2UI renderer and prompt chips
├── agents-cli-manifest.yaml   # Agent Platform deployment metadata
├── pyproject.toml             # Python dependencies and project settings
├── demo.gif                   # Looping walkthrough recording
└── README.md
```

---

## Setup and Local Development

### 1. Prerequisites

- Python 3.11+
- [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install)
- `agents-cli`:
  ```bash
  uv tool install google-agents-cli
  ```

### 2. Environment Configuration

Authenticate with Google Cloud and configure project settings:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project <YOUR_GCP_PROJECT_ID>
```

Set the Google Maps API key if testing location services:

```bash
export GOOGLE_MAPS_API_KEY="<YOUR_MAPS_API_KEY>"
```

### 3. Install Dependencies

Install the project dependencies using `agents-cli` or `pip`:

```bash
agents-cli install
# or: pip install -e .
```

### 4. Run the Agent Locally

Launch the ADK development playground to interact with the agent:

```bash
agents-cli playground
```

### 5. Run the Custom Web Frontend Locally

To run the custom chat interface and FastAPI proxy locally:

```bash
cd frontend
pip install -r requirements.txt

export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/<REGION>/reasoningEngines/<ENGINE_ID>"
export AGENT_DIRECTORY="app"
export PORT=8080

python main.py
```

Open a browser to the local port displayed in the console to test the chat interface.

---

## Deployment

### Deploy Agent to Agent Runtime

Deploy the agent logic, tools, and callbacks to Vertex AI Agent Platform:

```bash
agents-cli deploy --update-env-vars GOOGLE_MAPS_API_KEY="<YOUR_MAPS_API_KEY>"
```

### Deploy Frontend to Cloud Run

Build and deploy the chat frontend to Cloud Run:

```bash
cd frontend
gcloud run deploy talentscout-frontend \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="<YOUR_AGENT_RESOURCE_NAME>",AGENT_DIRECTORY="app"
```

Ensure the Cloud Run service account has `roles/aiplatform.user` permissions so it can query the deployed agent over A2A.
