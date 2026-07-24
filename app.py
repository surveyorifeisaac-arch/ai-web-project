import sqlite3
import os
import sys
from flask import Flask, render_template, request, redirect, url_for, session

# Helper path resolution logic for PyInstaller
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Initialize Flask with dynamic asset paths for compilation safety
app = Flask(__name__, 
            template_folder=get_resource_path('templates'),
            static_folder=get_resource_path('static'))
app.secret_key = "IFETH_CONSULT_SECURE_TOKEN_KEY"

def get_db_connection():
    # Force the engine to look for the DB file in the actual folder the exe sits in
    exe_dir = os.path.dirname(sys.executable) if hasattr(sys, 'frozen') else os.path.abspath(".")
    db_path = os.path.join(exe_dir, 'exam_vault.db')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# 1. ROUTE: Root Path handles redirect or Login Screen
@app.route('/')
def home():
    if 'student_id' in session:
        return redirect(url_for('show_exam'))
    return render_template('login.html', error=None)

# 2. ROUTE: Process the Login Submission
@app.route('/login', methods=['POST'])
def process_login():
    reg_no = request.form.get('reg_no').strip()
    
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE reg_no = ?', (reg_no,)).fetchone()
    conn.close()
    
    if student:
        # Save credentials inside browser session memory cookie
        session['student_id'] = student['reg_no']
        session['student_name'] = student['full_name']
        return redirect(url_for('show_exam'))
    else:
        return render_template('login.html', error="Invalid Registration Number. Access Denied.")

# 3. ROUTE: Show the Exam Page (Authenticated with Dynamic Duration)
@app.route('/exam')
def show_exam():
    if 'student_id' not in session:
        return redirect(url_for('home'))
        
    conn = get_db_connection()
    
    # 1. Fetch the student profile to look at their allocated subject
    student = conn.execute('SELECT * FROM students WHERE reg_no = ?', (session['student_id'],)).fetchone()
    questions = conn.execute('SELECT * FROM questions').fetchall()
    conn.close()
    
    # 2. Dynamic Time Rule Mapping (Determined by the Teacher/Subject Type)
    # Default fallback is 45 minutes if the subject doesn't match these custom rules
    exam_duration_minutes = 45 
    
    allocated_subject = student['allocated_subject'] if student else "General"
    
    # Teachers can easily adjust or add rules here for different durations:
    if "Science & Mathematics" in allocated_subject:
        exam_duration_minutes = 60  # 1 Hour for science
    elif "Mock Revision" in allocated_subject:
        exam_duration_minutes = 10  # 10 Minutes short quiz
    elif "Comprehensive Practical" in allocated_subject:
        exam_duration_minutes = 180 # 3 Hours for extensive layouts

    return render_template(
        'exam.html', 
        questions=questions, 
        student_name=session['student_name'],
        subject_name=allocated_subject,
        duration_mins=exam_duration_minutes # Sending this variable straight to the template
    )
# 4. ROUTE: Process Answers and Insert Dynamic Student Identity
@app.route('/submit-exam', methods=['POST'])
def submit_exam():
    if 'student_id' not in session:
        return redirect(url_for('home'))

    conn = get_db_connection()
    questions = conn.execute('SELECT * FROM questions').fetchall()
    
    total_questions = len(questions)
    score = 0
    
    for q in questions:
        field_name = f"q_{q['id']}"
        student_answer = request.form.get(field_name)
        if student_answer == q['correct_option']:
            score += 1
            
    # Insert with ACTUAL verified session names
    conn.execute('''
        INSERT INTO results (student_id, student_name, score, total_questions, sync_status)
        VALUES (?, ?, ?, ?, 'PENDING')
    ''', (session['student_id'], session['student_name'], score, total_questions))
    
    conn.commit()
    conn.close()
    
    student_name = session['student_name']
    
    # Wipe the login session now that the test is done
    session.clear()
    
    return f"""
    <div style="font-family:sans-serif; text-align:center; margin-top:50px;">
        <h2>Examination Submitted Successfully!</h2>
        <p>Thank you, {student_name}. Your responses have been securely logged to the local server vault.</p>
        <p>Score: <strong>{score} / {total_questions}</strong></p>
        <a href="/">Return to Portal Main Home</a>
    </div>
    """
# =====================================================================
# UPGRADE: ADMIN BACKEND FOR RICH TEXT CREATOR
# =====================================================================

# 5. ROUTE: Render the new Text Editor Page
@app.route('/admin/create-question', methods=['GET'])
def admin_create_question():
    return render_template('create_question.html')

# 6. ROUTE: Receive and Insert the Full Form Payload to SQLite Vault
@app.route('/admin/save-question', methods=['POST'])
def admin_save_question():
    # Capture the rich question and individual form field string data
    rich_question_payload = request.form.get('formatted_question')
    opt_a = request.form.get('option_a')
    opt_b = request.form.get('option_b')
    opt_c = request.form.get('option_c')
    opt_d = request.form.get('option_d')
    correct_opt = request.form.get('correct_option')
    
    if not rich_question_payload or rich_question_payload.strip() == "<p><br></p>":
        return "<h3>Error: Question text cannot be empty.</h3>", 400
        
    conn = get_db_connection()
    try:
        # Saving all distinct components directly to your production table setup
        conn.execute('''
            INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_option)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (rich_question_payload, opt_a, opt_b, opt_c, opt_d, correct_opt))
        conn.commit()
    except sqlite3.Error as error:
        print(f"Local Database Error: {error}")
        conn.rollback()
        return f"<h3>Database Insertion Failed: {error}</h3>", 500
    finally:
        conn.close()

    return f"""
    <div style="font-family:sans-serif; text-align:center; margin-top:50px;">
        <h2 style="color: #28a745;">Question & Options Saved Successfully!</h2>
        <br>
        <a href="/admin/create-question" style="background:#0056b3; color:white; padding:10px 15px; text-decoration:none; border-radius:4px; font-weight:bold;">Create Another Question</a>
        &nbsp;&nbsp;&nbsp;&nbsp;
        <a href="/" style="color:#6c757d;">Go to Main Portal Login</a>
    </div>
    """

# =====================================================================
# UPGRADE: DYNAMIC STUDENT REGISTRATION MANAGEMENT
# =====================================================================

def generate_next_registration_number():
    """Checks the database for the highest active ID and builds the next serial token"""
    conn = get_db_connection()
    # Pull the highest registered number matching your format
    last_reg = conn.execute('''
        SELECT reg_no FROM students 
        WHERE reg_no LIKE 'IFETH/ST/%' 
        ORDER BY reg_no DESC LIMIT 1
    ''').fetchone()
    conn.close()

    if not last_reg:
        return "IFETH/ST/001"

    # Isolate the trailing digits (e.g., "IFETH/ST/014" -> "014")
    try:
        last_numeric_part = last_reg['reg_no'].split('/')[-1]
        next_counter = int(last_numeric_part) + 1
    except (ValueError, IndexError):
        next_counter = 1

    # Format with leading zeros up to 3 digits wide
    return f"IFETH/ST/{next_counter:03d}"


# 7. ROUTE: Render the Student Enrollment Dashboard UI
@app.route('/admin/students', methods=['GET'])
def admin_student_dashboard():
    conn = get_db_connection()
    all_students = conn.execute('SELECT * FROM students ORDER BY reg_no ASC').fetchall()
    conn.close()
    
    # Generate what the *next* registration number will be as a preview
    predicted_next = generate_next_registration_number()
    
    return render_template('manage_students.html', students=all_students, next_reg=predicted_next)


# 8. ROUTE: Process Bulk Text Enrollment Submission with Sequential Correction
@app.route('/admin/students/save-bulk', methods=['POST'])
def admin_save_bulk_students():
    raw_names_input = request.form.get('student_names_list')
    subject_input = request.form.get('allocated_subject')
    
    if not raw_names_input or not raw_names_input.strip():
        return "<h3>Error: Student list cannot be empty.</h3>", 400
    if not subject_input or not subject_input.strip():
        return "<h3>Error: Please specify an allocated subject.</h3>", 400

    names_list = [name.strip() for name in raw_names_input.split('\n') if name.strip()]
    
    conn = get_db_connection()
    
    # 1. Look up the highest registered number ONCE before entering the loop
    last_reg = conn.execute('''
        SELECT reg_no FROM students 
        WHERE reg_no LIKE 'IFETH/ST/%' 
        ORDER BY reg_no DESC LIMIT 1
    ''').fetchone()

    # 2. Extract the base counter integer
    if last_reg:
        try:
            last_numeric_part = last_reg['reg_no'].split('/')[-1]
            current_counter = int(last_numeric_part)
        except (ValueError, IndexError):
            current_counter = 0
    else:
        current_counter = 0

    added_count = 0
    try:
        for full_name in names_list:
            # 3. Safely increment the counter inside Python memory for each name
            current_counter += 1
            new_reg_no = f"IFETH/ST/{current_counter:03d}"
            
            # 4. Insert into the database
            conn.execute('''
                INSERT INTO students (reg_no, full_name, allocated_subject)
                VALUES (?, ?, ?)
            ''', (new_reg_no, full_name, subject_input.strip()))
            added_count += 1
            
        conn.commit() # Commit all entries cleanly at the end of the batch
    except sqlite3.Error as e:
        print(f"Enrollment Database Error: {e}")
        conn.rollback()
        return f"<h3>Database error during processing: {e}</h3>", 500
    finally:
        conn.close()

    return f"""
    <div style="font-family:sans-serif; text-align:center; margin-top:50px;">
        <h2 style="color: #28a745;">Successfully Registered {added_count} New Students!</h2>
        <p>All profiles have been bound uniquely to the '{subject_input}' module.</p>
        <br>
        <a href="/admin/students" style="background:#0056b3; color:white; padding:10px 15px; text-decoration:none; border-radius:4px; font-weight:bold;">Return to Student Management</a>
    </div>
    """

# =====================================================================
# UPGRADE: ASYNCHRONOUS OFFLINE IMAGE UPLOADS FOR QUILL
# =====================================================================
from werkzeug.utils import secure_filename

# 9. ROUTE: Intercept dropped editor images, save locally, and return the true URL path
@app.route('/admin/upload-image', methods=['POST'])
def admin_upload_image():
    if 'image' not in request.files:
        return {"error": "No file payload detected"}, 400
        
    file = request.files['image']
    if file.filename == '':
        return {"error": "No selected filename available"}, 400

    if file:
        # Secure the filename against malicious directory traversals
        filename = secure_filename(file.filename)
        
        # Build path pointing inside your existing question_images folder
        # Using your local execution directory context safely
        base_dir = os.path.abspath(".")
        upload_folder = os.path.join(base_dir, 'static', 'question_images')
        
        # Ensure the folder physically exists if wiped during a build
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        file_save_path = os.path.join(upload_folder, filename)
        file.save(file_save_path)
        
        # Return the clean routing URL path straight back to the frontend editor
        local_url = url_for('static', filename=f'question_images/{filename}')
        return {"url": local_url}, 200
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)