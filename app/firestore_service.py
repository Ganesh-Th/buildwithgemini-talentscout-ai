"""Firestore backend for TalentScout AI.

Hardcodes the GCP project ID string as required for Agent Platform.
"""

from typing import Any
import uuid
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-70611c3d6bad"

_db = None


def get_firestore_client() -> firestore.Client:
    """Returns a singleton Firestore client with hardcoded project ID."""
    global _db
    if _db is None:
        _db = firestore.Client(project=PROJECT_ID)
    return _db


def search_jobs(
    query: str = "",
    domain: str = "",
    location: str = "",
) -> list[dict[str, Any]]:
    """Search job postings stored in Firestore.

    Args:
        query: Keywords to match against job title, company, description, or required skills (e.g. 'Python', 'Staff', 'AI').
        domain: Filter by domain, e.g. 'AI/ML' or 'Full-Stack'.
        location: Filter or match by location, e.g. 'San Francisco', 'Remote', 'New York'.

    Returns:
        A list of matching job posting dictionaries.
    """
    db = get_firestore_client()
    docs = db.collection("job_postings").stream()

    results = []
    q_lower = query.strip().lower()
    domain_lower = domain.strip().lower()
    loc_lower = location.strip().lower()

    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id

        # Domain filter
        if domain_lower and domain_lower not in data.get("domain", "").lower():
            continue

        # Location filter
        if loc_lower and loc_lower not in data.get("location", "").lower():
            continue

        # Query keywords match across title, company, description, skills
        if q_lower:
            searchable = " ".join([
                data.get("title", ""),
                data.get("company", ""),
                data.get("description", ""),
                " ".join(data.get("skills", [])),
            ]).lower()
            if q_lower not in searchable:
                continue

        results.append(data)

    return results


def add_job_posting(
    title: str,
    company: str,
    domain: str,
    location: str,
    skills: list[str],
    salary_range: str = "",
    experience_level: str = "Mid-Senior",
    description: str = "",
    apply_url: str = "",
) -> dict[str, Any]:
    """Add a new job posting to Firestore.

    Args:
        title: Title of the position (e.g. 'Machine Learning Research Engineer').
        company: Hiring company or organization (e.g. 'Google DeepMind').
        domain: Target technical domain, typically 'AI/ML' or 'Full-Stack'.
        location: Work location or arrangement (e.g. 'San Francisco, CA (Hybrid)' or 'Remote').
        skills: List of required or preferred skills (e.g. ['Python', 'JAX', 'Distributed Systems']).
        salary_range: Estimated compensation range (e.g. '$190,000 - $250,000').
        experience_level: Seniority level (e.g. 'Junior', 'Mid-Level', 'Senior', 'Staff', 'Lead').
        description: Brief overview of the responsibilities and role.
        apply_url: URL link where candidate can apply.

    Returns:
        A dictionary confirming the created job posting with its ID.
    """
    db = get_firestore_client()
    doc_id = f"job-{uuid.uuid4().hex[:8]}"

    job_data = {
        "id": doc_id,
        "title": title,
        "company": company,
        "domain": domain,
        "location": location,
        "skills": skills,
        "salary_range": salary_range,
        "experience_level": experience_level,
        "description": description,
        "apply_url": apply_url,
    }

    db.collection("job_postings").document(doc_id).set(job_data)
    return {"status": "success", "message": f"Job posting '{title}' at {company} created successfully.", "job": job_data}


def search_tech_events(
    query: str = "",
    domain: str = "",
    location: str = "",
) -> list[dict[str, Any]]:
    """Search tech events and conferences stored in Firestore.

    Args:
        query: Keywords to match against event title, organizer, topics, or description (e.g. 'Agents', 'Web', 'Hackathon').
        domain: Filter by domain, e.g. 'AI/ML' or 'Full-Stack'.
        location: Filter or match by location, e.g. 'San Francisco', 'Virtual', 'New York'.

    Returns:
        A list of matching tech event dictionaries.
    """
    db = get_firestore_client()
    docs = db.collection("tech_events").stream()

    results = []
    q_lower = query.strip().lower()
    domain_lower = domain.strip().lower()
    loc_lower = location.strip().lower()

    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id

        # Domain filter
        if domain_lower and domain_lower not in data.get("domain", "").lower():
            continue

        # Location filter
        if loc_lower and loc_lower not in data.get("location", "").lower():
            continue

        # Query keywords match across title, organizer, topics, description
        if q_lower:
            searchable = " ".join([
                data.get("title", ""),
                data.get("organizer", ""),
                data.get("description", ""),
                " ".join(data.get("topics", [])),
            ]).lower()
            if q_lower not in searchable:
                continue

        results.append(data)

    return results


def add_tech_event(
    title: str,
    organizer: str,
    domain: str,
    date: str,
    location: str,
    topics: list[str],
    description: str = "",
    registration_url: str = "",
) -> dict[str, Any]:
    """Add a new tech event or conference to Firestore.

    Args:
        title: Name of the event (e.g. 'AI World Fair 2026').
        organizer: Host or organizing entity (e.g. 'AI Foundation').
        domain: Target technical domain, typically 'AI/ML' or 'Full-Stack'.
        date: Event date in YYYY-MM-DD format (e.g. '2026-10-15').
        location: City/venue or 'Virtual'.
        topics: List of topic tags (e.g. ['Agents', 'LLMs', 'Evaluation']).
        description: Summary of the event agenda and highlights.
        registration_url: Link to register or buy tickets.

    Returns:
        A dictionary confirming the created tech event with its ID.
    """
    db = get_firestore_client()
    doc_id = f"event-{uuid.uuid4().hex[:8]}"

    event_data = {
        "id": doc_id,
        "title": title,
        "organizer": organizer,
        "domain": domain,
        "date": date,
        "location": location,
        "topics": topics,
        "description": description,
        "registration_url": registration_url,
    }

    db.collection("tech_events").document(doc_id).set(event_data)
    return {"status": "success", "message": f"Tech event '{title}' created successfully.", "event": event_data}


def calculate_resume_match(
    candidate_skills: list[str],
    job_id: str = "",
    required_skills: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate the match percentage and skill gap between candidate skills and job requirements.

    Args:
        candidate_skills: List of skills, languages, and tools the candidate has (e.g. ['Python', 'PyTorch', 'FastAPI']).
        job_id: Optional ID of a job posting in Firestore (e.g. 'job-gdm-001'). If provided, its required skills and title are used.
        required_skills: Optional list of target skills to compare against if job_id is not provided.

    Returns:
        A dictionary with match_score (0-100), matched_skills, missing_skills, and recommendation verdict.
    """
    target_skills: list[str] = []
    job_title = "Custom Role"

    if job_id:
        db = get_firestore_client()
        doc = db.collection("job_postings").document(job_id).get()
        if doc.exists:
            data = doc.to_dict() or {}
            target_skills = data.get("skills", [])
            job_title = f"{data.get('title', 'Role')} at {data.get('company', 'Company')}"

    if not target_skills and required_skills:
        target_skills = required_skills

    if not target_skills:
        return {
            "job": job_title,
            "match_score": 0,
            "matched_skills": [],
            "missing_skills": [],
            "verdict": "No target skills provided or job posting not found.",
        }

    cand_set = {s.strip().lower() for s in candidate_skills if s.strip()}
    matched = []
    missing = []

    for req in target_skills:
        req_norm = req.strip().lower()
        if any(req_norm in c or c in req_norm for c in cand_set):
            matched.append(req)
        else:
            missing.append(req)

    score = int(round((len(matched) / len(target_skills)) * 100))

    if score >= 80:
        verdict = "Strong Match — High likelihood of interview alignment"
    elif score >= 50:
        verdict = "Good Match — Relevant background with minor skill gaps to address"
    else:
        verdict = "Stretch Opportunity — Significant skill gaps required"

    return {
        "job": job_title,
        "match_score": score,
        "matched_skills": matched,
        "missing_skills": missing,
        "verdict": verdict,
    }

