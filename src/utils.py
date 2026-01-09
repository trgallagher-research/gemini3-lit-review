"""
Shared utilities for the literature review extraction pipeline.
"""

import os
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(text: str, max_length: int = 50) -> str:
    """
    Convert text to a safe filename.

    Args:
        text: The text to convert
        max_length: Maximum length of the filename

    Returns:
        A safe filename string
    """
    # Remove or replace unsafe characters
    safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in text)
    # Replace spaces with underscores
    safe = safe.replace(" ", "_")
    # Remove consecutive underscores
    while "__" in safe:
        safe = safe.replace("__", "_")
    # Trim to max length
    if len(safe) > max_length:
        safe = safe[:max_length].rstrip("_")
    return safe


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length, adding suffix if truncated.

    Args:
        text: The text to truncate
        max_length: Maximum length including suffix
        suffix: String to append if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_api_key(env_var: str = "GEMINI_API_KEY") -> Optional[str]:
    """
    Get API key from environment variable.

    Args:
        env_var: Name of the environment variable

    Returns:
        API key string or None if not found
    """
    return os.getenv(env_var)


def count_files_by_extension(folder: Path, extension: str) -> int:
    """Count files with a specific extension in a folder."""
    if not folder.exists():
        return 0
    return len(list(folder.glob(f"*{extension}")))


def validate_pdf_file(pdf_path: Path) -> tuple[bool, str]:
    """
    Validate that a file is a PDF.

    Args:
        pdf_path: Path to the file

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not pdf_path.exists():
        return False, f"File not found: {pdf_path}"

    if not pdf_path.is_file():
        return False, f"Not a file: {pdf_path}"

    if pdf_path.suffix.lower() != ".pdf":
        return False, f"Not a PDF file: {pdf_path}"

    # Check file size (at least 1KB, less than 100MB)
    size = pdf_path.stat().st_size
    if size < 1024:
        return False, f"File too small (may be empty): {pdf_path}"
    if size > 100 * 1024 * 1024:
        return False, f"File too large (>100MB): {pdf_path}"

    # Check PDF magic bytes
    try:
        with open(pdf_path, "rb") as f:
            header = f.read(5)
            if header != b"%PDF-":
                return False, f"Invalid PDF header: {pdf_path}"
    except Exception as e:
        return False, f"Error reading file: {e}"

    return True, ""
