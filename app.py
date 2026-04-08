# app.py
import os
import json
import anthropic # type: ignore
from flask import Flask, render_template, request, jsonify # type: ignore
from dotenv import load_dotenv
from tools import load_jobs, filtering_tool, ranking_tool, resume_tailoring_tool # type: ignore

load_dotenv()

app = Flask(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "filtering_tool",
        "description": (
            "Filters the job dataset using rule-based logic. "
            "Keeps jobs that match the candidate's preferred location and "
            "that the candidate is reasonably qualified for (experience-wise). "
            "Call this FIRST to reduce the dataset before ranking."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate": {
                    "type": "object",
                    "properties": {
                        "skills": {"type": "array", "items": {"type": "string"}},
                        "location": {"type": "string"},
                        "years_of_experience": {"type": "number"},
                    },
                    "required": ["skills", "location", "years_of_experience"],
                }
            },
            "required": ["candidate"],
        },
    },
    {
        "name": "ranking_tool",
        "description": (
            "Scores and ranks the filtered jobs by skill alignment and experience fit. "
            "Call this AFTER filtering_tool to get a prioritized list. "
            "Returns ranked jobs with scores and the top job."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filtered_jobs": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "candidate": {
                    "type": "object",
                    "properties": {
                        "skills": {"type": "array", "items": {"type": "string"}},
                        "location": {"type": "string"},
                        "years_of_experience": {"type": "number"},
                    },
                    "required": ["skills", "location", "years_of_experience"],
                },
            },
            "required": ["filtered_jobs", "candidate"],
        },
    },
    {
        "name": "resume_tailoring_tool",
        "description": (
            "Prepares context for tailoring the candidate's resume to the top job. "
            "Call this LAST after you have identified the best job."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "top_job": {"type": "object"},
                "candidate": {"type": "object"},
                "original_summary": {"type": "string"},
                "original_bullets": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["top_job", "candidate", "original_summary", "original_bullets"],
        },
    },
]


def run_agent(candidate, original_summary, original_bullets):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    MODEL = "claude-sonnet-4-20250514"

    jobs = load_jobs(candidate)

    filtered_jobs_store = []
    top_job_store = {}
    ranked_jobs_store = []

    system_prompt = """You are an intelligent job search assistant agent. Your job is to:
1. Analyze the candidate's profile carefully
2. Call the filtering_tool to remove irrelevant jobs
3. Call the ranking_tool on the filtered results to find the best matches
4. Identify the single best job for the candidate and explain your reasoning
5. Call the resume_tailoring_tool to prepare tailoring context
6. Generate a tailored resume summary AND rewrite two improved bullet points

Always explain your reasoning at each step. Be specific about WHY you're making each decision.
After all tools are called, provide:
- The #1 recommended job and why
- A rewritten resume summary (3-4 sentences, tailored to the job)
- Two improved experience bullet points (use strong action verbs, quantify where possible)"""

    user_message = f"""Please help me find the best job match and tailor my resume.

Candidate Profile:
- Skills: {', '.join(candidate['skills'])}
- Preferred Location: {candidate['location']}
- Years of Experience: {candidate['years_of_experience']}

Original Resume Summary:
{original_summary}

Original Bullet Points to Improve:
1. {original_bullets[0]}
2. {original_bullets[1]}

Start by filtering the {len(jobs)} available jobs, then rank them, then tailor my resume for the best match."""

    messages = [{"role": "user", "content": user_message}]
    final_reasoning = ""

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=8096,
            system=system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        for block in response.content:
            if hasattr(block, "text") and block.text:
                final_reasoning = block.text

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason in ("tool_use", "max_tokens"):
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = dict(block.input)

                    if tool_name == "filtering_tool":
                        result = filtering_tool(jobs, tool_input.get("candidate", candidate))
                        filtered_jobs_store = result.get("filtered_jobs", jobs)

                    elif tool_name == "ranking_tool":
                        filtered = tool_input.get("filtered_jobs", filtered_jobs_store)
                        cand = tool_input.get("candidate", candidate)
                        result = ranking_tool(filtered, cand)
                        ranked_jobs_store = result.get("ranked_jobs", [])
                        if result.get("top_job"):
                            top_job_store = result["top_job"]

                    elif tool_name == "resume_tailoring_tool":
                        top_job = tool_input.get("top_job", top_job_store)
                        cand = tool_input.get("candidate", candidate)
                        result = resume_tailoring_tool(
                            top_job, cand,
                            tool_input.get("original_summary", original_summary),
                            tool_input.get("original_bullets", original_bullets),
                        )
                    else:
                        result = {"error": f"Unknown tool: {tool_name}"}

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, indent=2),
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return {
        "top_job": top_job_store,
        "ranked_jobs": ranked_jobs_store[:10],
        "final_reasoning": final_reasoning,
        "total_jobs_fetched": len(jobs),
        "total_filtered": len(filtered_jobs_store),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def run():
    data = request.json
    candidate = {
        "skills": [s.strip() for s in data.get("skills", "").split(",") if s.strip()],
        "location": data.get("location", "remote"),
        "years_of_experience": int(data.get("years_of_experience", 3)),
    }
    original_summary = data.get("summary", "")
    original_bullets = [data.get("bullet1", ""), data.get("bullet2", "")]

    try:
        result = run_agent(candidate, original_summary, original_bullets)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
