import sys
import requests
from io import BytesIO
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QLabel  # Add this import
from PyQt5.QtWidgets import QLineEdit, QPushButton  # Add these imports

class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super(ClickableLabel, self).__init__(parent)
        self.initUI()

    def initUI(self):
        # Basic styling
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



class ImageGrid(QWidget):
    def __init__(self, image_paths):
        super().__init__()
        self.max_label_size = 100  # Initialize with a default size
        self.initUI(image_paths)

    def initUI(self, image_paths):
        self.setGeometry(300, 300, 600, 400)
        self.setWindowTitle('Image Viewer')

        # Initialize layout
        layout = QVBoxLayout(self)
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        container = QWidget()
        scroll_area.setWidget(container)
        self.grid = QGridLayout(container)

        # Initialize image list and pagination
        self.page = 0
        self.page_size = 20
        self.image_paths = image_paths
        self.updateGrid()

        # Add navigation buttons
        next_button = QPushButton('Next Page', self)
        next_button.clicked.connect(lambda: self.changePage(1))
        layout.addWidget(next_button)

        prev_button = QPushButton('Previous Page', self)
        prev_button.clicked.connect(lambda: self.changePage(-1))
        layout.addWidget(prev_button)
        # Page number label
        self.page_number_label = QLabel(f"Page {self.page + 1}", self)  # Initialize with the first page
        self.page_number_label.setAlignment(Qt.AlignCenter)  # Center align the text
        # Text field to display the image address
        self.address_field = QLineEdit(self)
        self.address_field.setReadOnly(True)  # Make the field read-only
        layout.addWidget(self.address_field)

        # Copy button
        self.copy_button = QPushButton("Copy to Clipboard", self)
        self.copy_button.clicked.connect(self.copyTextToClipboard)
        layout.addWidget(self.copy_button)
        # Adjust layout to add page number label
        layout.addWidget(self.page_number_label)


    def onImageClicked(self, img_path):
        self.address_field.setText(img_path)  # Set the image address in the text field

    def copyTextToClipboard(self):
        text = self.address_field.text()
        QApplication.clipboard().setText(text)
        
    def resizeEvent(self, event):
        # Recalculate the max label size based on the new window size
        container_width = self.grid.parent().width() or 500  # Default to 500 if width is too small or zero
        num_images_per_row = 5
        self.max_label_size = max(container_width // num_images_per_row - 10, 100)  # Ensure a minimum size for the images

        self.updateGrid()  # Update the grid with the new size
        super(ImageGrid, self).resizeEvent(event)

    def load_image(self, img_path):
        if img_path.startswith('http://') or img_path.startswith('https://'):
            response = requests.get(img_path)
            image = QPixmap()
            image.loadFromData(response.content)
            return image
        else:
            return QPixmap(img_path)

    def updateGrid(self):
        # Clear existing widgets in the grid
        for i in reversed(range(self.grid.count())): 
            widget = self.grid.itemAt(i).widget()
            if widget is not None: 
                widget.deleteLater()

        start = self.page * self.page_size
        end = min(start + self.page_size, len(self.image_paths))

        container_width = self.grid.parent().width() or 500  # Provide a default width if the actual width is too small or zero
        num_images_per_row = 5
        max_label_size = max(container_width // num_images_per_row - 10, 100)  # Ensure a minimum size for the images


        for i, img_path in enumerate(self.image_paths[start:end], start=1):
            pixmap = self.load_image(img_path)
            label = ClickableLabel()
            label.setPixmap(pixmap.scaled(self.max_label_size, self.max_label_size, Qt.KeepAspectRatio))
            label.setMaximumSize(self.max_label_size, self.max_label_size)
            label.clicked.connect(lambda path=img_path: self.onImageClicked(path))
            self.grid.addWidget(label, (i - 1) // num_images_per_row, (i - 1) % num_images_per_row)

    def changePage(self, direction):
        new_page = self.page + direction
        max_page = (len(self.image_paths) - 1) // self.page_size
        if 0 <= new_page <= max_page:
            self.page = new_page
            self.updateGrid()
            self.page_number_label.setText(f"Page {self.page + 1}")  # Update page number label

    def onImageClicked(self, img_path):
        self.address_field.setText(img_path)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    image_paths = ['a1.png', 'a2.png', 'a3.png', 'a1.png', 'a2.png', 'a3.png']*10  # List of image paths or URLs
    ex = ImageGrid(image_paths)
    ex.show()
    sys.exit(app.exec_())