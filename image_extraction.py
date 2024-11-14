import fitz  # PyMuPDF
import os
import json
import uuid

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

def process_image(doc, xref, output_folder, pdf_page_num, image_index, size_limit, metadata):
    base_image = doc.extract_image(xref)
    image_bytes = base_image["image"]

    if len(image_bytes) < size_limit:
        return

    image_type = identify_image_type(image_bytes)
    if image_type == 'Unknown format':
        return

    unique_id = str(uuid.uuid4())
    image_name = f"{unique_id}.{image_type.lower()}"
    image_output_path = os.path.join(output_folder, image_name)
    save_image(image_bytes, image_output_path)

    # Update image metadata or add new entry
    metadata[unique_id] = {
        "file_name": doc.name,
        "page_number": pdf_page_num,
        "image_index": image_index,
        "image_type": image_type,
        "path": image_output_path
    }

def extract_images_from_page(page, output_folder, page_num, size_limit, metadata):
    image_list = page.get_images(full=True)
    for image_index, img in enumerate(image_list, start=1):
        xref = img[0]
        process_image(page.parent, xref, output_folder, page_num, image_index, size_limit, metadata)

def extract_images_from_pdf(pdf_path, output_folder, size_limit, metadata):
    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc, start=1):
        extract_images_from_page(page, output_folder, page_num, size_limit, metadata)
    doc.close()

def extract_images_from_directory(directory_path, output_folder, size_limit, page_limit):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Load existing metadata if it exists
    metadata = {}
    metadata_file_path = "images_metadata.json"
    if os.path.exists(metadata_file_path):
        with open(metadata_file_path, "r") as json_file:
            metadata = json.load(json_file)

    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_path = os.path.join(root, file)
                doc = fitz.open(pdf_path)
                if len(doc) <= page_limit:
                    extract_images_from_pdf(pdf_path, output_folder, size_limit, metadata)
                doc.close()

    # Save updated metadata to JSON file
    with open(metadata_file_path, "w") as json_file:
        json.dump(metadata, json_file, indent=4)
