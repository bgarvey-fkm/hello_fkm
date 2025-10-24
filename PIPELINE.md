# Income Verification Processing Pipeline

## Overview
This pipeline processes mortgage loan documents from the Harvest API, extracts borrower-stated income from Form 1003, calculates qualifying income using AI with Freddie Mac guidelines, and compares results for accuracy and consistency.

## System Architecture

```
Harvest API (Loans & PDFs)
         ↓
Azure Document Intelligence (PDF → Raw JSON)
         ↓
Azure OpenAI (Raw JSON → Semantic JSON)
         ↓
┌────────────────────┬────────────────────┬─────────────────────┐
│                    │                    │                     │
Form 1003 Tracker    AI Income Analyzer   UW Artifacts Scanner
(Borrower-Stated)    (Document-Based)     (UW-Approved)
         │                    │                     │
         └────────────────────┴─────────────────────┘
                          ↓
                  Comparison & Reconciliation
```

## Data Flow & Folder Structure

```
loan_docs/
  └── {loan_id}/                    # e.g., 1000175957
      ├── raw_json/                 # Azure Doc Intelligence output
      │   └── *.json                # Raw extracted JSON (text, tables, structure)
      │
      ├── semantic_json/            # Azure OpenAI structured data
      │   └── *.json                # Classified documents with extracted fields
      │       ├── metadata          # FileId, FileName, DocType, UploadDate, Timeline
      │       └── semantic_content  # document_type, summary, key_fields
      │
      └── income_analysis/          # Income verification results
          ├── form_1003_income_timeline.json         # Form 1003 data
          ├── form_1003_income_timeline.html         # Visual timeline
          ├── income_analysis_run1.json              # AI run 1
          ├── income_analysis_run2.json              # AI run 2
          ├── ...                                    # Additional runs
          ├── consistency_summary_runs1-5.json       # Batch summary
          ├── consistency_summary_all.json           # All runs summary
          ├── consistency_report_runs1-5.html        # Batch report
          ├── consistency_report_all.html            # Comprehensive report
          └── underwriter_artifacts_scan.json        # UW worksheets scan

portfolio_data/
  ├── deal_2_data.json                               # Loan list from Harvest API
  └── batch_analysis_deal2_{timestamp}.json          # Batch results (50 loans)

loan_files_inputs/
  └── loan_{loan_id}_tree.json                       # Document metadata from Harvest

guidelines/
  ├── freddie_mac_guide_5300_5400.json               # Parsed guide (297 pages)
  └── freddie_mac_guide_5300_5400_compressed.json    # 67 income rules
```

## Complete Processing Pipeline

### Pipeline Overview

| Step | Script | Input | Output | Purpose |
|------|--------|-------|--------|---------|
| 1 | `batch_process_deal.py` | Harvest API | raw_json + semantic_json | Download & process loans |
| 2 | `batch_income_and_1003_analysis.py` | semantic_json | income_analysis folder | Extract Form 1003 + AI income |
| 3 | `test_find_underwriter_worksheets.py` | semantic_json | underwriter_artifacts_scan.json | Find UW worksheets |

---

### Step 1: Batch Process Deal from Harvest API

**Script:** `batch_process_deal.py`

**Command:**
```powershell
python batch_process_deal.py --deal-id 2 --num-loans 50
```

**What it does:**
1. Fetches loan list from Harvest API `/api/deal/{deal_id}`
2. For each loan:
   - Gets document metadata tree `/api/doc_meta_data_tree/{loan_number}`
   - Downloads PDFs `/api/pdf/{file_id}`
   - Extracts with Azure Document Intelligence → `raw_json/`
   - Creates semantic JSON with Azure OpenAI → `semantic_json/`
3. Saves deal data to `portfolio_data/deal_{id}_data.json`
4. Saves metadata tree to `loan_files_inputs/loan_{id}_tree.json`

**Key Features:**
- Skip logic: Only processes new loans (checks for existing `semantic_json/`)
- Async processing for speed
- Error handling and progress tracking

**Output per loan:**
- `loan_docs/{loan_id}/raw_json/*.json` (~50-100 files)
- `loan_docs/{loan_id}/semantic_json/*.json` (~50-100 files)

**Semantic JSON Structure:**
```json
{
  "metadata": {
    "FileId": 20034,
    "FileName": "Paystubs_2025-05-21",
    "DocPredictionType": "Pay Statement",
    "SpringDocType": "NO_CATEGORY",
    "FileUploadDate": "2025-05-21T14:36:29",
    "Timeline": "App Taken"
  },
  "semantic_content": {
    "document_type": "paystub",
    "summary": "Paystub for period 05/01/2025-05/14/2025",
    "key_fields": {
      "employer": "ABC Company",
      "employee": "John Doe",
      "pay_period": "05/01/2025 - 05/14/2025",
      "gross_pay": 4480.00,
      "ytd_gross": 89600.00
    }
  },
  "income_verification_relevant": true  // Cached classification
}
```

---

### Step 2: Combined Form 1003 + AI Income Analysis

**Script:** `batch_income_and_1003_analysis.py`

**Command:**
```powershell
python batch_income_and_1003_analysis.py --deal-id 2 --num-loans 50 --income-runs 5
```

**What it does:**
For each loan:
1. **Form 1003 Extraction** (runs once):
   - Scans `semantic_json/` for Form 1003 documents
   - Sorts chronologically by FileUploadDate
   - Sends all versions to LLM for income extraction
   - Tracks income changes between versions
   - Saves: `form_1003_income_timeline.json` + `.html`

2. **AI Income Analysis** (runs N times, default 5):
   - Loads Freddie Mac guidelines (67 rules)
   - Filters documents using 4-question framework:
     * Is this a PRIMARY SOURCE document (borrower-provided)?
     * Does it contain income/employment information?
     * Can it verify qualifying income per Freddie Mac?
     * Is it current/acceptable per guidelines?
   - Caches classifications in `semantic_json` files
   - Sends filtered docs to LLM for income calculation
   - Applies Freddie Mac rules (pay frequency, 2-year averaging, etc.)
   - Saves: `income_analysis_run{N}.json`

3. **Consistency Analysis**:
   - Compares all runs (min, max, average, variance)
   - Identifies most common methodology
   - Generates batch summary (runs 1-5)
   - Generates comprehensive summary (all runs ever)
   - Creates HTML reports with statistics

4. **Comparison**:
   - Form 1003 (borrower-stated) vs AI Average (document-based)
   - Calculates difference ($) and percentage
   - Flags large discrepancies for review

**Output per loan:**
- `loan_docs/{loan_id}/income_analysis/form_1003_income_timeline.json`
- `loan_docs/{loan_id}/income_analysis/form_1003_income_timeline.html`
- `loan_docs/{loan_id}/income_analysis/income_analysis_run{1-N}.json`
- `loan_docs/{loan_id}/income_analysis/consistency_summary_runs{X}-{Y}.json`
- `loan_docs/{loan_id}/income_analysis/consistency_summary_all.json`
- `loan_docs/{loan_id}/income_analysis/consistency_report_runs{X}-{Y}.html`
- `loan_docs/{loan_id}/income_analysis/consistency_report_all.html`

**Batch Output:**
- `portfolio_data/batch_analysis_deal{id}_{timestamp}.json`
  - Summary statistics
  - Comparison table (all loans)
  - Form 1003 vs AI income comparison

---

### Step 3: Scan for Underwriter Worksheets

**Script:** `test_find_underwriter_worksheets.py`

**Command:**
```powershell
python test_find_underwriter_worksheets.py {loan_id}
```

**What it does:**
1. Loads all `semantic_json/*.json` files
2. Sends each file to LLM with intelligent classification prompt:
   - "Is this an underwriter work product?"
   - "Does it contain income calculations?"
   - "Extract: calculated income, comments, conditions"
3. Classifies documents into categories:
   - `income_worksheet` - UW income calculation sheets
   - `uw_comment` - Underwriter notes/comments
   - `aus_finding` - Automated underwriting system results
   - `voe` - Verbal/written verification of employment
   - `condition` - Underwriting conditions
   - `analysis` - Other UW analysis documents
4. Extracts structured data from each artifact
5. Saves results to `underwriter_artifacts_scan.json`

**Why LLM instead of keyword search?**
- Intelligent understanding of document purpose
- Catches variations in naming/format
- Extracts actual income amounts from worksheets
- More reliable than brittle regex patterns

**Output:**
- `loan_docs/{loan_id}/income_analysis/underwriter_artifacts_scan.json`

---

## Freddie Mac Guidelines Integration

### One-Time Setup (Already Complete)

**Step A: Parse Freddie Mac PDF**
```powershell
python utils/parse_freddie_mac_guide.py
```
- Input: `utils/FreddieMacGuide_5300_5400.pdf` (297 pages)
- Azure Document Intelligence: Extract text, tables, structure
- Output: `guidelines/freddie_mac_guide_5300_5400.json` (491K characters)

**Step B: Compress to Income Rules**
```powershell
python utils/compress_freddie_mac_guide.py
```
- Input: `guidelines/freddie_mac_guide_5300_5400.json`
- Azure OpenAI: Extract income calculation rules
- Output: `guidelines/freddie_mac_guide_5300_5400_compressed.json` (67 rules)

### Sample Compressed Rule
```json
{
  "section": "5303.1(c)(i)",
  "topic": "Base non-fluctuating employment earnings",
  "rule": "Base earnings considered stable when supported by YTD paystubs and W-2s",
  "details": [
    "Calculate by converting pay period gross to monthly using standard multipliers",
    "Weekly ×52/12, Bi-weekly ×26/12, Semi-monthly ×24/12"
  ],
  "examples": ["Weekly gross $800 → $800×52/12 = $2,773.33 monthly income"]
}
```

---

## Intelligent Document Filtering (4-Question Framework)

The income analysis agent uses a 4-question framework to identify PRIMARY SOURCE documents:

1. **Is this borrower-provided?** (vs 3rd party like credit report)
2. **Does it contain income/employment info?** (vs property/title docs)
3. **Can it verify qualifying income?** (per Freddie Mac acceptable evidence)
4. **Is it current/acceptable?** (paystubs within 30 days, W-2s within 1 year, etc.)

### Example Classification Results
For loan with 85 total documents:
- ✅ **Included (6 docs):**
  - 4 Paystubs (YTD earnings) — PRIMARY SOURCE per Freddie Mac
  - 2 W-2 Forms (2023, 2024) — PRIMARY SOURCE per Freddie Mac
- ❌ **Excluded (79 docs):**
  - Credit reports, appraisals, title docs, disclosures, etc.

### Caching System
- First run: Classifies all documents (slow)
- Subsequent runs: Uses cached `income_verification_relevant` flag (fast)
- Cache stored in `semantic_json/*.json` files
- Refilter option available to reclassify if needed

---

## Income Calculation Methodology

### AI Income Calculation Process

1. **Load Freddie Mac Guidelines** (67 rules)
2. **Filter Documents** (4-question framework)
3. **Analyze Pay Frequency**
   - Weekly: × 52 ÷ 12
   - Bi-weekly: × 26 ÷ 12
   - Semi-monthly: × 24 ÷ 12
   - Monthly: × 12 ÷ 12
4. **Calculate Base Income** (stable, recurring)
5. **Calculate Variable Income** (overtime, bonus, commission)
   - Requires 2-year history
   - Average over 24 months
6. **Reconcile Multiple Sources**
   - Paystubs vs W-2s
   - Most recent W-2 ÷ 12
7. **Output Methodology**
   - Total monthly gross income
   - Component breakdown
   - Calculation steps
   - Rule citations

### Example Output
```json
{
  "monthly_gross_income": 18620.07,
  "calculation_methodology": {
    "paystubs_analysis": "Weekly pay: $2,240/week × 52 / 12 = $9,706.67/month",
    "w2_analysis": "2024 W-2 box 1: $223,440.82 / 12 = $18,620.07/month",
    "reconciliation": "Used 2024 W-2 per Freddie Mac Section 5302.2(b)",
    "income_components": {
      "base_salary": 9706.67,
      "bonus": 4456.70,
      "commission": 4456.70
    }
  },
  "confidence_level": "medium",
  "freddie_mac_rules_applied": [
    "5302.2(b): Most recent W-2 divided by 12",
    "5303.1(c)(i): Pay frequency multipliers"
  ]
}
```

---

## Consistency Testing & Variance Analysis

### Why Run Multiple Times?

LLMs are non-deterministic - same input can produce different outputs. Running 5-10 times reveals:
- **Consistency** - Do we get same answer repeatedly?
- **Variance** - How much do results fluctuate?
- **Common methodologies** - Which approach appears most often?

### Results from 50-Loan Batch

| Metric | Value |
|--------|-------|
| Perfect Matches (0% variance) | 2 loans |
| High Consistency (<5% variance) | 35 loans |
| Medium Consistency (5-15% variance) | 10 loans |
| Low Consistency (>15% variance) | 3 loans |

### Factors Affecting Consistency

✅ **High Consistency:**
- Simple W-2 employee
- Complete documentation
- Single income source
- Clear pay frequency

⚠️ **Low Consistency:**
- Self-employed borrowers
- Multiple income sources
- Commission/bonus income
- Missing documents
- Conflicting information

---

## Three-Way Income Comparison

The pipeline provides three perspectives on income:

| Source | Description | Purpose |
|--------|-------------|---------|
| **Form 1003** | Borrower-stated | What applicant claims to earn |
| **AI Calculated** | Document-based | What evidence actually shows |
| **UW Worksheet** | Underwriter-approved | What was officially used for approval |

### Example Comparison (Loan 1000175957)
- **Form 1003:** $18,599.14/month
- **AI Average (22 runs):** $19,329.72/month (+3.93%)
- **UW Worksheet:** $18,599.14/month (matches Form 1003)
- **Variance:** 18.86% across AI runs (LOW consistency)

**Interpretation:**
- Borrower stated conservatively (or UW adjusted down)
- AI found ~$730 more per month in documentation
- Large AI variance suggests complex income structure
- UW sided with borrower's conservative estimate

---

## Performance & Scalability

### Processing Speed
- **Batch Download (50 loans):** ~15-20 minutes
- **PDF Extraction (per loan):** ~2-3 minutes
- **Semantic JSON (per loan):** ~3-5 minutes
- **Form 1003 Extraction (per loan):** ~10 seconds
- **AI Income Analysis (per run):** ~30-60 seconds
- **Total per loan (5 runs):** ~10-12 minutes

### Cost Estimates (Azure OpenAI)
- **Semantic JSON creation:** ~$0.10-0.20 per loan
- **Income analysis (5 runs):** ~$0.05-0.10 per loan
- **Form 1003 extraction:** ~$0.02 per loan
- **Total per loan:** ~$0.17-0.32

### Async Processing
- Document filtering uses async/await for parallel LLM calls
- Multiple income runs execute concurrently
- Batch processing scales efficiently

---

## Auto-Increment & Data Accumulation

### Run Numbering System
- Detects existing runs in `income_analysis/` folder
- Finds highest run number
- Starts new batch from `max + 1`
- **Example:** If runs 1-19 exist, next batch starts at run 20

### Dual Summary System

**Batch-Specific Summary:**
- `consistency_summary_runs1-5.json` (first batch)
- `consistency_summary_runs6-10.json` (second batch)
- `consistency_summary_runs20-22.json` (third batch)
- Shows statistics for just that batch

**Comprehensive Summary:**
- `consistency_summary_all.json` (always updated)
- Includes ALL runs ever performed
- Cumulative statistics across all batches
- Example: Loan 1000175957 has 22 total runs accumulated

---

## Error Handling & Edge Cases

### Document Classification Failures
- Invalid JSON → Skip with warning
- Missing metadata → Use empty string
- Classification timeout → Retry once

### Form 1003 Not Found
- Some loans may not have Form 1003 in semantic_json
- Script continues, marks as "Not Found"
- Batch summary shows count of successful extractions

### Income Calculation Errors
- Insufficient documentation → Lower confidence level
- Conflicting information → Note in methodology
- Missing W-2s/paystubs → Explain in output

---

## Adding New Loans

```powershell
# Download next batch from Harvest API
python batch_process_deal.py --deal-id 2 --num-loans 100

# Analyze new loans (automatically skips already processed)
python batch_income_and_1003_analysis.py --deal-id 2 --num-loans 100 --income-runs 5

# Scan for UW worksheets (run individually)
python test_find_underwriter_worksheets.py 1000178XXX
```

---

## Benefits of Current Architecture

✅ **Scalable** - Process hundreds of loans efficiently  
✅ **Cached** - Avoid re-classification on subsequent runs  
✅ **Transparent** - Detailed methodology for every calculation  
✅ **Consistent** - Multiple runs reveal AI variance  
✅ **Comprehensive** - Three-way comparison (Form 1003 vs AI vs UW)  
✅ **Accumulative** - Data builds up over time, never overwritten  
✅ **Batch-friendly** - Process entire portfolios at once  
✅ **Git-safe** - Loan data excluded, code tracked  

---

*Pipeline updated: 2025-10-24*  
*Production-ready income verification system*
