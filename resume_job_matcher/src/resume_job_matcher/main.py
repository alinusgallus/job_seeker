#!/usr/bin/env python
import sys
import warnings
from datetime import datetime
from resume_job_matcher.src.resume_job_matcher.crew import ResumeJobMatcher
from resume_job_matcher.src.resume_job_matcher.preprocessing import preprocess_documents
from pathlib import Path
import PyPDF2

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def read_txt(file_path):
    with open(file_path, 'r') as file:
        return file.read()
    
def read_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text()
    return text

def run(resume_text=None, job_posting_text=None):
    """
    Run the crew with spaCy preprocessing.
    
    Args:
        resume_text (str, optional): Resume text content
        job_posting_text (str, optional): Job posting text content
    """
    if not resume_text or not job_posting_text:
        raise ValueError("Both resume text and job posting text are required")
    
    try:
        # Step 1: Preprocess with spaCy
        preprocessed_data = preprocess_documents(resume_text, job_posting_text)
        
        # Step 2: Run CrewAI analysis
        result = ResumeJobMatcher().crew().kickoff(inputs=preprocessed_data)
        
        # Step 3: Return the combined results
        return {
            "ai_analysis": result,
            "similarity_score": preprocessed_data["similarity_score"],
            "matching_keywords_count": preprocessed_data["matching_count"],
            "missing_keywords_count": preprocessed_data["missing_count"]
        }
    
    except Exception as e:
        raise Exception(f"An error occurred while running the analysis: {e}")

# Keep your existing train, replay, and test functions as they are
def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI LLMs"
    }
    try:
        ResumeJobMatcher().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        ResumeJobMatcher().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "AI LLMs"
    }
    try:
        ResumeJobMatcher().crew().test(n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")