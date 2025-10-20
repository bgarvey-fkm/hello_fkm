# Project Structure - Post Cleanup

**Date:** 2025-10-19  
**Status:** ✅ Reorganized and Cleaned

---

## 📁 Current Directory Structure

```
hello_fkm/
│
├── 📂 loan_docs/                    # LOAN DATA (organized by loan ID)
│   ├── 1000182227/                  # Loan: Rebecca Shook & Katie Madson
│   │   ├── source_pdfs/             # Original PDF documents
│   │   ├── images/                  # PNG images (for vision API)
│   │   ├── text/                    # Extracted text from PDFs
│   │   ├── base64/                  # Base64-encoded images
│   │   └── json/                    # Structured JSON from Azure OpenAI
│   │
│   └── 1000182277/                  # Loan: John Collins
│       ├── source_pdfs/             # Original PDF documents
│       ├── images/                  # PNG images (for vision API)
│       ├── text/                    # Extracted text from PDFs
│       ├── base64/                  # Base64-encoded images
│       └── json/                    # Structured JSON from Azure OpenAI
│
├── 📂 reports/                      # ANALYSIS REPORTS (all loans)
│   ├── form_1003_analysis_*.json    # Form 1003 extraction results
│   ├── verification_analysis_*.json # Document verification results
│   ├── verification_analysis_*.md   # Human-readable reports
│   ├── timeline_analysis_*.md       # Timeline analysis reports
│   ├── timeline_visualization_*.html # Interactive timeline views
│   ├── *_income_analysis.md         # Income verification reports
│   ├── *_dti_reconciliation.html    # DTI reconciliation reports
│   └── PIPELINE_COMPARISON.md       # Multi-loan comparison
│
├── 📂 .venv/                        # Python virtual environment
├── 📂 .git/                         # Git repository
├── 📂 __pycache__/                  # Python cache
│
├── 📄 .env                          # Environment variables (API keys)
├── 📄 .gitignore                    # Git ignore rules
├── 📄 requirements.txt              # Python dependencies
├── 📄 README.md                     # Project documentation
├── 📄 PIPELINE.md                   # Pipeline documentation
│
└── 📜 Python Scripts:
    ├── process_loan_docs.py         # Step 1: Extract text/base64 from docs
    ├── create_underwriting_summary.py # Step 2: Generate JSON via Azure OpenAI
    ├── form_1003_analysis_agent.py  # Step 3a: Identify & extract 1003 assertions
    ├── document_verification_agent.py # Step 3b: Verify docs match assertions
    ├── timeline_analysis_agent.py   # Timeline analysis (2 dimensions)
    ├── create_timeline_visualization.py # HTML timeline visualization
    ├── analyze_loan_timeline.py     # Basic timeline extraction
    ├── income_verification_2turn.py # Income verification (2-turn)
    ├── debt_verification_2turn.py   # Debt verification (2-turn)
    ├── dti_reconciliation_agent.py  # DTI reconciliation
    ├── reorganize_by_loan_id.py     # Utility: Reorganize by loan ID
    ├── cleanup_old_structure.py     # Utility: Clean up old directories
    └── (other utility scripts...)
```

---

## 🗑️ Removed (Old Flat Structure)

The following directories were removed during cleanup:
- ❌ `image_files/` → Now in `loan_docs/{loan_id}/images/`
- ❌ `loan_docs_inputs/` → Now in `loan_docs/{loan_id}/text/` and `/base64/`
- ❌ `loan_docs_json/` → Now in `loan_docs/{loan_id}/json/`
- ❌ `loan_summary/` → Now in `reports/`

**Total cleaned:** ~21.7 MB across 100 files

---

## 🔄 Processing Pipeline

### **Step 1: Document Conversion**
```bash
python process_loan_docs.py
```
- Input: `loan_docs/{loan_id}/source_pdfs/` and `/images/`
- Output: 
  - Text files → `loan_docs/{loan_id}/text/`
  - Base64 files → `loan_docs/{loan_id}/base64/`

### **Step 2: Azure OpenAI Processing**
```bash
python create_underwriting_summary.py
```
- Input: Files from `/text/` and `/base64/`
- Output: Structured JSON → `loan_docs/{loan_id}/json/`

### **Step 3: Form 1003 Analysis (2-Turn)**
```bash
python form_1003_analysis_agent.py
```
- Turn 1: Identify all 1003-related JSON files
- Turn 2: Extract borrower assertions (employment, income, assets, liabilities, property)
- Output: `reports/form_1003_analysis_{loan_id}_{timestamp}.json`

### **Step 4: Document Verification**
```bash
python document_verification_agent.py
```
- Input: 1003 assertions + all loan JSON files
- Checks: Do we have sufficient docs to verify each assertion?
- Output: 
  - `reports/verification_analysis_{loan_id}_{timestamp}.json`
  - `reports/verification_analysis_{loan_id}_{timestamp}.md`

### **Optional: Timeline Analysis**
```bash
python timeline_analysis_agent.py
```
- Analyzes two temporal dimensions:
  1. Underwriting process timeline (when docs created)
  2. Historical data timeline (dates within docs)
- Output: `reports/timeline_analysis_{loan_id}_{timestamp}.md`

### **Optional: Timeline Visualization**
```bash
python create_timeline_visualization.py
```
- Creates interactive HTML timeline
- Output: `reports/timeline_visualization_{loan_id}_{timestamp}.html`

---

## 📊 Current Loans Processed

### Loan 1000182227 - Rebecca Shook & Katie Madson
- **Application Date:** 2025-08-20
- **Loan Amount:** $73,000 (subordinate lien)
- **Property:** 6552 Palomino Way, West Linn, OR
- **Status:** 43 documents processed, verification complete
- **Issues:** Missing Katie's recent paystub, bank statements, IDs

### Loan 1000182277 - John Collins
- **Application Date:** 2025-08-21
- **Loan Amount:** TBD
- **Property:** 1002 Edgemoor Rd
- **Status:** 30 documents processed, verification complete
- **Issues:** Missing VOE, title report, bank statements, flood zone conflict

---

## 🔐 Protected Directories (.gitignore)

The following directories are excluded from Git:
- `loan_docs/` - Contains PII and loan data
- `reports/` - Contains analysis with PII
- `.env` - Contains API keys
- `.venv/` - Python virtual environment
- `__pycache__/` - Python cache

---

## 🎯 Key Insights

### What Works Well
✅ **Loan ID organization** - Easy to add new loans, everything is self-contained
✅ **1003 anchoring** - Form 1003 is the starting point, all validation flows from it
✅ **2-turn agents** - Turn 1 identifies, Turn 2 analyzes (very effective)
✅ **Temporal analysis** - Distinguishing process timeline vs data timeline is powerful
✅ **Automated verification** - Agents catch missing docs and discrepancies

### What We Learned
- Missing documents are common (bank statements, IDs)
- Document freshness matters (30-day paystub rule)
- Data quality issues happen (entry errors, conflicts)
- 1003 is the true anchor of underwriting

---

## 📝 Next Steps

1. **Add more loans** - Drop PDFs/PNGs into `loan_docs/{new_loan_id}/source_pdfs/` and run pipeline
2. **Build stips generator** - Auto-create list of required documents
3. **Add investor guidelines** - Different rules for FHA/VA/Conventional
4. **Create clearance tracker** - Track when conditions are satisfied
5. **Build dashboard** - Overview of all loans and their status

---

*Structure reorganized: 2025-10-19*  
*Previous flat structure cleaned up*
