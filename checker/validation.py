import json

import pandas as pd

from checker.missing import DEFAULT_MARKERS

EMAIL_PATTERN = r"[^@\s]+@[^@\s]+\.[^@\s]+"


def load_rules(text) -> list:
    """Parse a JSON rules file: {"rules": [ {...}, {...} ]}."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Rules file is not valid JSON: {e}")
    rules = data.get("rules") if isinstance(data, dict) else None
    if not isinstance(rules, list):
        raise ValueError('Rules file must look like {"rules": [ ... ]}.')
    return rules


# Each check receives the non-missing, trimmed values of one column and
# returns a Series of the same index: "" if the value is fine, otherwise
# a short description of the problem.

def _check_email(values, rule):
    ok = values.str.fullmatch(EMAIL_PATTERN)
    return ok.map({True: "", False: "invalid email format"})


def _check_date(values, rule):
    fmt = rule.get("format", "%Y-%m-%d")
    parsed = pd.to_datetime(values, format=fmt, errors="coerce")
    return parsed.notna().map({True: "", False: f"not a valid date in format {fmt}"})


def _check_range(values, rule):
    nums = pd.to_numeric(values, errors="coerce")
    lo, hi = rule.get("min"), rule.get("max")
    problem = pd.Series("", index=values.index)
    problem[nums.isna()] = "not a number"
    if lo is not None:
        problem[nums < lo] = "outside range"
    if hi is not None:
        problem[nums > hi] = "outside range"
    return problem


def _check_allowed(values, rule):
    allowed = [str(v) for v in rule.get("values", [])]
    ok = values.isin(allowed)
    return ok.map({True: "", False: "not in allowed values"})


CHECKS = {
    "email": _check_email,
    "date": _check_date,
    "range": _check_range,
    "allowed": _check_allowed,
}


def _label(rule) -> str:
    kind = rule["type"]
    if kind == "email":
        return "email format"
    if kind == "date":
        return f"date ({rule.get('format', '%Y-%m-%d')})"
    if kind == "range":
        return f"range {rule.get('min', '-')} to {rule.get('max', '-')}"
    return "allowed values"


def validate(df: pd.DataFrame, rules: list, markers=None) -> dict:
    """Apply validation rules without modifying the data.

    Missing cells (blank, whitespace-only, or a marker) are skipped so they
    are not double-counted. Row numbers match CSV line numbers (header = 1).
    """
    if markers is None:
        markers = DEFAULT_MARKERS
    marker_set = {m.strip().lower() for m in markers if m.strip()}

    failures, summary_rows, config_errors = [], [], []

    for rule in rules:
        if not isinstance(rule, dict):
            config_errors.append(f"Rule skipped: {rule!r} is not an object.")
            continue
        col, kind = rule.get("column"), rule.get("type")
        if col not in df.columns:
            config_errors.append(f"Rule for column '{col}' skipped: column not found in file.")
            continue
        if kind not in CHECKS:
            config_errors.append(f"Rule for column '{col}' skipped: unknown type '{kind}'.")
            continue

        stripped = df[col].str.strip()
        skip = (stripped == "") | stripped.str.lower().isin(marker_set)
        to_check = stripped[~skip]

        problems = CHECKS[kind](to_check, rule)
        bad = problems[problems != ""]
        label = _label(rule)

        for idx, problem in bad.items():
            failures.append(
                {
                    "row_number": idx + 2,
                    "column": col,
                    "value": df.at[idx, col],
                    "rule": label,
                    "problem": problem,
                }
            )
        summary_rows.append(
            {"column": col, "rule": label, "checked": len(to_check), "failures": len(bad)}
        )

    details = pd.DataFrame(
        failures, columns=["row_number", "column", "value", "rule", "problem"]
    )
    details = details.sort_values(["row_number", "column"], kind="stable").reset_index(drop=True)
    summary = pd.DataFrame(summary_rows, columns=["column", "rule", "checked", "failures"])

    return {
        "total_failures": len(details),
        "summary": summary,
        "details": details,
        "config_errors": config_errors,
    }