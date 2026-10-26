import os


def database_url() -> str:
    """Where to keep state. Local default is a SQLite file.

    In the cloud this is set to a PostgreSQL URL such as:
    postgresql+psycopg://user:password@host:5432/dbname
    """
    return os.environ.get("DATABASE_URL", "sqlite:///checker.db")


def store_values() -> bool:
    """Whether to keep the actual cell values of issues. Off by default,
    so the database holds counts and locations, not patient contents."""
    return os.environ.get("STORE_VALUES", "false").strip().lower() in {"1", "true", "yes"}

def s3_bucket() -> str | None:
    """Name of the S3 bucket for saved files. Unset means use a local folder."""
    return os.environ.get("S3_BUCKET") or None


def artifact_dir() -> str:
    """Local folder for saved files when no S3 bucket is configured."""
    return os.environ.get("ARTIFACT_DIR", "artifacts")