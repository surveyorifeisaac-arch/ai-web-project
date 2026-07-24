import sqlite3

def setup_students_table():
    conn = sqlite3.connect('exam_vault.db')
    cursor = conn.cursor()
    
    # Create the students table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        reg_no TEXT PRIMARY KEY,
        full_name TEXT NOT NULL,
        allocated_subject TEXT NOT NULL
    )
    ''')
    
    # Clear any previous mock users and insert fresh clean test profiles
    cursor.execute("DELETE FROM students")
    cursor.execute("INSERT INTO students (reg_no, full_name, allocated_subject) VALUES (?, ?, ?)", 
                   ("IFETH/ST/001", "Chidi Okafor", "Science & Mathematics"))
    cursor.execute("INSERT INTO students (reg_no, full_name, allocated_subject) VALUES (?, ?, ?)", 
                   ("IFETH/ST/002", "Funmi Aminu", "Science & Mathematics"))
    
    conn.commit()
    conn.close()
    print("Database updated: 'students' table is live with test accounts.")

if __name__ == "__main__":
    setup_students_table()