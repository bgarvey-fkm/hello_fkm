# Pipeline Scripts

This folder contains the core processing pipeline for loan document analysis.

---

## 📋 Pipeline Steps

### **Step 1: Document Conversion**
**Script:** `process_loan_docs.py`

Converts raw documents into processable formats:
- **PDFs → Text**: Extracts text using pdfplumber
- **PNGs → Base64**: Encodes images for Azure OpenAI Vision API

**Input:**
- `loan_docs/{loan_id}/source_pdfs/*.pdf`
- `loan_docs/{loan_id}/images/*.PNG`

**Output:**
- `loan_docs/{loan_id}/text/*_text.txt`
- `loan_docs/{loan_id}/base64/*_base64.txt`

**Usage:**
```bash
python pipeline/process_loan_docs.py
```

---

### **Step 2: Azure OpenAI Processing**
**Script:** `create_structured_json.py`

Processes documents with Azure OpenAI to create structured JSON:
- Analyzes text and images
- Extracts structured data (borrower info, income, debts, property, etc.)
- Uses async parallel processing for speed

**Input:**
- Files from Step 1: `text/` and `base64/` folders

**Output:**
- `loan_docs/{loan_id}/json/*.json` (structured data for each document)

**Usage:**
```bash
python pipeline/create_structured_json.py
```

---

### **Step 3: Form 1003 Analysis (2-Turn)**
**Script:** `form_1003_analysis_agent.py`

Identifies and extracts all borrower assertions from Form 1003:
- **Turn 1**: Identifies which JSON files contain 1003 data
- **Turn 2**: Extracts comprehensive borrower assertions

The Form 1003 is the **anchor** - it contains what borrowers declared:
- Employment and income
- Assets
- Liabilities (debts)
- Property information
- Loan details
- Personal information

**Input:**
- All JSON files from Step 2: `loan_docs/{loan_id}/json/`

**Output:**
- `reports/form_1003_analysis_{loan_id}_{timestamp}.json`

**Usage:**
```bash
python pipeline/form_1003_analysis_agent.py
```

---

### **Step 4: Document Verification**
**Script:** `document_verification_agent.py`

Verifies if the loan file has sufficient documentation to validate all 1003 assertions:
- Checks what borrowers declared on 1003
- Matches to validation documents (paystubs, credit, appraisal, etc.)
- Identifies missing documents
- Finds discrepancies between declared vs verified data
- Checks document freshness (30-day paystub rule, etc.)

**Input:**
- Form 1003 analysis from Step 3
- All JSON files from Step 2

**Output:**
- `reports/verification_analysis_{loan_id}_{timestamp}.json`
- `reports/verification_analysis_{loan_id}_{timestamp}.md`

**Usage:**
```bash
python pipeline/document_verification_agent.py
```

---

## 🔄 Complete Pipeline

To process a new loan from scratch:

```bash
# Step 1: Convert documents
python pipeline/process_loan_docs.py

# Step 2: Create structured JSON with Azure OpenAI
python pipeline/create_structured_json.py

# Step 3: Extract Form 1003 assertions
python pipeline/form_1003_analysis_agent.py

# Step 4: Verify documentation
python pipeline/document_verification_agent.py
```

---

## ⚙️ Configuration

Each script has a `loan_id` variable that needs to be updated before running:

```python
loan_id = "1000182227"  # Change this to process different loans
```

**Current Loans:**
- `1000182227` - Rebecca Shook & Katie Madson
- `1000182277` - John Collins

---

## 📊 Key Concepts

### **Form 1003 as Anchor**
The pipeline is built around the concept that **Form 1003 is the starting point**:
1. Borrowers sign the 1003 on Day 0 (application date)
2. They make declarations about income, debts, assets, property
3. ALL other documents exist to **validate** these declarations

### **Validation Categories**
Documents fall into two categories:

**PULLED DATA** (Lender orders):
- Credit report → validates liabilities
- Appraisal → validates property value
- VOE → validates employment/income
- Title report → validates ownership/liens

**SUBMITTED DOCUMENTS** (Borrower provides):
- Paystubs → validate income
- W-2s → validate income history
- Bank statements → validate assets
- Insurance → validate property insurance

### **Document Freshness Rules**
- Paystubs: Within 30 days of application
- Credit report: Within 90-120 days
- W-2s: Most recent 2 years
- Appraisal: Ordered after application, typically within 30 days

---

## 🎯 Output

After running the full pipeline, you'll have:

1. **Structured JSON** for every document
2. **1003 Analysis** showing all borrower assertions
3. **Verification Report** showing:
   - What's verified ✅
   - What's missing ❌
   - What has discrepancies ⚠️
   - Whether file is ready for underwriting

---

*Pipeline designed for mortgage loan underwriting document analysis*
