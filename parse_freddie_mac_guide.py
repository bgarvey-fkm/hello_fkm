"""
Parse Freddie Mac Guide PDF with Azure Document Intelligence
"""
import asyncio
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

# Load environment variables
load_dotenv()


async def parse_freddie_mac_guide():
    """Parse the Freddie Mac guide PDF and save to guidelines folder."""
    
    pdf_path = Path("FreddieMacGuide_5300_5400 (1).pdf")
    output_path = Path("guidelines/freddie_mac_guide_5300_5400.json")
    
    if not pdf_path.exists():
        print(f"Error: PDF file not found at {pdf_path}")
        return
    
    # Ensure guidelines directory exists
    output_path.parent.mkdir(exist_ok=True)
    
    # Initialize Azure Document Intelligence client
    endpoint = os.getenv("DOC_INTELLIGENCE_ENDPOINT")
    key = os.getenv("DOC_INTELLIGENCE_KEY")
    
    if not endpoint or not key:
        print("Error: Azure credentials not found in environment variables")
        print(f"  DOC_INTELLIGENCE_ENDPOINT: {endpoint}")
        print(f"  DOC_INTELLIGENCE_KEY: {'[SET]' if key else '[NOT SET]'}")
        return
    
    print(f"Parsing {pdf_path.name}...")
    print(f"File size: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    client = DocumentIntelligenceClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key)
    )
    
    async with client:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
            poller = await client.begin_analyze_document(
                "prebuilt-layout",
                pdf_bytes,
                content_type="application/pdf"
            )
            
            print("Analysis started... This may take a few minutes for a large document.")
            result = await poller.result()
            print(f"✓ Analysis complete!")
            
            # Extract structured data
            data = {
                "source": pdf_path.name,
                "title": "Freddie Mac Single-Family Seller/Servicer Guide - Sections 5300-5400",
                "sections": "Income and Employment Documentation",
                "page_count": len(result.pages) if result.pages else 0,
                "content": result.content,
                "tables": []
            }
            
            # Extract tables if present
            if result.tables:
                print(f"Found {len(result.tables)} tables")
                for i, table in enumerate(result.tables):
                    table_data = {
                        "table_number": i + 1,
                        "row_count": table.row_count,
                        "column_count": table.column_count,
                        "cells": []
                    }
                    for cell in table.cells:
                        table_data["cells"].append({
                            "row": cell.row_index,
                            "col": cell.column_index,
                            "content": cell.content
                        })
                    data["tables"].append(table_data)
            
            # Save to JSON
            with open(output_path, "w", encoding="utf-8") as out:
                json.dump(data, out, indent=2, ensure_ascii=False)
            
            print(f"\n✓ Saved to {output_path}")
            print(f"  Pages: {data['page_count']}")
            print(f"  Tables: {len(data['tables'])}")
            print(f"  Content length: {len(data['content'])} characters")


if __name__ == "__main__":
    asyncio.run(parse_freddie_mac_guide())
