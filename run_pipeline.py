#!/usr/bin/env python3
"""
Gemini 3 Literature Review Extraction Pipeline

Usage:
    python run_pipeline.py                      # Full run
    python run_pipeline.py --test               # Test with first 3 sources
    python run_pipeline.py --skip-framing       # Skip framing translation
    python run_pipeline.py --aggregate-only     # Only run aggregation
    python run_pipeline.py --force              # Force re-extraction
"""

import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.ingest import (
    parse_form_response,
    match_pdfs_to_sources,
    rename_pdfs,
    generate_yaml_config,
    validate_setup
)
from src.framing import translate_framing, create_fallback_framing
from src.extract import GeminiExtractor, run_extraction_batch
from src.aggregate import (
    load_extractions,
    generate_markdown_review,
    generate_excel_matrix,
    calculate_coverage_stats
)
from src.checkpoints import (
    checkpoint_config_review,
    checkpoint_extraction_spotcheck,
    checkpoint_final_review
)


def main():
    parser = argparse.ArgumentParser(description="Gemini 3 Literature Review Pipeline")
    parser.add_argument("--excel", type=Path, default=Path("input/form_response.xlsx"),
                        help="Path to Microsoft Forms Excel export")
    parser.add_argument("--pdfs", type=Path, default=Path("input/pdfs"),
                        help="Path to folder containing PDFs")
    parser.add_argument("--test", action="store_true",
                        help="Test mode: only process first 3 sources")
    parser.add_argument("--skip-framing", action="store_true",
                        help="Skip framing translation (use raw context)")
    parser.add_argument("--aggregate-only", action="store_true",
                        help="Skip extraction, only run aggregation")
    parser.add_argument("--force", action="store_true",
                        help="Force re-extraction (ignore existing JSONs)")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Skip confirmation prompts")
    parser.add_argument("--create-sample", action="store_true",
                        help="Create a sample Excel file and exit")
    args = parser.parse_args()

    # Handle sample creation
    if args.create_sample:
        from src.ingest import create_sample_excel
        sample_path = Path("input/sample_form_response.xlsx")
        create_sample_excel(sample_path)
        return 0

    # Load environment
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("ERROR: GEMINI_API_KEY not found or not configured in .env file")
        print("Please edit .env and add your Gemini API key")
        return 1

    # Define paths
    config_path = Path("config/project.yaml")
    pdfs_renamed_path = Path("pdfs")
    extractions_path = Path("extractions")
    output_path = Path("output")

    # ===========================================================================
    # PHASE 1: INGEST & CONVERT
    # ===========================================================================

    if not args.aggregate_only:
        print("\n" + "=" * 78)
        print("  PHASE 1: INGEST & CONVERT")
        print("=" * 78 + "\n")

        # Check if Excel file exists
        if not args.excel.exists():
            print(f"  ERROR: Excel file not found: {args.excel}")
            print(f"  Run with --create-sample to create a sample file")
            return 1

        # Parse Excel
        print(f"  Parsing {args.excel}...")
        try:
            parsed_data = parse_form_response(args.excel)
        except Exception as e:
            print(f"  ERROR: Failed to parse Excel file: {e}")
            return 1

        # Check if PDF folder exists
        if not args.pdfs.exists():
            print(f"  WARNING: PDF folder not found: {args.pdfs}")
            print(f"  Creating empty folder...")
            args.pdfs.mkdir(parents=True, exist_ok=True)

        # Match PDFs
        print(f"  Matching PDFs in {args.pdfs}...")
        parsed_data["sources"], unmatched = match_pdfs_to_sources(
            parsed_data["sources"], args.pdfs
        )

        if unmatched:
            print(f"  [!] Unmatched PDFs: {', '.join(unmatched[:5])}")
            if len(unmatched) > 5:
                print(f"      ... and {len(unmatched) - 5} more")

        # Validate
        validation_errors = validate_setup(parsed_data["sources"], args.pdfs)

        # Rename PDFs
        print(f"\n  Renaming PDFs to {pdfs_renamed_path}/...")
        rename_pdfs(parsed_data["sources"], args.pdfs, pdfs_renamed_path)

        # Update sources with renamed filenames
        for num, source in parsed_data["sources"].items():
            source["filename"] = source["renamed_filename"]

        # ======================================================================
        # PHASE 2: TRANSLATE FRAMING
        # ======================================================================

        print("\n" + "=" * 78)
        print("  PHASE 2: TRANSLATE FRAMING")
        print("=" * 78 + "\n")

        if args.skip_framing:
            # Use raw context as-is
            context_translated = create_fallback_framing(parsed_data["context_raw"])
            print("  Using raw context (framing translation skipped)")
        else:
            print("  Translating framing with Gemini Flash...")
            try:
                context_translated = translate_framing(
                    parsed_data["context_raw"],
                    api_key
                )
                print("  Framing translation complete")
            except Exception as e:
                print(f"  WARNING: Framing translation failed: {e}")
                print("  Using fallback framing...")
                context_translated = create_fallback_framing(parsed_data["context_raw"])

        parsed_data["context_translated"] = context_translated

        # Generate YAML config
        generate_yaml_config(parsed_data, config_path)
        print(f"\n  Config saved to {config_path}")

        # ======================================================================
        # CHECKPOINT 1: Config + Framing Review
        # ======================================================================

        if not args.yes:
            choice = checkpoint_config_review(
                project=parsed_data["project"],
                research_questions=parsed_data["research_questions"],
                sources=parsed_data["sources"],
                context_raw=parsed_data["context_raw"],
                context_translated=context_translated,
                validation_errors=validation_errors
            )

            if choice == 'q':
                print("\n  Aborted by user.")
                return 0
            elif choice == 'e':
                # Open editor for framing
                print(f"\n  Edit the framing in {config_path} and re-run.")
                return 0
            elif choice == 'c':
                # Open config file
                print(f"\n  Edit {config_path} and re-run with --skip-framing")
                return 0

    # ===========================================================================
    # Load config for remaining phases
    # ===========================================================================

    if not config_path.exists():
        print(f"\n  ERROR: Config file not found: {config_path}")
        print("  Run the full pipeline first to generate the config.")
        return 1

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # ===========================================================================
    # PHASE 3: EXTRACT
    # ===========================================================================

    if not args.aggregate_only:
        print("\n" + "=" * 78)
        print("  PHASE 3: EXTRACT")
        print("=" * 78 + "\n")

        # Clear extractions if forcing
        if args.force and extractions_path.exists():
            print("  Clearing existing extractions...")
            shutil.rmtree(extractions_path)

        extractor = GeminiExtractor(api_key)

        # Determine range
        end_at = 3 if args.test else None

        # Run first 3 for spot-check
        print("  Extracting first 3 sources for spot-check...\n")
        results = run_extraction_batch(
            extractor=extractor,
            pdf_folder=pdfs_renamed_path,
            sources=config["sources"],
            research_questions=config["research_questions"],
            context=config["context_translated"] or "",
            output_folder=extractions_path,
            start_from=1,
            end_at=3
        )

        # ======================================================================
        # CHECKPOINT 2: Extraction Spot-Check
        # ======================================================================

        if not args.yes and not args.test:
            choice = checkpoint_extraction_spotcheck(
                extractions=results,
                research_questions=config["research_questions"]
            )

            if choice == 'q':
                print("\n  Aborted by user.")
                return 0
            elif choice == 'r':
                print("\n  Edit the extraction prompt in src/extract.py and re-run.")
                return 0

        # Continue with remaining sources
        if not args.test and len(config["sources"]) > 3:
            print("\n  Continuing with remaining sources...\n")
            remaining_results = run_extraction_batch(
                extractor=extractor,
                pdf_folder=pdfs_renamed_path,
                sources=config["sources"],
                research_questions=config["research_questions"],
                context=config["context_translated"] or "",
                output_folder=extractions_path,
                start_from=4,
                end_at=None
            )
            results.extend(remaining_results)

    # ===========================================================================
    # PHASE 4: AGGREGATE
    # ===========================================================================

    print("\n" + "=" * 78)
    print("  PHASE 4: AGGREGATE")
    print("=" * 78 + "\n")

    if not extractions_path.exists() or not list(extractions_path.glob("*.json")):
        print("  ERROR: No extractions found. Run extraction first.")
        return 1

    extractions = load_extractions(extractions_path)

    # Generate outputs
    md_path = output_path / "review_by_rq.md"
    xlsx_path = output_path / "extraction_matrix.xlsx"

    print(f"  Generating {md_path}...")
    generate_markdown_review(
        extractions=extractions,
        research_questions=config["research_questions"],
        project=config["project"],
        output_path=md_path
    )

    print(f"  Generating {xlsx_path}...")
    generate_excel_matrix(
        extractions=extractions,
        research_questions=config["research_questions"],
        output_path=xlsx_path
    )

    # ===========================================================================
    # CHECKPOINT 3: Final Review
    # ===========================================================================

    output_files = {
        "Markdown review": md_path,
        "Excel matrix": xlsx_path,
        "Extractions": extractions_path
    }

    if not args.yes:
        choice = checkpoint_final_review(
            extractions=extractions,
            research_questions=config["research_questions"],
            output_files=output_files
        )

        if choice == 'q':
            print("\n  Outputs saved but not archived.")
            return 0
        elif choice == 'i':
            print(f"\n  Inspect JSONs in {extractions_path}/ and re-run with --aggregate-only")
            return 0
        elif choice == 'r':
            print("\n  Re-run with --aggregate-only")
            return 0

    # ===========================================================================
    # PHASE 5: ARCHIVE
    # ===========================================================================

    print("\n" + "=" * 78)
    print("  PHASE 5: ARCHIVE")
    print("=" * 78 + "\n")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    archive_path = Path("runs") / timestamp
    archive_path.mkdir(parents=True, exist_ok=True)

    # Copy files to archive
    shutil.copy2(config_path, archive_path / "project.yaml")
    shutil.copytree(extractions_path, archive_path / "extractions")
    shutil.copytree(output_path, archive_path / "output")

    print(f"  Archived to {archive_path}/")
    print("\n  [OK] Pipeline complete!")
    print(f"\n  Share these files with requester:")
    print(f"    - {md_path}")
    print(f"    - {xlsx_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
