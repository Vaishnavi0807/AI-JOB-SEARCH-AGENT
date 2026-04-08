# job_fetcher.py
import os
import requests
import time

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"

# Search queries covering AI/ML, Data Science, and Software Engineering
SEARCH_QUERIES = [
    "machine learning engineer",
    "AI engineer",
    "data scientist",
    "NLP engineer",
    "MLOps engineer",
    "deep learning engineer",
    "software engineer machine learning",
    "computer vision engineer",
    "data engineer",
    "applied scientist",
]


def fetch_jobs_from_adzuna(
    country: str = "us",
    results_per_query: int = 3,
    location: str = None,
) -> list[dict]:
    """
    Fetches AI/ML/Data Science/SWE jobs from Adzuna API.
    Runs multiple search queries to get diverse results.
    Returns a list of normalized job dicts (20-30 jobs).

    Args:
        country: Country code ('us', 'gb', 'ca', 'au')
        results_per_query: How many results per search query
        location: Optional location filter e.g. "New York"
    """
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")

    if not app_id or not app_key:
        raise ValueError("ADZUNA_APP_ID and ADZUNA_APP_KEY must be set in .env")

    all_jobs = []
    seen_ids = set()  # deduplicate by Adzuna job ID

    print(f"🌐 Fetching live jobs from Adzuna API...")

    for query in SEARCH_QUERIES:
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": results_per_query,
            "what": query,
            "content-type": "application/json",
            "sort_by": "relevance",
        }

        # Optional location filter
        if location:
            params["where"] = location

        url = f"{ADZUNA_BASE}/{country}/search/1"

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            for job in results:
                job_id = job.get("id", "")
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                # Normalize to our standard format
                normalized = normalize_job(job, query)
                if normalized:
                    all_jobs.append(normalized)

            print(f"   ✓ '{query}' → {len(results)} results")

        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  Failed to fetch '{query}': {e}")

        # Be polite to the API
        time.sleep(0.3)

    print(f"\n✅ Total unique jobs fetched: {len(all_jobs)}\n")
    return all_jobs


def normalize_job(raw: dict, search_query: str) -> dict | None:
    """
    Converts a raw Adzuna job dict into our standard format.
    Extracts skills from the description using keyword matching.
    """
    title = raw.get("title", "").strip()
    company = raw.get("company", {}).get("display_name", "Unknown Company")
    location = raw.get("location", {}).get("display_name", "Remote")
    description = raw.get("description", "").strip()
    url = raw.get("redirect_url", "")

    if not title or not description:
        return None

    # Shorten description to ~6 lines (first 600 chars)
    short_desc = description[:600].replace("\n", " ").strip()
    if len(description) > 600:
        short_desc += "..."

    # Extract skills by scanning description for known tech keywords
    detected_skills = extract_skills_from_text(description + " " + title)

    # Infer experience from description
    years_required = extract_experience_years(description)

    return {
        "Job Title": title,
        "Company": company,
        "Location": location,
        "Required Skills": ", ".join(detected_skills) if detected_skills else "Python, Machine Learning",
        "Years of Experience Required": years_required,
        "Job Description": short_desc,
        "URL": url,
        "Search Query": search_query,  # helpful for debugging
    }


# ── Skill extraction ─────────────────────────────────────────────────────────

SKILL_KEYWORDS = [
    # Languages
    "python", "r", "scala", "java", "c++", "sql", "javascript", "typescript",
    "swift", "kotlin", "go", "rust", "bash",
    # ML / AI frameworks
    "pytorch", "tensorflow", "keras", "jax", "sklearn", "scikit-learn",
    "huggingface", "transformers", "langchain", "llama", "openai",
    "xgboost", "lightgbm", "catboost",
    # Specific domains
    "nlp", "computer vision", "deep learning", "machine learning", "reinforcement learning",
    "llm", "llms", "rlhf", "fine-tuning", "retrieval", "rag",
    "recommendation systems", "time series", "forecasting",
    # MLOps / Infra
    "mlflow", "kubeflow", "airflow", "dbt", "spark", "kafka",
    "docker", "kubernetes", "terraform", "aws", "gcp", "azure",
    "ci/cd", "git", "linux",
    # Data
    "pandas", "numpy", "dask", "hadoop", "bigquery", "snowflake",
    "databricks", "redshift", "s3",
    # Other
    "api", "rest", "graphql", "microservices", "distributed systems",
    "statistics", "probability", "a/b testing", "experiment design",
    "cuda", "gpu", "opencv", "mlops",
]


def extract_skills_from_text(text: str) -> list[str]:
    """Scan text for known skill keywords (case-insensitive)."""
    text_lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        if skill in text_lower and skill not in found:
            found.append(skill)
    # Return top 8 most relevant skills to keep it concise
    return found[:8]


def extract_experience_years(text: str) -> int:
    """Try to extract years of experience requirement from job description."""
    import re
    # Match patterns like "3+ years", "2-4 years", "at least 5 years"
    patterns = [
        r"(\d+)\+?\s*years?\s*of\s*experience",
        r"(\d+)\+?\s*years?\s*experience",
        r"minimum\s*(\d+)\s*years?",
        r"at\s*least\s*(\d+)\s*years?",
        r"(\d+)\s*-\s*\d+\s*years?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))
    return 2  # default if not found