import os
import base64
from pathlib import Path
import pdfplumber

def process_image_files():
    """
    Process all PDF and PNG files in the image_files directory.
    - PNG files: Convert to base64
    - PDF files: Extract text
    Output saved to loan_docs_inputs directory
    """
    
    # Define directories
    input_dir = Path("image_files")
    output_dir = Path("loan_docs_inputs")
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    # Check if input directory exists
    if not input_dir.exists():
        print(f"Error: {input_dir} directory not found!")
        return
    
    # Get all files in the directory
    all_files = list(input_dir.glob("*"))
    
    # Filter for PDF and PNG files
    pdf_files = [f for f in all_files if f.suffix.lower() == ".pdf"]
    png_files = [f for f in all_files if f.suffix.lower() == ".png"]
    
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
            output_path = output_dir / output_filename
            
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
            output_path = output_dir / output_filename
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(text)
            
            print(f"✓ Extracted text from PDF: {pdf_file.name} -> {output_filename}")
        
        except Exception as e:
            print(f"✗ Error processing {pdf_file.name}: {e}")
    
    print()
    print("=" * 60)
    print(f"Processing complete! Output saved to: {output_dir}/")
    print(f"Total files processed: {len(pdf_files) + len(png_files)}")


if __name__ == "__main__":
    process_image_files()
