# Evaluation results

- Dataset: synthetic_health_records.csv (1,030 records)
- Answer key: synthetic_health_records_answer_key.csv
- Rules: synthetic_rules.json
- Missing-value markers: n/a, na, null, none, nan, -, --
- Analysis time (duplicates + missing + validation): 0.092 seconds
- Environment: Python 3.12.9, pandas 3.1.0, Windows

## Detection accuracy

| Check | Injected | Flagged | Correct | False positives | Missed | Precision | Recall |
|---|---|---|---|---|---|---|---|
| Duplicate rows (extra copies) | 30 | 30 | 30 | 0 | 0 | 1.00 | 1.00 |
| Missing cells | 85 | 85 | 85 | 0 | 0 | 1.00 | 1.00 |
| Validation failures | 90 | 90 | 90 | 0 | 0 | 1.00 | 1.00 |

## Recall by issue type

| Issue | Column | Kind | Injected | Detected |
|---|---|---|---|---|
| invalid | age | not a number | 10 | 10 |
| invalid | age | out of range | 20 | 20 |
| invalid | email | malformed | 20 | 20 |
| invalid | sex | not allowed | 10 | 10 |
| invalid | visit_date | impossible date | 10 | 10 |
| invalid | visit_date | wrong format | 20 | 20 |
| missing | age | blank | 25 | 25 |
| missing | age | marker | 15 | 15 |
| missing | email | blank | 20 | 20 |
| missing | email | marker | 10 | 10 |
| missing | name | blank | 10 | 10 |
| missing | visit_date | whitespace-only | 5 | 5 |

## Mismatches

None. Every injected issue was found and nothing else was flagged.

These figures come from one synthetic dataset built to match the rules, so they show the checker does what it was configured to do. They do not show how it would perform on real data.
