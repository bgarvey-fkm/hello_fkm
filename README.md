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

**Active Development**: Intelligent document filtering with Freddie Mac guidelines
- ✅ Parsed & compressed Freddie Mac Guide (297 pages → 67 rules)
- ✅ Implemented LLM-based intelligent document filtering
- ✅ Filters 63 documents → 8 income-relevant docs (paystubs, W-2s, tax transcripts, VOE)
- ✅ Consistency testing: 4-10% variance on test loans
- ✅ Batch processing pipeline for multiple loans
- 🔄 Next: Test on complex income scenarios (self-employed, multiple sources)

## 🏗️ System Architecture

### Complete Pipeline Flow

```
1. HARVEST API → Download Loan Documents
   ├─ API: https://harvestapi.firstkeyholdings.net:60000/api
   ├─ Endpoint: /doc_meta_data_tree/{loan_number}
   ├─ Endpoint: /pdf/{file_id}
   └─ Output: loan_docs/{loan_id}/raw_json/*.json (PDF extracted as JSON)

2. PDF EXTRACTION → Raw JSON
   ├─ Azure Document Intelligence (prebuilt-layout model)
   ├─ Input: PDF documents from Harvest API
   ├─ Processing: Extract text, tables, structure, metadata
   └─ Output: loan_docs/{loan_id}/raw_json/{file_id}.json

3. RAW JSON → Semantic JSON
   ├─ Azure OpenAI (GPT-4o-mini)
   ├─ Input: Raw extracted JSON from Document Intelligence
   ├─ Processing: Identify document type, extract key fields, structure data
   └─ Output: loan_docs/{loan_id}/semantic_json/{file_id}.json
        └─ Structure: {metadata: {...}, semantic_content: {...}}

4. FREDDIE MAC GUIDELINES → Compressed Rules
   ├─ Input: FreddieMacGuide_5300_5400.pdf (297 pages)
   ├─ Azure Document Intelligence: Parse PDF
   ├─ Azure OpenAI: Extract 67 income calculation rules
   └─ Output: guidelines/freddie_mac_guide_5300_5400_compressed.json

5. INTELLIGENT DOCUMENT FILTERING
   ├─ Input: ALL semantic JSON files (63 documents)
   ├─ Freddie Mac Guidelines: Load 67 income verification rules
   ├─ Azure OpenAI: Analyze each document for income relevance
   ├─ Decision: Include/Exclude with reasoning
   └─ Output: Filtered set (e.g., 8 income docs: paystubs, W-2s, tax transcripts, VOE)

6. INCOME CALCULATION
   ├─ Input: Filtered income documents
   ├─ Freddie Mac Guidelines: Apply calculation rules
   ├─ Azure OpenAI: Calculate monthly gross income
   ├─ Processing: Base pay + overtime + bonus + commission + pension
   └─ Output: Monthly gross income + detailed methodology

7. CONSISTENCY TESTING (Optional)
   ├─ Run Steps 5-6 multiple times (3, 5, 10 runs)
   ├─ Async parallel processing
   ├─ Variance analysis
   └─ Output: HTML report with statistics and methodology distribution
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
│   ├── process_from_harvest_api.py          # Download PDFs from Harvest API
│   └── process_semantic_compression.py      # Raw JSON → Semantic JSON
│
├── agents/                                  # 🤖 AI Analysis Agents
│   ├── income_analysis_agent.py             # Income calculation with consistency testing
│   ├── form_1003_income_tracker.py          # Extract Form 1003 income fields
│   └── document_semantic_processor.py       # PDF → Semantic JSON processor
│
├── guidelines/                              # 📚 Underwriting Guidelines
│   ├── freddie_mac_guide_5300_5400.json              # Parsed guide (297 pages)
│   ├── freddie_mac_guide_5300_5400_compressed.json   # 67 income calculation rules
│   └── spring_eq_guidelines.json            # Spring EQ underwriting guidelines
│
├── loan_docs/                               # 📁 Loan Documents (gitignored)
│   └── {loan_id}/
│       ├── raw_json/                        # Azure Doc Intelligence output
│       └── semantic_json/                   # Structured semantic documents
│
├── reports/                                 # 📊 Analysis Reports (gitignored)
│   ├── income_analysis_{loan_id}_run{N}.json
│   ├── income_analysis_consistency_{loan_id}.json
│   └── income_analysis_consistency_report_{loan_id}.html
│
├── loan_files_inputs/                       # 📥 Loan metadata from Harvest (gitignored)
│   └── loan_{loan_id}_tree.json
│
├── batch_process_deal.py                    # Process multiple loans from a deal
├── batch_income_analysis.py                 # Batch income analysis with variance testing
├── parse_freddie_mac_guide.py               # Parse Freddie Mac PDF with Doc Intelligence
├── compress_freddie_mac_guide.py            # Compress guide to 67 rules with LLM
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
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

## Usage

### Complete Workflow: From Harvest API to Income Calculation

#### Step 1: Download Loan Documents from Harvest API

```bash
# Process entire deal (multiple loans)
python batch_process_deal.py --deal-id 2 --num-loans 5

# This will:
# 1. Fetch loan list from Harvest API (/api/deal/{deal_id})
# 2. Download PDF documents for each loan (/api/pdf/{file_id})
# 3. Extract PDFs with Azure Document Intelligence
# 4. Create semantic JSON with Azure OpenAI
# 5. Save to loan_docs/{loan_id}/raw_json/ and semantic_json/
```

#### Step 2: Parse Freddie Mac Guide (One-time setup)

```bash
# Parse 297-page Freddie Mac PDF with Azure Document Intelligence
python parse_freddie_mac_guide.py
# Output: guidelines/freddie_mac_guide_5300_5400.json (491K characters)

# Compress to 67 structured income calculation rules
python compress_freddie_mac_guide.py
# Output: guidelines/freddie_mac_guide_5300_5400_compressed.json (67 rules)
```

#### Step 3: Run Income Analysis with Intelligent Filtering

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

#### Step 4: Consistency Testing (Multiple Runs)

```bash
# Run 10 parallel analyses to test variance
python agents/income_analysis_agent.py 1000175957 10

# Outputs:
# - reports/income_analysis_1000175957_run1.json
# - reports/income_analysis_1000175957_run2.json
# - ... (run3 through run10)
# - reports/income_analysis_consistency_1000175957.json (summary)
# - reports/income_analysis_consistency_report_1000175957.html (visual report)
```

#### Step 5: Batch Processing with Variance Testing

```bash
# Process 5 loans from Deal 2, run 5 analyses on each
python batch_income_analysis.py --deal-id 2 --num-loans 5 --income-runs 5

# Outputs:
# - Comprehensive HTML report with variance analysis for all loans
# - Individual loan reports
# - Summary statistics
```

### Example: Intelligent Document Filtering Output

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
3. 🔄 Test on complex income scenarios:
   - Self-employed borrowers (Schedule C, business returns)
   - Multiple income sources (W-2 + rental + pension)
   - Commission-based income (2-year averaging)
   - Co-borrower income aggregation
4. 🔄 Improve calculation consistency:
   - More prescriptive prompts
   - Deterministic calculation for simple cases
   - Hybrid approach: LLM for classification, formula for calculation

### Research & Development
- [ ] Test Freddie Mac guidelines on 20+ diverse loans
- [ ] Compare LLM calculations vs human underwriter results
- [ ] Build confidence scoring based on document quality
- [ ] Implement calculation explainability (show rule citations)
- [ ] Handle edge cases: gaps in employment, job changes, temporary income

### Production Readiness
- [ ] Error handling and validation
- [ ] Logging and monitoring
- [ ] Performance optimization (caching, batch processing)
- [ ] API endpoint for income verification service
- [ ] Integration with Form 1003 data for validation

## Technical Stack

### Azure Services
- **Azure OpenAI**: GPT-4o-mini (400K context window)
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
  AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
  AZURE_OPENAI_API_VERSION=2024-12-01-preview
  DOC_INTELLIGENCE_ENDPOINT=https://...
  DOC_INTELLIGENCE_KEY=...
  ```

## Security Notes

🔒 **Protected Information (NOT in GitHub):**
- `.env` - Azure OpenAI & Document Intelligence credentials
- `loan_docs/` - All loan documents and processed data (PHI/PII)
- `reports/` - All generated analysis reports
- `loan_files_inputs/` - Harvest API data with loan IDs
- `*.pdf` - Source Freddie Mac guide documents
- `deal_*.json` - Deal data from Harvest API
- `archive/` - Archived documentation

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
- Azure OpenAI API access (GPT-4o-mini or similar)
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
