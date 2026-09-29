"""External Public Job & Opportunity API integrations for TalentScout AI.

Fetches live tech job opportunities from verified, legitimate public job platforms:
1. Remotive Jobs API (free, verified global remote tech job listings)
2. Jobicy API (free, verified regional/remote tech jobs by geo)
3. Arbeitnow API (free, verified global and localized tech job board)
"""

import json
import os
import urllib.parse
import urllib.request
from typing import Any


def fetch_live_tech_jobs(
    query: str = "software engineer",
    location: str = "",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Fetch live tech job postings from verified public job APIs with location filtering.

    Args:
        query: Tech stack, skills, or role to search for (e.g. 'python', 'ai', 'full stack', 'react').
        location: Candidate location or preferred region (e.g. 'California', 'USA', 'Germany', 'Remote', 'APAC', 'EMEA').
        limit: Maximum number of job postings to return (defaults to 5).

    Returns:
        A list of live job postings with title, company, location, tags, salary, and application URL.
    """
    results: list[dict[str, Any]] = []
    location_clean = location.strip().lower()

    # 1. Remotive API query
    try:
        search_terms = f"{query} {location}".strip() if location else query
        params = {"search": search_terms, "limit": str(limit * 2)}
        url = f"https://remotive.com/api/remote-jobs?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "TalentScout-AI/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
            jobs = payload.get("jobs", [])
            for j in jobs:
                job_loc = j.get("candidate_required_location", "Remote")
                if location_clean and location_clean not in job_loc.lower() and "anywhere" not in job_loc.lower() and "remote" not in job_loc.lower():
                    continue
                results.append({
                    "title": j.get("title", ""),
                    "company": j.get("company_name", ""),
                    "location": job_loc,
                    "tags": j.get("tags", []),
                    "salary": j.get("salary") or "Competitive / Not specified",
                    "url": j.get("url", ""),
                    "source": "Remotive API",
                })
                if len(results) >= limit:
                    break
    except Exception as e:
        pass

    # 2. Jobicy API (if more jobs needed or specific geo requested)
    if len(results) < limit:
        try:
            geo_param = ""
            if any(k in location_clean for k in ["us", "usa", "united states", "california", "new york", "texas"]):
                geo_param = "usa"
            elif any(k in location_clean for k in ["uk", "united kingdom", "london"]):
                geo_param = "uk"
            elif any(k in location_clean for k in ["europe", "germany", "france", "emea"]):
                geo_param = "emea"
            elif any(k in location_clean for k in ["asia", "india", "singapore", "japan", "apac"]):
                geo_param = "apac"

            jobicy_params = {"count": str(limit)}
            if geo_param:
                jobicy_params["geo"] = geo_param
            if query:
                jobicy_params["tag"] = query.split()[0]
                
            url = f"https://jobicy.com/api/v2/remote-jobs?{urllib.parse.urlencode(jobicy_params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "TalentScout-AI/1.0"})
            with urllib.request.urlopen(req, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
                jobs = payload.get("jobs", [])
                for j in jobs:
                    job_loc = j.get("jobGeo", "Remote")
                    results.append({
                        "title": j.get("jobTitle", ""),
                        "company": j.get("companyName", ""),
                        "location": job_loc,
                        "tags": [j.get("jobCategory", "Tech")],
                        "salary": j.get("annualSalaryMin") and f"${j.get('annualSalaryMin'):,} - ${j.get('annualSalaryMax'):,}" or "Competitive",
                        "url": j.get("url", ""),
                        "source": "Jobicy API",
                    })
                    if len(results) >= limit:
                        break
        except Exception as e:
            pass

    # 3. Arbeitnow API (if still needed)
    if len(results) < limit:
        try:
            url = "https://www.arbeitnow.com/api/job-board-api"
            req = urllib.request.Request(url, headers={"User-Agent": "TalentScout-AI/1.0"})
            with urllib.request.urlopen(req, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
                for j in payload.get("data", []):
                    title = j.get("title", "")
                    job_loc = j.get("location", "Remote")
                    # Check keyword match
                    if query.lower() in title.lower() or any(t.lower() in title.lower() for t in query.split()):
                        if not location_clean or location_clean in job_loc.lower():
                            results.append({
                                "title": title,
                                "company": j.get("company_name", ""),
                                "location": job_loc,
                                "tags": j.get("tags", []),
                                "salary": "Competitive / Per posting",
                                "url": j.get("url", ""),
                                "source": "Arbeitnow API",
                            })
                            if len(results) >= limit:
                                break
        except Exception as e:
            pass

    return results[:limit]
