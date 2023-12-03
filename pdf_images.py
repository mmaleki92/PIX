import fitz  # PyMuPDF
import os

def extract_images_from_pdf(pdf_path, output_folder):
    # Open the PDF file
    doc = fitz.open(pdf_path)

    # Iterate through each page
    for i in range(len(doc)):
        page = doc.load_page(i)

        # Get the list of image dicts on the page
        image_list = page.get_images(full=True)

        # Extract each image
        for image_index, img in enumerate(image_list, start=1):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            # Define the image's output path
            image_name = f"image_page_{i}_img_{image_index}.png"
            image_output_path = os.path.join(output_folder, image_name)

            # Save the image
            with open(image_output_path, "wb") as img_file:
                img_file.write(image_bytes)

    # Close the document
    doc.close()

# Usage
pdf_path = 'path_to_your_pdf.pdf'
output_folder = 'path_to_output_folder'
extract_images_from_pdf(pdf_path, output_folder)