import os
from pathlib import Path
import json
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Azure Document Intelligence credentials
endpoint = os.getenv("AZURE_DOC_INTELLIGENCE_ENDPOINT")
api_key = os.getenv("AZURE_DOC_INTELLIGENCE_KEY")

# Initialize client
document_analysis_client = DocumentAnalysisClient(
    endpoint=endpoint, 
    credential=AzureKeyCredential(api_key)
)

# Process PDF
pdf_path = Path("image_files/img_test.pdf")

with open(pdf_path, "rb") as f:
    poller = document_analysis_client.begin_analyze_document(
        "prebuilt-layout",  # Use layout model - preserves structure, tables, etc.
        document=f
    )
    result = poller.result()

# Build structured document data for the LLM
structured_doc = {
    "pages": [],
    "tables": [],
    "key_value_pairs": []
}

# Extract pages with layout
for page in result.pages:
    page_data = {
        "page_number": page.page_number,
        "width": page.width,
        "height": page.height,
        "lines": []
    }
    for line in page.lines:
        page_data["lines"].append({
            "text": line.content,
            "bounding_box": [p for point in line.polygon for p in (point.x, point.y)]
        })
    structured_doc["pages"].append(page_data)

# Extract tables with structure preserved
for table in result.tables:
    table_data = {
        "row_count": table.row_count,
        "column_count": table.column_count,
        "cells": []
    }
    for cell in table.cells:
        table_data["cells"].append({
            "row_index": cell.row_index,
            "column_index": cell.column_index,
            "content": cell.content,
            "row_span": cell.row_span,
            "column_span": cell.column_span
        })
    structured_doc["tables"].append(table_data)

# Extract key-value pairs if present
if hasattr(result, 'key_value_pairs') and result.key_value_pairs:
    for kv in result.key_value_pairs:
        structured_doc["key_value_pairs"].append({
            "key": kv.key.content if kv.key else None,
            "value": kv.value.content if kv.value else None
        })

# Save structured JSON - this is what you send to the LLM
output_dir = pdf_path.parent
json_path = output_dir / f"{pdf_path.stem}_structured.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(structured_doc, f, indent=2)

print(f"Structured document saved to: {json_path}")
print(f"Processed {len(result.pages)} pages")
print(f"Found {len(result.tables)} tables")
print("\nThis structured JSON contains layout, tables, and text.")
print("Send this to your LLM instead of PNG + text - it's more accurate!")
