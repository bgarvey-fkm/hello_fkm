from pathlib import Path
import pdfplumber
import base64


output_dir = Path("image_files")

# Process img_2_test.pdf - Extract text
pdf_path = output_dir / "img_2_test.pdf"
if pdf_path.exists():
    with pdfplumber.open(str(pdf_path)) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    
    text_path = output_dir / "img_2_test_text.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Saved text: {text_path}")

# Convert img_2_test_png.PNG to base64
img_path = output_dir / "img_2_test_png.PNG"
if img_path.exists():
    with open(img_path, "rb") as img_file:
        b64_img = base64.b64encode(img_file.read()).decode("utf-8")
    b64_img_path = output_dir / "img_2_test_png_base64.txt"
    with open(b64_img_path, "w", encoding="utf-8") as f:
        f.write(b64_img)
    print(f"Saved base64: {b64_img_path}")
