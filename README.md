# Gemini 3 Literature Review Extraction Pipeline

A Python tool that uses Google's Gemini 3 AI to automatically extract evidence from academic PDF articles for your literature review. It reads your PDFs, finds relevant quotes and findings for your research questions, and creates a summary document you can use in your writing.

## What This Tool Does

1. **Reads your academic PDFs** - You provide PDF files of journal articles
2. **Answers your research questions** - You tell it what you're looking for
3. **Extracts exact quotes** - It finds and copies relevant passages from each article
4. **Records effect sizes** - It captures statistical results (like Cohen's d, correlation coefficients)
5. **Creates a summary** - It generates a Word-friendly document organized by research question
6. **Makes a spreadsheet** - It creates an Excel file with all the data for easy filtering

---

## Step-by-Step Guide for Beginners

### Step 1: Install Python (if you don't have it)

**Check if Python is installed:**
1. Open **Command Prompt** (Windows) or **Terminal** (Mac)
   - Windows: Press `Win + R`, type `cmd`, press Enter
   - Mac: Press `Cmd + Space`, type `Terminal`, press Enter
2. Type `python --version` and press Enter
3. If you see a version number (like `Python 3.11.0`), you're good! Skip to Step 2.
4. If you see an error, download Python from [python.org/downloads](https://www.python.org/downloads/)
   - **Important:** During installation, check the box that says "Add Python to PATH"

### Step 2: Get a Gemini API Key (free)

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key (it looks like `AIzaSyC...`) - you'll need this later
5. **Keep this key private** - don't share it or post it online

### Step 3: Download This Tool

**Option A: Download as ZIP (easiest)**
1. Click the green "Code" button at the top of this page
2. Click "Download ZIP"
3. Extract the ZIP file to a folder you can find easily (like your Documents folder)

**Option B: Using Git (if you have it)**
```
git clone https://github.com/trgallagher-research/gemini3-lit-review.git
```

### Step 4: Set Up the Tool

1. **Open Command Prompt/Terminal**

2. **Navigate to the tool's folder:**
   ```
   cd "C:\Users\YourName\Documents\gemini3-lit-review"
   ```
   (Replace the path with wherever you extracted the files)

3. **Install the required packages:**
   ```
   pip install -r requirements.txt
   ```
   Wait for it to finish - you'll see some download progress.

4. **Add your API key:**
   - Find the file called `.env.template` in the folder
   - Make a copy of it and rename the copy to `.env` (just `.env`, no other name)
   - Open `.env` with Notepad or any text editor
   - Replace `your_gemini_api_key_here` with your actual API key from Step 2
   - Save and close the file

### Step 5: Prepare Your Literature Review

#### 5a. Create your project Excel file

1. **Generate a template:**
   ```
   python run_pipeline.py --create-sample
   ```
   This creates a sample file at `input/sample_form_response.xlsx`

2. **Open the sample file** in Excel and look at the format

3. **Create your own file** called `form_response.xlsx` in the `input` folder with:

   | What to fill in | Example |
   |-----------------|---------|
   | **project_name** | My Systematic Review on Screen Time |
   | **requester_name** | Jane Smith |
   | **requester_email** | jane@university.edu |
   | **project_description** | A review examining effects of screen time on child development |
   | **rq_count** | 2 |
   | **rq1_id** | RQ1 |
   | **rq1_text** | What is the relationship between screen time and academic performance? |
   | **rq1_keywords** | screen time, academic, grades, achievement |
   | **rq2_id** | RQ2 |
   | **rq2_text** | Does screen time affect attention and concentration? |
   | **rq2_keywords** | attention, concentration, focus, ADHD |
   | **source_citations** | Smith (2023) - Screen time meta-analysis<br>Jones et al. (2024) - Digital media study<br>Brown (2022) - Child development review |
   | **context_description** | This review examines effects of recreational screen time on children |
   | **context_population** | Children aged 6-12 years |
   | **context_constructs** | Screen time, academic performance, attention |
   | **context_focus** | Educational and developmental outcomes |

   **Tips for source_citations:**
   - Put each source on a new line (press Alt+Enter in Excel for a new line within a cell)
   - Format: `Author (Year) - Brief title`
   - List them in the order you want them numbered

#### 5b. Add your PDF files

1. Find the `input/pdfs` folder inside the tool's folder
2. Copy all your PDF articles into this folder
3. **Naming tip:** Include the author name and year somewhere in the filename so the tool can match them
   - Good: `Smith_2023_screen_time.pdf` or `smith2023.pdf` or `downloaded_smith_2023.pdf`
   - Bad: `article1.pdf` or `document.pdf` (no author/year to match)

**The tool automatically renames your files!** You don't need to rename them yourself:
- It matches your PDFs to citations by looking for author names and years in filenames
- It creates numbered copies like `01_Smith_2023.pdf`, `02_Jones_2024.pdf`
- Your original files in `input/pdfs/` are **not modified** - only copies are made

Example of what you'll see:
```
Renaming PDFs to pdfs/...
 1. smith_screen_time_2023.pdf -> 01_Smith_2023.pdf
 2. jones_et_al_2024_study.pdf -> 02_Jones_2024.pdf
 3. brown2022.pdf -> 03_Brown_2022.pdf
```

### Step 6: Run the Tool

1. **Open Command Prompt/Terminal** and navigate to the tool's folder (like in Step 4)

2. **Run the pipeline:**
   ```
   python run_pipeline.py
   ```

3. **What happens next:**
   - The tool will show you what it found and ask for confirmation at several checkpoints
   - Press `A` and Enter to approve and continue
   - Press `Q` and Enter to quit if something looks wrong

4. **Wait for processing:**
   - Each PDF takes about 30-60 seconds to process
   - You'll see progress updates in the terminal

### Step 7: Find Your Results

When it's done, look in the `output` folder for:

1. **`review_by_rq.md`** - Your literature review organized by research question
   - Open this in Word, Google Docs, or any text editor
   - Copy and paste sections into your paper
   - Each finding includes the quote, where it came from, and effect sizes

2. **`extraction_matrix.xlsx`** - A spreadsheet with all the data
   - Open in Excel
   - Filter and sort by research question, study type, effect size, etc.
   - Useful for creating tables in your paper

---

## Troubleshooting Common Problems

### "Python is not recognized"
- Python isn't installed or isn't in your PATH
- Reinstall Python and make sure to check "Add Python to PATH"

### "No module named 'google'"
- The packages didn't install correctly
- Run `pip install -r requirements.txt` again

### "API key not found"
- Make sure you created a `.env` file (not `.env.template`)
- Make sure the API key is on the line after `GEMINI_API_KEY=`
- Make sure there are no extra spaces

### "No matching PDF found"
- The tool couldn't match your citation to a PDF file
- Rename your PDF to include the author name and year
- Example: For citation "Smith (2023)", name the file `Smith_2023.pdf`

### PDFs not processing correctly
- Make sure PDFs are text-based (not scanned images)
- If a PDF is a scan, you'll need to OCR it first
- Very large PDFs (>50MB) may have issues

---

## Tips for Best Results

1. **Use text-based PDFs** - Scanned documents won't work as well
2. **Be specific in your research questions** - Vague questions get vague answers
3. **Include keywords** - They help the AI know what to look for
4. **Check the spot-check** - Review the first 3 extractions carefully before processing all PDFs
5. **Verify quotes** - Always double-check extracted quotes against the original PDFs

---

## What the Tool Extracts

For each PDF and research question, the tool captures:

| Field | Description |
|-------|-------------|
| **has_evidence** | Whether the article addresses this research question |
| **answer** | Summary of what the article says about this topic |
| **supporting_quotes** | Exact quotes from the article with page/section numbers |
| **effect_size** | Statistical results (r, d, odds ratio, etc.) as reported |
| **direction** | Whether findings are positive, negative, or mixed |

---

## Advanced Options

For users comfortable with command line:

| Command | What it does |
|---------|--------------|
| `python run_pipeline.py --test` | Only process first 3 PDFs (good for testing) |
| `python run_pipeline.py --yes` | Skip all confirmation prompts |
| `python run_pipeline.py --force` | Re-process PDFs even if already done |
| `python run_pipeline.py --aggregate-only` | Regenerate outputs without re-reading PDFs |

---

## Project Structure

```
gemini3-lit-review/
├── input/
│   ├── form_response.xlsx    ← Your project details (you create this)
│   └── pdfs/                 ← Your PDF files go here
├── output/
│   ├── review_by_rq.md       ← Generated literature review
│   └── extraction_matrix.xlsx ← Generated spreadsheet
├── .env                      ← Your API key (you create this)
└── run_pipeline.py           ← The main program
```

---

## Getting Help

- **Issues or bugs:** [Open an issue on GitHub](https://github.com/trgallagher-research/gemini3-lit-review/issues)
- **Questions:** Contact the repository owner

---

## License

MIT - Feel free to use, modify, and share.
