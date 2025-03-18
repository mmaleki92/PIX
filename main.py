import sys
import os
import json
import time

from PyQt5.QtWidgets import (QApplication, QDialog, QWidget, QHBoxLayout, QFormLayout,
                             QGridLayout, QLabel, QPushButton, QScrollArea, QFileDialog,
                             QVBoxLayout, QLineEdit, QSlider, QCheckBox, QSplitter, 
                             QProgressBar, QMessageBox, QStyle, QStyleFactory)
from PyQt5.QtGui import QPixmap, QIcon, QFont, QPalette, QColor
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QThread, pyqtSlot, QRunnable, QThreadPool, QObject
from image_extraction import extract_images_from_directory

# Worker classes for background processing
class WorkerSignals(QObject):
    started = pyqtSignal()
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    error = pyqtSignal(str)
    result = pyqtSignal(list)

class ImageExtractionWorker(QRunnable):
    def __init__(self, dir_path, output_folder, size_limit, page_limit):
        super().__init__()
        self.dir_path = dir_path
        self.output_folder = output_folder
        self.size_limit = size_limit
        self.page_limit = page_limit
        self.signals = WorkerSignals()

    def run(self):
        self.signals.started.emit()
        try:
            # Create output folder if it doesn't exist
            if not os.path.exists(self.output_folder):
                os.makedirs(self.output_folder)
                
            extract_images_from_directory(self.dir_path, self.output_folder, self.size_limit, self.page_limit)
            
            # Get extracted image paths
            extracted_images = []
            if os.path.exists(self.output_folder):
                image_paths = os.listdir(self.output_folder)
                extracted_images = [os.path.join(self.output_folder, file) for file in image_paths 
                                   if file.endswith(('.png', '.jpg', '.jpeg'))]
            
            self.signals.result.emit(extracted_images)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()

class ImagePreviewDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super(ImagePreviewDialog, self).__init__(parent)
        self.setWindowTitle("Image Preview")
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d30;
                color: #f0f0f0;
            }
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0098ff;
            }
        """)
        self.setMinimumSize(700, 700)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Load and display the image
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.image_label = QLabel()
            self.image_label.setAlignment(Qt.AlignCenter)
            self.image_label.setPixmap(pixmap.scaled(650, 650, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            
            # Add a scrollable area for large images
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(self.image_label)
            layout.addWidget(scroll_area)

            # Information about the image
            info_layout = QHBoxLayout()
            size_label = QLabel(f"Size: {pixmap.width()}x{pixmap.height()} pixels")
            size_label.setStyleSheet("color: #cccccc; font-style: italic;")
            info_layout.addWidget(size_label)
            
            # Add file size info
            file_info = os.stat(image_path)
            file_size = file_info.st_size / 1024  # KB
            if file_size > 1024:
                file_size = f"{file_size/1024:.2f} MB"
            else:
                file_size = f"{file_size:.2f} KB"
            file_size_label = QLabel(f"File size: {file_size}")
            file_size_label.setStyleSheet("color: #cccccc; font-style: italic;")
            info_layout.addWidget(file_size_label)
            
            layout.addLayout(info_layout)
        else:
            error_label = QLabel("Image file not found or cannot be opened")
            error_label.setStyleSheet("color: #ff6b6b;")
            layout.addWidget(error_label)

        # Button layout
        button_layout = QHBoxLayout()
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        
        # Copy path button
        copy_path_button = QPushButton("Copy Image Path")
        copy_path_button.clicked.connect(lambda: QApplication.clipboard().setText(image_path))
        
        button_layout.addStretch()
        button_layout.addWidget(copy_path_button)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)


class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super(ClickableLabel, self).__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.selected = False
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            ClickableLabel {
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 4px;
                background-color: #2d2d30;
            }
            ClickableLabel:hover {
                border-color: #0098ff;
                background-color: #383838;
            }
        """)

    def setSelected(self, selected):
        self.selected = selected
        if selected:
            self.setStyleSheet("""
                ClickableLabel {
                    border: 3px solid #0098ff;
                    border-radius: 6px;
                    padding: 4px;
                    background-color: #383838;
                }
            """)
        else:
            self.initUI()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()


class ImageGrid(QWidget):
    def __init__(self, extraction_path):
        super().__init__()
        self.threadpool = QThreadPool()
        self.max_label_size = 150
        self.thumbnail_size = QSize(self.max_label_size, self.max_label_size)
        self.image_cache = {}
        self.use_thumbnails = True
        self.selected_label = None
        self.page = 0
        self.page_size = 40
        
        # Set dark theme application-wide
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #f0f0f0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0098ff;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #aaaaaa;
            }
            QLineEdit, QScrollArea {
                background-color: #2d2d30;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                padding: 4px;
                color: #f0f0f0;
            }
            QLabel {
                color: #f0f0f0;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #3f3f46;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #007acc;
                border: none;
                width: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #0098ff;
            }
            QCheckBox {
                color: #f0f0f0;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        
        if os.path.exists("images_metadata.json"):
            self.metadata = self.load_metadata("images_metadata.json")
        else:
            self.metadata = {}

        if os.path.exists(extraction_path):
            image_paths = os.listdir(extraction_path)
            self.extracted_image_paths = [os.path.join(extraction_path, file) for file in image_paths 
                                        if file.endswith(('.png', '.jpg', '.jpeg'))]
        else:
            self.extracted_image_paths = []
            
        self.image_paths = extraction_path
        self.initUI()

    def initUI(self):
        # Main layout is horizontal
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Container for the grid and its controls
        grid_container = QWidget()
        grid_layout = QVBoxLayout(grid_container)
        grid_layout.setSpacing(10)
        splitter.addWidget(grid_container)
        
        # Path and extraction controls
        self.show_path = QLabel("No directory selected")
        self.show_path.setWordWrap(True)
        self.show_path.setStyleSheet("font-weight: bold; color: #cccccc; padding: 5px;")
        grid_layout.addWidget(self.show_path)
        
        extraction_layout = QHBoxLayout()
        extraction_layout.setSpacing(8)
        
        self.path_button = QPushButton('Set Path', self)
        self.path_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.path_button.clicked.connect(self.openPathDialog)
        extraction_layout.addWidget(self.path_button)
        
        extract = QPushButton('Extract', self)
        extract.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        extract.clicked.connect(self.extractImages)
        extraction_layout.addWidget(extract)
        
        self.size_limit_input = QLineEdit(self)
        self.size_limit_input.setPlaceholderText("Size Limit (KB)")
        self.size_limit_input.setText("1000")
        extraction_layout.addWidget(self.size_limit_input)

        self.page_limit_input = QLineEdit(self)
        self.page_limit_input.setPlaceholderText("Page Limit")
        self.page_limit_input.setText("50")
        extraction_layout.addWidget(self.page_limit_input)
        
        grid_layout.addLayout(extraction_layout)
        
        # Progress bar for extraction (hidden initially)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0)  # Indeterminate mode
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3f3f46;
                border-radius: 4px;
                text-align: center;
                height: 20px;
                background-color: #2d2d30;
            }
            QProgressBar::chunk {
                background-color: #007acc;
                width: 20px;
            }
        """)
        grid_layout.addWidget(self.progress_bar)
        
        # Status label for extraction
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #cccccc; font-style: italic;")
        self.status_label.setVisible(False)
        grid_layout.addWidget(self.status_label)
        
        # Sidebar for full-size image display and info
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)
        splitter.addWidget(sidebar)

        # Window setup
        self.setGeometry(300, 300, 1200, 800)
        self.setWindowTitle('Image Viewer')

        # Scroll Area for thumbnails
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        grid_layout.addWidget(scroll_area, 1)
        container = QWidget()
        scroll_area.setWidget(container)
        self.grid = QGridLayout(container)
        self.grid.setSpacing(10)

        # Create pagination controls first before calling updateGrid
        pagination_layout = QHBoxLayout()
        
        prev_button = QPushButton('<', self)
        prev_button.clicked.connect(lambda: self.changePage(-1))
        pagination_layout.addWidget(prev_button)

        self.page_number_label = QLabel("Page 1", self)
        self.page_number_label.setAlignment(Qt.AlignCenter)
        pagination_layout.addWidget(self.page_number_label)

        next_button = QPushButton('>', self)
        next_button.clicked.connect(lambda: self.changePage(1))
        pagination_layout.addWidget(next_button)
        
        grid_layout.addLayout(pagination_layout)
        

        # Sidebar - Image information section
        sidebar_title = QLabel("Image Information")
        sidebar_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        sidebar_layout.addWidget(sidebar_title)
        
        # Address field for selected image
        address_label = QLabel("Image Path:")
        address_label.setStyleSheet("font-weight: bold;")
        sidebar_layout.addWidget(address_label)
        
        self.address_field = QLineEdit(self)
        self.address_field.setReadOnly(True)
        sidebar_layout.addWidget(self.address_field)

        # Copy button
        self.copy_button = QPushButton("Copy Path", self)
        self.copy_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.copy_button.clicked.connect(self.copyTextToClipboard)
        sidebar_layout.addWidget(self.copy_button)
        
        # Preview button
        self.preview_button = QPushButton("Preview Image", self)
        self.preview_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogContentsView))
        self.preview_button.clicked.connect(lambda: self.openPreviewDialog(self.address_field.text()) if self.address_field.text() else None)
        self.preview_button.setEnabled(False)
        sidebar_layout.addWidget(self.preview_button)

        # Form layout for metadata
        metadata_title = QLabel("Metadata")
        metadata_title.setStyleSheet("font-weight: bold; margin-top: 15px;")
        sidebar_layout.addWidget(metadata_title)
        
        self.info_form_widget = QWidget()
        self.info_form = QFormLayout(self.info_form_widget)
        self.info_form.setSpacing(8)
        sidebar_layout.addWidget(self.info_form_widget)
        
        # Add stretch to push everything up
        sidebar_layout.addStretch(1)

        # Controls section
        controls_title = QLabel("Display Controls")
        controls_title.setStyleSheet("font-weight: bold; margin-top: 15px;")
        sidebar_layout.addWidget(controls_title)
        
        # Thumbnail size slider
        size_layout = QHBoxLayout()
        size_label = QLabel("Thumbnail Size:")
        size_layout.addWidget(size_label)
        
        self.zoom_slider = QSlider(Qt.Horizontal, self)
        self.zoom_slider.setMinimum(50)
        self.zoom_slider.setMaximum(300)
        self.zoom_slider.setValue(self.max_label_size)
        self.zoom_slider.valueChanged.connect(self.onSliderValueChanged)
        size_layout.addWidget(self.zoom_slider)
        
        sidebar_layout.addLayout(size_layout)

        # Thumbnail toggle
        self.thumbnail_toggle = QCheckBox("Show Thumbnails", self)
        self.thumbnail_toggle.setChecked(self.use_thumbnails)
        self.thumbnail_toggle.stateChanged.connect(self.toggleThumbnails)
        sidebar_layout.addWidget(self.thumbnail_toggle)
        
        # Full-size image preview
        preview_title = QLabel("Quick Preview")
        preview_title.setStyleSheet("font-weight: bold; margin-top: 15px;")
        sidebar_layout.addWidget(preview_title)
        
        self.full_size_image_label = QLabel()
        self.full_size_image_label.setAlignment(Qt.AlignCenter)
        self.full_size_image_label.setMinimumHeight(200)
        self.full_size_image_label.setStyleSheet("background-color: #2d2d30; border: 1px solid #3f3f46; border-radius: 4px;")
        sidebar_layout.addWidget(self.full_size_image_label)

        # Set minimum widths
        grid_container.setMinimumWidth(650)
        sidebar.setMinimumWidth(350)

        # Adjust splitter sizes (70% grid, 30% sidebar)
        splitter.setSizes([700, 300])
        # Now we can safely call updateGrid
        self.updateGrid()
        
    def load_metadata(self, metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata: {str(e)}")
            return {}

    def openPathDialog(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Image Directory")
        if dir_path:
            self.dir_path = dir_path
            self.show_path.setText(f"Selected directory: {dir_path}")

    def extractImages(self):
        if not hasattr(self, 'dir_path') or not self.dir_path:
            QMessageBox.warning(self, "No Directory Selected", 
                               "Please select a directory first.")
            return
        
        try:
            size_limit = int(self.size_limit_input.text()) * 1024  # KB to bytes
            page_limit = int(self.page_limit_input.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", 
                               "Please enter valid numbers for size and page limits.")
            return
        
        # Show progress bar and status
        self.progress_bar.setVisible(True)
        self.status_label.setText("Extracting images... This may take a while.")
        self.status_label.setVisible(True)
        
        # Disable extraction controls during processing
        self.path_button.setEnabled(False)
        self.size_limit_input.setEnabled(False)
        self.page_limit_input.setEnabled(False)
        
        # Reset selected label to avoid reference to deleted object
        self.selected_label = None
        
        # Create and start the worker
        output_folder = 'extracted_images'
        worker = ImageExtractionWorker(self.dir_path, output_folder, size_limit, page_limit)
        
        # Connect signals
        worker.signals.started.connect(self.extraction_started)
        worker.signals.finished.connect(self.extraction_finished)
        worker.signals.error.connect(self.extraction_error)
        worker.signals.result.connect(self.update_extracted_images)
        
        # Start the extraction in a background thread
        self.threadpool.start(worker)

    @pyqtSlot()
    def extraction_started(self):
        print("Extraction started")
        
    @pyqtSlot()
    def extraction_finished(self):
        self.progress_bar.setVisible(False)
        self.status_label.setText("Extraction complete!")
        
        # Re-enable extraction controls
        self.path_button.setEnabled(True)
        self.size_limit_input.setEnabled(True)
        self.page_limit_input.setEnabled(True)
        
    @pyqtSlot(str)
    def extraction_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error_msg}")
        self.status_label.setStyleSheet("color: #ff6b6b;")
        
        # Re-enable extraction controls
        self.path_button.setEnabled(True)
        self.size_limit_input.setEnabled(True)
        self.page_limit_input.setEnabled(True)
    
    @pyqtSlot(list)
    def update_extracted_images(self, extracted_images):
        self.extracted_image_paths = extracted_images
        self.page = 0  # Reset to first page
        # Clear any stored references to UI elements before updating the grid
        self.selected_label = None
        self.updateGrid()  # Refresh the grid with new images
        
        # Reload metadata
        if os.path.exists("images_metadata.json"):
            self.metadata = self.load_metadata("images_metadata.json")
            
        # Show count of extracted images
        self.status_label.setText(f"Extracted {len(self.extracted_image_paths)} images.")

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            zoom_factor = 20
            if delta > 0:  # Zooming in
                self.max_label_size = min(self.max_label_size + zoom_factor, 300)
            else:  # Zooming out
                self.max_label_size = max(self.max_label_size - zoom_factor, 50)
                
            self.zoom_slider.setValue(self.max_label_size)
            self.updateGrid()
        else:
            super().wheelEvent(event)

    def openPreviewDialog(self, img_path):
        if img_path and os.path.exists(img_path):
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
        if text:
            QApplication.clipboard().setText(text)
            self.status_label.setText("Path copied to clipboard")
            self.status_label.setStyleSheet("color: #4CAF50;")
            self.status_label.setVisible(True)

    def load_image(self, img_path):
        if not os.path.exists(img_path):
            # Return a placeholder for missing images
            placeholder = QPixmap(self.max_label_size, self.max_label_size)
            placeholder.fill(Qt.gray)
            return placeholder
            
        if img_path not in self.image_cache:
            try:
                image = QPixmap(img_path)
                if not image.isNull():
                    self.image_cache[img_path] = image
                else:
                    # Return a placeholder for corrupted images
                    placeholder = QPixmap(self.max_label_size, self.max_label_size)
                    placeholder.fill(Qt.red)
                    self.image_cache[img_path] = placeholder
            except Exception as e:
                print(f"Error loading image {img_path}: {str(e)}")
                placeholder = QPixmap(self.max_label_size, self.max_label_size)
                placeholder.fill(Qt.red)
                self.image_cache[img_path] = placeholder
        return self.image_cache[img_path]

    def updateGrid(self):
        # Clear existing grid and reset selected label
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        
        self.selected_label = None
        self.full_size_image_label.clear()
        self.address_field.clear()
        self.preview_button.setEnabled(False)
        
        # Clear form layout
        while self.info_form.rowCount() > 0:
            self.info_form.removeRow(0)

        image_paths_to_display = self.extracted_image_paths
        if not image_paths_to_display:
            # Show a message when no images are available
            no_images_label = QLabel("No images available.\nSelect a directory and click 'Extract' to begin.")
            no_images_label.setStyleSheet("color: #cccccc; font-size: 14px;")
            no_images_label.setAlignment(Qt.AlignCenter)
            self.grid.addWidget(no_images_label, 0, 0)
            self.page_number_label.setText("Page 0 of 0")
            return
            
        start = self.page * self.page_size
        end = min(start + self.page_size, len(image_paths_to_display))

        container_width = self.grid.parent().width() or 600
        self.num_images_per_row = max(container_width // (self.max_label_size + 20), 1)

        for i, img_path in enumerate(image_paths_to_display[start:end], start=1):
            if not os.path.exists(img_path):
                continue  # Skip images that don't exist
                
            pixmap = self.load_image(img_path)
            scaled_pixmap = pixmap.scaled(self.max_label_size, self.max_label_size, 
                                          Qt.KeepAspectRatio, Qt.SmoothTransformation)

            label = ClickableLabel()
            label.setPixmap(scaled_pixmap)
            label.setFixedSize(self.max_label_size, self.max_label_size)
            label.setToolTip(os.path.basename(img_path))
            
            # Store image path as property on the label to avoid closure issues
            label.img_path = img_path
            
            # Connect signals with direct method reference
            label.clicked.connect(lambda label=label: self.onImageClicked(label.img_path, label))
            label.double_clicked.connect(lambda label=label: self.openPreviewDialog(label.img_path))

            row = (i - 1) // self.num_images_per_row
            col = (i - 1) % self.num_images_per_row
            self.grid.addWidget(label, row, col)
            
        # Update page number display
        total_pages = max((len(image_paths_to_display) - 1) // self.page_size + 1, 1)
        self.page_number_label.setText(f"Page {self.page + 1} of {total_pages}")

    def changePage(self, direction):
        image_paths_to_display = self.extracted_image_paths
        if not image_paths_to_display:
            return
            
        new_page = self.page + direction
        max_page = (len(image_paths_to_display) - 1) // self.page_size
        
        if 0 <= new_page <= max_page:
            self.page = new_page
            self.updateGrid()

    def onImageClicked(self, img_path, clicked_label):
        # Make sure we have valid objects before doing anything
        if not os.path.exists(img_path):
            return
            
        # Deselect previous label if any and it still exists
        if self.selected_label is not None:
            try:
                # Check if the label is still valid
                self.selected_label.selected = False
                self.selected_label.setStyleSheet("""
                    ClickableLabel {
                        border: 2px solid #555555;
                        border-radius: 6px;
                        padding: 4px;
                        background-color: #2d2d30;
                    }
                    ClickableLabel:hover {
                        border-color: #0098ff;
                        background-color: #383838;
                    }
                """)
            except RuntimeError:
                # Label was deleted, just ignore
                pass
            
        # Select the clicked label
        self.selected_label = clicked_label
        if clicked_label is not None:
            try:
                clicked_label.setSelected(True)
            except RuntimeError:
                # Label was deleted, just ignore
                self.selected_label = None
                return
        
        # Update the address field
        self.address_field.setText(img_path)
        self.preview_button.setEnabled(True)
        
        # Show quick preview in sidebar
        pixmap = self.load_image(img_path)
        preview_pixmap = pixmap.scaled(330, 330, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.full_size_image_label.setPixmap(preview_pixmap)

        # Extract the image ID from the filename
        image_id = os.path.splitext(os.path.basename(img_path))[0]

        # Clear previous metadata
        while self.info_form.rowCount() > 0:
            self.info_form.removeRow(0)
        
        # Get and display metadata
        metadata = self.metadata.get(image_id, {})
        if metadata:
            for key, value in metadata.items():
                label = QLabel(f"{key}:")
                label.setStyleSheet("font-weight: bold;")
                value_label = QLabel(str(value))
                self.info_form.addRow(label, value_label)
        else:
            no_metadata_label = QLabel("No metadata available")
            no_metadata_label.setStyleSheet("color: #cccccc; font-style: italic;")
            self.info_form.addRow(no_metadata_label)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create('Fusion'))  # Use Fusion style for better cross-platform look
    ex = ImageGrid("extracted_images")
    ex.show()
    sys.exit(app.exec_())