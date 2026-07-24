import csv
import sqlite3
import os

def upload_questions_from_csv(csv_filename):
    # Check if the file actually exists before processing
    if not os.path.exists(csv_filename):
        print(f"Error: The file '{csv_filename}' was not found.")
        return

    conn = sqlite3.connect('exam_vault.db')
    cursor = conn.cursor()
    
    success_count = 0

    # Open the CSV file with utf-8 encoding to support math symbols (like ° or √)
    with open(csv_filename, mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        
        for row in csv_reader:
            try:
                cursor.execute('''
                    INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_option, diagram_file)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['question_text'].strip(),
                    row['option_a'].strip(),
                    row['option_b'].strip(),
                    row['option_c'].strip(),
                    row['option_d'].strip(),
                    row['correct_option'].strip().upper(),
                    row['diagram_file'].strip() if row['diagram_file'] else None
                ))
                success_count += 1
            except Exception as e:
                print(f"Skipping row due to error: {e}")

    conn.commit()
    conn.close()
    print(f"Success! {success_count} questions were parsed and loaded into the local vault.")

if __name__ == "__main__":
    upload_questions_from_csv('questions_template.csv')