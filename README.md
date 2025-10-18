# Loan Document Analysis & Underwriting System

A sophisticated Python-based system for processing mortgage loan documents using Azure OpenAI with vision capabilities. Features automated document extraction, parallel processing, income verification, and comprehensive underwriting analysis with quality control.

## Features

- **🚀 Parallel Document Processing**: Async Azure OpenAI calls for maximum speed
- **👁️ Vision AI Analysis**: Extract data from both PDFs and images using GPT-4 vision
- **💰 Income Verification**: 2-turn quality control process with independent analysis
- **📊 Underwriting Analysis**: Comprehensive loan underwriting with DTI calculations
- **🔍 Discrepancy Detection**: Compare underwriting worksheets against source documents
- **📝 Conservative vs Aggressive Assessment**: Intelligent risk evaluation
- **📄 HTML Reports**: Professional, color-coded reports with detailed citations

## Project Structure

```
hello_fkm/
├── process_loan_docs.py              # Step 1: Batch process PDFs (text extraction) and PNGs (base64)
├── create_underwriting_summary.py    # Step 2: Async parallel document analysis with Azure OpenAI
├── create_underwriting_report.py     # Step 3: Comprehensive underwriting report with DTI
├── income_verification_agent.py      # Single-pass income analysis with top-line determination
├── income_verification_2turn.py      # 2-turn: Independent analysis + Spring EQ reconciliation
├── azure_test.py                     # Original document analysis script
├── pdf_to_png_and_text.py           # Original PDF processing script
├── requirements.txt                  # Python dependencies
├── .env.example                      # Example environment variables
├── image_files/                      # Input PDFs and PNGs (gitignored)
├── loan_docs_inputs/                 # Extracted text and base64 images (gitignored)
├── loan_docs_json/                   # AI-analyzed document JSONs (gitignored)
└── loan_summary/                     # Generated HTML reports (gitignored)
```

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/bgarvey-fkm/hello_fkm.git
cd hello_fkm
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

### 5. Create Required Directories

```bash
mkdir image_files
mkdir loan_docs_inputs
mkdir loan_docs_json
mkdir loan_summary
```

## Usage

### Complete Pipeline (Recommended)

Process all loan documents through the full pipeline:

```bash
# Step 1: Place PDFs and PNGs in image_files/ directory
# Examples: paystub.pdf, w2.pdf, credit.pdf, form_1003.pdf, appraisal_img.PNG, etc.

# Step 2: Extract text from PDFs and convert PNGs to base64
python process_loan_docs.py

# Step 3: Process all documents in parallel with Azure OpenAI (creates individual JSONs)
python create_underwriting_summary.py

# Step 4: Generate comprehensive underwriting report
python create_underwriting_report.py

# Step 5: Open loan_summary/underwriting_report.html in your browser
```

### Income Verification (Single-Pass)

Generate a detailed income verification report:

```bash
python income_verification_agent.py
# Opens: loan_summary/income_verification_report.html
```

**Features:**
- Top-line determination: "Qualifying Monthly Income: $X,XXX"
- Detailed calculation breakdown with formulas
- 2-year averaging for variable income (bonus/commission/overtime)
- Cross-reference analysis (1003 vs documentation)
- Income trend analysis
- Detailed citations with document names and dates

### Income Verification (2-Turn Quality Control)

Run independent analysis and compare with underwriting worksheet:

```bash
python income_verification_2turn.py
```

**TURN 1:** Independent Analysis (excludes Spring EQ worksheet)
- Analyzes source documents only (paystubs, W-2s, 1003, etc.)
- Makes independent income determination
- Saves to: `loan_summary/turn1_independent_income_analysis.md`

**TURN 2:** Reconciliation with Spring EQ
- Compares Turn 1 analysis with Spring EQ underwriting worksheet
- Identifies all discrepancies
- Assesses conservative vs aggressive assumptions
- Saves to: `loan_summary/turn2_income_reconciliation.html`

**Risk Assessment Logic:**
- 🟢 **Conservative (Good):** Spring EQ uses lower income = reduces risk
- 🔴 **Aggressive (Concern):** Spring EQ uses higher income = overstating ability
- 🔵 **Neutral:** Acceptable variance or different methodology

## Document Types Supported

The system processes and analyzes:

- **Income Documents:**
  - Paystubs (PDF or PNG)
  - W-2 Forms (multiple years)
  - Tax Returns (1040, Schedule C, Schedule E)
  - 1099 Forms

- **Credit Documents:**
  - Credit Reports
  - Mortgage Statements
  - Payoff Notices

- **Property Documents:**
  - Appraisals
  - Property Tax Bills
  - Flood Zone Determinations

- **Application Documents:**
  - Form 1003 (Uniform Residential Loan Application)
  - Spring EQ Underwriting Worksheets

## Underwriting Concepts

The system understands sophisticated underwriting principles:

### Conservative vs Aggressive Underwriting

**Conservative (Lower Risk - Positive):**
- Using **lower income** than documented → Reduces risk ✅
- Using **higher debts** than documented → Reduces risk ✅
- Qualifying at **higher payment** than final loan → Stress tested ✅
- Using **lower property value** than appraisal → Reduces risk ✅

**Aggressive (Higher Risk - Concern):**
- Using **higher income** than documented → Overstating ability 🚩
- Using **lower debts** than shown → Understating obligations 🚩
- Qualifying at **lower payment** than final loan → Payment shock risk 🚩
- Using **higher property value** than appraisal → Overstating collateral 🚩

### Income Qualification Rules

- **Base Salary:** Current pay rate from most recent paystub
- **Variable Income:** Requires 2-year history, uses 2-year average if stable/increasing
- **Declining Income:** Not included or reduced amount used
- **Self-Employment:** 2-year tax returns, add back depreciation
- **Rental Income:** Schedule E net income after expenses
- **Investment Income:** 2-year average from tax returns

## Output Reports

### 1. Underwriting Report (`underwriting_report.html`)
- Executive Summary
- Discrepancy Analysis (if Spring EQ worksheet present)
- Borrower Information
- Income Analysis with calculations
- Debt Analysis
- DTI Calculations (Front-End and Back-End)
- Credit Summary
- Asset Summary
- Property Information
- Risk Assessment
- Underwriting Recommendation

### 2. Income Verification Report (`income_verification_report.html`)
- **Qualifying Monthly Income** (top-line determination)
- Detailed Calculation Breakdown
- Income Components Excluded (with rationale)
- Income Source Table with citations
- Cross-Reference Analysis
- Income Trend Analysis
- Recommendations

### 3. 2-Turn Reconciliation Report (`turn2_income_reconciliation.html`)
- Executive Summary (Turn 1 vs Spring EQ comparison)
- Detailed Comparison Table
- Discrepancy Analysis (conservative/neutral/aggressive)
- Methodology Comparison
- Document Citations
- Overall Assessment
- Recommendations

## Key Technologies

- **Azure OpenAI**: GPT-4 with vision capabilities
- **pdfplumber**: PDF text extraction
- **asyncio**: Parallel document processing
- **Base64 encoding**: Image transmission to vision model
- **Python 3.8+**: Modern async/await patterns

## Performance

- **Parallel Processing**: All documents processed simultaneously using async/await
- **Speed**: 17+ documents processed in seconds (limited only by API rate limits)
- **Efficiency**: Single API call per document, no sequential bottlenecks

## Security Notes

🔒 **Protected Information (NOT in GitHub):**
- `.env` - Azure OpenAI credentials
- `image_files/` - All PDFs and PNGs (loan documents)
- `loan_docs_inputs/` - Base64 encoded images and extracted text
- `loan_docs_json/` - All analyzed document JSONs
- `loan_summary/` - All HTML reports and analysis

✅ **Safe to Share (in GitHub):**
- Python scripts (`.py` files)
- `.env.example` - Template with no actual credentials
- `.gitignore` - Protection rules
- `README.md` - Documentation
- `requirements.txt` - Python dependencies

**Never commit sensitive data or API keys to version control!**

## Requirements

- Python 3.8+
- Azure OpenAI API access with vision-capable deployment (gpt-4o, gpt-4o-mini, etc.)
- Network drive or local filesystem access

## Known Limitations

- **DLL Restrictions**: Some PDF libraries (PyMuPDF, pdf2image, pypdfium2) cannot load DLLs on network drives
- **Workaround**: Use pdfplumber (pure Python) for text extraction and manual PNG creation for images
- **Rate Limits**: Azure OpenAI rate limits may affect large batch processing

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Specify your license]

## Author

Brendan Garvey - First Key Mortgage

## Acknowledgments

- Azure OpenAI for vision and chat capabilities
- pdfplumber for reliable PDF text extraction
