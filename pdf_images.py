import fitz  # PyMuPDF
import os

def extract_images_from_pdf(pdf_path, output_folder):
    # Open the PDF file
    doc = fitz.open(pdf_path)

    # Iterate through each page
    for i in range(len(doc)):
        page = doc.load_page(i)
        image_list = page.get_images(full=True)

        # Extract each image
        for image_index, img in enumerate(image_list, start=1):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            # Define the image's output path
            image_name = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{i}_img_{image_index}.png"
            image_output_path = os.path.join(output_folder, image_name)

            # Save the image
            with open(image_output_path, "wb") as img_file:
                img_file.write(image_bytes)

    # Close the document
    doc.close()

def extract_images_from_directory(directory_path, output_folder):
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Walk through the directory
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_path = os.path.join(root, file)
                extract_images_from_pdf(pdf_path, output_folder)

# Usage
directory_path = 'path_to_your_directory'
output_folder = 'imgs'
extract_images_from_directory(directory_path, output_folder)
