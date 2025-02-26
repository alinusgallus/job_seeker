# resume_job_matcher/src/resume_job_matcher/preprocessing.py
import spacy
from typing import Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def preprocess_documents(resume_text: str, job_posting_text: str) -> Dict[str, Any]:
    """
    Perform spaCy preprocessing on resume and job posting texts.
    
    This function:
    1. Cleans and normalizes the texts
    2. Extracts keywords using TF-IDF
    3. Analyzes similarity between documents
    4. Formats results for CrewAI agents
    
    Args:
        resume_text: The full text of the resume
        job_posting_text: The full text of the job posting
        
    Returns:
        Dictionary with preprocessed data for CrewAI agents
    """
    # Clean texts
    cleaned_resume = clean_text(resume_text)
    cleaned_job = clean_text(job_posting_text)
    
    # Extract keywords and analyze similarity
    resume_keywords, job_keywords, similarity_results = compare_documents(cleaned_resume, cleaned_job)
    
    # Identify resume sections
    resume_sections = extract_resume_sections(cleaned_resume)
    
    # Format data for CrewAI
    return {
        # Full texts for the agents
        "resume": cleaned_resume,
        "job_posting": cleaned_job,
        
        # Structured data for the matching specialist
        "resume_keywords": format_resume_keywords(resume_keywords, similarity_results),
        "job_keywords": format_job_keywords(job_keywords, similarity_results),
        
        # Additional metadata
        "similarity_score": similarity_results["similarity_score"],
        "matching_count": len(similarity_results["matching_keywords"]),
        "missing_count": len(similarity_results["missing_keywords"])
    }

def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    
    # Remove special characters but preserve sentence structure
    text = re.sub(r'[^\w\s\.\,\;\:\-\(\)]', ' ', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_resume_sections(text: str) -> Dict[str, str]:
    """
    Extract common sections from a resume text.
    
    Args:
        text: Clean resume text
        
    Returns:
        Dictionary mapping section names to content
    """
    # Common section headers in resumes
    section_patterns = {
        "summary": [r'\b(?:summary|profile|objective|about me)\b', r'^summary$', r'^profile$'],
        "experience": [r'\b(?:experience|work|employment|history)\b', r'^experience$', r'^work experience$'],
        "education": [r'\b(?:education|academic|degree|university|college)\b', r'^education$'],
        "skills": [r'\b(?:skills|expertise|technologies|competencies)\b', r'^skills$', r'^technical skills$'],
        "projects": [r'\b(?:projects|portfolio)\b', r'^projects$'],
        "certifications": [r'\b(?:certifications|certificates|credentials)\b', r'^certifications$']
    }
    
    # Process with spaCy to get sentence boundaries
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents]
    
    sections = {}
    current_section = None
    section_content = []
    
    for sentence in sentences:
        # Check if this sentence is a section header
        found_section = False
        for section, patterns in section_patterns.items():
            if any(re.search(pattern, sentence.lower()) for pattern in patterns):
                # If we've been building a previous section, add it
                if current_section and section_content:
                    sections[current_section] = ' '.join(section_content)
                    
                # Start a new section
                current_section = section
                section_content = []
                found_section = True
                break
        
        # If not a header, add to current section
        if not found_section and current_section:
            section_content.append(sentence)
    
    # Add the last section
    if current_section and section_content:
        sections[current_section] = ' '.join(section_content)
    
    return sections

def compare_documents(resume_text: str, job_text: str) -> tuple:
    """
    Compare resume and job posting using TF-IDF vectorization.
    
    Args:
        resume_text: Cleaned resume text
        job_text: Cleaned job posting text
        
    Returns:
        Tuple of (resume_keywords, job_keywords, similarity_results)
    """
    # Create TF-IDF vectorizer
    vectorizer = TfidfVectorizer(
        stop_words='english',
        ngram_range=(1, 2),  # Include both unigrams and bigrams
        max_features=1000
    )
    
    # Fit and transform both documents
    tfidf_matrix = vectorizer.fit_transform([resume_text, job_text])
    
    # Calculate similarity
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    
    # Get feature names
    feature_names = vectorizer.get_feature_names_out()
    
    # Get TF-IDF scores for both documents
    resume_scores = tfidf_matrix[0].toarray()[0]
    job_scores = tfidf_matrix[1].toarray()[0]
    
    # Create keyword lists
    resume_keywords = [
        {"word": feature_names[i], "score": float(resume_scores[i])}
        for i in range(len(feature_names))
        if resume_scores[i] > 0.01  # Only include significant terms
    ]
    
    job_keywords = [
        {"word": feature_names[i], "score": float(job_scores[i])}
        for i in range(len(feature_names))
        if job_scores[i] > 0.01  # Only include significant terms
    ]
    
    # Sort by importance
    resume_keywords.sort(key=lambda x: x["score"], reverse=True)
    job_keywords.sort(key=lambda x: x["score"], reverse=True)
    
    # Find matching keywords
    similarity_results = {
        "similarity_score": float(similarity),
        "matching_keywords": [],
        "missing_keywords": []
    }
    
    # Create lookup dictionaries
    resume_dict = {item["word"]: item["score"] for item in resume_keywords}
    job_dict = {item["word"]: item["score"] for item in job_keywords}
    
    # Find matches and missing terms
    for word, score in job_dict.items():
        if word in resume_dict:
            similarity_results["matching_keywords"].append({
                "word": word,
                "resume_score": resume_dict[word],
                "job_score": score
            })
        else:
            similarity_results["missing_keywords"].append({
                "word": word,
                "job_score": score
            })
    
    # Sort the results
    similarity_results["matching_keywords"].sort(key=lambda x: x["job_score"], reverse=True)
    similarity_results["missing_keywords"].sort(key=lambda x: x["job_score"], reverse=True)
    
    return resume_keywords, job_keywords, similarity_results

def format_resume_keywords(resume_keywords, similarity_results):
    """Format resume keywords for CrewAI analysis."""
    # Extract top keywords
    top_keywords = resume_keywords[:20]
    
    # Format matching keywords
    matching = similarity_results["matching_keywords"][:15]
    matching_formatted = "\n".join([
        f"- {item['word']} (relevance: {item['job_score']:.2f})"
        for item in matching
    ])
    
    # Create a summary text for CrewAI
    result = f"""
RESUME ANALYSIS SUMMARY:

TOP RESUME KEYWORDS:
{', '.join([kw['word'] for kw in top_keywords])}

KEYWORDS MATCHING JOB REQUIREMENTS:
{matching_formatted}

OVERALL SIMILARITY SCORE: {similarity_results['similarity_score']:.2f} (0-1 scale)
"""
    return result

def format_job_keywords(job_keywords, similarity_results):
    """Format job keywords for CrewAI analysis."""
    # Extract top keywords
    top_keywords = job_keywords[:20]
    
    # Format missing keywords
    missing = similarity_results["missing_keywords"][:15]
    missing_formatted = "\n".join([
        f"- {item['word']} (relevance: {item['job_score']:.2f})"
        for item in missing
    ])
    
    # Create a summary text for CrewAI
    result = f"""
JOB ANALYSIS SUMMARY:

TOP JOB REQUIREMENT KEYWORDS:
{', '.join([kw['word'] for kw in top_keywords])}

KEY REQUIREMENTS MISSING FROM RESUME:
{missing_formatted}

OVERALL SIMILARITY SCORE: {similarity_results['similarity_score']:.2f} (0-1 scale)
"""
    return result