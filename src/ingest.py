"""
Parse Microsoft Forms Excel export and prepare project configuration.
No LLM calls - pure structural transformation.
"""

import pandas as pd
import yaml
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


def parse_form_response(excel_path: Path) -> dict:
    """
    Parse Excel export from Microsoft Forms.
    Returns structured project data.
    """
    df = pd.read_excel(excel_path)

    # Forms exports one row per response - get the latest
    row = df.iloc[-1]

    # Parse project metadata
    project = {
        "name": str(row.get("project_name", "Untitled Project")).strip(),
        "requester": str(row.get("requester_name", "Unknown")).strip(),
        "email": str(row.get("requester_email", "")).strip(),
        "description": str(row.get("project_description", "")).strip(),
        "date": datetime.now().strftime("%Y-%m-%d")
    }

    # Parse research questions
    rq_count = int(row.get("rq_count", 1))
    research_questions = []

    for i in range(1, rq_count + 1):
        rq_id = str(row.get(f"rq{i}_id", "")).strip()
        rq_text = str(row.get(f"rq{i}_text", "")).strip()
        rq_keywords = row.get(f"rq{i}_keywords", "")

        if rq_id and rq_text:
            # Handle NaN values for keywords
            if pd.isna(rq_keywords):
                keywords = []
            else:
                keywords = [k.strip() for k in str(rq_keywords).split(",") if k.strip()]
            research_questions.append({
                "id": rq_id,
                "text": rq_text,
                "keywords": keywords
            })

    # Parse source citations
    citations_raw = str(row.get("source_citations", ""))
    sources = parse_source_citations(citations_raw)

    # Parse context
    context_raw = {
        "description": str(row.get("context_description", "")).strip(),
        "population": str(row.get("context_population", "")).strip(),
        "constructs": str(row.get("context_constructs", "")).strip(),
        "focus": str(row.get("context_focus", "")).strip() if not pd.isna(row.get("context_focus")) else ""
    }

    return {
        "project": project,
        "research_questions": research_questions,
        "sources": sources,
        "context_raw": context_raw,
        "pdf_folder_link": str(row.get("pdf_folder_link", "")).strip() if not pd.isna(row.get("pdf_folder_link")) else ""
    }


def parse_source_citations(citations_text: str) -> dict:
    """
    Parse newline-separated citations into numbered dict.

    Input:
        Kong et al. (2023) - Media multitasking meta-analysis
        Rioja et al. (2023) - Executive function longitudinal study

    Output:
        {1: {"citation": "Kong et al. (2023)", "title": "Media multitasking meta-analysis"}, ...}
    """
    sources = {}
    lines = [line.strip() for line in citations_text.split("\n") if line.strip()]

    for i, line in enumerate(lines, start=1):
        # Try to split on " - " for citation - title format
        if " - " in line:
            citation, title = line.split(" - ", 1)
        else:
            citation = line
            title = ""

        # Extract author and year for filename
        author_year = extract_author_year(citation)

        sources[i] = {
            "citation": citation.strip(),
            "title": title.strip(),
            "author_year": author_year,
            "original_filename": None,  # To be matched later
            "renamed_filename": f"{i:02d}_{author_year}.pdf"
        }

    return sources


def extract_author_year(citation: str) -> str:
    """
    Extract author and year from citation for filename.
    'Kong et al. (2023)' -> 'Kong_2023'
    'Smith & Jones (2024)' -> 'Smith_Jones_2024'
    """
    # Extract year
    year_match = re.search(r"\((\d{4})\)", citation)
    year = year_match.group(1) if year_match else "XXXX"

    # Extract first author(s)
    author_part = re.sub(r"\s*\(\d{4}\).*", "", citation)
    author_part = re.sub(r"\s*et al\.?", "", author_part)
    author_part = re.sub(r"\s*&\s*", "_", author_part)
    author_part = re.sub(r"[^a-zA-Z_]", "", author_part)

    # Clean up multiple underscores
    while "__" in author_part:
        author_part = author_part.replace("__", "_")
    author_part = author_part.strip("_")

    if not author_part:
        author_part = "Unknown"

    return f"{author_part}_{year}"


def match_pdfs_to_sources(sources: dict, pdf_folder: Path) -> tuple[dict, list]:
    """
    Attempt to match PDF files to source citations.
    Uses fuzzy matching on author names and years.
    Returns updated sources dict with original_filename populated.
    """
    if not pdf_folder.exists():
        return sources, []

    pdf_files = list(pdf_folder.glob("*.pdf"))
    unmatched_pdfs = list(pdf_files)

    for source_num, source in sources.items():
        author_year = source["author_year"].lower()
        author_parts = [p.lower() for p in author_year.split("_") if p and p != "xxxx"]
        best_match = None
        best_score = 0

        for pdf in unmatched_pdfs:
            pdf_name = pdf.stem.lower()
            # Scoring: count matching parts
            score = 0
            for part in author_parts:
                if len(part) >= 3 and part in pdf_name:  # Only match meaningful parts
                    score += 1

            # Also check for year match
            year_match = re.search(r"\d{4}", source["author_year"])
            if year_match and year_match.group() in pdf_name:
                score += 1

            if score > best_score:
                best_score = score
                best_match = pdf

        if best_match and best_score > 0:
            source["original_filename"] = best_match.name
            unmatched_pdfs.remove(best_match)

    return sources, [p.name for p in unmatched_pdfs]


def rename_pdfs(sources: dict, input_folder: Path, output_folder: Path) -> None:
    """
    Copy and rename PDFs to numbered format.
    """
    output_folder.mkdir(parents=True, exist_ok=True)

    for source_num, source in sources.items():
        if source.get("original_filename"):
            src = input_folder / source["original_filename"]
            dst = output_folder / source["renamed_filename"]
            if src.exists():
                shutil.copy2(src, dst)
                print(f"  {source_num:2d}. {source['original_filename']} -> {source['renamed_filename']}")
            else:
                print(f"  {source_num:2d}. [WARNING] Source file not found: {source['original_filename']}")
        else:
            print(f"  {source_num:2d}. [SKIPPED] No matching PDF for: {source['citation'][:40]}...")


def generate_yaml_config(parsed_data: dict, output_path: Path) -> None:
    """
    Generate project.yaml from parsed form data.
    """
    # Build sources dict with only the fields needed for config
    sources_config = {}
    for num, s in parsed_data["sources"].items():
        sources_config[num] = {
            "citation": s["citation"],
            "title": s["title"],
            "filename": s["renamed_filename"]
        }

    config = {
        "project": parsed_data["project"],
        "research_questions": parsed_data["research_questions"],
        "sources": sources_config,
        "context_raw": parsed_data["context_raw"],
        "context_translated": None,  # Populated in Phase 2
        "settings": {
            "extraction_model": "gemini-3-pro-preview",
            "framing_model": "gemini-3-flash-preview",
            "temperature": 0.2,
            "require_quotes": True
        }
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def validate_setup(sources: dict, pdf_folder: Path) -> list:
    """
    Validate that all required files exist.
    Returns list of errors.
    """
    errors = []

    for source_num, source in sources.items():
        if not source.get("original_filename"):
            errors.append(f"Source {source_num} ({source['citation'][:40]}...): No matching PDF found")
        else:
            pdf_path = pdf_folder / source["original_filename"]
            if not pdf_path.exists():
                errors.append(f"Source {source_num}: File not found: {source['original_filename']}")

    return errors


def create_sample_excel(output_path: Path) -> None:
    """
    Create a sample Excel file that matches the expected Microsoft Forms format.
    Useful for testing or as a template.
    """
    data = {
        "project_name": ["Sample Literature Review"],
        "requester_name": ["John Doe"],
        "requester_email": ["john.doe@example.com"],
        "project_description": ["A systematic review of technology use in education"],
        "rq_count": [2],
        "rq1_id": ["RQ1"],
        "rq1_text": ["What is the impact of technology on student learning outcomes?"],
        "rq1_keywords": ["technology, learning, outcomes, education"],
        "rq2_id": ["RQ2"],
        "rq2_text": ["How does screen time affect cognitive development in adolescents?"],
        "rq2_keywords": ["screen time, cognitive, development, adolescents"],
        "rq3_id": [""],
        "rq3_text": [""],
        "rq3_keywords": [""],
        "rq4_id": [""],
        "rq4_text": [""],
        "rq4_keywords": [""],
        "rq5_id": [""],
        "rq5_text": [""],
        "rq5_keywords": [""],
        "source_citations": ["Smith et al. (2023) - Digital learning meta-analysis\nJones & Brown (2022) - Screen time longitudinal study\nWilliams (2024) - Educational technology review"],
        "pdf_folder_link": ["https://example.com/shared/pdfs"],
        "context_description": ["This review examines the effects of digital technology and screen-based devices on learning and cognitive development in school-age children and adolescents."],
        "context_population": ["Children and adolescents aged 6-18"],
        "context_constructs": ["Technology use, screen time, learning outcomes, cognitive development, academic performance"],
        "context_focus": ["Educational settings"]
    }

    df = pd.DataFrame(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False, engine="openpyxl")
    print(f"Sample Excel file created at: {output_path}")
