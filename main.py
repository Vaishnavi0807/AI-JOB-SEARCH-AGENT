# main.py
import os
from dotenv import load_dotenv
from agent import run_agent # type: ignore

load_dotenv()

def main():
    candidate = {
        "skills": ["Python", "PyTorch", "Machine Learning", "SQL", "NLP", "HuggingFace"],
        "location": "remote",
        "years_of_experience": 3,
    }

    original_summary = (
        "Machine learning engineer with experience building and deploying models. "
        "Familiar with Python and deep learning frameworks. "
        "Worked on data pipelines and model evaluation at a mid-size tech company."
    )

    original_bullets = [
        "Worked on machine learning models and helped improve performance",
        "Collaborated with team members on various data science projects",
    ]

    run_agent(candidate, original_summary, original_bullets)

if __name__ == "__main__":
    main()