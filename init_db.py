import sqlite3

def initialize_database():
    # Connect to (or create) the database file
    connection = sqlite3.connect('exam_vault.db')
    cursor = connection.cursor()

    # 1. Create the Questions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL,
        option_a TEXT,
        option_b TEXT,
        option_c TEXT,
        option_d TEXT,
        correct_option TEXT
    )
    ''')

    # 2. Create the Results table (Crucial for your Google Sheets sync later)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        student_name TEXT NOT NULL,
        score INTEGER NOT NULL,
        total_questions INTEGER NOT NULL,
        exam_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sync_status TEXT DEFAULT 'PENDING'
    )
    ''')

    # Insert a sample question to test the engine
    cursor.execute('''
    INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_option) 
    VALUES (?, ?, ?, ?, ?, ?)
    ''', ("What is the primary function of a Router?", "Storage", "Directing Network Traffic", "Printing Documents", "Cooling the Server", "B"))

    connection.commit()
    connection.close()
    print("Success: 'exam_vault.db' created with Questions and Results tables!")

if __name__ == "__main__":
    initialize_database()