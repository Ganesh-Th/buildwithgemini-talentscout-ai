"""Seed Firestore with initial job postings and tech events.

Hardcodes the GCP project ID string as required for Agent Platform.
"""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-70611c3d6bad"

SAMPLE_JOBS = [
    {
        "id": "job-gdm-001",
        "title": "Senior AI/ML Systems Engineer",
        "company": "Google DeepMind",
        "domain": "AI/ML",
        "location": "San Francisco, CA (Hybrid)",
        "skills": ["Python", "PyTorch", "JAX", "Distributed Training", "Ray"],
        "experience_level": "Senior",
        "salary_range": "$210,000 - $280,000",
        "description": "Design and optimize large-scale inference and training clusters for next-generation frontier models.",
        "apply_url": "https://deepmind.google/careers/senior-systems-engineer",
    },
    {
        "id": "job-stripe-002",
        "title": "Staff Full-Stack Engineer",
        "company": "Stripe",
        "domain": "Full-Stack",
        "location": "Seattle, WA / Remote",
        "skills": ["TypeScript", "React", "Node.js", "Python", "PostgreSQL", "GraphQL"],
        "experience_level": "Staff",
        "salary_range": "$195,000 - $265,000",
        "description": "Build resilient global payment dashboards and financial developer tooling used by millions of businesses.",
        "apply_url": "https://stripe.com/jobs/staff-fullstack",
    },
    {
        "id": "job-anthropic-003",
        "title": "Lead Agentic AI Engineer",
        "company": "Anthropic",
        "domain": "AI/ML",
        "location": "San Francisco, CA",
        "skills": ["Python", "LLM Evaluation", "Agentic Frameworks", "FastAPI", "Vector DBs"],
        "experience_level": "Lead",
        "salary_range": "$220,000 - $310,000",
        "description": "Create automated multi-agent benchmarks, evaluation pipelines, and tool execution harnesses.",
        "apply_url": "https://anthropic.com/careers/lead-agentic-engineer",
    },
    {
        "id": "job-vercel-004",
        "title": "Full-Stack AI Application Developer",
        "company": "Vercel",
        "domain": "Full-Stack",
        "location": "Remote (US)",
        "skills": ["Next.js", "TypeScript", "Tailwind CSS", "Python", "Gemini API"],
        "experience_level": "Mid-Senior",
        "salary_range": "$170,000 - $230,000",
        "description": "Deliver lightning-fast AI user interfaces and streaming frontend experiences on Edge Runtime.",
        "apply_url": "https://vercel.com/careers/fullstack-ai-developer",
    },
    {
        "id": "job-databricks-005",
        "title": "Machine Learning Platform Engineer",
        "company": "Databricks",
        "domain": "AI/ML",
        "location": "New York, NY (Hybrid)",
        "skills": ["MLflow", "Kubernetes", "Python", "Apache Spark", "Go"],
        "experience_level": "Senior",
        "salary_range": "$185,000 - $250,000",
        "description": "Scale MLOps infrastructure, model serving pipelines, and feature stores for enterprise enterprise customers.",
        "apply_url": "https://databricks.com/company/careers/ml-platform-engineer",
    },
]

SAMPLE_EVENTS = [
    {
        "id": "event-aiewf-2026",
        "title": "AI Engineer World's Fair 2026",
        "organizer": "AI Engineer Foundation",
        "domain": "AI/ML",
        "location": "San Francisco, CA & Virtual",
        "date": "2026-10-14",
        "topics": ["LLM Agents", "Reasoning Models", "Production ML", "A2A Protocol"],
        "description": "The largest gathering of engineers building software with foundation models and multi-agent systems.",
        "registration_url": "https://ai.engineer/worlds-fair",
    },
    {
        "id": "event-fullstack-2026",
        "title": "NextGen Full-Stack Summit 2026",
        "organizer": "O'Reilly Media",
        "domain": "Full-Stack",
        "location": "New York, NY",
        "date": "2026-11-05",
        "topics": ["Modern Web Architecture", "AI-Assisted Development", "Edge Computing", "TypeScript 6"],
        "description": "Deep-dive sessions on building, deploying, and scaling modern web applications with integrated AI.",
        "registration_url": "https://oreilly.com/nextgen-fullstack-2026",
    },
    {
        "id": "event-gemini-devday",
        "title": "Google Cloud Gemini Developer Day",
        "organizer": "Google Cloud",
        "domain": "AI/ML",
        "location": "Mountain View, CA & Global Stream",
        "date": "2026-10-28",
        "topics": ["Agent Platform", "Gemini 3.6", "ADK", "Multimodal Agents", "Vertex AI"],
        "description": "Hands-on keynotes, code labs, and demos showing how to build and scale production agents on Google Cloud.",
        "registration_url": "https://cloud.google.com/gemini-dev-day",
    },
    {
        "id": "event-agent-hack",
        "title": "Autonomous Agent Hackathon",
        "organizer": "SF Tech Collective",
        "domain": "Full-Stack",
        "location": "San Francisco, CA",
        "date": "2026-11-14",
        "topics": ["Autonomous Agents", "Human-in-the-Loop", "A2UI", "FastAPI"],
        "description": "A 48-hour collaborative build sprint pairing AI researchers and full-stack developers to ship live agents.",
        "registration_url": "https://sftechcollective.org/hackathon-2026",
    },
]


def seed():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)

    # Seed job postings
    jobs_col = db.collection("job_postings")
    print(f"Seeding {len(SAMPLE_JOBS)} job postings...")
    for job in SAMPLE_JOBS:
        doc_id = job["id"]
        jobs_col.document(doc_id).set(job)
        print(f"  ✓ Added job: {job['title']} at {job['company']}")

    # Seed tech events
    events_col = db.collection("tech_events")
    print(f"\nSeeding {len(SAMPLE_EVENTS)} tech events...")
    for event in SAMPLE_EVENTS:
        doc_id = event["id"]
        events_col.document(doc_id).set(event)
        print(f"  ✓ Added event: {event['title']} ({event['date']})")

    print("\n✅ Firestore successfully seeded!")


if __name__ == "__main__":
    seed()
