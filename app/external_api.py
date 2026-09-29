"""External Public API integration for TalentScout AI.

Fetches live tech job opportunities from the free public Remotive Jobs API
(listed in the public-apis directory).
"""

import json
import os
import urllib.parse
import urllib.request
from typing import Any


def fetch_live_tech_jobs(
    query: str = "software engineer",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Fetch live remote tech and developer job postings from the public Remotive Jobs API.

    Args:
        query: Tech stack or keywords to search for (e.g. 'python', 'ai', 'full stack', 'react').
        limit: Maximum number of job postings to return (defaults to 5).

    Returns:
        A list of live job postings with title, company, location, tags, salary, and application URL.
    """
    # Read optional API key from environment variable if configured
    api_key = os.getenv("REMOTIVE_API_KEY", "")
    params = {"search": query, "limit": str(limit)}
    url = f"https://remotive.com/api/remote-jobs?{urllib.parse.urlencode(params)}"

    headers = {"User-Agent": "TalentScout-AI/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
            jobs = payload.get("jobs", [])
            results = []
            for j in jobs[:limit]:
                results.append({
                    "title": j.get("title", ""),
                    "company": j.get("company_name", ""),
                    "location": j.get("candidate_required_location", "Remote"),
                    "tags": j.get("tags", []),
                    "salary": j.get("salary") or "Competitive / Not specified",
                    "url": j.get("url", ""),
                    "source": "Remotive Public API",
                })
            return results
    except Exception as e:
        return [{"error": f"Failed to fetch live tech jobs: {str(e)}"}]
