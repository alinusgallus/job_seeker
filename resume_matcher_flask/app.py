from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import uuid
import PyPDF2
import docx2txt
import sys
import importlib.util

app = Flask(__name__)

# Basic configuration
app.config['SECRET_KEY'] = 'simple-dev-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'txt'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Import your main module dynamically
def import_resume_matcher():
    try:
        # Try to find the correct path to your main.py file
        main_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                               'resume_job_matcher', 'src', 'resume_job_matcher', 'main.py')
        
        # Check if the file exists
        if not os.path.exists(main_path):
            raise FileNotFoundError(f"Could not find main.py at {main_path}")
        
        # Import the module
        spec = importlib.util.spec_from_file_location("resume_matcher_main", main_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        return module.run
    except Exception as e:
        print(f"Error importing resume_job_matcher: {e}")
        return None

# Get the run function
run_function = import_resume_matcher()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_text_from_file(file_path):
    """Extract text from various file formats"""
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.pdf':
        # Extract text from PDF
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ''
            for page in reader.pages:
                text += page.extract_text()
        return text
    
    elif file_ext == '.docx':
        # Extract text from DOCX
        return docx2txt.process(file_path)
    
    else:  # Assume it's a text file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()

@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    success = None
    
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'resume' not in request.files:
            error = 'No resume file provided'
            return render_template('index.html', error=error)
        
        file = request.files['resume']
        
        # Check if file was selected
        if file.filename == '':
            error = 'No resume file selected'
            return render_template('index.html', error=error)
        
        # Get job description
        job_description = request.form.get('job_description', '').strip()
        if not job_description:
            error = 'Please enter a job description'
            return render_template('index.html', error=error)
        
        # Check if file type is allowed
        if file and allowed_file(file.filename):
            # Generate unique filename
            filename = str(uuid.uuid4()) + '_' + file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Save file
            file.save(file_path)
            
            # Extract text from resume
            try:
                resume_text = extract_text_from_file(file_path)
                
                # Check if we successfully imported the run function
                if run_function:
                    # Process using your existing backend
                    analysis_result = run_function(resume_text=resume_text, job_posting_text=job_description)
                    
                    # Store the result in the session
                    session['analysis_result'] = analysis_result
                    
                    # Clean up the uploaded file
                    os.remove(file_path)
                    
                    # Redirect to results page
                    return redirect(url_for('results'))
                else:
                    # If import failed, just provide a message for now
                    success = 'Resume and job description received successfully, but backend processing is not available.'
                    # Store resume text and job description in session for debugging
                    session['resume_text'] = resume_text
                    session['job_description'] = job_description
                
            except Exception as e:
                error = f'Error processing file: {str(e)}'
        else:
            error = 'File type not allowed. Please upload a PDF, DOCX, or TXT file.'
    
    return render_template('index.html', error=error, success=success)

@app.route('/results')
def results():
    # Get analysis result from session
    analysis_result = session.get('analysis_result')
    
    # If no result in session, redirect to home page
    if not analysis_result:
        flash('No analysis results found. Please submit a resume and job description.')
        return redirect(url_for('index'))
    
    return render_template('results.html', result=analysis_result)

if __name__ == '__main__':
    app.run(debug=True)