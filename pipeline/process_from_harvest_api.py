"""
Process Loan Documents from Harvest API (ASYNC VERSION)

Fetches PDFs via Harvest API based on metadata JSON, processes with Document Intelligence,
and combines metadata with extracted content.

This version uses asyncio to process multiple documents in parallel for much faster execution.

Usage:
    python process_from_harvest_api.py <metadata_json_path> <loan_id>
    
Example:
    python process_from_harvest_api.py loan_files_inputs/test_harvest_input.json 1000179167
"""

import json
import sys
import os
from pathlib import Path
import urllib.parse
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
import aiohttp
import urllib3

# Disable SSL warnings for Harvest API
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# Harvest API configuration
HARVEST_API_BASE = "https://harvestapi.firstkeyholdings.net:60000/pdf/"

# Azure Document Intelligence configuration (from .env)
AZURE_DOC_INTELLIGENCE_ENDPOINT = os.getenv('DOC_INTELLIGENCE_ENDPOINT')
AZURE_DOC_INTELLIGENCE_KEY = os.getenv('DOC_INTELLIGENCE_KEY')


async def fetch_pdf_from_harvest(file_path: str, session: aiohttp.ClientSession) -> bytes:
    """Fetch PDF from Harvest API given UNC path (async)."""
    encoded_path = urllib.parse.quote(file_path, safe='')
    url = f"{HARVEST_API_BASE}{encoded_path}"
    
    try:
        async with session.get(url, ssl=False, timeout=aiohttp.ClientTimeout(total=60)) as response:
            if response.status == 200:
                pdf_bytes = await response.read()
                return pdf_bytes
            else:
                return None
    except Exception as e:
        return None


async def process_with_document_intelligence(pdf_bytes: bytes, file_name: str) -> dict:
    """Process PDF with Azure Document Intelligence (async)."""
    if not AZURE_DOC_INTELLIGENCE_ENDPOINT or not AZURE_DOC_INTELLIGENCE_KEY:
        return None
    
    try:
        async with DocumentIntelligenceClient(
            endpoint=AZURE_DOC_INTELLIGENCE_ENDPOINT,
            credential=AzureKeyCredential(AZURE_DOC_INTELLIGENCE_KEY)
        ) as client:
            
            # Analyze document with layout model
            poller = await client.begin_analyze_document(
                "prebuilt-layout",
                pdf_bytes,
                content_type="application/pdf"
            )
            
            result = await poller.result()
            
            # Convert to JSON-serializable dict
            return result.as_dict()
            
    except Exception as e:
        return None


def combine_metadata_with_content(metadata: dict, doc_intelligence_result: dict) -> dict:
    """Combine file metadata with Document Intelligence output."""
    return {
        "metadata": metadata,
        "document_intelligence": doc_intelligence_result,
        "processing_info": {
            "processed_at": datetime.now().isoformat(),
            "source": "harvest_api",
            "pipeline_version": "2.0_async"
        }
    }


async def process_single_document(metadata: dict, idx: int, total: int, output_dir: Path, session: aiohttp.ClientSession):
    """Process a single document (async)."""
    file_id = metadata.get('FileId')
    file_name = metadata.get('FileName', 'Unknown')
    file_full_name = metadata.get('FileFullName')
    is_expandable = metadata.get('IsExpandable', False)
    
    print(f"[{idx}/{total}] 📄 FileId {file_id}: {file_name}")
    
    # Skip the expandable loan package
    if is_expandable:
        print(f"  ⏭️  Skipping expandable loan package")
        return {'status': 'skipped', 'reason': 'expandable'}
    
    if not file_full_name:
        print(f"  ⏭️  Skipping - no file path")
        return {'status': 'skipped', 'reason': 'no_path'}
    
    # Fetch PDF from Harvest API
    pdf_bytes = await fetch_pdf_from_harvest(file_full_name, session)
    if not pdf_bytes:
        print(f"  ❌ Failed to fetch PDF")
        return {'status': 'error', 'reason': 'fetch_failed'}
    
    print(f"  ✅ Downloaded {len(pdf_bytes):,} bytes")
    
    # Process with Document Intelligence
    doc_intelligence_result = await process_with_document_intelligence(pdf_bytes, file_name)
    if not doc_intelligence_result:
        print(f"  ❌ Failed to process with Document Intelligence")
        return {'status': 'error', 'reason': 'processing_failed'}
    
    pages = len(doc_intelligence_result.get('pages', []))
    print(f"  ✅ Extracted {pages} pages")
    
    # Combine metadata with content
    combined_result = combine_metadata_with_content(metadata, doc_intelligence_result)
    
    # Save to JSON file
    output_file = output_dir / f"FID{file_id}_{file_name.replace('/', '_').replace(':', '_')[:100]}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(combined_result, f, indent=2, ensure_ascii=False)
    
    print(f"  💾 Saved: {output_file.name}")
    
    return {'status': 'success', 'file_id': file_id, 'pages': pages}


async def process_loan_from_metadata(metadata_json_path: str, loan_id: str):
    """Process all documents for a loan from metadata JSON (async)."""
    
    # Load metadata
    print(f"\n{'='*80}")
    print(f"� PROCESSING LOAN {loan_id} FROM HARVEST API (ASYNC)")
    print(f"{'='*80}\n")
    
    with open(metadata_json_path, 'r') as f:
        metadata_list = json.load(f)
    
    print(f"📋 Found {len(metadata_list)} documents in metadata")
    print(f"⚡ Mode: PARALLEL ASYNC PROCESSING\n")
    
    # Create output directory
    loan_dir = Path(f"loan_docs/{loan_id}")
    raw_json_dir = loan_dir / "raw_json"
    raw_json_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Output directory: {raw_json_dir}\n")
    print("=" * 80)
    print()
    
    # Create aiohttp session for HTTP requests
    async with aiohttp.ClientSession() as session:
        # Process all documents in parallel
        tasks = [
            process_single_document(metadata, idx, len(metadata_list), raw_json_dir, session)
            for idx, metadata in enumerate(metadata_list, 1)
        ]
        
        results = await asyncio.gather(*tasks)
    
    # Summary
    processed = sum(1 for r in results if r['status'] == 'success')
    skipped = sum(1 for r in results if r['status'] == 'skipped')
    errors = sum(1 for r in results if r['status'] == 'error')
    
    print()
    print("=" * 80)
    print(f"📊 PROCESSING COMPLETE")
    print("=" * 80)
    print(f"  ✅ Processed: {processed}")
    print(f"  ⏭️  Skipped: {skipped}")
    print(f"  ❌ Errors: {errors}")
    print(f"  📁 Output: {raw_json_dir}")
    print("=" * 80)
    print()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python process_from_harvest_api.py <metadata_json_path> <loan_id>")
        print("Example: python process_from_harvest_api.py loan_files_inputs/test_harvest_input.json 1000179167")
        sys.exit(1)
    
    metadata_json_path = sys.argv[1]
    loan_id = sys.argv[2]
    
    if not Path(metadata_json_path).exists():
        print(f"❌ Error: Metadata file not found: {metadata_json_path}")
        sys.exit(1)
    
    # Run async function
    asyncio.run(process_loan_from_metadata(metadata_json_path, loan_id))
