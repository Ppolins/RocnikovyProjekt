import sqlite3
import os
import random
import string
import csv
import ast
import signal
from collections import Counter

DB_NAME = "student_queries.db"
CREATE_TABLES_PATH = "data/createTables/createTables.txt"
STUDENTS_FOLDER = "data/students"
RESULTS_CSV = "results.csv"
TIMEOUT_SECONDS = 3

# PREPÍNAČ DATABÁZY:
# Ak je True – vytvárame stabilnú databázu s fixnými údajmi,
# ak je False – vytvárame náhodnú (nestabilnú) databázu s generovanými dátami
USE_STABLE_DB = True

# ----------------- Stabilná databáza s fixnými údajmi -----------------

def load_tables_from_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
        tables = ast.literal_eval(content)
    return tables

def create_stable_database():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    conn = sqlite3.connect(DB_NAME)
    conn.execute('PRAGMA foreign_keys = ON')
    tables = load_tables_from_file(CREATE_TABLES_PATH)

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

    # Fixné vložené údaje do tabuliek
    conn.executemany("INSERT INTO Students (name) VALUES (?)", [
        ('Alice',), ('Bob',), ('Charlie',), ('Diana',)
    ])
    conn.executemany("INSERT INTO Courses (title, parent_id) VALUES (?, ?)", [
        ('math', None),  # id = 1
        ('algebra', 1),  # id = 2
        ('geometry', 1),  # id = 3
        ('history', None), # id = 4
        ('english', None)  # id = 5
    ])
    conn.executemany("INSERT INTO Enrollments (student_id, course_id) VALUES (?, ?)", [
        (1, 4), (2, 5), (3, 1), (4, 4), (1, 2)
    ])

    conn.commit()
    conn.close()

# ----------------- Náhodná (nestabilná) databáza s generovanými dátami -----------------

def random_word(length=5):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def create_random_database():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    conn = sqlite3.connect(DB_NAME)
    conn.execute('PRAGMA foreign_keys = ON')
    tables = load_tables_from_file(CREATE_TABLES_PATH)

    for table_name, columns in tables.items():
        try:
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

        except Exception as e:
            print(f"Chyba pri vytváraní tabuľky {table_name}: {e}")

    conn.commit()
    conn.close()

def insert_random_data():
    conn = sqlite3.connect(DB_NAME)

    # Vkladáme náhodných študentov
    for _ in range(10):
        name = random_word(7)
        conn.execute("INSERT INTO Students (name) VALUES (?);", (name,))

    # Vkladáme náhodné kurzy bez parent_id (najskôr NULL)
    for _ in range(5):
        title = random_word(10)
        conn.execute("INSERT INTO Courses (title, parent_id) VALUES (?, NULL);", (title,))

    conn.commit()

    # Teraz nastavíme parent_id pre niektoré kurzy, aby sme vytvorili hierarchiu
    courses = conn.execute("SELECT id FROM Courses").fetchall()
    for course in courses:
        course_id = course[0]
        parent_id = random.choice(courses)[0]
        # Kontrola, aby kurz nebol svojím vlastným rodičom
        if course_id != parent_id:
            try:
                conn.execute("UPDATE Courses SET parent_id = ? WHERE id = ?;", (parent_id, course_id))
            except Exception as e:
                print(f"Chyba pri nastavovaní parent_id pre kurz {course_id}: {e}")

    conn.commit()

    # Vkladáme zápisy študentov do kurzov náhodne
    students = conn.execute("SELECT id FROM Students").fetchall()
    courses = conn.execute("SELECT id FROM Courses").fetchall()

    for _ in range(15):
        student_id = random.choice(students)[0]
        course_id = random.choice(courses)[0]
        conn.execute("INSERT INTO Enrollments (student_id, course_id) VALUES (?, ?);", (student_id, course_id))

    conn.commit()
    conn.close()

# ----------------- Spoločné funkcie pre vykonávanie dotazov a analýzu výsledkov -----------------

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException()

def run_query_with_timeout(path):
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(TIMEOUT_SECONDS)

    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        with open(path, "r") as f:
            query = f.read()
        cur.execute(query)
        rows = cur.fetchall()
        signal.alarm(0)
        return [tuple(row) for row in rows]
    except TimeoutException:
        return "TLE"
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        signal.alarm(0)

def normalize_result(result, query):
    if isinstance(result, str):
        return result
    # Ignorujeme poradie výsledkov, ak dotaz obsahuje ORDER BY,
    # aby sme posúdili správnosť aj pri rozdielnom poradí
    return frozenset(sorted(set(result)))

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

def save_results_to_csv(results):
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Student", "Výsledok"])
        for student, result in results.items():
            writer.writerow([student, result])
    print(f"Výsledky sú uložené v {RESULTS_CSV}")

# Hlavná funkcia

def main():
    if USE_STABLE_DB:
        print("Používame stabilnú databázu s fixnými údajmi.")
        create_stable_database()
    else:
        print("Používame náhodnú (nestabilnú) databázu.")
        create_random_database()
        insert_random_data()

    student_results = {}
    queries_by_student = {}

    for file in os.listdir(STUDENTS_FOLDER):
        if file.endswith(".sql"):
            path = os.path.join(STUDENTS_FOLDER, file)
            student_name = file[:-4]
            with open(path, "r") as f:
                query = f.read()
            result = run_query_with_timeout(path)
            student_results[student_name] = result
            queries_by_student[student_name] = query

    print("\n== Výsledky študentov ==\n")
    for student, result in student_results.items():
        print(f"{student}: {result}")
    evaluation = compare_results(student_results, queries_by_student)
    save_results_to_csv(evaluation)

if __name__ == "__main__":
    main()
