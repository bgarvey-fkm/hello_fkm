import os
import sys
import json
import asyncio
from pathlib import Path
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

async def process_single_pdf(client, pdf_file, json_output_dir):
    """
    Process a single PDF file with Document Intelligence.
    Returns: (success: bool, filename: str, error: str or None)
    """
    try:
        print(f"Processing: {pdf_file.name}...")
        
        # Read the PDF file
        with open(pdf_file, "rb") as f:
            pdf_data = f.read()
        
        # Analyze with Document Intelligence
        poller = await client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=pdf_data,
            content_type="application/pdf"
        )
        
        result = await poller.result()
        
        # Extract structured data
        doc_data = {
            "document_name": pdf_file.name,
            "api_version": result.api_version,
            "model_id": "prebuilt-layout",
            "content": result.content,
            "pages_count": len(result.pages) if result.pages else 0,
            "tables": [
                {
                    "row_count": table.row_count,
                    "column_count": table.column_count,
                    "cells": [
                        {
                            "row": cell.row_index,
                            "col": cell.column_index,
                            "content": cell.content,
                            "kind": cell.kind if hasattr(cell, 'kind') else None
                        }
                        for cell in table.cells
                    ]
                }
                for table in (result.tables or [])
            ],
            "paragraphs": [
                {
                    "content": para.content,
                    "role": para.role if hasattr(para, 'role') else None
                }
                for para in (result.paragraphs or [])[:50]  # Limit to first 50 paragraphs
            ] if result.paragraphs else []
        }
        
        # Save to JSON
        output_filename = f"{pdf_file.stem}.json"
        output_path = json_output_dir / output_filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(doc_data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ {pdf_file.name}: {len(doc_data['content'])} chars, "
              f"{len(doc_data['tables'])} tables, "
              f"{len(doc_data['paragraphs'])} paragraphs")
        
        return (True, pdf_file.name, None)
    
    except Exception as e:
        print(f"  ✗ {pdf_file.name}: Error - {e}")
        return (False, pdf_file.name, str(e))


async def process_image_files(loan_id="1000182227"):
    """
    Process all PDF files using Azure Document Intelligence (async).
    - PDF files: Extract structured content (text, tables, layout) → loan_docs/{loan_id}/json/
    
    Processes multiple PDFs in parallel for faster execution!
    """
    
    # Azure Document Intelligence Configuration
    DOC_INTELLIGENCE_ENDPOINT = "https://jwink-mcf50yni-swedencentral.cognitiveservices.azure.com/"
    DOC_INTELLIGENCE_KEY = os.getenv("AZURE_OPENAI_KEY")
    
    # Define directories
    loan_dir = Path(f"loan_docs/{loan_id}")
    source_pdfs_dir = loan_dir / "source_pdfs"
    json_output_dir = loan_dir / "json"
    
    # Create output directory
    json_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if input directory exists
    if not source_pdfs_dir.exists():
        print(f"Error: {source_pdfs_dir} directory not found!")
        return
    
    # Get all PDF files
    pdf_files = list(source_pdfs_dir.glob("*.pdf"))
    
    print(f"Found {len(pdf_files)} PDF files")
    print("=" * 80)
    print("Using Azure Document Intelligence (prebuilt-layout model)")
    print("Processing PDFs in parallel with async I/O...")
    print("=" * 80)
    print()
    
    # Initialize async client
    async with DocumentIntelligenceClient(
        endpoint=DOC_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(DOC_INTELLIGENCE_KEY)
    ) as client:
        
        # Process all PDFs concurrently
        tasks = [process_single_pdf(client, pdf_file, json_output_dir) for pdf_file in pdf_files]
        results = await asyncio.gather(*tasks)
    
    # Count successes and failures
    successful = [r for r in results if r[0]]
    failed = [r for r in results if not r[0]]
    
    print()
    print("=" * 80)
    print(f"Processing complete!")
    print(f"  ✓ Successfully processed: {len(successful)} files")
    if failed:
        print(f"  ✗ Errors: {len(failed)} files")
        for _, filename, error in failed:
            print(f"    - {filename}: {error}")
    print(f"  Output directory: {json_output_dir}/")
    print("=" * 80)


if __name__ == "__main__":
    # Accept loan_id from command line argument or use default
    if len(sys.argv) > 1:
        loan_id = sys.argv[1]
    else:
        loan_id = "1000182227"
    
    asyncio.run(process_image_files(loan_id))
