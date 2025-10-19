"""
Reorganize loan documents by Loan ID
This script will:
1. Extract loan ID from Form 1003 JSON
2. Create new folder structure: loan_docs/{loan_id}/{source_pdfs,images,base64,json}
3. Move all existing files to the new structure
4. Create a reports folder for agent outputs
"""

import os
import json
import shutil
from pathlib import Path


def extract_loan_id(json_file_path):
    """Extract loan ID from form_1003.json or spring_uw.json"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Try different possible locations for loan ID
            loan_id = (
                data.get('loan', {}).get('loan_id') or
                data.get('loan', {}).get('lender_loan_number') or
                data.get('loan', {}).get('loan_number')
            )
            return loan_id
    except Exception as e:
        print(f"Error reading {json_file_path}: {e}")
        return None


def create_loan_folder_structure(base_path, loan_id):
    """Create folder structure for a loan"""
    loan_path = base_path / "loan_docs" / loan_id
    
    folders = {
        'source_pdfs': loan_path / "source_pdfs",
        'images': loan_path / "images",
        'base64': loan_path / "base64",
        'json': loan_path / "json"
    }
    
    # Create all folders
    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)
    
    # Create reports folder at root level
    reports_path = base_path / "reports"
    reports_path.mkdir(exist_ok=True)
    
    return folders, reports_path


def move_files(base_path, loan_id):
    """Move existing files to new structure"""
    
    # Create new folder structure
    folders, reports_path = create_loan_folder_structure(base_path, loan_id)
    
    print(f"\nOrganizing files for Loan ID: {loan_id}")
    print(f"Creating structure in: {base_path / 'loan_docs' / loan_id}")
    
    # Move source PDFs
    image_files = base_path / "image_files"
    if image_files.exists():
        pdf_count = 0
        png_count = 0
        for file in image_files.glob("*.pdf"):
            dest = folders['source_pdfs'] / file.name
            shutil.copy2(file, dest)
            pdf_count += 1
            print(f"  Copied: {file.name} -> source_pdfs/")
        
        # Move PNG images
        for file in image_files.glob("*.PNG"):
            dest = folders['images'] / file.name
            shutil.copy2(file, dest)
            png_count += 1
            print(f"  Copied: {file.name} -> images/")
        
        print(f"  Total: {pdf_count} PDFs, {png_count} images")
    
    # Move base64 text files
    inputs_dir = base_path / "loan_docs_inputs"
    if inputs_dir.exists():
        base64_count = 0
        for file in inputs_dir.glob("*_base64.txt"):
            dest = folders['base64'] / file.name
            shutil.copy2(file, dest)
            base64_count += 1
            print(f"  Copied: {file.name} -> base64/")
        print(f"  Total: {base64_count} base64 files")
    
    # Move JSON files
    json_dir = base_path / "loan_docs_json"
    if json_dir.exists():
        json_count = 0
        for file in json_dir.glob("*.json"):
            dest = folders['json'] / file.name
            shutil.copy2(file, dest)
            json_count += 1
            print(f"  Copied: {file.name} -> json/")
        print(f"  Total: {json_count} JSON files")
    
    # Move any existing markdown reports
    report_count = 0
    for pattern in ["*.md", "*.html"]:
        for file in base_path.glob(pattern):
            if file.name != "README.md":  # Don't move README
                dest = reports_path / f"{loan_id}_{file.name}"
                if file.exists():
                    shutil.copy2(file, dest)
                    report_count += 1
                    print(f"  Copied: {file.name} -> reports/{loan_id}_{file.name}")
    
    if report_count > 0:
        print(f"  Total: {report_count} report files")
    
    print(f"\n✅ Successfully organized {loan_id} with new folder structure!")
    return folders, reports_path


def main():
    base_path = Path(__file__).parent
    
    # Find loan ID from existing JSON files
    json_dir = base_path / "loan_docs_json"
    loan_id = None
    
    # Try to extract from form_1003.json first
    form_1003_path = json_dir / "form_1003.json"
    if form_1003_path.exists():
        loan_id = extract_loan_id(form_1003_path)
    
    # If not found, try spring_uw.json
    if not loan_id:
        spring_uw_path = json_dir / "spring_uw.json"
        if spring_uw_path.exists():
            loan_id = extract_loan_id(spring_uw_path)
    
    if not loan_id:
        print("❌ Could not find loan ID in JSON files!")
        print("   Make sure form_1003.json or spring_uw.json exists in loan_docs_json/")
        return
    
    # Move files to new structure
    folders, reports_path = move_files(base_path, loan_id)
    
    print("\n" + "="*70)
    print("NEW FOLDER STRUCTURE:")
    print("="*70)
    print(f"loan_docs/")
    print(f"  └── {loan_id}/")
    print(f"      ├── source_pdfs/  (original PDF files)")
    print(f"      ├── images/       (PNG images from PDFs)")
    print(f"      ├── base64/       (base64 encoded images)")
    print(f"      └── json/         (extracted JSON data)")
    print(f"reports/")
    print(f"  └── {loan_id}_*.md, {loan_id}_*.html")
    print("="*70)
    
    print("\n⚠️  NEXT STEPS:")
    print("1. Review the new folder structure")
    print("2. Run update_scripts_for_new_structure.py to update all Python scripts")
    print("3. Test the updated scripts")
    print("4. Delete old folders if everything works (image_files, loan_docs_inputs, loan_docs_json)")


if __name__ == "__main__":
    main()
