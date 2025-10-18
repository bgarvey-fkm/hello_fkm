# Document Analysis and Financial Reporting System

A Python-based system for extracting, analyzing, and generating financial reports from PDF documents using Azure OpenAI and document processing tools.

## Features

- **PDF Text Extraction**: Extract text from PDF documents using pdfplumber
- **Image Conversion**: Convert PDFs to PNG images and base64 encoding
- **AI-Powered Analysis**: Use Azure OpenAI to analyze documents and extract structured data
- **Financial Reporting**: Generate HTML reports with DTI (Debt-to-Income) calculations
- **Document Intelligence**: Support for Azure Document Intelligence for advanced layout and table extraction

## Project Structure

```
hello_fkm/
├── azure_test.py                 # Main script for document analysis with Azure OpenAI
├── pdf_to_png_and_text.py       # Extract text and convert images from PDFs
├── generate_loan_summary.py     # Generate HTML financial summary reports
├── azure_doc_intelligence.py    # Azure Document Intelligence integration (optional)
├── convert_pdf_to_png.py        # Standalone PDF to PNG converter
├── hello_fkm.py                 # Simple test script
├── requirements.txt             # Python dependencies
├── .env.example                 # Example environment variables
├── image_files/                 # Directory for input PDFs and generated files (gitignored)
└── loan_summary/                # Directory for generated reports (gitignored)
```

## Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
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

Copy `.env.example` to `.env` and fill in your Azure credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:
```
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

### 5. Create Required Directories

```bash
mkdir image_files
mkdir loan_summary
```

## Usage

### 1. Process PDF Documents

Place your PDF files in the `image_files/` directory, then run:

```bash
python pdf_to_png_and_text.py
```

This will:
- Extract text from PDFs
- Convert images to PNG format (if available)
- Generate base64-encoded versions of images

### 2. Analyze Documents with AI

Run the analysis script to extract structured data:

```bash
python azure_test.py
```

This will:
- Load the PDF text and image data
- Send to Azure OpenAI for analysis
- Generate a structured JSON response with document data

### 3. Generate Financial Reports

Create HTML reports from the analyzed data:

```bash
python generate_loan_summary.py
```

This will:
- Load both JSON analysis files (payroll and mortgage)
- Calculate DTI (Debt-to-Income) ratios
- Generate a comprehensive HTML report in `loan_summary/`

## Workflow Example

```bash
# Step 1: Place PDFs in image_files/ directory
# - img_test.pdf (paystub)
# - img_2_test.pdf (mortgage statement)

# Step 2: Extract text and prepare images
python pdf_to_png_and_text.py

# Step 3: Analyze documents
python azure_test.py

# Step 4: Generate financial report
python generate_loan_summary.py

# Step 5: Open loan_summary/financial_summary_report.html in browser
```

## Azure Document Intelligence (Optional)

For advanced document processing with better table and layout extraction:

1. Create an Azure Document Intelligence resource
2. Add credentials to `.env`:
   ```
   AZURE_DOC_INTELLIGENCE_ENDPOINT=https://your-doc-intel.cognitiveservices.azure.com/
   AZURE_DOC_INTELLIGENCE_KEY=your-key
   ```
3. Run: `python azure_doc_intelligence.py`

## Requirements

- Python 3.8+
- Azure OpenAI API access
- Azure Document Intelligence (optional)

## Security Notes

- Never commit `.env` file to version control
- `image_files/` and `loan_summary/` are gitignored to protect sensitive data
- Keep your API keys secure

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]
