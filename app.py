import streamlit as st
from PyPDF2 import PdfReader
from resume_job_matcher.src.resume_job_matcher.main import run

st.title("Resume Keyword Matcher")

# Add PDF file uploader
uploaded_resume = st.file_uploader(
    "Upload your resume",
    type=["pdf"],
    help="Please upload your resume in PDF format"
)

# Show warning if no file is uploaded
if uploaded_resume is None:
    st.warning("Please upload your resume to continue")

# Job posting text area
job_posting = st.text_area(
    "Paste the job posting",
    height=200,
    placeholder="Copy and paste the job description here..."
)

# Submit button
submit_button = st.button("Match Resume with Job Posting", type="primary")

# Process the resume and job posting when submit is clicked
if uploaded_resume is not None and submit_button:
    try:
        # Read PDF content
        pdf_reader = PdfReader(uploaded_resume)
        resume_text = ""
        for page in pdf_reader.pages:
            resume_text += page.extract_text()

        # Debug prints
        st.write("Debug - Resume Text:", resume_text[:100])
        st.write("Debug - Job Posting:", job_posting[:100])

        with st.spinner('Analyzing resume and job posting...'):
            result = run(
                resume_text=resume_text,
                job_posting_text=job_posting
            )
            st.write(result)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

