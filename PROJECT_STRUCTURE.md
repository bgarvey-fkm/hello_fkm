# Project Structure - Income Verification Pipeline

**Date:** 2025-10-24  
**Status:** ✅ Production-Ready Income Verification System

---

## 📁 Current Directory Structure

```
hello_fkm/
│
├── 📂 agents/                               # AI ANALYSIS AGENTS
│   ├── document_semantic_processor.py       # PDF → Semantic JSON
│   ├── form_1003_income_tracker.py          # Extract Form 1003 income timeline
│   └── income_analysis_agent.py             # AI income calculation with Freddie Mac rules
│
├── 📂 pipeline/                             # DOCUMENT PROCESSING PIPELINE
│   ├── process_from_harvest_api.py          # Download PDFs from Harvest API
│   └── process_semantic_compression.py      # Raw JSON → Semantic JSON
│
├── 📂 guidelines/                           # UNDERWRITING GUIDELINES
│   ├── freddie_mac_guide_5300_5400.json     # Parsed Freddie Mac guide (297 pages)
│   ├── freddie_mac_guide_5300_5400_compressed.json # 67 income calculation rules
│   └── spring_eq_guidelines.json            # Spring EQ underwriting guidelines
│
├── 📂 utils/                                # UTILITIES & ONE-TIME SETUP
│   ├── form_1003_schema.json                # Form 1003 JSON template
│   ├── FreddieMacGuide_5300_5400.pdf        # Source Freddie Mac PDF
│   ├── parse_freddie_mac_guide.py           # Parse PDF with Document Intelligence
│   └── compress_freddie_mac_guide.py        # Compress guide to 67 rules
│
├── 📂 loan_docs/                            # LOAN DATA (organized by loan ID)
│   └── {loan_id}/                           # e.g., 1000175957
│       ├── raw_json/                        # Azure Doc Intelligence output
│       ├── semantic_json/                   # Structured semantic documents
│       └── income_analysis/                 # Income analysis results
│           ├── form_1003_income_timeline.json     # Form 1003 income data
│           ├── form_1003_income_timeline.html     # Form 1003 visual timeline
│           ├── income_analysis_run1.json          # AI income calculation run 1
│           ├── income_analysis_run2.json          # AI income calculation run 2
│           ├── consistency_summary_runs1-5.json   # Batch summary (runs 1-5)
│           ├── consistency_summary_all.json       # Comprehensive summary (all runs)
│           ├── consistency_report_runs1-5.html    # Batch HTML report
│           ├── consistency_report_all.html        # Comprehensive HTML report
│           └── underwriter_artifacts_scan.json    # UW worksheets scan results
│
├── 📂 portfolio_data/                       # BATCH ANALYSIS RESULTS
│   ├── deal_2_data.json                     # Deal 2 loan list (859 loans)
│   └── batch_analysis_deal2_{timestamp}.json # Batch analysis results (50 loans)
│
├── 📂 loan_files_inputs/                    # HARVEST API METADATA
│   └── loan_{loan_id}_tree.json             # Document metadata trees
│
├── 📂 reports/                              # LEGACY REPORTS (archived)
│
├── 📂 archive/                              # ARCHIVED CODE (old agents)
│
├── 📄 .env                                  # Environment variables (API keys)
├── 📄 .env.example                          # Template for .env
├── 📄 .gitignore                            # Git ignore rules
├── 📄 requirements.txt                      # Python dependencies
│
├── 📄 README.md                             # Project documentation
├── 📄 PIPELINE.md                           # Pipeline documentation
├── � PROJECT_STRUCTURE.md                  # This file
│
└── 📜 BATCH WORKFLOW SCRIPTS (Root):
    ├── batch_process_deal.py                # Download & process loans from Harvest API
    ├── batch_income_and_1003_analysis.py    # Combined Form 1003 + AI income analysis
    ├── batch_income_analysis.py             # Batch income consistency testing
    └── test_find_underwriter_worksheets.py  # LLM-powered UW artifacts scanner
```


---

## � Complete Processing Pipeline

### **Workflow: Harvest API → Income Verification**

```
1. Download Loans from Harvest API
   ↓
2. Extract PDFs with Azure Document Intelligence
   ↓
3. Create Semantic JSON with Azure OpenAI
   ↓
4. Extract Form 1003 Income (borrower-stated)
   ↓
5. Calculate AI Income (from documents using Freddie Mac rules)
   ↓
6. Compare Form 1003 vs AI Income
   ↓
7. Scan for Underwriter Worksheets (UW-approved income)
```

### **Step 1: Batch Process Deal**
```bash
python batch_process_deal.py --deal-id 2 --num-loans 50
```
- Downloads loan list from Harvest API
- For each loan:
  - Downloads PDF documents
  - Extracts with Azure Document Intelligence → `raw_json/`
  - Creates semantic JSON with Azure OpenAI → `semantic_json/`
- Saves deal data to `portfolio_data/deal_2_data.json`

### **Step 2: Combined Form 1003 + AI Income Analysis**
```bash
python batch_income_and_1003_analysis.py --deal-id 2 --num-loans 50 --income-runs 5
```
- For each loan:
  - Extracts Form 1003 income (once)
  - Runs AI income calculation (5 times for consistency)
  - Compares Form 1003 vs AI average
  - Generates variance analysis
- Creates batch summary with comparison table
- Saves to `portfolio_data/batch_analysis_deal2_{timestamp}.json`

### **Step 3: Scan for Underwriter Worksheets**
```bash
python test_find_underwriter_worksheets.py {loan_id}
```
- LLM-powered classification of each semantic JSON
- Identifies: income worksheets, UW comments, AUS findings, VOE, conditions
- Extracts calculated income amounts and underwriter decisions
- Saves to `loan_docs/{loan_id}/income_analysis/underwriter_artifacts_scan.json`

---

## 📊 Current Portfolio Status

### Deal 2 Analysis
- **Total Loans in Deal:** 859
- **Loans Processed:** 50
- **Form 1003 Extracted:** 48 (96% success rate)
- **Income Analysis Complete:** 50 (100%)
- **Batch Analysis Reports:** Available in `portfolio_data/`

### Key Findings
- **Perfect Matches:** 2 loans (AI = Form 1003 exactly)
- **Close Matches (<5% diff):** Multiple loans showing AI consistency
- **Large Discrepancies (>20%):** 7 loans requiring investigation
- **Highest Variance:** Loan 1000178434 (+101.60% - AI found double the stated income)
- **Average AI Consistency:** 0.93% - 22.47% variance across loans

### Example: Loan 1000175957
- **Form 1003 Income:** $18,599.14/month
- **AI Average (22 runs):** $19,329.72/month
- **Underwriter Approved:** $18,599.14/month (from 4 worksheets)
- **Variance:** 18.86% (LOW consistency)
- **Gap:** AI calculates +$730.58 more than borrower/UW

---

## 🔐 Protected Directories (.gitignore)

The following directories are excluded from Git:
- `loan_docs/` - Contains PII and loan data
- `portfolio_data/` - Contains batch analysis with PII
- `loan_files_inputs/` - Contains Harvest API metadata
- `reports/` - Contains analysis reports
- `.env` - Contains API keys
- `.venv/` - Python virtual environment
- `__pycache__/` - Python cache
- `archive/` - Archived code and documentation

---

## 🎯 Key Features

### ✅ What Works Well
- **Intelligent Document Filtering** - LLM identifies PRIMARY SOURCE documents per Freddie Mac guidelines
- **Form 1003 Extraction** - Chronological timeline of borrower-stated income
- **AI Income Calculation** - Applies 67 Freddie Mac rules for qualifying income
- **Consistency Testing** - Multiple runs reveal AI variance (0%-22%)
- **Batch Processing** - Efficient async processing of 50+ loans
- **Three-Way Comparison** - Form 1003 vs AI vs Underwriter
- **Auto-increment Runs** - Accumulates data over time without overwriting
- **Dual Summary System** - Both batch-specific and comprehensive reports

### 📈 Technical Insights
1. **Intelligent Filtering Works** - Successfully identifies paystubs, W-2s, VOEs, tax transcripts
2. **AI Consistency Varies by Loan** - Simple cases: 0-5% variance, Complex cases: 15-25%
3. **Document Quality Matters** - Complete documentation → low variance
4. **LLM Classification Superior** - Replaces keyword search for finding UW worksheets
5. **Freddie Mac Guidelines Help** - 67 compressed rules improve accuracy

---

## 📝 Next Steps

1. **Investigate High-Variance Loans** - Review loans with >20% discrepancy
2. **Scan All UW Worksheets** - Run artifacts scanner on all 50 loans
3. **Build Reconciliation Report** - Side-by-side: Form 1003 | AI | UW
4. **Test Complex Income** - Self-employed, commission, multiple sources
5. **Improve Prompt Engineering** - Reduce AI variance for simple cases
6. **Scale to More Loans** - Process remaining 809 loans from Deal 2

---

*Structure updated: 2025-10-24*  
*Income verification pipeline production-ready*
