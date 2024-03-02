import fitz  # PyMuPDF
import os

def identify_image_type(image_bytes):
    if image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'PNG'
    elif image_bytes[0:2] == b'\xff\xd8':
        return 'JPEG'
    else:
        return 'Unknown format'

def save_image(image_bytes, image_output_path):
    with open(image_output_path, "wb") as img_file:
        img_file.write(image_bytes)

def process_image(doc, xref, output_folder, pdf_page_num, image_index, size_limit):
    base_image = doc.extract_image(xref)
    image_bytes = base_image["image"]

    if len(image_bytes) < size_limit:
        return

    image_type = identify_image_type(image_bytes)
    if image_type == 'Unknown format':
        return

    image_name = f"{os.path.splitext(os.path.basename(doc.name))[0]}_page_{pdf_page_num}_img_{image_index}.{image_type.lower()}"
    image_output_path = os.path.join(output_folder, image_name)
    save_image(image_bytes, image_output_path)

def extract_images_from_page(page, output_folder, page_num, size_limit):
    image_list = page.get_images(full=True)
    for image_index, img in enumerate(image_list, start=1):
        xref = img[0]
        process_image(page.parent, xref, output_folder, page_num, image_index, size_limit)

def extract_images_from_pdf(pdf_path, output_folder, size_limit):
    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc, start=1):
        extract_images_from_page(page, output_folder, page_num, size_limit)
    doc.close()

def extract_images_from_directory(directory_path, output_folder, size_limit, page_limit):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_path = os.path.join(root, file)
                doc = fitz.open(pdf_path)
                if len(doc) <= page_limit:
                    extract_images_from_pdf(pdf_path, output_folder, size_limit)
                doc.close()

# Usage example
directory_path = '/media/mra75x/52D6F481D6F4669F/Users/PC/Zotero/storage'
output_folder = 'extracted_images'
size_limit = 100000  # 100 KB
page_limit = 7
extract_images_from_directory(directory_path, output_folder, size_limit, page_limit)
