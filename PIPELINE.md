# Complete Processing Pipeline - New Folder Structure

## Overview
All files for each loan are now organized under `loan_docs/{loan_id}/` with clear subfolder purposes.

## Folder Structure
```
loan_docs/
  └── {loan_id}/              # e.g., 1000182277
      ├── source_pdfs/        # Original PDF documents (input)
      ├── images/             # PNG images converted from PDFs (input)
      ├── text/               # Extracted text from PDFs
      ├── base64/             # Base64 encoded images for API calls
      └── json/               # Structured JSON extracted by Azure OpenAI

reports/
  ├── {loan_id}_income_analysis.md
  ├── {loan_id}_debt_analysis.md
  └── {loan_id}_dti_reconciliation.html
```

## Complete Processing Pipeline

### Step 1: Prepare Source Documents
**Manual Step**
- Place original PDFs in `loan_docs/{loan_id}/source_pdfs/`
- Place PNG images in `loan_docs/{loan_id}/images/`

### Step 2: Extract Text and Create Base64
**Script:** `process_loan_docs.py`
```powershell
python process_loan_docs.py
```

**What it does:**
- Reads PDFs from `loan_docs/{loan_id}/source_pdfs/`
- Extracts text → saves to `loan_docs/{loan_id}/text/`
- Reads PNGs from `loan_docs/{loan_id}/images/`
- Converts to base64 → saves to `loan_docs/{loan_id}/base64/`

**Output:**
- `loan_docs/{loan_id}/text/*.txt` (11 files)
- `loan_docs/{loan_id}/base64/*_base64.txt` (19 files)

### Step 3: Create Structured JSON with Azure OpenAI
**Script:** `create_underwriting_summary.py`
```powershell
python create_underwriting_summary.py
```

**What it does:**
- Reads all files from `loan_docs/{loan_id}/text/` and `loan_docs/{loan_id}/base64/`
- Sends each to Azure OpenAI Vision API in parallel
- Extracts structured data (JSON)
- Saves to `loan_docs/{loan_id}/json/`

**Output:**
- `loan_docs/{loan_id}/json/*.json` (30 files)

### Step 4: Income Verification Agent
**Script:** `income_verification_2turn.py`
```powershell
python income_verification_2turn.py
```

**What it does:**
- Loads all JSONs from `loan_docs/{loan_id}/json/` (except Spring EQ)
- Analyzes income documentation
- Applies 2-year averaging for variable income
- Determines qualifying monthly income

**Output:**
- `reports/{loan_id}_income_analysis.md`

### Step 5: Debt Verification Agent
**Script:** `debt_verification_2turn.py`
```powershell
python debt_verification_2turn.py
```

**What it does:**
- Loads all JSONs from `loan_docs/{loan_id}/json/` (except Spring EQ)
- Identifies all debt obligations
- Estimates interest rates using financial formulas
- Identifies debts being paid off with loan proceeds
- Calculates Current DTI and Proposed DTI
- Computes Front-End and Back-End ratios

**Output:**
- `reports/{loan_id}_debt_analysis.md`

### Step 6: DTI Reconciliation Agent
**Script:** `dti_reconciliation_agent.py`
```powershell
python dti_reconciliation_agent.py
```

**What it does:**
- Loads `reports/{loan_id}_income_analysis.md`
- Loads `reports/{loan_id}_debt_analysis.md`
- Loads Spring EQ worksheet JSONs from `loan_docs/{loan_id}/json/`
- Loads all source JSONs for verification
- Compares independent analyses with Spring EQ worksheet
- Identifies variances and assesses risk level
- Generates comprehensive HTML report

**Output:**
- `reports/{loan_id}_dti_reconciliation.html`

## File Counts Per Loan

| Folder | Count | Purpose |
|--------|-------|---------|
| `source_pdfs/` | 11 | Original PDF documents |
| `images/` | 19 | PNG images (from PDFs or standalone) |
| `text/` | 11 | Extracted text from PDFs |
| `base64/` | 19 | Base64 encoded PNGs for API |
| `json/` | 30 | Structured data from Azure OpenAI |
| **Total per loan** | **~90** | **All processing artifacts** |

## Adding a New Loan

1. Create loan folder structure:
```powershell
mkdir loan_docs\{new_loan_id}\source_pdfs
mkdir loan_docs\{new_loan_id}\images
```

2. Place source files:
   - PDFs → `loan_docs/{new_loan_id}/source_pdfs/`
   - PNGs → `loan_docs/{new_loan_id}/images/`

3. Update scripts to use new loan_id:
   - Edit `process_loan_docs.py`: change `loan_id="1000182277"` to your loan ID
   - Edit `create_underwriting_summary.py`: change `loan_id="1000182277"` to your loan ID
   - Edit `income_verification_2turn.py`: change `loan_id="1000182277"` to your loan ID
   - Edit `debt_verification_2turn.py`: change `loan_id="1000182277"` to your loan ID
   - Edit `dti_reconciliation_agent.py`: change `loan_id="1000182277"` to your loan ID

4. Run the pipeline (Steps 2-6 above)

## Benefits of New Structure

✅ **Scalable**: Add unlimited loans without file conflicts
✅ **Organized**: All files for one loan in one place
✅ **Clear**: Folder names indicate file purpose
✅ **Traceable**: Easy to see processing stages
✅ **Maintainable**: Reports separate from source data
✅ **Git-friendly**: Loan data excluded, code tracked

## Old Folders (Can Be Deleted)

Once you've verified everything works:
- `image_files/` → migrated to `loan_docs/{loan_id}/source_pdfs/` and `images/`
- `loan_docs_inputs/` → migrated to `loan_docs/{loan_id}/text/` and `base64/`
- `loan_docs_json/` → migrated to `loan_docs/{loan_id}/json/`
- `loan_summary/` → migrated to `reports/`

## Notes

- All preprocessing scripts now support the loan ID parameter
- All agent scripts use the new folder structure
- Reports are named with loan ID prefix for easy identification
- `.gitignore` updated to exclude `loan_docs/` and `reports/` folders
