# Pipeline Upgrade: Azure Document Intelligence

## What Changed

### Old Pipeline (pdfplumber + base64)
**Step 1:** `process_loan_docs.py`
- Extracted plain text from PDFs using pdfplumber → `text/` folder
- Converted PNGs to base64 → `base64/` folder
- **Problems:**
  - Lost table structure (everything became plain text)
  - Needed PNG images for better quality
  - No understanding of document layout

**Step 2:** `create_structured_json.py`
- Sent text files + base64 images to Azure OpenAI
- Used vision API for PNGs, text API for PDFs
- Generated structured JSON for each document

### New Pipeline (Document Intelligence)
**Step 1:** `process_loan_docs.py`
- Uses **Azure Document Intelligence** (`prebuilt-layout` model)
- Directly processes PDFs (no PNGs needed!)
- Extracts:
  - ✅ Full text content
  - ✅ **Table structure** (rows, columns, cells with coordinates)
  - ✅ **Paragraphs** with roles
  - ✅ **Layout information**
- Outputs structured JSON to `json/` folder
- **Benefits:**
  - Preserves table structure
  - Better text extraction quality
  - No need for PNG conversion
  - One step instead of two

**Step 2:** `create_structured_json.py` (OPTIONAL)
- Can now enrich Document Intelligence JSON with additional LLM analysis
- Adds semantic understanding and field extraction
- Creates `*_analyzed.json` files

## API Endpoint

- **Endpoint:** `https://jwink-mcf50yni-swedencentral.cognitiveservices.azure.com/`
- **Key:** Same as Azure OpenAI (stored in `.env` as `AZURE_OPENAI_KEY`)
- **Model:** `prebuilt-layout` (for general documents with tables)

## Example Output

### Document Intelligence JSON Structure:
```json
{
  "document_name": "w2.pdf",
  "api_version": "2024-11-30",
  "model_id": "prebuilt-layout",
  "content": "Full text extracted...",
  "pages_count": 1,
  "tables": [
    {
      "row_count": 6,
      "column_count": 3,
      "cells": [
        {
          "row": 0,
          "col": 0,
          "content": "a Employee's ssn 625-05-4012",
          "kind": "content"
        },
        ...
      ]
    }
  ],
  "paragraphs": [
    {
      "content": "Copy C For EMPLOYEE'S RECORDS",
      "role": "title"
    },
    ...
  ]
}
```

## Performance Comparison

| Metric | Old Pipeline | New Pipeline |
|--------|-------------|--------------|
| **Steps** | 2 (extract + analyze) | 1-2 (extract, optional analyze) |
| **Files Generated** | 44 text + 30 base64 + 44 JSON = 118 | 14 JSON (or 28 with analysis) |
| **Table Extraction** | ❌ Lost (plain text) | ✅ Preserved (structured) |
| **Processing Time** | Fast (pdfplumber) + Slow (LLM) | Moderate (Doc Intel) + Optional (LLM) |
| **Quality** | Medium (lost structure) | High (preserves layout) |
| **PNG Images Needed** | ✅ Yes (30 files) | ❌ No |

## Folder Structure (Before/After)

### Before:
```
loan_docs/1000182227/
├── source_pdfs/     (14 PDFs) 
├── images/          (30 PNGs) - REQUIRED
├── text/            (14 .txt) - generated
├── base64/          (30 .txt) - generated
└── json/            (44 .json) - generated
```

### After:
```
loan_docs/1000182227/
├── source_pdfs/     (14 PDFs)
└── json/            (14 .json from Doc Intel, 14 _analyzed.json optional)
```

**Eliminated:**
- ❌ `images/` folder (no longer needed!)
- ❌ `text/` folder
- ❌ `base64/` folder

## Migration Steps

1. ✅ Updated `pipeline/process_loan_docs.py` to use Document Intelligence
2. ✅ Updated `pipeline/create_structured_json.py` to work with Doc Intel JSON
3. ✅ Installed `azure-ai-documentintelligence` package
4. ⏳ Testing on loan 1000182227
5. ⏳ Update documentation
6. ⏳ Update remaining agent scripts

## Cost Considerations

- **Azure Document Intelligence:** ~$0.01 per page (14 PDFs ≈ $0.14-$0.50 depending on pages)
- **Azure OpenAI:** Same as before (reduced if using Doc Intel output directly)
- **Trade-off:** Higher quality extraction at slightly higher cost

## Next Steps

1. Complete testing on loan 1000182227
2. Verify form_1003_analysis_agent_v2 works with new JSON format
3. Update income/debt verification agents if needed
4. Consider removing PNG image generation from preprocessing
5. Update README.md with new pipeline flow
