"""
Move extracted text files to the new loan folder structure
"""

import shutil
from pathlib import Path


def main():
    base_path = Path(__file__).parent
    loan_id = "1000182277"
    
    # Create text folder
    text_folder = base_path / "loan_docs" / loan_id / "text"
    text_folder.mkdir(exist_ok=True)
    
    # Source folder
    inputs_dir = base_path / "loan_docs_inputs"
    
    if not inputs_dir.exists():
        print(f"❌ {inputs_dir} not found!")
        return
    
    print(f"Moving extracted text files to: loan_docs/{loan_id}/text/")
    print("="*70)
    
    # Move all *_text.txt files
    text_count = 0
    for text_file in inputs_dir.glob("*_text.txt"):
        dest = text_folder / text_file.name
        shutil.copy2(text_file, dest)
        text_count += 1
        print(f"  ✓ Copied: {text_file.name}")
    
    print("="*70)
    print(f"✅ Moved {text_count} text files")
    
    print("\nUPDATED FOLDER STRUCTURE:")
    print(f"loan_docs/")
    print(f"  └── {loan_id}/")
    print(f"      ├── source_pdfs/  (original PDF files)")
    print(f"      ├── images/       (PNG images from PDFs)")
    print(f"      ├── text/         (extracted text from PDFs) ← NEW")
    print(f"      ├── base64/       (base64 encoded images)")
    print(f"      └── json/         (extracted JSON data)")


if __name__ == "__main__":
    main()
