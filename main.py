import sys
import os
import json

from PyQt5.QtWidgets import (QApplication, QDialog, QWidget, QHBoxLayout,
                              QGridLayout, QLabel, QPushButton, QScrollArea, QFileDialog,
                                QVBoxLayout, QLineEdit, QSlider, QCheckBox, QSplitter)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from image_extraction import extract_images_from_directory

class ImagePreviewDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super(ImagePreviewDialog, self).__init__(parent)
        self.setWindowTitle("Image Preview")
        layout = QVBoxLayout(self)

        # Load and display the image
        pixmap = QPixmap(image_path)
        label = QLabel()
        label.setPixmap(pixmap.scaled(600, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(label)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)


class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()  # Signal for double-click event
    def __init__(self, parent=None):
        super(ClickableLabel, self).__init__(parent)
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            ClickableLabel {
                border: 2px solid #8f8f91;
                border-radius: 4px;
                background-color: #f0f0f0;
            }
            ClickableLabel:hover {
                border-color: #1c1c1c;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()  # Emit double-click signal

class ImageGrid(QWidget):
    def __init__(self, image_paths):
        super().__init__()
        self.max_label_size = 100
        self.thumbnail_size = QSize(self.max_label_size, self.max_label_size)
        self.image_cache = {}
        self.use_thumbnails = True  # Default to using thumbnails
        if os.path.exists("images_metadata.json"):
            self.metadata = self.load_metadata("images_metadata.json")  # Load JSON metadata
        else:
            self.metadata = {}
        self.extracted_image_paths = []  # Store extracted image paths
        self.initUI(image_paths)

    def initUI(self, image_paths):
        # Main layout is now horizontal
        main_layout = QHBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Container for the grid and its controls
        grid_container = QWidget()
        grid_layout = QVBoxLayout(grid_container)
        self.show_path = QLabel("") 
        grid_layout.addWidget(self.show_path)
        splitter.addWidget(grid_container)
        
        extraction_layout = QHBoxLayout()
        
        # Button to open directory selection dialog
        self.path_button = QPushButton('Set Path', self)
        self.path_button.clicked.connect(self.openPathDialog)  # Connect to method
        extraction_layout.addWidget(self.path_button)
        
        # Extraction button
        extract = QPushButton('Extract', self)
        extract.clicked.connect(self.extractImages)  # Connect to extraction method
        extraction_layout.addWidget(extract)
        
        # Size limit input field (in KB)
        self.size_limit_input = QLineEdit(self)
        self.size_limit_input.setPlaceholderText("Size Limit (KB)")
        self.size_limit_input.setText("1000")  # Default value
        extraction_layout.addWidget(self.size_limit_input)

        # Page limit input field
        self.page_limit_input = QLineEdit(self)
        self.page_limit_input.setPlaceholderText("Page Limit")
        self.page_limit_input.setText("50")  # Default value
        extraction_layout.addWidget(self.page_limit_input)
        
        grid_layout.addLayout(extraction_layout)
        
        # Sidebar for full-size image display and additional controls
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        splitter.addWidget(sidebar)

        self.setGeometry(300, 300, 600, 400)
        self.setWindowTitle('Image Viewer')

        # Scroll Area for the thumbnails
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        grid_layout.addWidget(scroll_area)
        container = QWidget()
        scroll_area.setWidget(container)
        self.grid = QGridLayout(container)

        # Pagination controls and other widgets
        self.page = 0
        self.page_size = 40
        self.image_paths = image_paths
        self.updateGrid()        # Layout for pagination controls
        pagination_layout = QHBoxLayout()
        grid_layout.addLayout(pagination_layout)

        # Previous button
        prev_button = QPushButton('<', self)
        prev_button.clicked.connect(lambda: self.changePage(-1))
        pagination_layout.addWidget(prev_button)

        # Page number label
        self.page_number_label = QLabel(f"Page {self.page + 1}", self)
        self.page_number_label.setAlignment(Qt.AlignCenter)
        pagination_layout.addWidget(self.page_number_label)

        # Next button
        next_button = QPushButton('>', self)
        next_button.clicked.connect(lambda: self.changePage(1))
        pagination_layout.addWidget(next_button)

        # Address field for the selected image
        self.address_field = QLineEdit(self)
        self.address_field.setReadOnly(True)
        sidebar_layout.addWidget(self.address_field)

        # Button to copy the image path to the clipboard
        self.copy_button = QPushButton("Copy to Clipboard", self)
        self.copy_button.clicked.connect(self.copyTextToClipboard)
        sidebar_layout.addWidget(self.copy_button)

        # Slider for zoom control
        self.zoom_slider = QSlider(Qt.Horizontal, self)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(500)
        self.zoom_slider.setValue(self.max_label_size)
        self.zoom_slider.valueChanged.connect(self.onSliderValueChanged)
        grid_layout.addWidget(self.zoom_slider)

        # Toggle button for switching between thumbnails and full-size images
        self.thumbnail_toggle = QCheckBox("Show Thumbnails", self)
        self.thumbnail_toggle.setChecked(self.use_thumbnails)
        self.thumbnail_toggle.stateChanged.connect(self.toggleThumbnails)
        grid_layout.addWidget(self.thumbnail_toggle)

        # Full-size image label
        self.full_size_image_label = QLabel()
        self.full_size_image_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(self.full_size_image_label)

        # Set a minimum width for the sidebar and grid container
        grid_container.setMinimumWidth(300)
        sidebar.setMinimumWidth(200)
        self.full_size_image_label.setMinimumWidth(200)

        # Adjust the splitter to give 1/3 of the window to the sidebar
        splitter.setSizes([900, 300])  # Adjust these values as needed

    def load_metadata(self, metadata_path):
        with open(metadata_path, 'r') as f:
            return json.load(f)

    def openPathDialog(self):
        # Open a file dialog to select a directory
        dir_path = QFileDialog.getExistingDirectory(self, "Select Image Directory")
        if dir_path:
            self.dir_path = dir_path  # Store the selected directory path
            self.show_path.setText(dir_path)

    def extractImages(self):
        if not hasattr(self, 'dir_path') or not self.dir_path:
            return  # No directory path selected, do nothing
        
        # Retrieve size and page limits from the input fields
        try:
            size_limit = int(self.size_limit_input.text()) * 1024  # Convert KB to bytes
            page_limit = int(self.page_limit_input.text())
        except ValueError:
            # Handle invalid input (e.g., non-integer values)
            return
        
        output_folder = 'extracted_images'
        extract_images_from_directory(self.dir_path, output_folder, size_limit, page_limit)

        # Set new image paths based on the extracted images
        self.extracted_image_paths = [os.path.join(output_folder, file) for file in os.listdir(output_folder) if file.endswith(('.png', '.jpg', '.jpeg'))]
        self.page = 0  # Reset to the first page
        self.updateGrid()  # Refresh the grid with new images

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            zoom_factor = 50
            if delta > 0:  # Scrolled up
                self.max_label_size += zoom_factor
            elif delta < 0:  # Scrolled down
                self.max_label_size = max(self.max_label_size - zoom_factor, 10)
            self.updateGrid()
        self.zoom_slider.setValue(self.max_label_size)

    def openPreviewDialog(self, img_path):
        dialog = ImagePreviewDialog(img_path, self)
        dialog.exec_()

    def toggleThumbnails(self, state):
        self.use_thumbnails = bool(state)
        self.updateGrid()

    def onSliderValueChanged(self):
        self.max_label_size = self.zoom_slider.value()
        self.updateGrid()

    def copyTextToClipboard(self):
        text = self.address_field.text()
        QApplication.clipboard().setText(text)

    def load_image(self, img_path):
        if img_path not in self.image_cache:
            image = QPixmap(img_path)
            self.image_cache[img_path] = image
        return self.image_cache[img_path]

    def updateGrid(self):
        # Clear the existing grid layout items
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Use the extracted image paths if extraction has occurred
        image_paths_to_display = self.extracted_image_paths or self.image_paths
        start = self.page * self.page_size
        end = min(start + self.page_size, len(image_paths_to_display))

        container_width = self.grid.parent().width() or 500
        self.num_images_per_row = max(container_width // self.max_label_size, 1)

        for i, img_path in enumerate(image_paths_to_display[start:end], start=1):
            pixmap = self.load_image(img_path)

            # Scale pixmap to fit self.max_label_size while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(self.max_label_size, self.max_label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            label = ClickableLabel(img_path)
            label.setPixmap(scaled_pixmap)
            label.setFixedSize(min(scaled_pixmap.width(), self.max_label_size), min(scaled_pixmap.height(), self.max_label_size))

            # Connect click and double-click signals
            label.clicked.connect(lambda path=img_path: self.onImageClicked(path))
            label.double_clicked.connect(lambda path=img_path: self.openPreviewDialog(path))

            row = (i - 1) // self.num_images_per_row
            col = (i - 1) % self.num_images_per_row
            self.grid.addWidget(label, row, col)

    def changePage(self, direction):
        new_page = self.page + direction
        max_page = (len(self.extracted_image_paths) - 1) // self.page_size if self.extracted_image_paths else (len(self.image_paths) - 1) // self.page_size
        if 0 <= new_page <= max_page:
            self.page = new_page
            self.updateGrid()
            self.page_number_label.setText(f"Page {self.page + 1}")

    def onImageClicked(self, img_path):
        # Extract the image ID from the filename
        image_id = os.path.splitext(os.path.basename(img_path))[0]

        # Update the address field with the image path
        self.address_field.setText(img_path)

        # Display metadata if available
        metadata = self.metadata.get(image_id, {})
        print(metadata)

        self.updateGrid()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageGrid("extracted_images")
    ex.show()
    sys.exit(app.exec_())