from pathlib import Path
import pypdfium2 as pdfium

# Open the PDF
pdf_path = Path("image_files/img_test.pdf")
output_dir = pdf_path.parent

# Load the PDF
pdf = pdfium.PdfDocument(str(pdf_path))

# Render the first page
page = pdf[0]
pil_image = page.render(scale=2).to_pil()

# Save as PNG
output_path = output_dir / "img_test_rendered.png"
pil_image.save(output_path)

print(f"Saved rendered PNG: {output_path}")

# Close the PDF
pdf.close()
