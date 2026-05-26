from pathlib import Path
import re
import unicodedata


def slugify(value: str | None, fallback: str = "unknown") -> str:
    if not value:
        return fallback
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or fallback


def safe_filename(filename: str | None) -> str:
    filename = filename or "uploaded-file"
    path = Path(filename)
    stem = slugify(path.stem, fallback="file")
    suffix = path.suffix.lower()
    return f"{stem}{suffix}"
