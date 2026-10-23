# CSV Data Quality Checker

A lightweight Python tool for finding and reporting common data-quality problems in CSV files. Upload a file, review what was found, optionally remove exact duplicate rows, and download a cleaned CSV and a data-quality report.

The project is inspired by data-quality challenges in health information management. It is a small, demonstrable tool, not a healthcare information system. It runs locally and uses only synthetic data.

## What it does

- **Upload and preview** a CSV: record count, columns, first rows.
- **Exact duplicate detection**: counts extra copies and duplicate groups and lists their row numbers.
- **Missing-value detection**: blank cells, whitespace-only cells and configurable markers (`N/A`, `null`, `-`, ...), with counts and percentages per column.
- **Format and validity checks** from a JSON rules file: `email`, `date`, `range` and `allowed` (a list of permitted values).
- **Data-quality summary**: records analysed, duplicates, missing cells, validation failures, affected rows and columns.
- **Controlled cleaning**: the only cleaning action is removing exact duplicate rows, and only if the user ticks the box. The rows to be removed are shown first.
- **Downloads**: a cleaned CSV and a Markdown report documenting every issue and every cleaning action.

### Design principles

- **Report before changing.** Nothing is altered until the user asks.
- **No silent fixes.** Missing values are never filled and invalid entries are never edited. They stay in the cleaned file and are documented in the report.
- **No double counting.** Missing cells are skipped by the validation rules, so a blank age is reported once, as missing.
- **Row numbers match CSV line numbers** (the header is line 1), so every issue can be found in the original file.

## Installation

Requires Python 3.10 or newer.

```
git clone https://github.com/<your-username>/csv-quality-checker.git
cd csv-quality-checker
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux, activate with `source .venv/bin/activate`.

## Usage

```
streamlit run app.py
```

1. Upload a CSV file.
2. Review the duplicate, missing-value and validation sections. Edit the missing-value markers if needed.
3. Optionally upload your own rules file. Otherwise `rules/example_rules.json` is used.
4. Choose whether to remove exact duplicates, then download the cleaned CSV and the report.

### Rules file format

```json
{
  "rules": [
    { "column": "age", "type": "range", "min": 0, "max": 120 },
    { "column": "sex", "type": "allowed", "values": ["M", "F"] },
    { "column": "email", "type": "email" },
    { "column": "visit_date", "type": "date", "format": "%Y-%m-%d" }
  ]
}
```

Rules that name a missing column or an unknown type are reported as warnings and skipped.

## Project structure

```
app.py                              Streamlit interface
checker/duplicates.py               exact duplicate detection
checker/missing.py                  missing-value detection
checker/validation.py               rule-based validation
checker/report.py                   summary, cleaning and report generation
rules/example_rules.json            example validation rules
rules/synthetic_rules.json          rules used for the evaluation
data/synthetic_health_records.csv   synthetic test dataset
data/synthetic_health_records_answer_key.csv   every injected issue
scripts/generate_synthetic_data.py  reproducible dataset generator (fixed seed)
scripts/evaluate.py                 compares detections with the answer key
tests/                              Pytest tests
```

## Testing

```
python -m pytest -v
```

The tests cover duplicates, missing values, validation rules, report generation and edge cases (header-only files, empty files, malformed CSVs, unexpected values).

## Evaluation

The dataset is generated with `python scripts/generate_synthetic_data.py`. It contains 1,030 invented records: 1,000 unique records plus 30 exact duplicate rows. Known issues were injected and recorded in an answer key: 85 missing cells, 90 invalid cells and 30 duplicate rows. `python scripts/evaluate.py` compares what the tool detects with the answer key.

Measured results (full output in `evaluation_results.md`):

| Check | Injected | Correct | False positives | Missed | Precision | Recall |
|---|---|---|---|---|---|---|
| Duplicate rows (extra copies) | 30 | 30 | 0 | 0 | 1.00 | 1.00 |
| Missing cells | 85 | 85 | 0 | 0 | 1.00 | 1.00 |
| Validation failures | 90 | 90 | 0 | 0 | 1.00 | 1.00 |

Analysis time on the 1,030-record dataset: **<your time> seconds** (<your Python version>, <your OS>).

**How to read these results.** The dataset was built around the same rules the checker applies, so perfect scores show that the code does what it was configured to do. They do not show how the tool would perform on real, messy data, where problems are less predictable.

Counting conventions: duplicates are counted as extra copies (the first occurrence is treated as the original); missing and invalid values are counted per cell.

## Limitations

This version does not:

- Identify near-duplicates or records that belong to the same person when details differ (for example, spelling variations in names).
- Decide whether a value is factually correct without a validation rule to compare it against.
- Infer replacements for missing or invalid values.
- Treat ambiguous values consistently with your data. For example, `12/01/2026` fails a `%Y-%m-%d` date rule, and the tool does not guess whether it means 12 January or 1 December.
- Assess algorithmic fairness or how data-quality issues affect predictive models.
- Connect to production healthcare databases or process real patient information. Do not upload real patient data.
- Handle very large files. It was tested on about 1,000 records and reads the whole file into memory.

Whether a marker such as `NA` counts as missing depends on the dataset (it could be a legitimate code). The marker list is editable for this reason.

## Possible future work

Probabilistic record linkage for near-duplicates, domain-specific validation (for example, clinical code lists), and evaluating how data-quality issues affect downstream analysis.

## Licence

<choose one, for example MIT, or remove this section>
