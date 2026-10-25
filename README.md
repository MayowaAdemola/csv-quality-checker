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
git clone https://github.com/MayowaAdemola/csv-quality-checker.git
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

Analysis time on the 1,030-record dataset: **0.092 seconds** (Python 3.12.9, pandas 3.1.0, Windows). Timing varies by machine.

**How to read these results.** The dataset was built around the same rules the checker applies, so perfect scores show that the code does what it was configured to do. They do not show how the tool would perform on real, messy data, where problems are less predictable.

Counting conventions: duplicates are counted as extra copies (the first occurrence is treated as the original); missing and invalid values are counted per cell.

## Limitations

## Limitations and research directions

This is a first-stage prototype. Each limitation below is a deliberate boundary of version one, and each points to a research question I want to investigate further.

- **Exact duplicates only.** The tool cannot tell that two records belong to the same person when details differ, for example spelling variations, different name order or transliteration differences. 
*Research direction:* probabilistic record linkage, and how often linkage errors occur in health records.

- **Rules check format, not truth.** A value can be valid yet wrong, such as an age of 34 recorded instead of 43, and the tool has no reference to catch it. 
*Research direction:* domain-specific validation using reference data, cross-field consistency checks and outlier detection.

- **No replacement of missing or invalid values.** The tool never fills or corrects anything. 
*Research direction:* when imputation is appropriate in health data, and how to report the uncertainty it adds.

- **Ambiguous values are not resolved.** For example, `12/01/2026` fails a `%Y-%m-%d` date rule, and the tool does not guess whether it means 12 January or 1 December. 
*Research direction:* context-aware parsing that infers a column's likely date convention and flags its confidence instead of silently converting.

- **No assessment of downstream effects.** The tool does not measure how missing values, duplicates and errors affect predictive models, or whether they affect some patient groups more than others. 
*Research direction:* data quality and algorithmic fairness, which is the central question this project is a first step towards.

- **Synthetic data only.** The tool has not been used on real patient information, and it should not be used that way. *Research direction:* privacy-preserving data-quality assessment on real health information systems, with proper ethical approval and data governance.
- **Small scale.** It was tested on about 1,000 records and reads the whole file into memory. 
*Research direction:* scalable, chunked processing and benchmarking on larger datasets.

Whether a marker such as `NA` counts as missing depends on the dataset (it could be a legitimate code). The marker list is editable for this reason.

## Possible future work

Probabilistic record linkage for near-duplicates, domain-specific validation (for example, clinical code lists), and evaluating how data-quality issues affect downstream analysis.