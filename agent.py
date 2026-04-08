# agent.py
import os
import json
import anthropic # type: ignore
from dotenv import load_dotenv
from tools import load_jobs, filtering_tool, ranking_tool, resume_tailoring_tool # type: ignore

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-20250514"

# ── Tool schemas for Claude ──────────────────────────────────────────────────

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
                    "description": "Candidate profile with skills, location, years_of_experience",
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
                    "description": "List of job dicts from filtering_tool output",
                    "items": {"type": "object"},
                },
                "candidate": {
                    "type": "object",
                    "description": "Candidate profile",
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
            "Call this LAST after you have identified the best job. "
            "Provide the top job dict, candidate profile, original resume summary, "
            "and two bullet points to improve."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "top_job": {"type": "object", "description": "The best job dict from ranking_tool"},
                "candidate": {"type": "object", "description": "Candidate profile"},
                "original_summary": {"type": "string", "description": "Current resume summary paragraph"},
                "original_bullets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Two experience bullet points to improve",
                },
            },
            "required": ["top_job", "candidate", "original_summary", "original_bullets"],
        },
    },
]


# ── Tool dispatcher ──────────────────────────────────────────────────────────

def dispatch_tool(tool_name: str, tool_input: dict, jobs: list[dict]) -> str:
    """Execute the requested tool and return result as JSON string."""
    print(f"\n🔧 Executing tool: {tool_name}")

    if tool_name == "filtering_tool":
        result = filtering_tool(jobs, tool_input["candidate"])
        # Save filtered jobs for use in ranking step
        dispatch_tool.filtered_jobs = result.get("filtered_jobs", jobs)
        dispatch_tool.last_candidate = tool_input["candidate"]

    elif tool_name == "ranking_tool":
        # Use filtered jobs from previous step if not provided
        filtered = tool_input.get("filtered_jobs", getattr(dispatch_tool, "filtered_jobs", jobs))
        candidate = tool_input.get("candidate", getattr(dispatch_tool, "last_candidate", {}))
        result = ranking_tool(filtered, candidate)
        # Save top job for resume tailoring step
        if result.get("top_job"):
            dispatch_tool.top_job = result["top_job"]

    elif tool_name == "resume_tailoring_tool":
        # Use top job from previous step if not provided
        top_job = tool_input.get("top_job", getattr(dispatch_tool, "top_job", {}))
        candidate = tool_input.get("candidate", getattr(dispatch_tool, "last_candidate", {}))
        result = resume_tailoring_tool(
            top_job,
            candidate,
            tool_input.get("original_summary", ""),
            tool_input.get("original_bullets", ["", ""]),
        )

    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    # Print summary
    if tool_name == "filtering_tool":
        print(f"   ✓ Filtered: {result['total_before']} → {result['total_after']} jobs")
    elif tool_name == "ranking_tool":
        top = result.get("top_job", {})
        print(f"   ✓ Ranked {result['total_ranked']} jobs")
        if top:
            print(f"   ✓ Top job: {top.get('Job Title')} @ {top.get('Company')} (score: {top.get('score')})")
    elif tool_name == "resume_tailoring_tool":
        print(f"   ✓ Tailoring context prepared for: {result.get('job_title')} @ {result.get('company')}")

    return json.dumps(result, indent=2)


# Initialize storage attributes
dispatch_tool.filtered_jobs = []
dispatch_tool.last_candidate = {}
dispatch_tool.top_job = {}


# ── Agent loop ───────────────────────────────────────────────────────────────

def run_agent(candidate: dict, original_summary: str, original_bullets: list[str]) -> None:
    """
    Main agentic loop. Sends candidate profile to Claude, lets it reason
    and decide which tools to call, then processes results autonomously.
    """
    print("=" * 60)
    print("🤖 JOB SEARCH AI AGENT STARTING")
    print("=" * 60)
    print(f"\n📋 Candidate Profile:")
    print(f"   Skills: {', '.join(candidate['skills'])}")
    print(f"   Location: {candidate['location']}")
    print(f"   Experience: {candidate['years_of_experience']} years")

    jobs = load_jobs(candidate)
    print(f"📂 Loaded {len(jobs)} job postings from Adzuna.\n")

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

    # ── Agentic loop ──
    step = 0
    while True:
        step += 1
        print(f"\n{'─'*50}")
        print(f"⚙️  Agent Step {step}: Calling Claude...")

        response = client.messages.create(
            model=MODEL,
            max_tokens=8096,
            system=system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        print(f"   Stop reason: {response.stop_reason}")

        # Collect text reasoning blocks
        for block in response.content:
            if hasattr(block, "text") and block.text:
                print(f"\n💭 Agent Reasoning:\n{block.text}")

        # If Claude is done, break
        if response.stop_reason == "end_turn":
            print("\n✅ Agent completed all steps.")
            break

        # If Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Add assistant message to history
            messages.append({"role": "assistant", "content": response.content})

            # Process each tool call
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_result = dispatch_tool(block.name, block.input, jobs)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_result,
                    })

            # Add tool results to conversation
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "max_tokens":
            # Still has tool calls pending, continue the loop
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_result = dispatch_tool(block.name, block.input, jobs)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_result,
                    })
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            else:
                print("⚠️  Max tokens reached with no tool calls. Stopping.")
                break

        else:
            print(f"⚠️  Unexpected stop reason: {response.stop_reason}")
            break

    print("\n" + "=" * 60)
    print("🏁 AGENT RUN COMPLETE")
    print("=" * 60)