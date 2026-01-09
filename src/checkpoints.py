"""
Human-in-the-loop checkpoint interactions.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


def checkpoint_config_review(
    project: dict,
    research_questions: list,
    sources: dict,
    context_raw: dict,
    context_translated: str,
    validation_errors: list
) -> str:
    """
    Checkpoint 1: Review configuration and translated framing.

    Returns: User choice ('a'=approve, 'e'=edit framing, 'c'=config file, 'q'=quit)
    """
    console.print()
    console.print("=" * 78, style="bold blue")
    console.print("  LITERATURE REVIEW EXTRACTION PIPELINE", style="bold white")
    console.print("=" * 78, style="bold blue")

    # Project info
    console.print()
    console.print(f"  Project:    [bold]{project.get('name', 'Untitled')}[/bold]")
    console.print(f"  Requester:  {project.get('requester', 'Unknown')}")
    console.print(f"  Date:       {project.get('date', 'Unknown')}")

    # Sources
    console.print()
    console.print("-" * 78)
    console.print("  SOURCE DOCUMENTS", style="bold")
    console.print("-" * 78)
    console.print()

    source_items = list(sources.items())
    for num, source in source_items[:10]:
        has_file = bool(source.get("original_filename"))
        status = "Y" if has_file else "X"
        style = "green" if has_file else "red"
        citation = source.get('citation', 'Unknown')
        if len(citation) > 50:
            citation = citation[:47] + "..."
        console.print(f"  [{style}]{status}[/{style}]  {num:2d}. {citation}")

    if len(source_items) > 10:
        console.print(f"      ... and {len(source_items) - 10} more")

    total = len(sources)
    found = sum(1 for s in sources.values() if s.get("original_filename"))
    console.print()
    console.print(f"  Status: {found}/{total} files matched")

    # Validation errors
    if validation_errors:
        console.print()
        console.print("  [red][!] VALIDATION ERRORS:[/red]")
        for err in validation_errors[:5]:
            console.print(f"    - {err}", style="red")
        if len(validation_errors) > 5:
            console.print(f"    ... and {len(validation_errors) - 5} more errors", style="red")

    # Research Questions
    console.print()
    console.print("-" * 78)
    console.print(f"  RESEARCH QUESTIONS ({len(research_questions)})", style="bold")
    console.print("-" * 78)
    console.print()

    for rq in research_questions:
        console.print(f"  [bold cyan][{rq['id']}][/bold cyan]")
        # Wrap text
        text = rq['text'].strip()
        for i in range(0, len(text), 70):
            console.print(f"    {text[i:i+70]}")
        if rq.get('keywords'):
            keywords = ', '.join(rq['keywords'][:5])
            console.print(f"    [dim]Keywords: {keywords}[/dim]")
        console.print()

    # Context comparison
    console.print("-" * 78)
    console.print("  FRAMING CONTEXT", style="bold")
    console.print("-" * 78)

    console.print()
    console.print("  [dim]Original (from form):[/dim]")
    description = context_raw.get('description', 'Not specified')
    if len(description) > 150:
        description = description[:147] + "..."
    console.print(f"    {description}")

    console.print()
    console.print("  [bold green]Translated (for extraction):[/bold green]")
    for line in context_translated.split("\n")[:8]:
        console.print(f"    {line}")
    if len(context_translated.split("\n")) > 8:
        console.print("    ...")

    # Options
    console.print()
    console.print("-" * 78)
    console.print()
    console.print("  [bold]Options:[/bold]")
    console.print("    [A] Approve and continue to extraction")
    console.print("    [E] Edit translated framing")
    console.print("    [C] Open config file for manual edits")
    console.print("    [Q] Quit")
    console.print()

    choice = console.input("  Your choice: ").strip().lower()
    return choice if choice in ['a', 'e', 'c', 'q'] else 'a'


def checkpoint_extraction_spotcheck(
    extractions: list,
    research_questions: list
) -> str:
    """
    Checkpoint 2: Review first 3 extractions before continuing.

    Returns: User choice ('c'=continue, 'r'=re-run, 'q'=quit)
    """
    console.print()
    console.print("=" * 78, style="bold blue")
    console.print("  EXTRACTION SPOT-CHECK", style="bold white")
    console.print("=" * 78, style="bold blue")
    console.print()

    for ext in extractions[:3]:
        if "error" in ext:
            console.print(f"  [red]Source {ext.get('source_number')}: ERROR - {ext['error'][:50]}[/red]")
            continue

        console.print(f"  [bold]Source {ext.get('source_number')}: {ext.get('citation', 'Unknown')}[/bold]")
        console.print(f"    Study type: {ext.get('study_type', 'Unknown')}")

        sample = ext.get("sample", {}) or {}
        if sample.get("n"):
            age_range = sample.get('age_range', 'age unknown')
            console.print(f"    Sample: n={sample['n']}, {age_range}")

        console.print()

        for rq in research_questions:
            rq_id = rq["id"]
            rq_data = ext.get("extractions", {}).get(rq_id, {})
            has_ev = rq_data.get("has_evidence", False)

            status = "[green]Y Evidence[/green]" if has_ev else "[dim]N None[/dim]"
            console.print(f"    {rq_id}: {status}")

            if has_ev:
                answer = rq_data.get("answer", "")
                if len(answer) > 100:
                    answer = answer[:97] + "..."
                console.print(f"      [dim]{answer}[/dim]")

                quotes = rq_data.get("supporting_quotes", [])
                if quotes and len(quotes) > 0:
                    quote = quotes[0].get("quote", "")
                    if len(quote) > 80:
                        quote = quote[:77] + "..."
                    console.print(f"      [italic]'{quote}'[/italic]")

        console.print()
        console.print("  " + "-" * 74)
        console.print()

    console.print("  [bold]Options:[/bold]")
    console.print("    [C] Continue with all remaining sources")
    console.print("    [R] Re-run with adjusted prompt (opens editor)")
    console.print("    [Q] Quit")
    console.print()

    choice = console.input("  Your choice: ").strip().lower()
    return choice if choice in ['c', 'r', 'q'] else 'c'


def checkpoint_final_review(
    extractions: list,
    research_questions: list,
    output_files: dict
) -> str:
    """
    Checkpoint 3: Review final outputs before archiving.

    Returns: User choice ('a'=approve, 'i'=inspect, 'r'=re-aggregate, 'q'=quit)
    """
    console.print()
    console.print("=" * 78, style="bold blue")
    console.print("  EXTRACTION COMPLETE", style="bold white")
    console.print("=" * 78, style="bold blue")
    console.print()

    # Stats
    total = len(extractions)
    errors = sum(1 for e in extractions if "error" in e)
    success = total - errors

    console.print(f"  Processed:  {success}/{total} sources")
    if errors > 0:
        console.print(f"  [red]Errors:     {errors}[/red]")
    console.print()

    # Coverage by RQ
    console.print("-" * 78)
    console.print("  EVIDENCE COVERAGE BY RESEARCH QUESTION", style="bold")
    console.print("-" * 78)
    console.print()

    for rq in research_questions:
        rq_id = rq["id"]
        with_evidence = sum(
            1 for ext in extractions
            if "error" not in ext
            and ext.get("extractions", {}).get(rq_id, {}).get("has_evidence", False)
        )
        pct = (with_evidence / success * 100) if success > 0 else 0

        # Progress bar (25 chars = 100%)
        bar_filled = int(pct / 4)
        bar_empty = 25 - bar_filled
        bar = "#" * bar_filled + "-" * bar_empty

        console.print(f"  {rq_id}")
        console.print(f"  [{bar}] {with_evidence}/{success} ({pct:.0f}%)")
        console.print()

    # Output files
    console.print("-" * 78)
    console.print("  OUTPUT FILES", style="bold")
    console.print("-" * 78)
    console.print()

    for name, path in output_files.items():
        console.print(f"  -> {path}")

    console.print()
    console.print("-" * 78)
    console.print()
    console.print("  [bold]Options:[/bold]")
    console.print("    [A] Approve and archive")
    console.print("    [I] Inspect individual extractions")
    console.print("    [R] Re-run aggregation")
    console.print("    [Q] Quit without archiving")
    console.print()

    choice = console.input("  Your choice: ").strip().lower()
    return choice if choice in ['a', 'i', 'r', 'q'] else 'a'


def display_progress(current: int, total: int, filename: str, status: str = "Processing") -> None:
    """Display a simple progress indicator."""
    pct = (current / total * 100) if total > 0 else 0
    bar_filled = int(pct / 5)  # 20 chars = 100%
    bar_empty = 20 - bar_filled
    bar = "#" * bar_filled + "-" * bar_empty

    console.print(f"\r  [{bar}] {current}/{total} | {status}: {filename[:40]}...", end="")


def display_extraction_detail(extraction: dict, research_questions: list) -> None:
    """Display detailed extraction for inspection."""
    if "error" in extraction:
        console.print(f"\n[red]Error: {extraction['error']}[/red]")
        return

    console.print()
    console.print("-" * 78)
    console.print(f"  Source {extraction.get('source_number')}: {extraction.get('citation', 'Unknown')}")
    console.print("-" * 78)
    console.print()
    console.print(f"  Title:      {extraction.get('title', 'Unknown')}")
    console.print(f"  Study Type: {extraction.get('study_type', 'Unknown')}")

    sample = extraction.get("sample", {}) or {}
    console.print(f"  Sample N:   {sample.get('n', 'N/A')}")
    console.print(f"  Age Range:  {sample.get('age_range', 'N/A')}")
    console.print(f"  Population: {sample.get('population', 'N/A')}")

    console.print()

    for rq in research_questions:
        rq_id = rq["id"]
        rq_data = extraction.get("extractions", {}).get(rq_id, {})
        has_ev = rq_data.get("has_evidence", False)

        console.print(f"  [{rq_id}] {'Evidence Found' if has_ev else 'No Evidence'}")

        if has_ev:
            console.print(f"    Answer: {rq_data.get('answer', 'N/A')}")
            console.print(f"    Effect Size: {rq_data.get('effect_size', 'N/A')}")
            console.print(f"    Direction: {rq_data.get('direction', 'N/A')}")

            quotes = rq_data.get("supporting_quotes", [])
            if quotes:
                console.print("    Quotes:")
                for i, q in enumerate(quotes[:2], 1):
                    quote_text = q.get('quote', '')
                    if len(quote_text) > 100:
                        quote_text = quote_text[:97] + "..."
                    console.print(f"      {i}. \"{quote_text}\"")
                    console.print(f"         Location: {q.get('location', 'N/A')}")

        console.print()
