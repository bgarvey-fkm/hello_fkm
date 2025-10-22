# Income Expert Pipeline# Pipeline Scripts



**Branch: income-expert**This folder contains the core processing pipeline for loan document analysis.



This folder contains the document processing pipeline for the Income Expert system, which downloads loan documents from the Harvest API and processes them for income analysis.---



---## 📋 Pipeline Steps



## 📋 Pipeline Steps### **Step 1: Document Conversion**

**Script:** `process_loan_docs.py`

### **Step 1: Download & Extract from Harvest API**

**Script:** `process_from_harvest_api.py`Converts raw documents into processable formats:

- **PDFs → Text**: Extracts text using pdfplumber

Downloads loan documents from Harvest API and processes them with Azure Document Intelligence:- **PNGs → Base64**: Encodes images for Azure OpenAI Vision API

- Fetches PDFs from Harvest API based on loan metadata

- Runs Azure Document Intelligence OCR extraction**Input:**

- Combines metadata with extracted content- `loan_docs/{loan_id}/source_pdfs/*.pdf`

- Saves to `raw_json/` directory- `loan_docs/{loan_id}/images/*.PNG`



**Input:****Output:**

- `loan_files_inputs/{input_file}.json` - Harvest API metadata with file paths and loan IDs- `loan_docs/{loan_id}/text/*_text.txt`

- `loan_docs/{loan_id}/base64/*_base64.txt`

**Output:**

- `loan_docs/{loan_id}/raw_json/*.json` - Each file contains:**Usage:**

  - `metadata`: Harvest API file metadata (FileId, FileName, FileUploadDate, etc.)```bash

  - `document_intelligence`: Raw OCR output (content, tables, paragraphs, etc.)python pipeline/process_loan_docs.py

```

**Usage:**

```bash---

python pipeline/process_from_harvest_api.py loan_files_inputs/loans_to_process.json

```### **Step 2: Azure OpenAI Processing**

**Script:** `create_structured_json.py`

**Features:**

- ✅ Async parallel processing (fast!)Processes documents with Azure OpenAI to create structured JSON:

- ✅ Automatic retry on failures- Analyzes text and images

- ✅ Progress tracking- Extracts structured data (borrower info, income, debts, property, etc.)

- ✅ Preserves complete metadata from Harvest- Uses async parallel processing for speed



---**Input:**

- Files from Step 1: `text/` and `base64/` folders

### **Step 2: Semantic Compression**

**Script:** `process_semantic_compression.py`**Output:**

- `loan_docs/{loan_id}/json/*.json` (structured data for each document)

Processes raw JSON files and creates compressed semantic JSON using LLM:

- Identifies document type (paystub, W2, 1099-R, credit report, etc.)**Usage:**

- Extracts meaningful data with appropriate schema for each document type```bash

- Compresses boilerplate while preserving 100% of underwriting-relevant informationpython pipeline/create_structured_json.py

- Preserves original metadata verbatim```



**Input:**---

- `loan_docs/{loan_id}/raw_json/*.json` (output from Step 1)

### **Step 3: Form 1003 Analysis (2-Turn)**

**Output:****Script:** `form_1003_analysis_agent.py`

- `loan_docs/{loan_id}/semantic_json/*.json` - Each file contains:

  - `metadata`: Original Harvest metadata (preserved exactly)Identifies and extracts all borrower assertions from Form 1003:

  - `semantic_content`: LLM-extracted structured data with document-specific schema- **Turn 1**: Identifies which JSON files contain 1003 data

  - `_processing_metadata`: Compression stats, model info, timestamps- **Turn 2**: Extracts comprehensive borrower assertions



**Usage:**The Form 1003 is the **anchor** - it contains what borrowers declared:

```bash- Employment and income

python pipeline/process_semantic_compression.py {loan_id}- Assets

- Liabilities (debts)

# Example:- Property information

python pipeline/process_semantic_compression.py 1000179167- Loan details

```- Personal information



**Features:****Input:**

- ✅ Async parallel processing- All JSON files from Step 2: `loan_docs/{loan_id}/json/`

- ✅ Automatic schema selection per document type

- ✅ ~80-90% size reduction while preserving key data**Output:**

- ✅ Document type classification- `reports/form_1003_analysis_{loan_id}_{timestamp}.json`



---**Usage:**

```bash

## 🔄 Complete Pipeline Workflowpython pipeline/form_1003_analysis_agent.py

```

To process new loans for income analysis:

---

```bash

# Step 1: Create input JSON with loan IDs to process### **Step 4: Document Verification**

# (Place in loan_files_inputs/loans_to_process.json)**Script:** `document_verification_agent.py`



# Step 2: Download and extract from Harvest APIVerifies if the loan file has sufficient documentation to validate all 1003 assertions:

python pipeline/process_from_harvest_api.py loan_files_inputs/loans_to_process.json- Checks what borrowers declared on 1003

- Matches to validation documents (paystubs, credit, appraisal, etc.)

# Step 3: Create semantic JSON- Identifies missing documents

python pipeline/process_semantic_compression.py {loan_id}- Finds discrepancies between declared vs verified data

- Checks document freshness (30-day paystub rule, etc.)

# Step 4: Run income analysis (in agents/ folder)

python agents/income_analysis_agent.py {loan_id} {num_runs}**Input:**

```- Form 1003 analysis from Step 3

- All JSON files from Step 2

---

**Output:**

## 📁 Folder Structure- `reports/verification_analysis_{loan_id}_{timestamp}.json`

- `reports/verification_analysis_{loan_id}_{timestamp}.md`

After running the pipeline, each loan will have:

**Usage:**

``````bash

loan_docs/python pipeline/document_verification_agent.py

└── {loan_id}/```

    ├── raw_json/               # Step 1 output

    │   ├── FID131516.json      # Document with metadata + OCR---

    │   ├── FID131517.json

    │   └── ...## 🔄 Complete Pipeline

    └── semantic_json/          # Step 2 output

        ├── FID131516.json      # Compressed with semantic contentTo process a new loan from scratch:

        ├── FID131517.json

        └── ...```bash

```# Step 1: Convert documents

python pipeline/process_loan_docs.py

---

# Step 2: Create structured JSON with Azure OpenAI

## 🎯 Document Types Processedpython pipeline/create_structured_json.py



The semantic compression automatically identifies and schemas these document types:# Step 3: Extract Form 1003 assertions

python pipeline/form_1003_analysis_agent.py

**Income Documents:**

- `paystub` - Pay stubs with YTD income# Step 4: Verify documentation

- `w2` - W-2 forms with annual wagespython pipeline/document_verification_agent.py

- `form_1099-r` - Pension/retirement distributions```

- `income_worksheet` - Underwriter income calculations

---

**Credit Documents:**

- `credit_report` - Full credit reports with tradelines## ⚙️ Configuration

- `mortgage_statement` - Monthly mortgage statements

Each script has a `loan_id` variable that needs to be updated before running:

**Property Documents:**

- `appraisal` - Property appraisals```python

- `property_tax_bill` - Tax assessmentsloan_id = "1000182227"  # Change this to process different loans

```

**Application Documents:**

- `form_1003` - Uniform Residential Loan Application**Current Loans:**

- And many more...- `1000182227` - Rebecca Shook & Katie Madson

- `1000182277` - John Collins

---

---

## ⚙️ Configuration

## 📊 Key Concepts

Both scripts accept command-line arguments (no hardcoding needed!):

### **Form 1003 as Anchor**

```bashThe pipeline is built around the concept that **Form 1003 is the starting point**:

# Step 1: Input file path1. Borrowers sign the 1003 on Day 0 (application date)

python pipeline/process_from_harvest_api.py <input_json_path>2. They make declarations about income, debts, assets, property

3. ALL other documents exist to **validate** these declarations

# Step 2: Loan ID

python pipeline/process_semantic_compression.py <loan_id>### **Validation Categories**

```Documents fall into two categories:



---**PULLED DATA** (Lender orders):

- Credit report → validates liabilities

## 🔑 Environment Variables Required- Appraisal → validates property value

- VOE → validates employment/income

Both scripts use `.env` file:- Title report → validates ownership/liens



```env**SUBMITTED DOCUMENTS** (Borrower provides):

# Azure Document Intelligence (Step 1)- Paystubs → validate income

DOC_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/- W-2s → validate income history

DOC_INTELLIGENCE_KEY=your-key-here- Bank statements → validate assets

- Insurance → validate property insurance

# Azure OpenAI (Step 2)

AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/### **Document Freshness Rules**

AZURE_OPENAI_KEY=your-key-here- Paystubs: Within 30 days of application

AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini- Credit report: Within 90-120 days

AZURE_OPENAI_API_VERSION=2024-12-01-preview- W-2s: Most recent 2 years

```- Appraisal: Ordered after application, typically within 30 days



------



## ⚡ Performance## 🎯 Output



- **Async Processing**: All documents processed in parallelAfter running the full pipeline, you'll have:

- **Speed**: 50+ documents in under 2 minutes (combined pipeline)

- **Efficiency**: Single API call per document, per step1. **Structured JSON** for every document

2. **1003 Analysis** showing all borrower assertions

---3. **Verification Report** showing:

   - What's verified ✅

## 📊 Output Quality   - What's missing ❌

   - What has discrepancies ⚠️

**Raw JSON** (Step 1):   - Whether file is ready for underwriting

- Complete OCR extraction

- Full table structures---

- Document layout information

- ~500KB-2MB per document*Pipeline designed for mortgage loan underwriting document analysis*


**Semantic JSON** (Step 2):
- Structured, typed data
- Document-specific schemas
- Removes OCR noise and formatting artifacts
- ~50KB-200KB per document (80-90% reduction)

---

*Pipeline designed for income verification AI development*
