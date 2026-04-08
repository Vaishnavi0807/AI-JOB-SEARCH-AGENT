# tools.py
import pandas as pd
import json
from job_fetcher import fetch_jobs_from_adzuna


def load_jobs(candidate: dict = None) -> list[dict]:
    """
    Fetch live jobs from Adzuna API.
    Uses candidate's preferred location to focus results.
    """
    location = None
    if candidate:
        loc = candidate.get("location", "").lower()
        # Don't pass "remote" as location filter — Adzuna handles remote differently
        if loc and loc != "remote":
            location = loc

    jobs = fetch_jobs_from_adzuna(
        country="us",
        results_per_query=3,   # 3 results × 10 queries = ~25-30 unique jobs
        location=location,
    )
    return jobs


def filtering_tool(jobs: list[dict], candidate: dict) -> dict:
    """
    Rule-based filtering tool.
    Filters jobs by location preference and experience gap.
    """
    filtered = []
    removed = []

    preferred_location = candidate.get("location", "").lower()
    candidate_years = candidate.get("years_of_experience", 0)

    for job in jobs:
        reasons_removed = []

        job_location = job.get("Location", "").lower()
        location_ok = (
            "remote" in job_location
            or preferred_location in job_location
            or preferred_location == "remote"
            or preferred_location == ""
        )
        if not location_ok:
            reasons_removed.append(f"Location mismatch: {job['Location']}")

        try:
            required_years = float(job.get("Years of Experience Required", 0))
        except (ValueError, TypeError):
            required_years = 0

        experience_ok = candidate_years >= required_years * 0.8
        if not experience_ok:
            reasons_removed.append(
                f"Experience gap: needs {required_years} yrs, candidate has {candidate_years}"
            )

        if location_ok and experience_ok:
            filtered.append(job)
        else:
            removed.append({
                "job": job["Job Title"],
                "company": job["Company"],
                "reasons": reasons_removed,
            })

    return {
        "filtered_jobs": filtered,
        "total_before": len(jobs),
        "total_after": len(filtered),
        "removed_count": len(removed),
        "removed_sample": removed[:5],
    }


def ranking_tool(filtered_jobs: list[dict], candidate: dict) -> dict:
    """
    Scores and ranks jobs based on skill alignment and experience fit.
    Skill match: up to 70 pts | Experience fit: up to 30 pts
    """
    candidate_skills = [s.strip().lower() for s in candidate.get("skills", []) if s]
    candidate_years = candidate.get("years_of_experience", 0)

    ranked = []

    for job in filtered_jobs:
        raw_skills = job.get("Required Skills", "")
        required_skills = [s.strip().lower() for s in str(raw_skills).split(",") if s]

        if required_skills:
            matched = [s for s in required_skills if any(c in s or s in c for c in candidate_skills)]
            skill_score = (len(matched) / len(required_skills)) * 70
        else:
            matched = []
            skill_score = 35

        try:
            required_years = float(job.get("Years of Experience Required", 0))
        except (ValueError, TypeError):
            required_years = 0

        if required_years == 0:
            exp_score = 30
        else:
            gap = candidate_years - required_years
            exp_score = max(20, 30 - gap * 2) if gap >= 0 else max(0, 30 + gap * 10)

        total_score = round(skill_score + exp_score, 2)

        ranked.append({
            **job,
            "score": total_score,
            "skill_score": round(skill_score, 2),
            "exp_score": round(exp_score, 2),
            "matched_skills": matched,
            "match_rate": f"{len(matched)}/{len(required_skills)}" if required_skills else "N/A",
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)

    return {
        "ranked_jobs": ranked,
        "top_job": ranked[0] if ranked else None,
        "total_ranked": len(ranked),
    }


def resume_tailoring_tool(
    top_job: dict,
    candidate: dict,
    original_summary: str,
    original_bullets: list[str],
) -> dict:
    """Prepares context for the LLM to tailor the resume."""
    return {
        "job_title": top_job.get("Job Title", ""),
        "company": top_job.get("Company", ""),
        "required_skills": top_job.get("Required Skills", ""),
        "job_description": top_job.get("Job Description", ""),
        "candidate_skills": candidate.get("skills", []),
        "candidate_years": candidate.get("years_of_experience", 0),
        "original_summary": original_summary,
        "original_bullets": original_bullets,
        "matched_skills": top_job.get("matched_skills", []),
    }