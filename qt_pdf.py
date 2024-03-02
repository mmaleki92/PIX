import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QFileDialog, 
                             QSpinBox, QTextEdit)
from PyQt5.QtCore import QThread, pyqtSignal
import fitz  # PyMuPDF

# Your existing functions go here (identify_image_type, save_image, etc.)
# Assuming your original functions are defined above
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog, QSpinBox, QTextEdit, QProgressBar
from PyQt5.QtCore import QThread, pyqtSignal

import fitz  # PyMuPDF

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

class ImageExtractorThread(QThread):
    progress_signal = pyqtSignal(int)
    update_signal = pyqtSignal(str)
    
    def __init__(self, directory_path, output_folder, size_limit, page_limit):
        super().__init__()
        self.directory_path = directory_path
        self.output_folder = output_folder
        self.size_limit = size_limit
        self.page_limit = page_limit

    def run(self):
        try:
            pdf_files = [os.path.join(root, file) for root, dirs, files in os.walk(self.directory_path) for file in files if file.lower().endswith('.pdf')]
            total_files = len(pdf_files)
            processed_files = 0
            
            if not os.path.exists(self.output_folder):
                os.makedirs(self.output_folder)
            
            for pdf_path in pdf_files:
                doc = fitz.open(pdf_path)
                if len(doc) <= self.page_limit:
                    self.update_signal.emit(f"Extracting from {pdf_path}...")
                    for page_num, page in enumerate(doc, start=1):
                        extract_images_from_page(page, self.output_folder, page_num, self.size_limit)
                doc.close()
                processed_files += 1
                progress = int((processed_files / total_files) * 100)
                self.progress_signal.emit(progress)
                
            self.update_signal.emit("Extraction Complete.")
        except Exception as e:
            self.update_signal.emit(f"Error: {str(e)}")


def extract_images_from_page(page, output_folder, page_num, size_limit):
    image_list = page.get_images(full=True)
    for image_index, img in enumerate(image_list, start=1):
        xref = img[0]
        process_image(page.parent, xref, output_folder, page_num, image_index, size_limit)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):

        self.setWindowTitle("PDF Image Extractor")
        self.setGeometry(100, 100, 400, 300)
        
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        layout = QVBoxLayout(centralWidget)
        
        self.directoryLineEdit = QLineEdit()
        self.browseButton = QPushButton("Browse...")
        self.browseButton.clicked.connect(self.openFileDialog)
        self.outputLineEdit = QLineEdit()
        self.outputBrowseButton = QPushButton("Browse...")
        self.outputBrowseButton.clicked.connect(self.openOutputDialog)
        self.sizeLimitSpinBox = QSpinBox()
        self.sizeLimitSpinBox.setMaximum(10000000)
        self.sizeLimitSpinBox.setValue(100000)  # Default value
        self.pageLimitSpinBox = QSpinBox()
        self.pageLimitSpinBox.setMaximum(1000)
        self.pageLimitSpinBox.setValue(7)  # Default value
        self.extractButton = QPushButton("Extract Images")
        self.extractButton.clicked.connect(self.startExtraction)
        self.statusText = QTextEdit()
        self.statusText.setReadOnly(True)
        self.progressBar = QProgressBar(self)
        layout.addWidget(self.progressBar)
        
        layout.addWidget(QLabel("PDF Directory:"))
        layout.addWidget(self.directoryLineEdit)
        layout.addWidget(self.browseButton)
        layout.addWidget(QLabel("Output Directory:"))
        layout.addWidget(self.outputLineEdit)
        layout.addWidget(self.outputBrowseButton)
        layout.addWidget(QLabel("Size Limit (bytes):"))
        layout.addWidget(self.sizeLimitSpinBox)
        layout.addWidget(QLabel("Page Limit:"))
        layout.addWidget(self.pageLimitSpinBox)
        layout.addWidget(self.extractButton)
        layout.addWidget(self.statusText)
        
    def openFileDialog(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Directory")
        if directory:
            self.directoryLineEdit.setText(directory)
    
    def openOutputDialog(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.outputLineEdit.setText(directory)
    
    def startExtraction(self):
        directory_path = self.directoryLineEdit.text()
        output_folder = self.outputLineEdit.text()
        size_limit = self.sizeLimitSpinBox.value()
        page_limit = self.pageLimitSpinBox.value()
        
        self.extractThread = ImageExtractorThread(directory_path, output_folder, size_limit, page_limit)
        self.extractThread.update_signal.connect(self.updateStatus)
        self.extractThread.progress_signal.connect(self.progressBar.setValue)
        self.extractThread.start()

    
    def updateStatus(self, message):
        self.statusText.append(message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())
