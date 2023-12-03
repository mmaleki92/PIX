import fitz  # PyMuPDF
import os

def identify_image_type(image_bytes):
    # Check for PNG signature
    if image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'PNG'

    # Check for JPEG signature
    elif image_bytes[0:2] == b'\xff\xd8':
        return 'JPEG'

    else:
        return 'Unknown format'

def extract_images_from_pdf(pdf_path, output_folder, size_limit):
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

            # Check the size of the image
            if len(image_bytes) >= size_limit:
                # Identify image type (JPEG or PNG)
                image_type = identify_image_type(image_bytes)
                if image_type == 'Unknown format':
                    continue  # Skip if format is unknown

                # Define the image's output path with the correct extension
                image_extension = image_type.lower()
                image_name = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_page_{i}_img_{image_index}.{image_extension}"
                image_output_path = os.path.join(output_folder, image_name)

                # Save the image
                with open(image_output_path, "wb") as img_file:
                    img_file.write(image_bytes)

    # Close the document
    doc.close()

def extract_images_from_directory(directory_path, output_folder, size_limit, page_limit):
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Walk through the directory
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_path = os.path.join(root, file)

                # Open the PDF to check the number of pages
                doc = fitz.open(pdf_path)
                if len(doc) <= page_limit:
                    extract_images_from_pdf(pdf_path, output_folder, size_limit)
                doc.close()

# Usage
directory_path = '/home/drghodrat/Zotero/storage'
output_folder = 'imgs'

if not os.path.exists(output_folder):
    os.mkdir(output_folder)

size_limit = 100000  # Image size limit in bytes (100 KB)
page_limit = 7  # Maximum number of pages allowed in a PDF to be processed
extract_images_from_directory(directory_path, output_folder, size_limit, page_limit)