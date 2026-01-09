"""
Extract evidence from PDFs using Gemini 3 Pro.
Handles file uploads, thought signatures, and retries.
"""

from google import genai
from google.genai import types
import json
import time
from pathlib import Path
from typing import Optional


class GeminiExtractor:
    """
    PDF evidence extractor using Gemini 3 Pro.
    Handles file uploads, thought signatures, and retries.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-3-pro-preview"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def upload_pdf(self, pdf_path: Path):
        """Upload PDF to Gemini File API."""
        return self.client.files.upload(file=str(pdf_path))

    def extract_from_pdf(
        self,
        pdf_path: Path,
        source_number: int,
        research_questions: list,
        context: str,
        retry_attempts: int = 3
    ) -> dict:
        """
        Extract evidence from a single PDF.

        Args:
            pdf_path: Path to PDF file
            source_number: Source number for reference
            research_questions: List of RQ dicts with id, text, keywords
            context: Light framing context
            retry_attempts: Number of retries on failure

        Returns:
            Extraction result dict
        """
        # Upload PDF
        uploaded_file = None
        try:
            uploaded_file = self.upload_pdf(pdf_path)
        except Exception as e:
            return {
                "source_number": source_number,
                "filename": pdf_path.name,
                "error": f"Failed to upload PDF: {str(e)}",
                "extractions": {}
            }

        # Build prompt
        prompt = self._build_extraction_prompt(
            source_number=source_number,
            filename=pdf_path.name,
            research_questions=research_questions,
            context=context
        )

        # Attempt extraction with retries
        last_error = None
        for attempt in range(retry_attempts):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[
                        types.Part.from_uri(file_uri=uploaded_file.uri, mime_type=uploaded_file.mime_type),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json"
                    )
                )

                # Parse JSON response
                result = json.loads(response.text)

                # Clean up uploaded file
                self.delete_uploaded_file(uploaded_file)

                return result

            except json.JSONDecodeError as e:
                last_error = f"JSON parse error: {e}"
                # Try to extract JSON from response if wrapped in markdown
                if hasattr(response, 'text'):
                    extracted = self._extract_json_from_text(response.text)
                    if extracted:
                        self.delete_uploaded_file(uploaded_file)
                        return extracted
            except Exception as e:
                last_error = str(e)

            wait_time = (2 ** attempt) * 2  # Exponential backoff
            print(f"    [!] Attempt {attempt + 1} failed: {last_error}")
            if attempt < retry_attempts - 1:
                print(f"    Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

        # Clean up on failure
        self.delete_uploaded_file(uploaded_file)

        # All retries failed
        return {
            "source_number": source_number,
            "filename": pdf_path.name,
            "error": str(last_error),
            "extractions": {}
        }

    def _extract_json_from_text(self, text: str) -> Optional[dict]:
        """Try to extract JSON from text that may be wrapped in markdown."""
        import re
        # Try to find JSON block in markdown
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def _build_extraction_prompt(
        self,
        source_number: int,
        filename: str,
        research_questions: list,
        context: str
    ) -> str:
        """Build the extraction prompt dynamically based on RQs."""

        # Build RQ section
        rq_sections = []
        for rq in research_questions:
            keywords_str = ", ".join(rq.get("keywords", []))
            section = f"### {rq['id']}\n{rq['text'].strip()}"
            if keywords_str:
                section += f"\nRelevant keywords: {keywords_str}"
            rq_sections.append(section)

        rq_text = "\n\n".join(rq_sections)

        # Build expected JSON schema
        rq_ids = [rq["id"] for rq in research_questions]
        extraction_entries = []
        for rq_id in rq_ids:
            extraction_entries.append(f'''    "{rq_id}": {{
      "has_evidence": <true/false>,
      "answer": "<summary of findings OR 'No relevant evidence in this article'>",
      "supporting_quotes": [
        {{"quote": "<exact quote from article>", "location": "<page number or section>"}}
      ],
      "effect_size": "<as reported in article, or null>",
      "direction": "<positive/negative/mixed/null>"
    }}''')

        extractions_schema = ",\n".join(extraction_entries)

        return f"""You are a research assistant extracting evidence from academic articles for a systematic literature review.

## Context
{context}

## Your Task
Read this article carefully and answer each research question below based ONLY on evidence explicitly stated in the article.

Source Number: {source_number}
Filename: {filename}

## Research Questions

{rq_text}

## Required Output Format

Return a JSON object with exactly this structure:

{{
  "source_number": {source_number},
  "filename": "{filename}",
  "citation": "<Author (Year) format - use 'et al.' for 3+ authors>",
  "title": "<Full article title as it appears>",
  "study_type": "<meta-analysis / systematic review / RCT / quasi-experimental / longitudinal / cross-sectional / qualitative / theoretical / other>",
  "sample": {{
    "n": <number or null if not applicable>,
    "age_range": "<age range string or null>",
    "population": "<description of participants>",
    "notes": "<any relevant notes about the sample>"
  }},
  "extractions": {{
{extractions_schema}
  }}
}}

## Critical Instructions

1. **Evidence-based only**: Report ONLY findings explicitly stated in the article. Do not infer, speculate, or generalise beyond what the text says.

2. **Exact quotes required**: For each RQ where has_evidence is true, provide at least one exact quote from the article with its location (page number, section name, or paragraph reference).

3. **No evidence is valid**: If the article does not address a research question, set has_evidence to false and state "No relevant evidence in this article." in the answer field. Every RQ MUST have an entry in extractions.

4. **Effect sizes**: Report effect sizes exactly as stated (e.g., "r = 0.35", "d = 0.42", "OR = 2.1", "beta = -0.23"). Set to null if not reported or not applicable.

5. **Direction**:
   - "positive" = technology/media use associated with BETTER outcomes
   - "negative" = technology/media use associated with WORSE outcomes
   - "mixed" = findings show both positive and negative effects
   - null = no evidence or not applicable

6. **Study type**: Classify based on the methodology section. Use "other" only if none of the categories fit.

7. **Citation format**: "Author (Year)" for 1-2 authors, "Author et al. (Year)" for 3+ authors.

Return ONLY valid JSON. No markdown formatting, no explanatory text."""

    def delete_uploaded_file(self, file) -> None:
        """Clean up uploaded file from Gemini."""
        if file is None:
            return
        try:
            self.client.files.delete(name=file.name)
        except Exception:
            pass  # Ignore deletion errors


def run_extraction_batch(
    extractor: GeminiExtractor,
    pdf_folder: Path,
    sources: dict,
    research_questions: list,
    context: str,
    output_folder: Path,
    start_from: int = 1,
    end_at: Optional[int] = None
) -> list:
    """
    Run extraction on a batch of PDFs.

    Args:
        extractor: GeminiExtractor instance
        pdf_folder: Folder containing renamed PDFs
        sources: Dict of source metadata
        research_questions: List of RQs
        context: Light framing context
        output_folder: Folder to save extraction JSONs
        start_from: First source number to process
        end_at: Last source number to process (None = all)

    Returns:
        List of extraction results
    """
    output_folder.mkdir(parents=True, exist_ok=True)
    results = []

    if end_at is None:
        end_at = max(sources.keys()) if sources else 0

    # Filter sources in range
    sources_in_range = {k: v for k, v in sources.items() if start_from <= k <= end_at}

    for source_num, source in sources_in_range.items():
        filename = source.get("filename", f"{source_num:02d}_unknown.pdf")
        pdf_path = pdf_folder / filename
        json_path = output_folder / f"{pdf_path.stem}.json"

        # Skip if already processed
        if json_path.exists():
            print(f"  [{source_num}/{end_at}] {filename} (skipped - already exists)")
            with open(json_path, encoding="utf-8") as f:
                results.append(json.load(f))
            continue

        print(f"  [{source_num}/{end_at}] {filename}")
        print(f"          Uploading...", end=" ", flush=True)

        result = extractor.extract_from_pdf(
            pdf_path=pdf_path,
            source_number=source_num,
            research_questions=research_questions,
            context=context
        )

        # Save result
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Display quick summary
        if "error" not in result:
            evidence_summary = []
            for rq in research_questions:
                rq_id = rq["id"]
                has_ev = result.get("extractions", {}).get(rq_id, {}).get("has_evidence", False)
                evidence_summary.append(f"{rq_id}: {'Y' if has_ev else 'N'}")
            print(f"Done -> {' | '.join(evidence_summary)}")
        else:
            error_msg = result.get('error', 'Unknown error')
            print(f"ERROR: {error_msg[:50]}...")

        results.append(result)

        # Small delay to avoid rate limits
        time.sleep(1)

    return results


def load_extraction(json_path: Path) -> dict:
    """Load a single extraction JSON file."""
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def get_extraction_summary(extraction: dict) -> dict:
    """Get a summary of an extraction for display."""
    if "error" in extraction:
        return {
            "source_number": extraction.get("source_number"),
            "status": "error",
            "error": extraction.get("error"),
            "evidence_count": 0
        }

    evidence_count = sum(
        1 for rq_data in extraction.get("extractions", {}).values()
        if rq_data.get("has_evidence", False)
    )

    return {
        "source_number": extraction.get("source_number"),
        "citation": extraction.get("citation", "Unknown"),
        "study_type": extraction.get("study_type", "Unknown"),
        "status": "success",
        "evidence_count": evidence_count,
        "total_rqs": len(extraction.get("extractions", {}))
    }
