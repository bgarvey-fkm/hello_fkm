import os
import base64
from pathlib import Path
import pdfplumber

def process_image_files(loan_id="1000182277"):
    """
    Process all PDF and PNG files in the loan_docs/{loan_id}/source_pdfs and images directories.
    - PNG files: Convert to base64 → loan_docs/{loan_id}/base64/
    - PDF files: Extract text → loan_docs/{loan_id}/text/
    """
    
    # Define directories
    loan_dir = Path(f"loan_docs/{loan_id}")
    source_pdfs_dir = loan_dir / "source_pdfs"
    images_dir = loan_dir / "images"
    base64_output_dir = loan_dir / "base64"
    text_output_dir = loan_dir / "text"
    
    # Create output directories if they don't exist
    base64_output_dir.mkdir(parents=True, exist_ok=True)
    text_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if input directories exist
    if not source_pdfs_dir.exists() and not images_dir.exists():
        print(f"Error: Neither {source_pdfs_dir} nor {images_dir} directory found!")
        return
    
    # Get all files from both directories
    pdf_files = list(source_pdfs_dir.glob("*.pdf")) if source_pdfs_dir.exists() else []
    png_files = list(images_dir.glob("*.PNG")) if images_dir.exists() else []
    
    print(f"Found {len(pdf_files)} PDF files and {len(png_files)} PNG files")
    print("=" * 60)
    
    # Process PNG files - convert to base64
    for png_file in png_files:
        try:
            with open(png_file, "rb") as f:
                png_data = f.read()
                base64_data = base64.b64encode(png_data).decode("utf-8")
            
            # Save base64 to output directory
            output_filename = f"{png_file.stem}_base64.txt"
            output_path = base64_output_dir / output_filename
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(base64_data)
            
            print(f"✓ Converted PNG to base64: {png_file.name} -> {output_filename}")
        
        except Exception as e:
            print(f"✗ Error processing {png_file.name}: {e}")
    
    print()
    
    # Process PDF files - extract text
    for pdf_file in pdf_files:
        try:
            with pdfplumber.open(pdf_file) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # Save text to output directory
            output_filename = f"{pdf_file.stem}_text.txt"
            output_path = text_output_dir / output_filename
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            
            print(f"✓ Extracted text from PDF: {pdf_file.name} -> {output_filename}")
        
        except Exception as e:
            print(f"✗ Error processing {pdf_file.name}: {e}")
    
    print()
    print("=" * 60)
    print(f"Processing complete!")
    print(f"  Base64 files: {base64_output_dir}/")
    print(f"  Text files: {text_output_dir}/")
    print(f"Total files processed: {len(pdf_files) + len(png_files)}")


if __name__ == "__main__":
    process_image_files()
