"""
Translate plain-language context into structured light framing.
Uses Gemini 3 Flash.
"""

from google import genai
from google.genai import types
from pathlib import Path
from typing import Optional


def translate_framing(context_raw: dict, api_key: str, model_name: str = "gemini-3-flash-preview") -> str:
    """
    Convert plain-language context to structured light framing.

    Args:
        context_raw: Dict with keys: description, population, constructs, focus
        api_key: Gemini API key
        model_name: Model to use for framing translation

    Returns:
        Structured framing paragraph
    """
    client = genai.Client(api_key=api_key)

    prompt = f"""You are helping structure context for an academic literature review extraction task.

The requester provided this plain-language description of their review:

---
WHAT THIS REVIEW IS ABOUT:
{context_raw.get('description', 'Not specified')}

TARGET POPULATION:
{context_raw.get('population', 'Not specified')}

KEY CONSTRUCTS OF INTEREST:
{context_raw.get('constructs', 'Not specified')}

FOCUS AREA:
{context_raw.get('focus', 'Not specified')}
---

Rewrite this as a concise "light framing" paragraph (4-6 sentences) that:
1. States the review's focus clearly in the first sentence
2. Defines the target population precisely
3. Lists key constructs with brief operational definitions
4. Notes the application context

The framing should help an AI extraction model understand what to look for WITHOUT biasing it toward any particular findings or conclusions. Use neutral, descriptive language.

Output ONLY the framing paragraph, nothing else. Use this structure:

This review examines [topic] in [population with age range if specified].

Key constructs of interest include:
- [Construct 1]: [brief definition]
- [Construct 2]: [brief definition]
- [etc.]

The focus is on findings relevant to [application context]."""

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=500
        )
    )

    return response.text.strip()


def display_framing_comparison(context_raw: dict, context_translated: str) -> None:
    """
    Display original and translated framing for user review.
    """
    print("\n" + "-" * 78)
    print("  ORIGINAL CONTEXT (from form)")
    print("-" * 78)

    description = context_raw.get('description', 'Not specified')
    print(f"\n  Description: {description[:200]}{'...' if len(description) > 200 else ''}")
    print(f"  Population:  {context_raw.get('population', 'Not specified')}")

    constructs = context_raw.get('constructs', 'Not specified')
    print(f"  Constructs:  {constructs[:100]}{'...' if len(constructs) > 100 else ''}")
    print(f"  Focus:       {context_raw.get('focus', 'Not specified')}")

    print("\n" + "-" * 78)
    print("  TRANSLATED LIGHT FRAMING")
    print("-" * 78)
    # Indent and wrap the translated framing
    for line in context_translated.split("\n"):
        print(f"  {line}")


def create_fallback_framing(context_raw: dict) -> str:
    """
    Create a simple framing without LLM when API is unavailable or skipped.

    Args:
        context_raw: Dict with keys: description, population, constructs, focus

    Returns:
        Basic structured framing paragraph
    """
    description = context_raw.get('description', 'the specified topic')
    population = context_raw.get('population', 'the target population')
    constructs = context_raw.get('constructs', 'relevant constructs')
    focus = context_raw.get('focus', 'the specified context')

    framing = f"""This review examines {description}

Target population: {population}

Key constructs of interest: {constructs}

The focus is on findings relevant to {focus}."""

    return framing


def validate_framing(framing: str) -> tuple[bool, list]:
    """
    Validate the translated framing for completeness.

    Args:
        framing: The translated framing text

    Returns:
        Tuple of (is_valid, list of warnings)
    """
    warnings = []

    if len(framing) < 100:
        warnings.append("Framing is very short (< 100 characters)")

    if len(framing) > 2000:
        warnings.append("Framing is very long (> 2000 characters)")

    # Check for key elements
    lower_framing = framing.lower()
    if "population" not in lower_framing and "participants" not in lower_framing:
        warnings.append("Framing may not clearly specify target population")

    if "construct" not in lower_framing and "-" not in framing:
        warnings.append("Framing may not list key constructs")

    is_valid = len(warnings) == 0
    return is_valid, warnings
