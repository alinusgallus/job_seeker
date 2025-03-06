from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import uuid
import time
import PyPDF2
import docx2txt
import sys
import importlib.util

app = Flask(__name__)

# Add the min function to Jinja
app.jinja_env.globals.update(min=min)

# Enable debug mode for templates
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Basic configuration
app.config['SECRET_KEY'] = 'simple-dev-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'txt'}
app.config['SESSION_TYPE'] = 'filesystem'  # For more reliable session storage

# In-memory storage for analysis results (to avoid session size limitations)
app.config['ANALYSIS_RESULTS'] = {}
app.config['ANALYSIS_TIMESTAMPS'] = {}  # To track result creation time
app.config['MAX_STORED_RESULTS'] = 50   # Maximum number of results to store
app.config['RESULT_TTL'] = 3600         # Time-to-live in seconds (1 hour)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Import your main module dynamically
def import_resume_matcher():
    try:
        # Add the parent directory to sys.path to enable imports
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # Now try to import the module directly
        from resume_job_matcher.src.resume_job_matcher.main import run
        return run
    except Exception as e:
        print(f"Error importing resume_job_matcher: {e}")
        # Print more detailed error information for debugging
        import traceback
        traceback.print_exc()
        return None

# Get the run function
run_function = import_resume_matcher()

def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def cleanup_old_results():
    """Remove old results to prevent memory growth
    
    This function:
    1. Removes results older than RESULT_TTL
    2. If still too many results, removes oldest results
    """
    current_time = time.time()
    expired_ids = []
    
    # First pass: remove expired results (older than TTL)
    for result_id, timestamp in list(app.config['ANALYSIS_TIMESTAMPS'].items()):
        if current_time - timestamp > app.config['RESULT_TTL']:
            expired_ids.append(result_id)
    
    # Remove expired results
    for result_id in expired_ids:
        if result_id in app.config['ANALYSIS_RESULTS']:
            del app.config['ANALYSIS_RESULTS'][result_id]
        if result_id in app.config['ANALYSIS_TIMESTAMPS']:
            del app.config['ANALYSIS_TIMESTAMPS'][result_id]
    
    # If still too many results, remove oldest ones
    if len(app.config['ANALYSIS_RESULTS']) > app.config['MAX_STORED_RESULTS']:
        # Sort by timestamp, oldest first
        sorted_items = sorted(
            app.config['ANALYSIS_TIMESTAMPS'].items(), 
            key=lambda x: x[1]
        )
        
        # Calculate how many to remove
        remove_count = len(app.config['ANALYSIS_RESULTS']) - app.config['MAX_STORED_RESULTS']
        
        # Remove oldest results
        for i in range(remove_count):
            if i < len(sorted_items):
                result_id = sorted_items[i][0]
                if result_id in app.config['ANALYSIS_RESULTS']:
                    del app.config['ANALYSIS_RESULTS'][result_id]
                if result_id in app.config['ANALYSIS_TIMESTAMPS']:
                    del app.config['ANALYSIS_TIMESTAMPS'][result_id]
    
    # Log cleanup stats
    print(f"Cleanup: removed {len(expired_ids)} expired results, now storing {len(app.config['ANALYSIS_RESULTS'])} results")

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
    debug_info = None
    
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
                
                # Print debug info about the extracted text
                print(f"DEBUG - Extracted resume text (first 200 chars): {resume_text[:200]}")
                print(f"DEBUG - Total resume text length: {len(resume_text)} characters")
                
                # Check if we successfully imported the run function
                if run_function:
                    # Process using your existing backend
                    analysis_result = run_function(
                        resume_text=resume_text, 
                        job_posting_text=job_description,
                        save_output=True  # Enable saving debug output
                    )
                    
                    # Store the result in application memory instead of the session
                    # Generate a unique ID for this result
                    result_id = str(uuid.uuid4())
                    
                    # Clean up old results before adding new one
                    cleanup_old_results()
                    
                    # Store the result and timestamp
                    app.config['ANALYSIS_RESULTS'][result_id] = analysis_result
                    app.config['ANALYSIS_TIMESTAMPS'][result_id] = time.time()
                    
                    # Store only the ID in the session (much smaller)
                    session['result_id'] = result_id
                    print(f"Stored analysis result with ID: {result_id}")
                    
                    # Clean up the uploaded file
                    os.remove(file_path)
                    
                    # Redirect to results page
                    return redirect(url_for('results'))
                else:
                    # If import failed, provide more detailed information
                    success = 'Resume and job description received successfully, but backend processing is not available.'
                    debug_info = "Python path: " + str(sys.path)
                    # Store resume text and job description in session for debugging
                    session['resume_text'] = resume_text
                    session['job_description'] = job_description
                
            except Exception as e:
                import traceback
                error = f'Error processing file: {str(e)}'
                debug_info = traceback.format_exc()
        else:
            error = 'File type not allowed. Please upload a PDF, DOCX, or TXT file.'
    
    return render_template('index.html', error=error, success=success, debug_info=debug_info)

@app.route('/results')
def results():
    # Get result ID from session
    result_id = session.get('result_id')
    print(f"Looking up result with ID: {result_id}")
    
    # If no result ID in session, redirect to home page
    if not result_id:
        flash('No analysis results found. Please submit a resume and job description.')
        return redirect(url_for('index'))
    
    # Get the full result from application memory
    analysis_result = app.config['ANALYSIS_RESULTS'].get(result_id)
    
    # If result not found in application memory, redirect to home page
    if not analysis_result:
        flash('Analysis results expired or not found. Please submit your resume again.')
        return redirect(url_for('index'))
    
    print(f"Retrieved result from application memory. Keys: {analysis_result.keys()}")
    
    # Ensure we have the required keys to avoid template errors
    if 'matching_keywords_count' not in analysis_result:
        analysis_result['matching_keywords_count'] = 0
    if 'missing_keywords_count' not in analysis_result:
        analysis_result['missing_keywords_count'] = 0
    
    # Check if ai_analysis exists and looks valid
    if 'ai_analysis' not in analysis_result:
        # If ai_analysis is missing but we have other analytics fields,
        # move those into an ai_analysis object
        print("ai_analysis not found in result")
        if any(key in analysis_result for key in ['match_percentage', 'overall_match_assessment']):
            ai_fields = ['match_percentage', 'overall_match_assessment', 
                         'key_strengths_alignment', 'critical_gaps', 
                         'improvement_recommendations']
            
            ai_analysis = {}
            for field in ai_fields:
                if field in analysis_result:
                    ai_analysis[field] = analysis_result.pop(field)
            
            analysis_result['ai_analysis'] = ai_analysis
    
    # Fix the crew output if it has placeholder values
    if (analysis_result['ai_analysis'].get('overall_match_assessment') == 'The AI analysis could not be properly formatted as JSON. Basic information has been extracted.' or
        analysis_result['ai_analysis'].get('key_strengths_alignment') == 'Please refer to the raw output for details on strengths.'):
        
        print("Detected placeholder values in ai_analysis, attempting to update from crew output")
        
        # Try to read the most recent crew raw output file
        import glob
        
        # Get the most recent raw output file
        raw_files = glob.glob(os.path.join(os.path.dirname(__file__), 'crew_raw_output_*.txt'))
        if raw_files:
            latest_file = max(raw_files, key=os.path.getctime)
            print(f"Found latest crew output file: {latest_file}")
            
            try:
                with open(latest_file, 'r') as f:
                    raw_content = f.read()
                
                # Check if it contains JSON
                import re
                import json
                
                # Try to extract JSON
                json_match = re.search(r'({[\s\S]*"match_percentage"[\s\S]*})', raw_content)
                if json_match:
                    try:
                        json_str = json_match.group(1)
                        print(f"Found JSON in raw output: {json_str[:100]}...")
                        parsed_json = json.loads(json_str)
                        
                        # Update the ai_analysis with the JSON values
                        for key, value in parsed_json.items():
                            analysis_result['ai_analysis'][key] = value
                        
                        print("Successfully updated ai_analysis from raw output JSON")
                    except json.JSONDecodeError:
                        print("Found JSON-like pattern but couldn't parse it")
                else:
                    print("No JSON found in raw output")
                    
                    # Try to extract sections with regex
                    # Overall Assessment
                    overall_match = re.search(r'(?:Overall Assessment|Overall Match)[:\n]+(.*?)(?:\*\*|\n\n|$)', 
                                            raw_content, re.DOTALL | re.IGNORECASE)
                    if overall_match:
                        analysis_result['ai_analysis']['overall_match_assessment'] = overall_match.group(1).strip()
                        
                    # Extract other sections similarly
                    sections = {
                        'key_strengths_alignment': r'(?:Key Strengths|Strengths|Alignment)[:\n]+(.*?)(?:\*\*|\n\n|$)',
                        'critical_gaps': r'(?:Critical Gaps|Gaps|Missing Skills)[:\n]+(.*?)(?:\*\*|\n\n|$)',
                        'improvement_recommendations': r'(?:Recommendations|Improvement|Suggestions)[:\n]+(.*?)(?:\*\*|\n\n|$)'
                    }
                    
                    for key, pattern in sections.items():
                        match = re.search(pattern, raw_content, re.DOTALL | re.IGNORECASE)
                        if match:
                            analysis_result['ai_analysis'][key] = match.group(1).strip()
                
            except Exception as e:
                print(f"Error reading/processing raw output: {str(e)}")
    
    # Print some debugging info
    if 'matching_keywords' in analysis_result:
        print(f"Matching keywords: {analysis_result['matching_keywords'][:5]} (total: {len(analysis_result['matching_keywords'])})")
    if 'missing_keywords' in analysis_result:
        print(f"Missing keywords: {analysis_result['missing_keywords'][:5]} (total: {len(analysis_result['missing_keywords'])})")
    
    # Check if this is a debug request
    if request.args.get('debug') == 'true':
        return render_template('debug.html', result=analysis_result)
    else:
        return render_template('results.html', result=analysis_result)

@app.route('/debug')
def debug():
    """Debug route to view session and template data"""
    result_id = session.get('result_id')
    if result_id and result_id in app.config['ANALYSIS_RESULTS']:
        analysis_result = app.config['ANALYSIS_RESULTS'][result_id]
    else:
        analysis_result = {}
    return render_template('debug.html', result=analysis_result)

if __name__ == '__main__':
    app.run(debug=True)