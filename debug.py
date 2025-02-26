from resume_job_matcher.src.resume_job_matcher.main import run

# Sample resume text
resume_text = """
John Smith
123 Main Street, City, State 12345
(555) 123-4567 | john.smith@email.com

SUMMARY
Experienced software engineer with 5+ years of experience in full-stack development.
Proficient in Python, JavaScript, and cloud technologies.

SKILLS
Programming: Python, JavaScript, TypeScript, Java, SQL
Frameworks: Django, React, Node.js, Express
Cloud: AWS (EC2, S3, Lambda), Docker, Kubernetes
Tools: Git, JIRA, Jenkins, Terraform

EXPERIENCE
Senior Software Engineer | ABC Tech Inc. | Jan 2020 - Present
- Led development of microservices architecture reducing system response time by 40%
- Implemented CI/CD pipeline resulting in 30% faster deployment cycles

Software Developer | XYZ Solutions | Jun 2018 - Dec 2019
- Developed RESTful APIs using Django and PostgreSQL
- Created responsive front-end applications with React

EDUCATION
Bachelor of Science in Computer Science
University of Technology | Graduated: May 2018

CERTIFICATIONS
AWS Certified Developer - Associate
Docker Certified Associate
"""

# Sample job posting
job_posting = """
Senior Full Stack Developer

We are seeking an experienced Full Stack Developer to join our growing engineering team.

Required Skills:
- 4+ years of experience in software development
- Strong proficiency in Python and JavaScript
- Experience with React, Node.js and modern front-end frameworks
- Familiarity with cloud platforms (AWS, GCP, or Azure)
- Knowledge of database systems (SQL and NoSQL)
- Experience with Docker and containerization
- Understanding of CI/CD pipelines

Responsibilities:
- Design and implement robust, scalable applications
- Collaborate with cross-functional teams
- Review code and mentor junior developers
- Troubleshoot and debug applications
- Participate in architecture decisions

Qualifications:
- Bachelor's degree in Computer Science or related field
- Strong problem-solving abilities
- Excellent communication skills
- Experience in an Agile development environment

Benefits:
- Competitive salary
- Health insurance
- Flexible work schedule
- Professional development budget
"""

try:
    # Run without try/except to see full traceback
    result = run(resume_text=resume_text, job_posting_text=job_posting)
    print("SUCCESS! Here's the result:")
    print(result)
except Exception as e:
    import traceback
    print(f"ERROR: {str(e)}")
    print("\nFULL TRACEBACK:")
    print(traceback.format_exc()) 