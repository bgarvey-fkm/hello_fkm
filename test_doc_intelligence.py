"""
Test Azure Document Intelligence API

This script tests the Azure Document Intelligence endpoint to see what it extracts
from a PDF document (layout, tables, key-value pairs, etc.)
"""

import os
import json
import time
from pathlib import Path
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, AnalyzeResult
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

# Azure Document Intelligence Configuration
DOC_INTELLIGENCE_ENDPOINT = "https://jwink-mcf50yni-swedencentral.cognitiveservices.azure.com/"
DOC_INTELLIGENCE_KEY = os.getenv("AZURE_OPENAI_KEY")  # Using same key as OpenAI

def analyze_pdf_with_doc_intelligence(pdf_path: str, output_path: str = None):
    """
    Analyze a PDF using Azure Document Intelligence.
    
    Available models:
    - prebuilt-read: Extract text, layout, languages
    - prebuilt-layout: Extract text, tables, selection marks, structure
    - prebuilt-document: Extract text, tables, key-value pairs
    - prebuilt-invoice: Extract invoice-specific fields
    - prebuilt-receipt: Extract receipt-specific fields
    """
    
    print("=" * 80)
    print("AZURE DOCUMENT INTELLIGENCE TEST")
    print("=" * 80)
    print(f"\nAnalyzing: {pdf_path}")
    print(f"Endpoint: {DOC_INTELLIGENCE_ENDPOINT}")
    print(f"Using API Key: {DOC_INTELLIGENCE_KEY[:20]}...")
    
    # Initialize the client
    client = DocumentIntelligenceClient(
        endpoint=DOC_INTELLIGENCE_ENDPOINT,
        credential=AzureKeyCredential(DOC_INTELLIGENCE_KEY)
    )
    
    # Read the PDF file
    with open(pdf_path, "rb") as f:
        pdf_data = f.read()
    
    print(f"\nPDF size: {len(pdf_data):,} bytes")
    
    # Test different models
    models_to_test = [
        ("prebuilt-layout", "Layout Analysis (text, tables, structure)"),
        ("prebuilt-document", "Document Analysis (text, tables, key-value pairs)"),
    ]
    
    results = {}
    
    for model_id, description in models_to_test:
        print(f"\n{'=' * 80}")
        print(f"Testing Model: {model_id}")
        print(f"Description: {description}")
        print(f"{'=' * 80}")
        
        try:
            # Start the analysis
            print(f"\nSending request to Azure Document Intelligence...")
            poller = client.begin_analyze_document(
                model_id=model_id,
                body=pdf_data,
                content_type="application/pdf"
            )
            
            print(f"Analysis started. Waiting for completion...")
            result: AnalyzeResult = poller.result()
            
            print(f"✅ Analysis complete!")
            
            # Extract key information
            analysis = {
                "model_id": model_id,
                "api_version": result.api_version,
                "content_length": len(result.content) if result.content else 0,
                "pages_count": len(result.pages) if result.pages else 0,
                "tables_count": len(result.tables) if result.tables else 0,
                "key_value_pairs_count": len(result.key_value_pairs) if result.key_value_pairs else 0,
                "paragraphs_count": len(result.paragraphs) if result.paragraphs else 0,
            }
            
            print(f"\n📊 SUMMARY:")
            print(f"   API Version: {analysis['api_version']}")
            print(f"   Pages: {analysis['pages_count']}")
            print(f"   Content Length: {analysis['content_length']:,} characters")
            print(f"   Tables Found: {analysis['tables_count']}")
            print(f"   Key-Value Pairs: {analysis['key_value_pairs_count']}")
            print(f"   Paragraphs: {analysis['paragraphs_count']}")
            
            # Show sample content (first 500 chars)
            if result.content:
                print(f"\n📄 SAMPLE CONTENT (first 500 chars):")
                print("-" * 80)
                print(result.content[:500])
                print("-" * 80)
            
            # Show tables if found
            if result.tables:
                print(f"\n📋 TABLES FOUND: {len(result.tables)}")
                for idx, table in enumerate(result.tables[:2]):  # Show first 2 tables
                    print(f"\n   Table {idx + 1}:")
                    print(f"   - Rows: {table.row_count}")
                    print(f"   - Columns: {table.column_count}")
                    print(f"   - Cells: {len(table.cells)}")
                    
                    # Show first few cells
                    print(f"   - Sample cells:")
                    for cell in table.cells[:5]:
                        print(f"     [{cell.row_index}, {cell.column_index}]: {cell.content}")
            
            # Show key-value pairs if found
            if result.key_value_pairs:
                print(f"\n🔑 KEY-VALUE PAIRS FOUND: {len(result.key_value_pairs)}")
                for idx, kv in enumerate(result.key_value_pairs[:10]):  # Show first 10
                    key = kv.key.content if kv.key else "N/A"
                    value = kv.value.content if kv.value else "N/A"
                    confidence = kv.confidence if kv.confidence else 0
                    print(f"   {idx + 1}. {key} = {value} (confidence: {confidence:.2f})")
            
            # Store full result
            results[model_id] = {
                "summary": analysis,
                "content": result.content,
                "tables": [
                    {
                        "row_count": t.row_count,
                        "column_count": t.column_count,
                        "cells": [
                            {
                                "row": c.row_index,
                                "col": c.column_index,
                                "content": c.content
                            }
                            for c in t.cells
                        ]
                    }
                    for t in (result.tables or [])
                ],
                "key_value_pairs": [
                    {
                        "key": kv.key.content if kv.key else None,
                        "value": kv.value.content if kv.value else None,
                        "confidence": kv.confidence
                    }
                    for kv in (result.key_value_pairs or [])
                ] if result.key_value_pairs else []
            }
            
        except Exception as e:
            print(f"❌ Error with model {model_id}: {e}")
            results[model_id] = {"error": str(e)}
    
    # Save results to JSON
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Full results saved to: {output_path}")
    
    print("\n" + "=" * 80)
    print("✅ DOCUMENT INTELLIGENCE TEST COMPLETE")
    print("=" * 80)
    
    return results


def main():
    # Test with the first PDF in loan 1000182227
    loan_id = "1000182227"
    source_pdf_dir = Path(f"loan_docs/{loan_id}/source_pdfs")
    
    if not source_pdf_dir.exists():
        print(f"Error: Directory not found: {source_pdf_dir}")
        return
    
    # Get first PDF file
    pdf_files = list(source_pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"Error: No PDF files found in {source_pdf_dir}")
        return
    
    # Use a simple document for testing (avoid large credit reports)
    test_pdf = None
    preferred_files = ["w2", "paystub", "loan_est", "note"]
    
    for pref in preferred_files:
        matching = [f for f in pdf_files if pref in f.name.lower()]
        if matching:
            test_pdf = matching[0]
            break
    
    if not test_pdf:
        test_pdf = pdf_files[0]  # Use first file if no preferred found
    
    # Create output path
    output_path = Path(f"loan_docs/{loan_id}/reports/doc_intelligence_test_{test_pdf.stem}.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Run the test
    results = analyze_pdf_with_doc_intelligence(str(test_pdf), str(output_path))
    
    print(f"\n🎯 RECOMMENDATION:")
    print(f"   - If tables are extracted well → use prebuilt-layout")
    print(f"   - If key-value pairs are useful → use prebuilt-document")
    print(f"   - For invoices/receipts → use specialized models")
    print(f"   - Current pipeline uses pdfplumber (text only)")


if __name__ == "__main__":
    main()
