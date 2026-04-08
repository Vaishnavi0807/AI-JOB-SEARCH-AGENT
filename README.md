# 🤖 AI Job Search Agent

An intelligent AI-powered job search and resume optimization agent built with **Claude AI**, **Flask**, and the **Adzuna Jobs API**. The agent autonomously fetches live job postings, filters and ranks them based on your profile, and tailors your resume for the best match.

---

##  Demo

> Fill in your candidate profile → Click Search → Get your best job match + tailored resume instantly.

---

## Features

- **Live Job Fetching** — Pulls 30 real AI/ML/Data Science jobs from Adzuna API in real time
- **AI Agent Reasoning** — Claude autonomously decides which tools to call and in what order
- **3 Intelligent Tools** — Filtering, Ranking, and Resume Tailoring
- **Resume Tailoring** — Rewrites your summary and improves bullet points for the top job
- **Clean Web UI** — Built with Flask, no frontend framework needed
- **Similar Jobs** — Shows other ranked job matches with scores

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Agent | Anthropic Claude (claude-sonnet-4) |
| Job Data | Adzuna Jobs API |
| Backend | Python + Flask |
| Frontend | HTML + CSS + JavaScript |
| Environment | python-dotenv |

---

##  Project Structure

```
ai-job-search-agent/
├── app.py               # Flask backend + agent loop
├── main.py              # CLI version of the agent
├── agent.py             # Claude agent with tool calling
├── tools.py             # Filtering, ranking, resume tailoring tools
├── job_fetcher.py       # Adzuna API integration
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── .gitignore
└── templates/
    └── index.html       # Frontend UI
```

---

##  How the Agent Works

```
User Input (Candidate Profile)
        │
        ▼
  ┌─────────────┐
  │  Claude LLM  │  ◄──── System Prompt
  │  (Reasoner) │
  └──────┬──────┘
         │ decides to call tools
    ┌────┴────────────────┐
    ▼                     ▼
Filtering Tool       Ranking Tool
(rule-based)         (skill scoring)
    │                     │
    └────────┬────────────┘
             ▼
     Resume Tailoring Tool
             │
             ▼
    Final Output:
    - Top Job Recommendation
    - Tailored Resume Summary
    - Improved Bullet Points
    - Similar Jobs List
```

---

##  Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Vaishnavi0807/AI-JOB-SEARCH-AGENT.git
cd AI-JOB-SEARCH-AGENT
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

```env
ANTHROPIC_API_KEY=your_anthropic_key_here
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
```

### 4. Get your API keys

| Service | Link | Cost |
|---|---|---|
| Anthropic (Claude) | https://console.anthropic.com/settings/keys | ~$5 credits |
| Adzuna Jobs API | https://developer.adzuna.com | Free |

### 5. Run the web app

```bash
python app.py
```

Open your browser and go to: **http://127.0.0.1:5000**

### 6. (Optional) Run CLI version

```bash
python main.py
```

---

##  Tools Explained

###  Filtering Tool
Applies rule-based filtering to remove jobs that:
- Don't match the candidate's preferred location
- Require significantly more experience than the candidate has

###  Ranking Tool
Scores each job out of 100:
- Skill Match (70 pts) — how many required skills the candidate has
- Experience Fit (30 pts) — how closely experience aligns

###  Resume Tailoring Tool
Prepares context for Claude to:
- Rewrite the resume summary targeting the top job
- Improve two bullet points with strong action verbs and quantified results

---

##  Requirements

```
anthropic
flask
pandas
python-dotenv
requests
```

Install all with:
```bash
pip install -r requirements.txt
```

---

##  Environment Variables

Never commit your `.env` file. Use `.env.example` as a template:

```env
ANTHROPIC_API_KEY=your_anthropic_key_here
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_APP_KEY=your_adzuna_app_key
```

---

##  License

This project was built as part of an AI for Engineers course assignment.

---

## Author

**Vaishnavi**  
GitHub: [@Vaishnavi0807](https://github.com/Vaishnavi0807)
