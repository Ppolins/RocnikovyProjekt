import sqlite3
import os
import random
import string
import csv
import ast
import time
import signal
from collections import Counter
from multiprocessing import Process, Queue
import argparse
from dotenv import load_dotenv
import google.generativeai as genai

# ----------------- Načítanie API kľúča -----------------

# Načítame API kľúč zo súboru .env a nastavíme model Gemini.
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name="gemini-1.5-pro")

# ----------------- AI spätná väzba -----------------

# Funkcia na získanie spätnej väzby od AI modelu pre študentov na základe ich SQL dotazu
def get_ai_feedback(student, query, result):
    prompt = f"""
    Študent: {student}
    SQL dotaz: {query[:150]}  # Krátky dotaz na obmedzenie počtu tokenov
    Výsledok: {result}

    Napíš krátku spätnú väzbu pre študenta v slovenčine.
    """

    try:
        # Vygenerovanie odpovede AI
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"CHYBA AI: {e}"

# ----------------- Stabilná databáza -----------------

# Funkcia na načítanie definícií tabuliek zo súboru
def load_tables_from_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
        tables = ast.literal_eval(content)
    return tables

# Funkcia na vytvorenie databázy so statickými údajmi a tabuľkami
def create_stable_database(db_name, create_tables_path):
    if os.path.exists(db_name):
        os.remove(db_name)

    conn = sqlite3.connect(db_name)
    conn.execute('PRAGMA foreign_keys = ON')
    tables = load_tables_from_file(create_tables_path)

    for table_name, columns in tables.items():
        regular_columns = []
        foreign_keys = []
        for col in columns:
            if col.startswith("FOREIGN KEY"):
                foreign_keys.append(col)
            else:
                regular_columns.append(col)

        full_column_def = regular_columns + foreign_keys
        create_query = f"CREATE TABLE IF NOT EXISTS {table_name} (" + ", ".join(full_column_def) + ");"
        conn.execute(create_query)

    # Vloženie predpripravených údajov do tabuliek
    conn.executemany("INSERT INTO Students (name) VALUES (?)", [
        ('Alice',), ('Bob',), ('Charlie',), ('Diana',)
    ])
    conn.executemany("INSERT INTO Courses (title, parent_id) VALUES (?, ?)", [
        ('math', None),
        ('algebra', 1),
        ('geometry', 1),
        ('history', None),
        ('english', None)
    ])
    conn.executemany("INSERT INTO Enrollments (student_id, course_id) VALUES (?, ?)", [
        (1, 4), (2, 5), (3, 1), (4, 4), (1, 2)
    ])

    conn.commit()
    conn.close()

# ----------------- Náhodná databáza -----------------

# Funkcia na generovanie náhodného slova
def random_word(length=5):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

# Funkcia na vytvorenie náhodnej databázy s náhodnými údajmi
def create_random_database(db_name, create_tables_path):
    if os.path.exists(db_name):
        os.remove(db_name)

    conn = sqlite3.connect(db_name)
    conn.execute('PRAGMA foreign_keys = ON')
    tables = load_tables_from_file(create_tables_path)

    for table_name, columns in tables.items():
        regular_columns = []
        foreign_keys = []
        for col in columns:
            if col.startswith("FOREIGN KEY"):
                foreign_keys.append(col)
            else:
                regular_columns.append(col)

        full_column_def = regular_columns + foreign_keys
        create_query = f"CREATE TABLE IF NOT EXISTS {table_name} (" + ", ".join(full_column_def) + ");"
        conn.execute(create_query)

    conn.commit()
    conn.close()

# Funkcia na vloženie náhodných dát do databázy
def insert_random_data(db_name):
    conn = sqlite3.connect(db_name)

    # Vloženie náhodných študentov
    for _ in range(10):
        name = random_word(7)
        conn.execute("INSERT INTO Students (name) VALUES (?);", (name,))

    # Vloženie náhodných kurzov
    for _ in range(5):
        title = random_word(10)
        conn.execute("INSERT INTO Courses (title, parent_id) VALUES (?, NULL);", (title,))

    conn.commit()

    courses = conn.execute("SELECT id FROM Courses").fetchall()
    # Nastavenie rodičovských kurzov
    for course in courses:
        course_id = course[0]
        parent_id = random.choice(courses)[0]
        if course_id != parent_id:
            conn.execute("UPDATE Courses SET parent_id = ? WHERE id = ?;", (parent_id, course_id))

    conn.commit()

    students = conn.execute("SELECT id FROM Students").fetchall()
    courses = conn.execute("SELECT id FROM Courses").fetchall()

    # Vloženie náhodných zápisov do kurzov
    for _ in range(15):
        student_id = random.choice(students)[0]
        course_id = random.choice(courses)[0]
        conn.execute("INSERT INTO Enrollments (student_id, course_id) VALUES (?, ?);", (student_id, course_id))

    conn.commit()
    conn.close()

# ----------------- Spoločné funkcie -----------------

# Funkcia pre spustenie SQL dotazu s obmedzením času
def query_worker(path, db_name, queue):
    try:
        conn = sqlite3.connect(db_name)
        cur = conn.cursor()
        with open(path, "r") as f:
            query = f.read()
        cur.execute(query)
        rows = cur.fetchall()
        conn.close()
        queue.put(rows)
    except Exception as e:
        queue.put(f"ERROR: {e}")

# Funkcia na spustenie dotazu s časovým limitom
def run_query_with_timeout(path, db_name, timeout_seconds):
    queue = Queue()
    p = Process(target=query_worker, args=(path, db_name, queue))
    p.start()
    p.join(timeout_seconds)

    if p.is_alive():
        p.terminate()
        p.join()
        return "TLE"

    if queue.empty():
        return "ERROR: No result"

    return queue.get()

# Funkcia na normalizáciu výsledkov z dotazov
def normalize_result(result, query):
    if isinstance(result, str):
        return result
    return frozenset(sorted(set(result)))

# Funkcia na zistenie väčšinového výsledku zo všetkých študentov
def find_majority_result(normalized_results):
    countable = [v for v in normalized_results.values() if isinstance(v, (tuple, frozenset))]
    result_counts = Counter(countable)
    total = len(normalized_results)

    if not result_counts:
        return None, 0

    most_common, count = result_counts.most_common(1)[0]
    if count > total / 2:
        return most_common, count
    return None, count

# Funkcia na porovnanie výsledkov medzi študentmi
def compare_results(results, queries_by_student):
    normalized_results = {
        student: normalize_result(result, queries_by_student.get(student, ""))
        for student, result in results.items()
    }

    majority_result, count = find_majority_result(normalized_results)
    total = len(normalized_results)

    evaluation = {}

    if majority_result is None:
        print("\nVýsledky sú nejednoznačné – žiadna odpoveď nemá nadpolovičnú väčšinu.\n")
        for student in normalized_results:
            evaluation[student] = (
                normalized_results[student]
                if isinstance(normalized_results[student], str)
                else "FAIL"
            )
    else:
        print(f"\nPrijatý výsledok ako správny (viac ako polovica - {count}/{total})\n")
        for student, norm_result in normalized_results.items():
            if norm_result == majority_result:
                evaluation[student] = "OK"
            elif isinstance(norm_result, str):
                evaluation[student] = norm_result
            else:
                evaluation[student] = "FAIL"

    for student, status in evaluation.items():
        print(f"{student}: {status}")

    return evaluation

# Funkcia na uloženie výsledkov do CSV súboru
def save_results_to_csv(results, output_file):
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Student", "Výsledok"])
        for student, result in results.items():
            writer.writerow([student, result])
    print(f"Výsledky sú uložené v {output_file}")

# ----------------- Argumenty -----------------

# Funkcia na spracovanie argumentov z príkazového riadku
def parse_arguments():
    parser = argparse.ArgumentParser(description="Porovnanie SQL dotazov študentov.")
    parser.add_argument("--students", default="data/students", help="Cesta k priečinku so SQL dotazmi študentov.")
    parser.add_argument("--tables", default="data/createTables/createTables.txt", help="Cesta k definícii tabuliek.")
    parser.add_argument("--output", default="results.csv", help="Výstupný CSV súbor s výsledkami.")
    parser.add_argument("--timeout", type=int, default=3, help="Časový limit na vykonanie dotazu (v sekundách).")
    parser.add_argument("--random-db", action="store_true", help="Povoliť náhodné dáta v databáze.")
    return parser.parse_args()

# ----------------- Hlavná funkcia -----------------

def main():
    args = parse_arguments()

    db_name = "student_queries.db"
    students_folder = args.students
    tables_path = args.tables
    output_file = args.output
    timeout_seconds = args.timeout
    use_random_db = args.random_db

    if not use_random_db:
        print("Používame stabilnú databázu s fixnými údajmi.")
        create_stable_database(db_name, tables_path)
    else:
        print("Používame náhodnú databázu.")
        try:
            create_random_database(db_name, tables_path)
            insert_random_data(db_name)
        except Exception as e:
            print(f"Chyba pri náhodnej databáze: {e}")
            exit(1)

    student_results = {}
    queries_by_student = {}

    # Spracovanie dotazov pre študentov
    for file in os.listdir(students_folder):
        if file.endswith(".sql"):
            path = os.path.join(students_folder, file)
            student_name = file[:-4]
            with open(path, "r") as f:
                query = f.read()
            result = run_query_with_timeout(path, db_name, timeout_seconds)
            student_results[student_name] = result
            queries_by_student[student_name] = query

    # Vyhodnotenie výsledkov a generovanie spätných väzieb pre študentov
    evaluation = compare_results(student_results, queries_by_student)
    save_results_to_csv(evaluation, output_file)

    # Generovanie AI spätnej väzby pre neúspešných študentov
    print("\n== AI spätná väzba (iba pre FAIL) ==\n")
    for student, result in evaluation.items():
        if result == "FAIL":
            feedback = get_ai_feedback(student, queries_by_student[student], result)
            print(f"\n{student}:")
            print(feedback)

if __name__ == "__main__":
    main()
