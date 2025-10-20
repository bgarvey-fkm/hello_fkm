import os
import sys
import json
import asyncio
from pathlib import Path
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
subscription_key = os.getenv("AZURE_OPENAI_KEY")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")


async def process_loan_document(file_path, client):
    """
    Process a single Document Intelligence JSON output and enrich it with LLM analysis.
    The file already contains structured content and tables from Document Intelligence.
    We just add intelligent extraction of key fields.
    """
    
    # Read the Document Intelligence JSON
    with open(file_path, "r", encoding="utf-8") as f:
        doc_intel_data = json.load(f)
    
    print(f"Processing: {file_path.name}...")
    
    # Extract the content and tables
    content = doc_intel_data.get("content", "")
    tables = doc_intel_data.get("tables", [])
    
    # Create a summary of tables for the LLM
    tables_summary = []
    for idx, table in enumerate(tables[:5]):  # Limit to first 5 tables
        cells_text = "\n".join([
            f"  [{cell['row']},{cell['col']}]: {cell['content']}"
            for cell in table['cells'][:20]  # First 20 cells per table
        ])
        tables_summary.append(f"Table {idx + 1} ({table['row_count']}x{table['column_count']}):\n{cells_text}")
    
    tables_text = "\n\n".join(tables_summary) if tables_summary else "No tables found"
    
    # Use LLM to extract structured data from the Document Intelligence output
    response = await client.chat.completions.create(     
        messages=[         
            {
                "role": "system",
                "content": """You are a Mortgage Loan Origination Document Processor. You receive structured content extracted from PDFs by Azure Document Intelligence (text + tables).

Your job:
1. Identify the document type (paystub, W-2, Form 1003, credit report, appraisal, loan estimate, etc.)
2. Extract ALL relevant data fields specific to that document type
3. Use the table data when available - it's already structured with row/column positions
4. Return a well-structured JSON object with:
   - "document_type" field
   - "document_date" field if present
   - All relevant financial figures, dates, names, addresses
   - For forms with tables, preserve the table structure

Return ONLY valid JSON, no explanations or markdown."""
            },
            {
                "role": "user",
                "content": f"""Analyze this document and extract all relevant information into structured JSON.

DOCUMENT TEXT:
{content[:30000]}

TABLES EXTRACTED:
{tables_text}

Return ONLY the JSON object with all extracted data."""
            }    
        ],
        max_completion_tokens=16384, 
        model=deployment
    )
    
    json_response = response.choices[0].message.content
    
    # Try to parse to validate it's proper JSON
    try:
        parsed_json = json.loads(json_response)
        return parsed_json
    except json.JSONDecodeError as e:
        print(f"Warning: Response for {file_path.name} may not be valid JSON: {e}")
        return {"error": "Invalid JSON response", "raw_response": json_response}


async def create_document_json_files(loan_id="1000182227"):
    """
    Process each document in loan_docs/{loan_id}/base64 and loan_docs/{loan_id}/text 
    and create individual JSON files in parallel
    """
    
    json_dir = Path(f"loan_docs/{loan_id}/json")
    
    if not json_dir.exists():
        print(f"Error: {json_dir} directory not found!")
        print(f"Run 'process_loan_docs.py {loan_id}' first to generate Document Intelligence outputs")
        return
    
    # Get all JSON files from Document Intelligence (not already analyzed)
    all_files = [f for f in json_dir.glob("*.json") if not f.stem.endswith("_analyzed")]
    
    if not all_files:
        print("No Document Intelligence JSON files found to process")
        return
    
    print(f"Found {len(all_files)} Document Intelligence outputs to analyze")
    print("="*80)
    
    # Initialize Azure OpenAI async client
    client = AsyncAzureOpenAI(
        api_version=api_version, 
        azure_endpoint=endpoint, 
        api_key=subscription_key
    )
    
    # Create tasks for all documents to process in parallel
    async def process_and_save(file):
        try:
            # Process the document
            json_data = await process_loan_document(file, client)
            
            # Create output filename with _analyzed suffix
            output_filename = file.stem + "_analyzed.json"
            output_path = json_dir / output_filename
            
            # Save JSON file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2)
            
            print(f"✓ Saved: {output_filename}")
            return True
            
        except Exception as e:
            print(f"✗ Error processing {file.name}: {e}")
            return False
    
    # Run all processing tasks in parallel
    results = await asyncio.gather(*[process_and_save(file) for file in all_files])
    
    print("="*80)
    print(f"Processing complete! Analyzed JSON files saved to: {json_dir}/")
    print(f"Total files processed: {len(all_files)}")
    print(f"Successful: {sum(results)}, Failed: {len(results) - sum(results)}")


if __name__ == "__main__":
    # Accept loan_id from command line argument or use default
    if len(sys.argv) > 1:
        loan_id = sys.argv[1]
    else:
        loan_id = "1000182227"
    
    asyncio.run(create_document_json_files(loan_id))
