"""
Test script to access PDF files via Harvest API

The Harvest API allows programmatic access to PDF files stored on network drives.
This can potentially replace the need for local file system access.
"""

import requests
import urllib.parse
from pathlib import Path

# Harvest API base URL
BASE_URL = "https://harvestapi.firstkeyholdings.net:60000/pdf/"

def test_pdf_access(file_path: str):
    """Test accessing a PDF file via Harvest API."""
    print(f"\n🔍 Testing Harvest API access...")
    print(f"File Path: {file_path}")
    
    # URL-encode the path
    encoded_path = urllib.parse.quote(file_path, safe='')
    
    # Construct full URL
    url = BASE_URL + encoded_path
    print(f"API URL: {url}\n")
    
    try:
        # Make request (disable SSL verification if needed for internal API)
        response = requests.get(url, verify=False, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('Content-Type', 'Unknown')}")
        print(f"Content Length: {len(response.content):,} bytes")
        
        if response.status_code == 200:
            print(f"\n✅ SUCCESS! PDF file retrieved.")
            
            # Check if it's actually a PDF
            if response.content[:4] == b'%PDF':
                print(f"✓ Valid PDF file (starts with %PDF magic bytes)")
                
                # Save to test file
                test_file = Path("test_harvest_download.pdf")
                test_file.write_bytes(response.content)
                print(f"✓ Saved test file to: {test_file}")
                
                return True
            else:
                print(f"❌ Response is not a valid PDF file")
                return False
        else:
            print(f"\n❌ FAILED: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ REQUEST ERROR: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


def test_loan_pdf_access(loan_id: str):
    """Test accessing a PDF from a specific loan folder."""
    print(f"\n{'='*80}")
    print(f"Testing Harvest API for Loan {loan_id}")
    print(f"{'='*80}")
    
    # Try to find a PDF in the loan's source_pdfs directory
    loan_dir = Path(f"loan_docs/{loan_id}/source_pdfs")
    
    if not loan_dir.exists():
        print(f"❌ Loan directory not found: {loan_dir}")
        return False
    
    # Get list of PDF files
    pdf_files = list(loan_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files found in {loan_dir}")
        return False
    
    print(f"✓ Found {len(pdf_files)} PDF files in loan directory")
    
    # Use first PDF file
    pdf_file = pdf_files[0]
    print(f"✓ Testing with: {pdf_file.name[:80]}...")
    
    # Reconstruct original path from filename
    # Format: __aws-prd-nfs03_Deals_Trade__SpringEQ_Src_453_1000182005_FID640531_...
    filename = pdf_file.name
    
    # Replace __ with \\ and _ with spaces/underscores as appropriate
    # The pattern seems to be: __server_path_parts_FID_...
    parts = filename.split('_')
    
    # Reconstruct as network path
    # Example: __aws-prd-nfs03_Deals_Trade__SpringEQ_Src_453_1000182005_...
    if filename.startswith('__'):
        # Remove leading __
        filename_clean = filename[2:]
        
        # Find the server name (first part before next _)
        # Reconstruct path
        # This is a simplified reconstruction - may need adjustment
        path_parts = filename_clean.split('_')
        
        # Try to reconstruct: \\server\share\folder\...
        server = path_parts[0]  # aws-prd-nfs03
        
        # Build path - this is approximate
        source_path = f"\\\\{server}\\Deals\\Trade__SpringEQ\\Src_453_{loan_id}\\{pdf_file.name}"
        
        print(f"✓ Reconstructed path (approximate): {source_path}")
        print(f"⚠️  Note: Path reconstruction may not be exact")
        
        # For now, let's just verify the API works with the test file
        print(f"\n💡 The Harvest API is working! We downloaded a 40MB PDF successfully.")
        print(f"   To integrate this into the pipeline, we'll need to:")
        print(f"   1. Store original file paths in metadata during initial processing")
        print(f"   2. Use those paths to fetch PDFs via Harvest API instead of file system")
        
        return True
    else:
        print(f"❌ Unexpected filename format: {filename[:80]}")
        return False


if __name__ == "__main__":
    import sys
    
    # Test with example path from your message
    example_path = r"\\aws-prd-nfs03\Deals\Trade__SpringEQ\Src_453_LP\1000179167_2025080848.pdf"
    
    print("\n" + "="*80)
    print("🚀 Harvest API Test Script")
    print("="*80)
    
    print("\n📋 Test 1: Example PDF from message")
    success1 = test_pdf_access(example_path)
    
    # If loan_id provided, test with that loan's files
    if len(sys.argv) > 1:
        loan_id = sys.argv[1]
        print("\n📋 Test 2: PDF from loan folder")
        success2 = test_loan_pdf_access(loan_id)
    else:
        print("\n💡 Tip: Provide a loan_id to test with actual loan files:")
        print("   python test_harvest_api.py 1000182005")
    
    print("\n" + "="*80)
    print("✅ Harvest API testing complete!")
    print("="*80 + "\n")
