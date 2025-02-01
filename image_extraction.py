import fitz  # PyMuPDF
import os
import json
import uuid
from multiprocessing import Pool, cpu_count
from functools import partial

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
        return None

    image_type = identify_image_type(image_bytes)
    if image_type == 'Unknown format':
        return None

    unique_id = str(uuid.uuid4())
    image_name = f"{unique_id}.{image_type.lower()}"
    image_output_path = os.path.join(output_folder, image_name)
    save_image(image_bytes, image_output_path)

    return {
        unique_id: {
            "file_name": os.path.basename(doc.name),
            "page_number": pdf_page_num,
            "image_index": image_index,
            "image_type": image_type,
            "path": image_output_path
        }
    }

def process_pdf(pdf_path, output_folder, size_limit, page_limit):
    metadata = {}
    try:
        doc = fitz.open(pdf_path)
        if len(doc) > page_limit:
            doc.close()
            return metadata
        
        for page_num, page in enumerate(doc, start=1):
            image_list = page.get_images(full=True)
            for image_index, img in enumerate(image_list, start=1):
                xref = img[0]
                image_metadata = process_image(doc, xref, output_folder, page_num, image_index, size_limit)
                if image_metadata:
                    metadata.update(image_metadata)
        doc.close()
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
    return metadata

def extract_images_from_directory(directory_path, output_folder, size_limit, page_limit):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Load existing metadata
    metadata_file_path = "images_metadata.json"
    existing_metadata = {}
    if os.path.exists(metadata_file_path):
        with open(metadata_file_path, "r") as json_file:
            existing_metadata = json.load(json_file)

    # Collect all PDF files
    pdf_paths = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_paths.append(os.path.join(root, file))

    # Configure multiprocessing
    num_processes = cpu_count()
    process_args = [(pdf_path, output_folder, size_limit, page_limit) for pdf_path in pdf_paths]

    # Process PDFs in parallel
    with Pool(num_processes) as pool:
        results = pool.starmap(process_pdf, process_args)

    # Merge results
    new_metadata = existing_metadata.copy()
    for result in results:
        new_metadata.update(result)

    # Save metadata
    with open(metadata_file_path, "w") as json_file:
        json.dump(new_metadata, json_file, indent=4)