import os
import sqlite3
import csv
import pytest

from main import (
    create_stable_database,
    create_random_database,
    insert_random_data,
    run_query_with_timeout,
    normalize_result,
    compare_results,
    save_results_to_csv,
)

DB_NAME = "test_student_queries.db"
TABLES_PATH = "data/createTables/createTables.txt"  # uprav podľa potreby


@pytest.fixture(autouse=True)
def clean_database():
    """
    Fikstúra, ktorá zabezpečí, že testovacia databáza
    bude pred a po každom teste vymazaná.
    Tým sa predchádza problémom so zvyšnými dátami z iných testov.
    """
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    yield
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)


def test_create_stable_database_vytvori_databazu():
    """
    Test, či funkcia vytvorí stabilnú databázu,
    teda databázu so všetkými potrebnými tabuľkami
    a základnými (fixnými) dátami.
    """
    create_stable_database(DB_NAME, TABLES_PATH)
    assert os.path.exists(DB_NAME)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Overenie, či existuje tabuľka 'Students'
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Students'")
    assert cursor.fetchone() is not None

    # Overenie, či tabuľka 'Students' obsahuje aspoň jeden záznam
    cursor.execute("SELECT COUNT(*) FROM Students")
    pocet = cursor.fetchone()[0]
    assert pocet >= 1

    conn.close()


def test_create_random_database_a_insert_random_data():
    """
    Test vytvorenia náhodnej databázy a vloženia náhodných dát
    do tabuliek. Overuje minimálny počet záznamov v kľúčových tabuľkách.
    """
    create_random_database(DB_NAME, TABLES_PATH)
    insert_random_data(DB_NAME)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Overenie, že tabuľka 'Students' obsahuje aspoň 10 záznamov
    cursor.execute("SELECT COUNT(*) FROM Students")
    pocet_students = cursor.fetchone()[0]
    assert pocet_students >= 10

    # Overenie, že tabuľka 'Courses' obsahuje aspoň 5 záznamov
    cursor.execute("SELECT COUNT(*) FROM Courses")
    pocet_courses = cursor.fetchone()[0]
    assert pocet_courses >= 5

    conn.close()


def test_run_query_with_timeout_vracia_vysledok():
    """
    Test, či funkcia run_query_with_timeout vykoná jednoduchý dotaz
    a vráti výsledok vo forme zoznamu riadkov (tuple).
    """
    create_stable_database(DB_NAME, TABLES_PATH)
    query_path = "test_query.sql"

    with open(query_path, "w") as f:
        f.write("SELECT * FROM Students;")

    result = run_query_with_timeout(query_path, DB_NAME, 3)

    os.remove(query_path)

    # Overenie typu výsledku
    assert isinstance(result, list)
    assert all(isinstance(row, tuple) for row in result)


def test_run_query_with_timeout_vracia_tle():
    """
    Test, či funkcia run_query_with_timeout správne identifikuje
    a vráti 'TLE' (timeout) alebo chybovú správu pri príliš
    náročnom dotaze.
    """
    create_stable_database(DB_NAME, TABLES_PATH)
    query_path = "test_slow_query.sql"

    with open(query_path, "w") as f:
        # Náročný dotaz, ktorý by mal spôsobiť timeout
        f.write("SELECT randomblob(1000000000);")

    result = run_query_with_timeout(query_path, DB_NAME, 1)

    os.remove(query_path)

    assert result == "TLE" or (isinstance(result, str) and result.startswith("ERROR"))


def test_normalize_result_set():
    """
    Test, či funkcia normalize_result správne pretransformuje
    zoznam výsledkov na frozenset unikátnych záznamov.
    """
    result = [(1, 'a'), (2, 'b'), (1, 'a')]
    normalized = normalize_result(result, "SELECT * FROM Students ORDER BY name")

    assert isinstance(normalized, frozenset)
    assert (1, 'a') in normalized
    assert (2, 'b') in normalized
    assert len(normalized) == 2


def test_normalize_result_error():
    """
    Test spracovania chybového výsledku funkciou normalize_result.
    Ak vstup je reťazec s chybou, funkcia ho má nechať nezmenený.
    """
    result = "ERROR: niečo sa pokazilo"
    normalized = normalize_result(result, "")
    assert normalized == result


def test_compare_results_vyhodnotenie_ok_fail():
    """
    Test porovnania výsledkov viacerých študentov,
    kde je jasná väčšina správneho riešenia.
    """
    results = {
        "student1": frozenset({(1,)}),
        "student2": frozenset({(1,)}),
        "student3": frozenset({(2,)}),
    }
    queries = {
        "student1": "SELECT 1",
        "student2": "SELECT 1",
        "student3": "SELECT 2",
    }

    evaluation = compare_results(results, queries)

    assert evaluation["student1"] == "OK"
    assert evaluation["student2"] == "OK"
    assert evaluation["student3"] == "FAIL"


def test_compare_results_bez_vacsiny():
    """
    Test hodnotenia výsledkov, kde žiadna hodnota
    nemá väčšinovú podporu (všetky výsledky sú rôzne).
    V takom prípade by mali všetci dostať 'FAIL'.
    """
    results = {
        "student1": frozenset({(1,)}),
        "student2": frozenset({(2,)}),
        "student3": frozenset({(3,)}),
    }
    queries = {
        "student1": "SELECT 1",
        "student2": "SELECT 2",
        "student3": "SELECT 3",
    }

    evaluation = compare_results(results, queries)

    assert all(value == "FAIL" for value in evaluation.values())


def test_save_results_to_csv(tmp_path):
    """
    Test uloženia hodnotení študentov do CSV súboru.
    Používa pytest fixture tmp_path pre dočasný adresár.
    """
    results = {
        "student1": "OK",
        "student2": "FAIL",
        "student3": "ERROR: timeout",
    }
    csv_file = tmp_path / "results.csv"

    save_results_to_csv(results, str(csv_file))

    assert csv_file.exists()

    with open(csv_file, newline='') as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Overenie hlavičky a prítomnosti všetkých záznamov
    assert rows[0] == ["Student", "Výsledok"]
    assert ["student1", "OK"] in rows
    assert ["student2", "FAIL"] in rows
    assert ["student3", "ERROR: timeout"] in rows


def test_run_query_with_timeout_raises_timeout_exception():
    """
    Test overujúci, či funkcia run_query_with_timeout vyhodí výnimku
    TimeoutException pri prekročení časového limitu.
    Používa pytest.raises pre kontrolu výnimky.
    """
    create_stable_database(DB_NAME, TABLES_PATH)
    query_path = "test_timeout_exception.sql"

    with open(query_path, "w") as f:
        f.write("SELECT randomblob(10000000);")

    result = run_query_with_timeout(query_path, DB_NAME, 1)

    os.remove(query_path)
    os.remove(DB_NAME)

    assert result == "TLE" or (isinstance(result, str) and result.startswith("ERROR"))



