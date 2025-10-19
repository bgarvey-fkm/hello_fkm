# Loan Document Analysis & Underwriting System

A sophisticated Python-based system for processing mortgage loan documents using Azure OpenAI with vision capabilities. Features automated document extraction, parallel processing, multi-agent income and debt verification, and comprehensive DTI reconciliation with quality control.

## Features

- **🚀 Parallel Document Processing**: Async Azure OpenAI calls for maximum speed (30+ docs in seconds)
- **👁️ Vision AI Analysis**: Extract data from both PDFs and images using GPT-4 vision
- **💰 Income Verification Agent**: Independent analysis with 2-year averaging for variable income
- **💳 Debt Verification Agent**: DTI calculations with debt consolidation and payoff detection
- **🔄 DTI Reconciliation Agent**: 3-way comparison (income + debt + Spring EQ worksheet)
- **📊 Loan ID Organization**: Scalable folder structure supporting multiple loans
- **🔍 Conservative vs Aggressive Assessment**: Intelligent risk evaluation
- **📄 Professional Reports**: Markdown and HTML reports with detailed citations

## Project Structure

```
hello_fkm/
├── process_loan_docs.py              # Step 1: Extract text from PDFs and base64 from PNGs
├── create_underwriting_summary.py    # Step 2: Async parallel analysis with Azure OpenAI
├── income_verification_2turn.py      # Step 3: Independent income analysis agent
├── debt_verification_2turn.py        # Step 4: Independent debt analysis agent
├── dti_reconciliation_agent.py       # Step 5: DTI reconciliation report
├── reorganize_by_loan_id.py          # Utility: Reorganize files by loan ID
├── move_text_files.py                # Utility: Move text files to new structure
├── requirements.txt                  # Python dependencies
├── .env.example                      # Example environment variables
├── PIPELINE.md                       # Complete processing pipeline documentation
├── loan_docs/                        # Loan documents organized by loan ID (gitignored)
│   └── {loan_id}/
│       ├── source_pdfs/              # Original PDF documents
│       ├── images/                   # PNG images from PDFs
│       ├── text/                     # Extracted text from PDFs
│       ├── base64/                   # Base64 encoded images for API
│       └── json/                     # Structured JSON from Azure OpenAI
└── reports/                          # Generated analysis reports (gitignored)
    ├── {loan_id}_income_analysis.md
    ├── {loan_id}_debt_analysis.md
    └── {loan_id}_dti_reconciliation.html
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

### 5. Create Loan Folder Structure

```bash
# For each loan, create the folder structure
mkdir -p loan_docs/{loan_id}/source_pdfs
mkdir -p loan_docs/{loan_id}/images
mkdir -p reports
```

## Usage

### Complete Pipeline (Recommended)

See [PIPELINE.md](PIPELINE.md) for detailed step-by-step documentation.

**Quick Start:**

```bash
# Step 1: Place documents in loan folder
# - PDFs → loan_docs/{loan_id}/source_pdfs/
# - PNGs → loan_docs/{loan_id}/images/

# Step 2: Extract text from PDFs and convert PNGs to base64
python process_loan_docs.py

# Step 3: Process all documents in parallel with Azure OpenAI
python create_underwriting_summary.py

# Step 4: Run income verification agent
python income_verification_2turn.py

# Step 5: Run debt verification agent
python debt_verification_2turn.py

# Step 6: Generate DTI reconciliation report
python dti_reconciliation_agent.py
```

### Output Reports

All reports are generated in the `reports/` folder with loan ID prefixes:

1. **`{loan_id}_income_analysis.md`** - Qualifying monthly income determination
   - 2-year averaging for variable income
   - Detailed calculations with citations
   - Income source breakdown

2. **`{loan_id}_debt_analysis.md`** - Debt obligations and DTI analysis
   - Front-End and Back-End DTI calculations
   - Debt consolidation and payoff identification
   - Interest rate estimation for unclear debts
   - Current DTI vs Proposed DTI comparison

3. **`{loan_id}_dti_reconciliation.html`** - Comprehensive 3-way comparison
   - Independent income analysis vs Spring EQ
   - Independent debt analysis vs Spring EQ
   - Variance analysis with conservative/aggressive assessment
   - Source document verification

## Document Types Supported

The system processes and analyzes:

- **Income Documents:** Paystubs, W-2 Forms, Tax Returns, 1099 Forms
- **Credit Documents:** Credit Reports, Mortgage Statements, Payoff Notices
- **Property Documents:** Appraisals, Property Tax Bills, Flood Zone Determinations
- **Application Documents:** Form 1003, Spring EQ Underwriting Worksheets

## Underwriting Concepts

### Conservative vs Aggressive Underwriting

**Conservative (Lower Risk - Positive):**
- Using **lower income** than documented → Reduces risk ✅
- Using **higher debts** than documented → Reduces risk ✅
- Qualifying at **higher payment** than final loan → Stress tested ✅

**Aggressive (Higher Risk - Concern):**
- Using **higher income** than documented → Overstating ability 🚩
- Using **lower debts** than shown → Understating obligations 🚩
- Qualifying at **lower payment** than final loan → Payment shock risk 🚩

### Income Qualification Rules

- **Base Salary:** Current pay rate from most recent paystub
- **Variable Income:** Requires 2-year history, uses 2-year average if stable/increasing
- **Declining Income:** Not included or reduced amount used
- **Self-Employment:** 2-year tax returns, add back depreciation

### Debt Consolidation Logic

The system understands refinance scenarios:
- Identifies debts being paid off with loan proceeds
- Excludes paid-off debts from Proposed DTI calculation
- Calculates both Current DTI (before) and Proposed DTI (after payoffs)
- Assesses DTI improvement from debt consolidation

## Key Technologies

- **Azure OpenAI**: GPT-4 with vision capabilities
- **pdfplumber**: PDF text extraction
- **asyncio**: Parallel document processing
- **Base64 encoding**: Image transmission to vision model
- **Python 3.8+**: Modern async/await patterns

## Performance

- **Parallel Processing**: All documents processed simultaneously using async/await
- **Speed**: 30+ documents processed in seconds (limited only by API rate limits)
- **Efficiency**: Single API call per document, no sequential bottlenecks

## Security Notes

🔒 **Protected Information (NOT in GitHub):**
- `.env` - Azure OpenAI credentials
- `loan_docs/` - All loan documents and processed data
- `reports/` - All generated analysis reports

✅ **Safe to Share (in GitHub):**
- Python scripts (`.py` files)
- `.env.example` - Template with no actual credentials
- `.gitignore` - Protection rules
- `README.md`, `PIPELINE.md` - Documentation
- `requirements.txt` - Python dependencies

**Never commit sensitive data, loan information, or API keys to version control!**

## Requirements

- Python 3.8+
- Azure OpenAI API access with vision-capable deployment (gpt-4o, gpt-4o-mini, etc.)
- pdfplumber for PDF processing
- Network drive or local filesystem access

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Specify your license]

## Acknowledgments

- Azure OpenAI for vision and chat capabilities
- pdfplumber for reliable PDF text extraction
