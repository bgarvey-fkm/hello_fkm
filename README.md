# Income Expert - AI Income Verification System

**Branch: income-expert**

An intelligent mortgage income verification system that uses AI to analyze borrower income documents following Freddie Mac underwriting guidelines. The system features intelligent document filtering, automated income calculation, and consistency testing across multiple analysis runs.

## 🎯 Project Goal

Build a production-ready AI income verification system that:
1. **Intelligently filters** income documents using Freddie Mac guidelines
2. **Accurately calculates** qualifying monthly income for DTI ratios
3. **Tests consistency** across multiple LLM runs to identify variance
4. **Follows regulatory guidelines** (Freddie Mac Single-Family Seller/Servicer Guide)
5. **Provides transparency** with detailed calculation methodologies

## 📊 Current Status

**Production-Ready**: Complete income verification pipeline tested on 50 loans
- ✅ Parsed & compressed Freddie Mac Guide (297 pages → 67 rules)
- ✅ Implemented LLM-based intelligent document filtering
- ✅ Form 1003 extraction: 48/50 loans (96% success rate)
- ✅ AI income analysis: 50/50 loans (100% success rate)
- ✅ Three-way comparison: Form 1003 vs AI vs Underwriter
- ✅ Batch processing: 50 loans processed from Deal 2
- ✅ Consistency testing: 0.93% - 22.47% variance range
- 🔄 Next: Investigate high-variance loans and scale to remaining 809 loans

## 🏗️ System Architecture

### Complete Pipeline Visualization

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          INCOME EXPERT AI PIPELINE                              │
│                     From Loan Documents to Verified Income                      │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: DOCUMENT ACQUISITION & EXTRACTION                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

    📦 Harvest API                        🔍 Azure Document Intelligence
    ┌────────────┐                        ┌──────────────────────┐
    │ Deal 2     │                        │ PDF → Raw JSON       │
    │ 859 Loans  │──── Download PDFs ────▶│ • Extract text       │
    │            │                        │ • Extract tables     │
    └────────────┘                        │ • Parse structure    │
         │                                └──────────┬───────────┘
         │                                           │
         ├─ /doc_meta_data_tree/{loan_id}          │
         ├─ /pdf/{file_id}                          │
         │                                           ▼
         │                              loan_docs/{loan_id}/raw_json/
         │                              ├─ FID12345_Paystub.json
         │                              ├─ FID12346_W2.json
         │                              ├─ FID12347_1003.json
         │                              └─ ... (63 files total)


┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: SEMANTIC COMPRESSION (Azure OpenAI GPT-5-mini)                        │
└─────────────────────────────────────────────────────────────────────────────────┘

    📄 Raw JSON (63 files)                🧠 Semantic Analysis
    ┌──────────────────┐                  ┌─────────────────────────┐
    │ Document         │                  │ Identify doc type       │
    │ Intelligence     │─── Process ─────▶│ Extract key fields      │
    │ Output           │                  │ Structure semantically  │
    └──────────────────┘                  └──────────┬──────────────┘
         │                                           │
         │  Example Raw:                             │  Example Semantic:
         │  {                                        │  {
         │    "content": "Pay stub...",              │    "metadata": {...},
         │    "tables": [...],                       │    "semantic_content": {
         │    "pages": [...]                         │      "document_type": "paystub",
         │  }                                        │      "employer": "ABC Corp",
         │                                           │      "gross_pay": 4480.00,
         │                                           │      "ytd_gross": 89600.00
         │                                           │    }
         │                                           │  }
         │                                           ▼
         │                              loan_docs/{loan_id}/semantic_json/
         │                              ├─ FID12345_Paystub.json
         │                              ├─ FID12346_W2.json
         │                              ├─ FID12347_1003.json
         │                              └─ ... (63 semantic files)


┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: PARALLEL PROCESSING TRACKS                                            │
└─────────────────────────────────────────────────────────────────────────────────┘

    63 Semantic Files
         │
         ├──────────────────┬────────────────────┬──────────────────┐
         │                  │                    │                  │
         ▼                  ▼                    ▼                  ▼
    ┌─────────┐      ┌──────────┐      ┌────────────┐      ┌──────────┐
    │ TRACK 1 │      │ TRACK 2  │      │  TRACK 3   │      │ TRACK 4  │
    │ Classify│      │ Form     │      │ Employment │      │ Income   │
    │  Docs   │      │  1003    │      │  History   │      │ Analysis │
    └────┬────┘      └────┬─────┘      └─────┬──────┘      └────┬─────┘
         │                │                   │                   │
         │                │                   │                   │

┌────────┴──────────────────────────────────────────────────────────────────────┐
│ TRACK 1: INCOME DOCUMENT CLASSIFICATION                                        │
│ (pipeline/classify_income_documents.py)                                        │
└─────────────────────────────────────────────────────────────────────────────────┘

    All 63 Files ─────▶ 🤖 AI Classifier ─────▶ Classification Results
                        ┌──────────────┐
                        │ Is this doc  │        ✅ Income-Relevant (8):
                        │ relevant for │        • Paystubs (3)
                        │ income       │        • W-2s (2)
                        │ verification?│        • Tax transcripts (2)
                        │              │        • VOE (1)
                        │ Per Freddie  │
                        │ Mac rules?   │        ❌ Excluded (55):
                        └──────────────┘        • Appraisals
                                                • Disclosures
                                                • Title docs
                                                • etc.

┌────────┬──────────────────────────────────────────────────────────────────────┐
│ TRACK 2: FORM 1003 TIMELINE EXTRACTION                                         │
│ (agents/form_1003_income_tracker.py)                                           │
└─────────────────────────────────────────────────────────────────────────────────┘

    Filter: Form 1003 files only
         │
         ▼
    🔍 Extract Income Fields        📊 Track Changes Over Time
    ┌──────────────────┐            ┌─────────────────────────┐
    │ Section 5:       │            │ Version 1 (App Taken):  │
    │ • Borrower $XXX  │────────────│   Income: $7,500        │
    │ • Co-borrower $X │            │                         │
    │ Section 8:       │            │ Version 2 (Processing): │
    │ • Employment     │            │   Income: $7,770 ←─┐    │
    │ • Years          │            │                    │    │
    └──────────────────┘            │ Version 3 (CTC):   │    │
                                    │   Income: $7,770 ←─┘    │
                                    └─────────────────────────┘
         │
         ▼
    loan_docs/{loan_id}/income_analysis/
    └─ form_1003_income_timeline.json
       {
         "borrower_income": 4731.60,
         "co_borrower_income": 3039.32,
         "total_monthly_income": 7770.92,
         "versions_found": 3,
         "final_version_date": "2025-06-28"
       }

┌────────┬──────────────────────────────────────────────────────────────────────┐
│ TRACK 3: EMPLOYMENT HISTORY CONSOLIDATION                                      │
│ (agents/employment_history_agent.py)                                           │
└─────────────────────────────────────────────────────────────────────────────────┘

    Income Docs (from Track 1) ───▶ 🧠 Employment Analyzer
    • Paystubs                      ┌──────────────────────┐
    • W-2s                          │ For each borrower:   │
    • VOEs                          │ • Current employer   │
    • Tax returns                   │ • Job title          │
                                    │ • Start date         │
                                    │ • Employment type    │
                                    │ • Pay frequency      │
                                    └──────────┬───────────┘
                                               │
                                               ▼
    loan_docs/{loan_id}/employment_history/
    └─ employment_history.json
       {
         "borrowers": [
           {
             "name": "Amy",
             "current_employer": "County Public Schools",
             "job_title": "Special Education Teacher",
             "employment_type": "W-2 Employee",
             "start_date": "2018-08-15",
             "years_employed": 7.2,
             "pay_frequency": "Monthly"
           }
         ]
       }

┌────────┴──────────────────────────────────────────────────────────────────────┐
│ TRACK 4: AI INCOME ANALYSIS (CORE CALCULATION ENGINE)                          │
│ (agents/income_analysis_agent.py)                                              │
└─────────────────────────────────────────────────────────────────────────────────┘

    Inputs:
    ├─ Income Docs (from Track 1 classification)
    ├─ Freddie Mac Guidelines (67 rules)
    ├─ Edge Cases Library (EC001-EC005)
    └─ Form 1003 Data (for comparison)

         │
         ▼
    ┌──────────────────────────────────────────────────────────┐
    │  🤖 AI Income Calculator (GPT-5-mini)                │
    │                                                      │
    │  1. Load Freddie Mac Decision Tree                  │
    │     ├─ Base non-fluctuating salary rules            │
    │     ├─ Variable income (bonus/OT) rules             │
    │     ├─ Pay frequency multipliers                    │
    │     └─ Documentation requirements                   │
    │                                                      │
    │  2. Check Edge Cases (EC001-EC005)                  │
    │     ├─ EC001: Employment status change              │
    │     ├─ EC002: VA disability income                  │
    │     ├─ EC003: Return to work after leave            │
    │     ├─ EC004: Variable income w/o history           │
    │     └─ EC005: Teacher 10-month salary ⭐            │
    │                                                      │
    │  3. Apply Calculation Rules                         │
    │     • Identify pay frequency                        │
    │     • Calculate base income                         │
    │     • Evaluate variable income (2-yr history)       │
    │     • Apply special rules (teachers, etc.)          │
    │     • Reconcile multiple sources                    │
    │                                                      │
    │  4. Document Methodology                            │
    │     • Which docs used                               │
    │     • Which rules applied                           │
    │     • Step-by-step calculation                      │
    │     • Edge cases triggered                          │
    └──────────────────────────┬───────────────────────────┘
                               │
                               ▼
    loan_docs/{loan_id}/income_analysis/
    ├─ income_analysis_run_1.json
    ├─ income_analysis_run_2.json
    ├─ income_analysis_run_3.json
    └─ consistency_summary_all.json
       {
         "average_income": 7621.00,
         "variance_pct": 1.9,
         "methodology": "W-2 ÷ 12 (teacher exception)",
         "edge_cases_applied": ["EC005"],
         "confidence": "high"
       }


┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: INCOME COMPARISON & VALIDATION                                        │
│ (agents/income_comparison_agent.py)                                            │
└─────────────────────────────────────────────────────────────────────────────────┘

    Three-Way Comparison:

    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │  Form 1003   │      │  AI Analysis │      │  Comparison  │
    │  Timeline    │      │  Results     │      │  Analysis    │
    │              │      │              │      │              │
    │ Borrower     │      │ Borrower     │      │ Variance:    │
    │ stated       │◀────▶│ calculated   │─────▶│   ±2%        │
    │ $7,770/mo    │      │ $7,621/mo    │      │              │
    │              │      │              │      │ Status: ✅   │
    │ Final CTC    │      │ Avg of 3     │      │ Within tol.  │
    │ version      │      │ runs         │      │              │
    └──────────────┘      └──────────────┘      └──────────────┘

    Output: income_comparison_analysis.json
    {
      "loan_id": "1000178665",
      "form_1003_income": 7770.92,
      "ai_avg_income": 7621.00,
      "difference_pct": -1.93,
      "ai_consistency_rating": "HIGH",
      "variance_pct": 1.9,
      "assessment": "AI calculation within 2% of stated income",
      "notes": "Teacher exception (EC005) correctly applied"
    }


┌─────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 5: REPORTING & OUTPUTS                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘

    📊 Individual Loan Reports          📈 Aggregate Analytics
    ┌──────────────────────┐            ┌──────────────────────┐
    │ Per Loan:            │            │ Portfolio-wide:      │
    │ • Consistency HTML   │            │ • CSV exports        │
    │ • Form 1003 timeline │            │ • Accuracy histogram │
    │ • Employment history │            │ • Edge case freq.    │
    │ • Income comparison  │            │ • Variance analysis  │
    │ • Analysis runs 1-N  │            │ • HTML dashboards    │
    └──────────────────────┘            └──────────────────────┘
              │                                    │
              └────────────┬───────────────────────┘
                           │
                           ▼
              📁 Output Directory Structure:
              
              loan_docs/{loan_id}/
              ├─ income_analysis/
              │  ├─ form_1003_income_timeline.json
              │  ├─ income_analysis_run_1.json
              │  ├─ income_analysis_run_2.json
              │  ├─ income_analysis_run_3.json
              │  ├─ consistency_summary_all.json
              │  ├─ income_comparison_analysis.json
              │  └─ consistency_report.html
              └─ employment_history/
                 └─ employment_history.json
              
              aggregate_data/
              ├─ income_comparison_latest.csv
              └─ accuracy_histogram.png


┌─────────────────────────────────────────────────────────────────────────────────┐
│ KEY SUCCESS METRICS (Based on 50-Loan Production Test)                         │
└─────────────────────────────────────────────────────────────────────────────────┘

    ✅ Document Classification:    100% success (all loans processed)
    ✅ Form 1003 Extraction:        96% success (48/50 loans)
    ✅ AI Income Calculation:       100% success (50/50 loans)
    ✅ High Accuracy (<5% var):     70% of loans (35/50)
    ⭐ Edge Case Application:       Improved accuracy from 14.36% → 2%
    📊 Average Processing Time:     ~10-12 minutes per loan
    💰 Cost per Loan:              ~$0.17-0.32 (Azure OpenAI)
```

## Features

- **📥 Harvest API Integration**: Download loan documents with metadata trees
- **🔍 PDF Extraction**: Azure Document Intelligence for text, tables, structure
- **🧠 Semantic Analysis**: AI-powered document classification and field extraction
- **📚 Freddie Mac Guidelines**: 67 compressed income calculation rules
- **🎯 Intelligent Filtering**: LLM identifies income-relevant documents from ALL files
- **💰 Income Calculation**: Follows Freddie Mac underwriting guidelines
- **🧪 Consistency Testing**: Multi-run variance analysis (async parallel)
- **📊 Detailed Reports**: HTML/JSON with calculation methodologies
- **⚡ Batch Processing**: Process multiple loans from a deal

## Project Structure

```
hello_fkm/
├── pipeline/                                # 🔄 Document Processing Pipeline
│   └── process_semantic_compression.py      # Raw JSON → Semantic JSON
│
├── agents/                                  # 🤖 AI Analysis Agents
│   ├── income_analysis_agent.py             # Income calculation with consistency testing
│   ├── form_1003_income_tracker.py          # Extract Form 1003 income fields
│   └── document_semantic_processor.py       # PDF → Semantic JSON processor
│
├── utils/                                   # 🛠️ One-Time Setup Utilities
│   ├── parse_freddie_mac_guide.py           # Parse Freddie Mac PDF (one-time)
│   ├── compress_freddie_mac_guide.py        # Compress to 67 rules (one-time)
│   ├── FreddieMacGuide_5300_5400.pdf        # Source PDF (297 pages)
│   └── form_1003_schema.json                # Form 1003 field definitions
│
├── guidelines/                              # 📚 Underwriting Guidelines
│   ├── freddie_mac_guide_5300_5400.json              # Parsed guide (297 pages)
│   ├── freddie_mac_guide_5300_5400_compressed.json   # 67 income calculation rules
│   └── spring_eq_guidelines.json            # Spring EQ underwriting guidelines
│
├── loan_docs/                               # 📁 Loan Documents (gitignored)
│   └── {loan_id}/
│       ├── raw_json/                        # Azure Doc Intelligence output
│       ├── semantic_json/                   # Structured semantic documents
│       └── income_analysis/                 # AI income calculation runs
│
├── portfolio_data/                          # 📊 Batch Analysis Reports (gitignored)
│   ├── batch_analysis_deal2_*.json          # Batch-specific summaries
│   └── comprehensive_batch_summary_*.json   # Cumulative all-runs summary
│
├── loan_files_inputs/                       # 📥 Loan metadata from Harvest (gitignored)
│   └── loan_{loan_id}_tree.json
│
├── batch_process_deal.py                    # Step 1: Download & extract from Harvest
├── batch_income_and_1003_analysis.py        # Step 2: Form 1003 + AI income (MAIN PIPELINE)
├── test_find_underwriter_worksheets.py      # Step 3: Find UW-approved income
└── requirements.txt                         # Python dependencies
```

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/bgarvey-fkm/hello_fkm.git
cd hello_fkm
git checkout income-expert
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your Azure OpenAI credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:
```env
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

## Usage

### Complete Workflow: From Harvest API to Income Calculation

#### Step 1: Download Loan Documents from Harvest API

```bash
# Process entire deal (multiple loans)
python batch_process_deal.py --deal-id 2 --num-loans 50

# This will:
# 1. Fetch loan list from Harvest API (/api/deal/{deal_id})
# 2. Download PDF documents for each loan (/api/pdf/{file_id})
# 3. Extract PDFs with Azure Document Intelligence
# 4. Create semantic JSON with Azure OpenAI
# 5. Save to loan_docs/{loan_id}/raw_json/ and semantic_json/
```

#### Step 2: Run Combined Form 1003 + AI Income Analysis

```bash
# Extract Form 1003 income AND run AI analysis on 50 loans
python batch_income_and_1003_analysis.py --deal-id 2 --num-loans 50 --income-runs 5

# This will:
# 1. Extract Form 1003 income fields from semantic JSON (stated income)
# 2. Run AI income analysis with Freddie Mac guidelines (5 runs per loan)
# 3. Test consistency across multiple runs
# 4. Compare Form 1003 vs AI income
# 5. Generate comprehensive comparison table
# 6. Save to portfolio_data/batch_analysis_deal2_*.json

# Results from 50-loan test:
# - Form 1003 extraction: 48/50 (96% success)
# - AI income analysis: 50/50 (100% success)
# - Perfect matches (0% diff): 2 loans
# - Close matches (<5% diff): ~35 loans
# - Large discrepancies (>20%): 7 loans
```

#### Step 3: Find Underwriter-Approved Income (Optional)

```bash
# Search for underwriter worksheets/calculations
python test_find_underwriter_worksheets.py 1000175957

# This will:
# 1. Search semantic JSON for underwriter artifacts
# 2. Extract UW-approved income amounts
# 3. Compare with Form 1003 and AI calculations
# 4. Show three-way comparison
```

#### Legacy: Parse Freddie Mac Guide (One-time setup - already done)

```bash
# Parse 297-page Freddie Mac PDF with Azure Document Intelligence
python utils/parse_freddie_mac_guide.py
# Output: guidelines/freddie_mac_guide_5300_5400.json (491K characters)

# Compress to 67 structured income calculation rules
python utils/compress_freddie_mac_guide.py
# Output: guidelines/freddie_mac_guide_5300_5400_compressed.json (67 rules)
```

#### Legacy: Single-Loan Analysis (for testing)

```bash
# Single loan, single run
python agents/income_analysis_agent.py 1000175957 1

# Process:
# 1. Load Freddie Mac guidelines (67 rules)
# 2. Load ALL semantic JSON files (e.g., 63 documents)
# 3. LLM filters documents based on Freddie Mac income verification rules
#    → Identifies 8 relevant docs: paystubs, W-2s, tax transcripts, VOE
# 4. LLM calculates monthly gross income using Freddie Mac guidelines
# 5. Output: JSON with income amount + detailed methodology
```

## Key Findings from 50-Loan Production Batch

### Overall Results
- **Loans Processed**: 50 loans from Deal 2
- **Form 1003 Extraction**: 48/50 (96% success rate)
- **AI Income Analysis**: 50/50 (100% success rate)
- **Processing Time**: ~10-12 minutes per loan
- **Cost**: ~$0.17-0.32 per loan (Azure OpenAI)

### Comparison Results (Form 1003 vs AI Income)
- **Perfect Matches (0.00% diff)**: 2 loans
  - Loan 1000177311: Both $11,083.33/month
  - Loan 1000178066: Both $14,416.67/month
- **Close Matches (<5% diff)**: ~35 loans (70%)
- **Moderate Variance (5-20% diff)**: ~6 loans (12%)
- **High Variance (>20% diff)**: 7 loans (14%)

### Highest Discrepancies (Investigation Needed)
1. **Loan 1000178434**: +101.60% (AI found $20,160 vs stated $10,000)
2. **Loan 1000177371**: -53.74% (AI found $4,620 vs stated $9,987.96)
3. **Loan 1000177613**: -51.59% (AI found $3,893.96 vs stated $8,042)
4. **Loan 1000178589**: +48.42% (AI found $11,083.33 vs stated $7,468.89)
5. **Loan 1000178230**: +42.06% (AI found $15,833.33 vs stated $11,150)

### AI Consistency Testing
- **Best Consistency**: Loan 1000178372 (0.93% variance)
- **Average Consistency**: ~5-10% variance for most loans
- **Worst Consistency**: Loan 1000178255 (22.47% variance)
- **Finding**: Simple W-2 cases have <5% variance; complex/incomplete cases >15%

### Three-Way Comparison Example (Loan 1000175957)
```
Form 1003 Stated Income:    $18,620.07/month
AI Calculated Income:       $18,620.07/month  (0.00% difference)
Underwriter Approved:       $18,620.07/month
Status: ✅ Perfect three-way match
```

## Key Components Explained

### 1. Harvest API Integration

When processing loan 1000175957 with 63 total documents:

```
>> Analyzing all documents to determine income verification relevance...
>> Found 63 total documents
>> Filtering based on Freddie Mac income verification guidelines...
>> ✓ Included: NO_CATEGORY_Paystubs_2025-05-21... - Paystubs (YTD) — acceptable primary evidence
>> ✓ Included: NO_CATEGORY_W2_2025-05-21... - W-2 (2023) — acceptable prior-year wage documentation
>> ✓ Included: NO_CATEGORY_W2_2025-05-21... - W-2 (2024) — acceptable prior-year wage documentation
>> ✓ Included: NO_CATEGORY_Request_for_Transcript... - IRS tax transcript — acceptable alternative
>> ✓ Included: Title_Product_Documents_Verbal_VOE... - Verbal VOE — acceptable 10-day pre-closing verification
>> Filtered to 8 income verification documents (from 63 total)
```

### Example: Income Calculation Output

```json
{
  "monthly_gross_income": 18620.07,
  "calculation_methodology": {
    "paystubs_analysis": "Reviewed multiple recent paystubs (weekly pay frequency). Base: $2,240/week × 52 / 12 = $9,706.67/month",
    "w2_analysis": "Most recent W-2 (2024) box 1 wages = $223,440.82 / 12 = $18,620.07/month",
    "reconciliation": "Used 2024 W-2 as qualifying income per Freddie Mac Section 5302.2(b)",
    "income_components": {
      "base_salary": 9706.67,
      "overtime": 0.0,
      "bonus": 4456.70,
      "commission": 4456.70,
      "other": 0.0
    },
    "pay_frequency": "weekly",
    "calculation_steps": [
      "Step 1: Identify most recent W-2 (2024) = $223,440.82",
      "Step 2: Determine monthly qualifying income: $223,440.82 / 12 = $18,620.07",
      "Step 3: Verify paystubs support weekly base: $2,240 × 52 / 12 = $9,706.67",
      "Step 4: Calculate fluctuating component: $18,620.07 - $9,706.67 = $8,913.40"
    ]
  },
  "confidence_level": "medium",
  "notes": "Primary qualifying monthly income from 2024 W-2. Paystubs support base and recurring bonuses/commissions."
}
```

## Key Components Explained

### 1. Harvest API Integration

**Document Download Process:**
```python
# Get loan metadata tree
GET https://harvestapi.firstkeyholdings.net:60000/api/doc_meta_data_tree/{loan_number}
# Returns: Document hierarchy with FileIds, document types, upload dates

# Download individual PDFs
GET https://harvestapi.firstkeyholdings.net:60000/api/pdf/{file_id}
# Returns: PDF binary content
```

**Metadata Structure:**
- FileId: Unique document identifier
- FileName: Document name
- DocPredictionType: AI-predicted document category
- SpringDocType: Spring EQ document classification
- Timeline: Loan processing stage (App Taken, Conditional Approval, Clear to Close, etc.)

### 2. PDF → Raw JSON (Azure Document Intelligence)

**Process:**
- Model: `prebuilt-layout`
- Extracts: Text content, tables (with cells), document structure, page count
- Output format:
  ```json
  {
    "content": "Full text content...",
    "pages": [...],
    "tables": [
      {
        "row_count": 10,
        "column_count": 5,
        "cells": [{"row": 0, "col": 0, "content": "..."}]
      }
    ]
  }
  ```

### 3. Raw JSON → Semantic JSON (Azure OpenAI)

**Intelligent Document Classification:**
- LLM analyzes raw JSON content
- Identifies document type (paystub, W-2, 1099, bank statement, etc.)
- Extracts key fields specific to document type
- Structures data for downstream analysis

**Example Semantic JSON:**
```json
{
  "metadata": {
    "FileId": 20034,
    "FileName": "Paystubs_2025-05-21",
    "DocPredictionType": "Pay Statement",
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
  }
}
```

### 4. Freddie Mac Guidelines Integration

**Parsing Process:**
1. **Input**: FreddieMacGuide_5300_5400.pdf (297 pages, 1.7 MB)
2. **Azure Doc Intelligence**: Extract 491,423 characters, 284 tables
3. **Azure OpenAI**: Compress to 67 structured income calculation rules
4. **Output**: JSON with section numbers, topics, rules, details, examples

**Sample Compressed Rule:**
```json
{
  "section": "5303.1(c)(i)",
  "topic": "Base non-fluctuating employment earnings",
  "rule": "Base earnings considered stable when supported by YTD paystubs and W-2s",
  "details": [
    "Calculate by converting pay period gross to monthly using standard multipliers",
    "Weekly ×52/12, Bi-weekly ×26/12, Semi-monthly ×24/12"
  ],
  "examples": ["Weekly gross $800 → $800×52/12 = monthly income"]
}
```

### 5. Intelligent Document Filtering

**How It Works:**
1. Load ALL semantic JSON files (not just income docs)
2. Load Freddie Mac guidelines (67 rules)
3. For each document:
   - Create summary: file_id, file_name, document_type, content preview (500 chars)
   - LLM analyzes: "Is this relevant for income verification per Freddie Mac?"
   - Decision: Include with reason OR Exclude with reason
4. Return filtered list of income-relevant documents

**Benefits:**
- Captures ALL valid income sources (not just paystubs/W-2s)
- Finds: Employment verification letters, tax transcripts, pension statements, verbal VOEs
- Provides transparency (inclusion/exclusion reasons)
- Follows regulatory guidelines automatically

### 6. Income Calculation with Freddie Mac Guidelines

**Process:**
1. Receive filtered income documents
2. Apply Freddie Mac calculation rules:
   - Identify pay frequency (weekly, bi-weekly, semi-monthly, monthly)
   - Base pay calculation (apply multipliers)
   - Variable income (overtime, bonus, commission) - 2-year average requirement
   - Pension/retirement income (1099-R distributions)
   - Employment verification (10-day pre-closing VOE)
3. Reconcile multiple sources (paystubs vs W-2s)
4. Generate detailed methodology with rule references

**Key Freddie Mac Rules Applied:**
- Section 5302.2(b): Use most recent W-2 divided by 12
- Section 5303.1(c)(i): Pay frequency multipliers (weekly ×52/12, etc.)
- Section 5303.1(d)(ii)(A): Fluctuating earnings require 2-year history
- Section 5302.2(d): 10-day pre-closing employment verification

### 7. Consistency Testing & Variance Analysis

**Multi-Run Testing:**
- Run same analysis 3-10 times asynchronously
- Track variance in calculated income amounts
- Identify most common methodologies
- Generate statistics: min, max, average, variance percentage

**Insights from Testing:**
- Loan 1000175957: 4.06% variance (good consistency)
- Loan 1000176563: 35.90% variance (high - limited documentation)
- Guidelines can increase variance if too many options given
- Tighter prompts with prescriptive rules improve consistency

## Key Findings & Insights

### Intelligent Filtering Results (Loan 1000175957)
- **Total Documents**: 63 files in loan package
- **Income-Relevant**: 8 documents identified by LLM
- **Documents Found**:
  - 3 Paystubs (with YTD earnings)
  - 2 W-2 Forms (2023, 2024)
  - 2 IRS Tax Transcripts (Record of Account, Tax Transcript)
  - 1 Verbal VOE (employment verification)
- **Excluded**: 55 documents (appraisals, disclosures, title docs, etc.)

### Consistency Testing Results

**Loan 1000175957 (W-2 employee with bonuses):**
- 10-run test: **4.06% variance** ✅
- Average: $19,394.62/month
- Most common: $19,394.62 (appeared in 4/10 runs)
- Consistency: **HIGH** - Very consistent results

**With Freddie Mac Guidelines:**
- Initial test: **9.54% variance** ⚠️
- Finding: Guidelines gave LLM more options, increasing variance
- Solution: More prescriptive prompts needed ("ALWAYS use method X")

**Loan 1000176563 (Limited documentation):**
- Variance: **35.90%** ❌
- Issue: Incomplete income documentation
- Learning: Consistency depends on document quality

### Technical Insights

1. **More Guidelines ≠ Better Consistency**
   - Descriptive guidelines (showing options) can increase variance
   - Prescriptive rules ("ALWAYS do X") improve consistency
   - Balance needed between flexibility and determinism

2. **Intelligent Filtering Works**
   - Successfully identifies all Freddie Mac-approved income sources
   - Captures documents that hard-coded filters miss (VOE, tax transcripts)
   - Provides transparency with inclusion reasons

3. **LLM Calculation Variance**
   - Simple cases: 4-10% variance (acceptable)
   - Complex cases: 20-35% variance (needs improvement)
   - Methodology clustering: LLM often picks 2-3 common approaches

4. **Document Quality Matters**
   - Complete documentation → low variance
   - Missing documents → high variance
   - YTD paystubs + 2 years W-2s = best consistency

## Next Steps

### Immediate Priorities
1. ✅ ~~Intelligent document filtering with Freddie Mac guidelines~~
2. ✅ ~~Consistency testing framework~~
3. ✅ ~~Form 1003 extraction and comparison~~
4. ✅ ~~Batch processing pipeline (50 loans tested)~~
5. 🔄 **Investigate high-variance loans** (7 loans with >20% discrepancy)
   - Analyze semantic JSON for Loan 1000178434 (+101.60%)
   - Understand why AI found double the stated income
   - Compare with underwriter-approved amounts
6. 🔄 **Scale underwriter artifacts scanner** to all 50 loans
   - Build comprehensive three-way comparison dataset
   - Identify patterns in UW-approved vs AI vs Form 1003
7. 🔄 **Process remaining 809 loans** from Deal 2
   - Run batch_process_deal.py for next batch
   - Run combined analysis on larger dataset
   - Look for portfolio-wide patterns

### Research & Development
- [x] Test Freddie Mac guidelines on 50+ diverse loans ✅
- [ ] Compare LLM calculations vs human underwriter results (7 loans in progress)
- [ ] Build confidence scoring based on document quality
- [ ] Improve calculation consistency on complex scenarios:
  * Self-employed borrowers (Schedule C, business returns)
  * Multiple income sources (W-2 + rental + pension)
  * Commission-based income (2-year averaging)
  * Co-borrower income aggregation
- [ ] Handle edge cases: gaps in employment, job changes, temporary income

### Production Readiness
- [ ] Error handling and validation
- [ ] Logging and monitoring
- [ ] Performance optimization (caching, batch processing)
- [ ] API endpoint for income verification service
- [ ] Integration with Form 1003 data for validation

## Technical Stack

### Azure Services
- **Azure OpenAI**: GPT-5-mini (400K context window)
  - Document classification and field extraction
  - Intelligent document filtering
  - Income calculation with guidelines
  - Guideline compression (297 pages → 67 rules)
- **Azure Document Intelligence**: prebuilt-layout model
  - PDF text extraction
  - Table extraction with cell-level data
  - Document structure analysis

### Python Libraries
- `openai` - Azure OpenAI SDK
- `azure-ai-documentintelligence` - Document Intelligence SDK
- `requests` - Harvest API communication
- `asyncio` - Async/await parallel processing
- `pathlib` - File system operations
- `dotenv` - Environment variable management

### Data Flow
```
Harvest API (PDFs)
  ↓
Azure Document Intelligence (Raw JSON)
  ↓
Azure OpenAI (Semantic JSON)
  ↓
Freddie Mac Guidelines (Filtering Rules)
  ↓
Azure OpenAI (Intelligent Filtering)
  ↓
Azure OpenAI (Income Calculation)
  ↓
Reports (JSON + HTML)
```

### Environment Requirements
- Python 3.8+
- Azure OpenAI API access
- Azure Document Intelligence API access
- Network access to Harvest API
- Environment variables in `.env`:
  ```
  AZURE_OPENAI_ENDPOINT=https://...
  AZURE_OPENAI_KEY=...
  AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
  AZURE_OPENAI_API_VERSION=2024-12-01-preview
  DOC_INTELLIGENCE_ENDPOINT=https://...
  DOC_INTELLIGENCE_KEY=...
  ```

## Security Notes

🔒 **Protected Information (NOT in GitHub):**
- `.env` - Azure OpenAI & Document Intelligence credentials
- `loan_docs/` - All loan documents and processed data (PHI/PII)
- `portfolio_data/` - Batch analysis reports with loan-level data
- `loan_files_inputs/` - Harvest API data with loan IDs
- `*.pdf` - Source Freddie Mac guide documents
- `deal_*.json` - Deal data from Harvest API

✅ **Safe to Share (in GitHub):**
- Python scripts (`.py` files)
- `.env.example` - Template with no actual credentials
- `.gitignore` - Protection rules
- `README.md`, `PIPELINE.md`, `PROJECT_STRUCTURE.md`
- `requirements.txt` - Python dependencies
- `guidelines/*.json` - Freddie Mac compressed rules (public information)

⚠️ **Critical Security Rules:**
- **Never commit loan data** - Contains borrower PII/PHI
- **Never commit API keys** - Azure credentials are secrets
- **Never commit .env file** - Contains sensitive credentials
- **Review commits** - Double-check no loan IDs, names, or SSNs included

## Requirements

- Python 3.8+
- Azure OpenAI API access (GPT-5-mini or similar)
- Azure Document Intelligence API access
- Network access to Harvest API (internal FirstKey network)
- Sufficient Azure quota for batch processing

## Contributing

This is a development branch for income verification research. For collaboration:

1. **Review Documentation**: Read `PIPELINE.md` for technical details
2. **Check Reports**: Review HTML consistency reports for insights
3. **Test on New Loans**: Run on diverse income scenarios
4. **Share Findings**: Document edge cases and variance patterns
5. **Improve Guidelines**: Refine Freddie Mac rule application

## Related Documentation

- `PIPELINE.md` - Detailed technical pipeline documentation
- `PROJECT_STRUCTURE.md` - File organization and conventions
- `guidelines/freddie_mac_guide_5300_5400_compressed.json` - Income calculation rules
- `reports/` - HTML consistency reports (examples of analysis)

## Branch Information

- **Main Branch**: General underwriting agents and utilities
- **Income-Expert Branch** (this): Specialized income verification with Freddie Mac guidelines
- **Focus**: DTI-ready income calculation with regulatory compliance

## References

- **Freddie Mac Single-Family Seller/Servicer Guide** - Sections 5300-5400 (Income and Employment Documentation)
- **Azure Document Intelligence** - [Microsoft Documentation](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/)
- **Azure OpenAI** - [Service Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
