import fitz  # PyMuPDF
import os
import json
import uuid
import time
from multiprocessing import Pool, cpu_count, Manager
from functools import partial
import threading
import queue

# Global progress tracking
extraction_progress = {
    'processed_files': 0,
    'total_files': 0,
    'current_file': '',
    'extracted_images': 0
}

def identify_image_type(image_bytes):
    """Identify the type of image from its bytes."""
    if image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'PNG'
    elif image_bytes[0:2] == b'\xff\xd8':
        return 'JPEG'
    else:
        return 'Unknown format'

def save_image(image_bytes, image_output_path):
    """Save image bytes to file."""
    try:
        with open(image_output_path, "wb") as img_file:
            img_file.write(image_bytes)
        return True
    except Exception as e:
        print(f"Error saving image: {str(e)}")
        return False

def process_image(doc, xref, output_folder, pdf_page_num, image_index, size_limit, full_pdf_path):
    """Process a single image from a PDF document."""
    try:
        base_image = doc.extract_image(xref)
        image_bytes = base_image["image"]
        
        # Skip small images
        if len(image_bytes) < size_limit:
            return None
        
        image_type = identify_image_type(image_bytes)
        if image_type == 'Unknown format':
            return None
        
        # Create unique ID for the image
        unique_id = str(uuid.uuid4())
        image_name = f"{unique_id}.{image_type.lower()}"
        image_output_path = os.path.join(output_folder, image_name)
        
        if save_image(image_bytes, image_output_path):
            return {
                unique_id: {
                    "pdf_path": full_pdf_path,  # Store full path to PDF
                    "file_name": os.path.basename(doc.name),  # Keep filename too for display purposes
                    "page_number": pdf_page_num,
                    "image_index": image_index,
                    "image_type": image_type,
                    "size_bytes": len(image_bytes),
                    "path": image_output_path,
                    "extraction_date": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }
        return None
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return None

def process_pdf(args):
    """Process a single PDF file to extract images."""
    pdf_path, output_folder, size_limit, page_limit, lock = args
    
    metadata = {}
    try:
        # Update progress information
        with lock:
            extraction_progress['current_file'] = pdf_path  # Store full path in progress
        
        doc = fitz.open(pdf_path)
        if len(doc) > page_limit:
            doc.close()
            return metadata
        
        # Get absolute path to ensure consistency
        full_pdf_path = os.path.abspath(pdf_path)
        
        for page_num, page in enumerate(doc, start=1):
            image_list = page.get_images(full=True)
            for image_index, img in enumerate(image_list, start=1):
                xref = img[0]
                image_metadata = process_image(doc, xref, output_folder, page_num, image_index, 
                                              size_limit, full_pdf_path)
                if image_metadata:
                    metadata.update(image_metadata)
                    with lock:
                        extraction_progress['extracted_images'] += 1
        
        doc.close()
        
        # Update processed files count
        with lock:
            extraction_progress['processed_files'] += 1
            
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
        with lock:
            extraction_progress['processed_files'] += 1
            
    return metadata

def extract_images_from_directory(directory_path, output_folder, size_limit, page_limit):
    """Extract images from all PDFs in a directory."""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Load existing metadata
    metadata_file_path = "images_metadata.json"
    existing_metadata = {}
    if os.path.exists(metadata_file_path):
        try:
            with open(metadata_file_path, "r") as json_file:
                existing_metadata = json.load(json_file)
        except Exception as e:
            print(f"Error loading metadata: {str(e)}")
    
    # Collect all PDF files recursively from directory and subdirectories
    pdf_paths = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_paths.append(os.path.join(root, file))
    
    # Print summary of found files
    print(f"Found {len(pdf_paths)} PDF files in {directory_path} and its subdirectories")
    
    # Reset progress tracking
    extraction_progress['processed_files'] = 0
    extraction_progress['total_files'] = len(pdf_paths)
    extraction_progress['current_file'] = ''
    extraction_progress['extracted_images'] = 0
    
    # Create a manager for multiprocessing shared objects
    manager = Manager()
    lock = manager.Lock()
    
    # Configure multiprocessing
    num_processes = min(cpu_count(), 4)  # Limit max processes to avoid excessive resource usage
    process_args = [(pdf_path, output_folder, size_limit, page_limit, lock) for pdf_path in pdf_paths]
    
    # Process PDFs in parallel
    results = []
    with Pool(num_processes) as pool:
        results = pool.map(process_pdf, process_args)
    
    # Merge results
    new_metadata = existing_metadata.copy()
    for result in results:
        new_metadata.update(result)
    
    # Save updated metadata
    try:
        with open(metadata_file_path, "w") as json_file:
            json.dump(new_metadata, json_file, indent=4)
    except Exception as e:
        print(f"Error saving metadata: {str(e)}")
    
    return extraction_progress['extracted_images']

def get_extraction_progress():
    """Get current extraction progress information."""
    return extraction_progress.copy()

class ExtractionProgressMonitor(threading.Thread):
    """Thread to monitor extraction progress."""
    def __init__(self, callback=None, interval=0.5):
        super().__init__()
        self.callback = callback
        self.interval = interval
        self.running = True
    
    def run(self):
        while self.running:
            if self.callback:
                progress = get_extraction_progress()
                self.callback(progress)
            time.sleep(self.interval)
    
    def stop(self):
        self.running = False