"""Generate a reproducible synthetic health-records CSV with known issues.

Writes two files to data/:
  synthetic_health_records.csv              the dataset to analyse
  synthetic_health_records_answer_key.csv   every injected issue (ground truth)

All records are invented. No real patient data is used.
Run from the project root:  python scripts/generate_synthetic_data.py
"""
import csv
import random
from pathlib import Path

SEED = 42
N_RECORDS = 1000
N_DUPLICATES = 30

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_FILE = DATA_DIR / "synthetic_health_records.csv"
KEY_FILE = DATA_DIR / "synthetic_health_records_answer_key.csv"

COLUMNS = ["patient_id", "name", "age", "sex", "email", "visit_date"]

FIRST_NAMES = [
    "Amina", "Chidi", "Ngozi", "Tunde", "Fatima", "Emeka", "Zainab", "Ibrahim",
    "Chioma", "Segun", "Hauwa", "Kelechi", "Aisha", "Obinna", "Yetunde", "Musa",
]
LAST_NAMES = [
    "Bello", "Okafor", "Eze", "Adeyemi", "Abubakar", "Nwosu",
    "Ogunleye", "Danjuma", "Ibekwe", "Lawal", "Chukwu", "Balogun",
]

# (column, detail, values to choose from, how many cells)
MISSING_SPECS = [
    ("age", "blank", [""], 25),
    ("age", "marker", ["N/A", "-", "null", "NA"], 15),
    ("email", "blank", [""], 20),
    ("email", "marker", ["N/A", "None"], 10),
    ("name", "blank", [""], 10),
    ("visit_date", "whitespace-only", ["  "], 5),
]
INVALID_SPECS = [
    ("age", "out of range", ["-5", "121", "150", "200"], 20),
    ("age", "not a number", ["abc", "thirty"], 10),
    ("email", "malformed", ["no-at-sign.example.com", "chidi@example",
                            "a b@example.com", "x@@example.com"], 20),
    ("visit_date", "wrong format", ["12/01/2026", "2026/01/12", "Jan 12 2026"], 20),
    ("visit_date", "impossible date", ["2026-02-30", "2026-13-01"], 10),
    ("sex", "not allowed", ["X", "Unknown", "male"], 10),
]


def clean_record(i, rng):
    first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
    return {
        "patient_id": f"P{i:04d}",
        "name": f"{first} {last}",
        "age": str(rng.randint(1, 95)),
        "sex": rng.choice(["M", "F"]),
        "email": f"{first}.{last}{i}@example.com".lower(),
        "visit_date": f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
    }


def main():
    rng = random.Random(SEED)
    rows = [clean_record(i, rng) for i in range(1, N_RECORDS + 1)]

    used = set()   # (row index, column) cells that already carry an issue
    issues = []    # (row index, column, issue_type, detail)

    def inject(specs, issue_type):
        for column, detail, values, n in specs:
            candidates = [i for i in range(len(rows)) if (i, column) not in used]
            for i in rng.sample(candidates, n):
                used.add((i, column))
                rows[i][column] = rng.choice(values)
                issues.append((i, column, issue_type, detail))

    inject(MISSING_SPECS, "missing")
    inject(INVALID_SPECS, "invalid")

    # Exact duplicates are copies of rows with no other issue, placed right
    # after their original, so the copy is always the later ("extra") row.
    dirty_rows = {i for i, _ in used}
    clean_rows = [i for i in range(len(rows)) if i not in dirty_rows]
    sources = rng.sample(clean_rows, N_DUPLICATES)

    entries = [(float(i), i, False) for i in range(len(rows))]
    entries += [(i + rng.uniform(0.1, 0.9), i, True) for i in sources]
    entries.sort(key=lambda e: e[0])

    new_row_number = {}   # original index -> CSV line number
    dup_row_numbers = []
    for position, (_, i, is_copy) in enumerate(entries):
        line = position + 2          # header is line 1
        if is_copy:
            dup_row_numbers.append(line)
        else:
            new_row_number[i] = line

    DATA_DIR.mkdir(exist_ok=True)
    with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for _, i, _ in entries:
            writer.writerow(rows[i])

    key_rows = [
        (new_row_number[i], column, issue_type, detail)
        for i, column, issue_type, detail in issues
    ]
    key_rows += [(line, "(whole row)", "duplicate", "exact copy") for line in dup_row_numbers]
    key_rows.sort(key=lambda r: (r[0], r[1]))

    with open(KEY_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["row_number", "column", "issue_type", "detail"])
        writer.writerows(key_rows)

    n_missing = sum(1 for r in key_rows if r[2] == "missing")
    n_invalid = sum(1 for r in key_rows if r[2] == "invalid")
    print(f"Wrote {len(entries)} records to {DATA_FILE.name}")
    print(f"Injected: {n_missing} missing cells, {n_invalid} invalid cells, "
          f"{len(dup_row_numbers)} duplicate rows")
    print(f"Answer key: {KEY_FILE.name}")


if __name__ == "__main__":
    main()