# Gemini 3 Literature Review Extraction Pipeline

A Python pipeline that uses the Gemini 3 API to systematically extract evidence from academic PDFs for literature reviews.

## Features

- **Excel Input**: Parse Microsoft Forms exports for project configuration
- **PDF Matching**: Auto-match and rename PDFs to numbered format based on citations
- **AI Framing**: Translate plain-language context to structured framing (Gemini 3 Flash)
- **Evidence Extraction**: Extract evidence from PDFs with exact quotes and effect sizes (Gemini 3 Pro)
- **Structured Output**: Generate markdown review organized by research question
- **Excel Matrix**: Generate spreadsheet with all extractions for further analysis
- **Human-in-the-Loop**: Checkpoints for review at each phase
- **Archiving**: Archive completed runs with timestamps

## Installation

```bash
# Clone the repository
git clone https://github.com/trgallagher-research/gemini3-lit-review.git
cd gemini3-lit-review

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.template .env
# Edit .env and add your Gemini API key
```

## Quick Start

```bash
# Create a sample Excel file to see the expected format
python run_pipeline.py --create-sample

# Place your PDFs in input/pdfs/
# Edit input/form_response.xlsx with your project details

# Run the full pipeline
python run_pipeline.py

# Or test with first 3 PDFs only
python run_pipeline.py --test
```

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: INGEST                                                │
│  • Parse Excel export from Microsoft Forms                      │
│  • Match and rename PDFs (01_Author_Year.pdf)                   │
│  • Generate project.yaml configuration                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: FRAMING (Gemini 3 Flash)                              │
│  • Translate plain-language context to structured framing       │
│  • Checkpoint: Review configuration and framing                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: EXTRACT (Gemini 3 Pro)                                │
│  • Upload PDFs to Gemini File API                               │
│  • Extract evidence for each research question                  │
│  • Capture exact quotes, effect sizes, and directions           │
│  • Checkpoint: Spot-check first 3 extractions                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4: AGGREGATE                                             │
│  • Generate review_by_rq.md (narrative review)                  │
│  • Generate extraction_matrix.xlsx (spreadsheet)                │
│  • Checkpoint: Review coverage and outputs                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5: ARCHIVE                                               │
│  • Archive run with timestamp                                   │
│  • Ready for delivery                                           │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
gemini3-lit-review/
├── .env                    # API keys (not in git)
├── .env.template           # Template for API configuration
├── requirements.txt        # Python dependencies
├── run_pipeline.py         # Main entry point
├── src/
│   ├── ingest.py           # Excel parsing, PDF matching
│   ├── framing.py          # Gemini Flash framing translation
│   ├── extract.py          # Gemini Pro PDF extraction
│   ├── aggregate.py        # Markdown + Excel generation
│   ├── checkpoints.py      # Human-in-the-loop interactions
│   └── utils.py            # Shared utilities
├── input/
│   ├── form_response.xlsx  # Your project configuration
│   └── pdfs/               # Your source PDFs
├── config/                 # Generated project.yaml
├── pdfs/                   # Renamed PDFs
├── extractions/            # JSON outputs (one per PDF)
├── output/
│   ├── review_by_rq.md     # Narrative review
│   └── extraction_matrix.xlsx
└── runs/                   # Archived runs
```

## Excel Input Format

The pipeline expects an Excel file with these columns (matching Microsoft Forms export):

| Column | Description |
|--------|-------------|
| `project_name` | Name of your literature review project |
| `requester_name` | Your name |
| `requester_email` | Your email |
| `project_description` | Brief description of the review |
| `rq_count` | Number of research questions (1-5) |
| `rq1_id`, `rq1_text`, `rq1_keywords` | Research question 1 details |
| `rq2_id`, `rq2_text`, `rq2_keywords` | Research question 2 details |
| `source_citations` | Newline-separated list of citations |
| `context_description` | What the review is about |
| `context_population` | Target population |
| `context_constructs` | Key constructs of interest |
| `context_focus` | Focus area |

Run `python run_pipeline.py --create-sample` to generate a sample file.

## Command Line Options

| Flag | Description |
|------|-------------|
| `--excel PATH` | Path to Excel file (default: `input/form_response.xlsx`) |
| `--pdfs PATH` | Path to PDF folder (default: `input/pdfs`) |
| `--test` | Only process first 3 sources |
| `--skip-framing` | Skip LLM framing translation |
| `--aggregate-only` | Skip extraction, only regenerate outputs |
| `--force` | Re-extract even if JSONs exist |
| `--yes`, `-y` | Skip confirmation prompts |
| `--create-sample` | Create sample Excel file and exit |

## Output Example

### Markdown Review (`output/review_by_rq.md`)

```markdown
## RQ1: Impact of technology on learning outcomes

> What is the impact of technology-based interventions on student learning outcomes?

**Evidence found in 2/3 sources (67%)**

### Summary of Findings

**Zhang et al. (2025) [Source 2]**

The meta-analysis indicates that AI technologies in education have a
significant positive impact on educational outcomes.
*Effect size: Hedges' g = 0.86*

> "The overall analysis revealed a significant positive effect size
> (Hedges' g = 0.86, 95% CI [0.45, 1.27], p < 0.0001)"
> - Abstract
```

### Extraction JSON

Each PDF produces a structured JSON with:
- Citation and title
- Study type and sample information
- For each research question:
  - Whether evidence was found
  - Summary of findings
  - Exact quotes with locations
  - Effect sizes
  - Direction (positive/negative/mixed)

## Requirements

- Python 3.10+
- Gemini API key ([Get one here](https://aistudio.google.com/apikey))

## License

MIT

## Contributing

Contributions welcome! Please open an issue or submit a pull request.
