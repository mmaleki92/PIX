import sys
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QLineEdit, QSlider
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtCore import Qt, pyqtSignal, QSize

class ClickableLabel(QLabel):
    clicked = pyqtSignal()

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

class ImageGrid(QWidget):
    def __init__(self, image_paths):
        super().__init__()
        self.max_label_size = 100  # Default image label size
        self.thumbnail_size = QSize(self.max_label_size, self.max_label_size)  # Size of thumbnails
        self.image_cache = {}  # Image caching

        self.initUI(image_paths)

    def initUI(self, image_paths):
        self.setGeometry(300, 300, 600, 400)
        self.setWindowTitle('Image Viewer')

        layout = QVBoxLayout(self)
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        container = QWidget()
        scroll_area.setWidget(container)
        self.grid = QGridLayout(container)

        self.page = 0
        self.page_size = 20
        self.image_paths = image_paths
        self.updateGrid()

        next_button = QPushButton('Next Page', self)
        next_button.clicked.connect(lambda: self.changePage(1))
        layout.addWidget(next_button)

        prev_button = QPushButton('Previous Page', self)
        prev_button.clicked.connect(lambda: self.changePage(-1))
        layout.addWidget(prev_button)

        self.page_number_label = QLabel(f"Page {self.page + 1}", self)
        self.page_number_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.page_number_label)

        self.address_field = QLineEdit(self)
        self.address_field.setReadOnly(True)
        layout.addWidget(self.address_field)

        self.copy_button = QPushButton("Copy to Clipboard", self)
        self.copy_button.clicked.connect(self.copyTextToClipboard)
        layout.addWidget(self.copy_button)
        # Adding a slider for zoom control
        self.zoom_slider = QSlider(Qt.Horizontal, self)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(500)
        self.zoom_slider.setValue(self.max_label_size)
        self.zoom_slider.valueChanged.connect(self.onSliderValueChanged)
        layout.addWidget(self.zoom_slider)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            zoom_factor = 10
            if delta > 0:  # Scrolled up
                self.max_label_size += zoom_factor
            elif delta < 0:  # Scrolled down
                self.max_label_size = max(self.max_label_size - zoom_factor, 10)
            self.updateGrid()
        self.zoom_slider.setValue(self.max_label_size)

    def onSliderValueChanged(self):
        self.max_label_size = self.zoom_slider.value()
        self.updateGrid()

    def copyTextToClipboard(self):
        text = self.address_field.text()
        QApplication.clipboard().setText(text)

    def load_image(self, img_path):
        if img_path not in self.image_cache:
            if img_path.startswith('http://') or img_path.startswith('https://'):
                response = requests.get(img_path)
                image = QPixmap()
                image.loadFromData(response.content)
            else:
                image = QPixmap(img_path)

            # Create a thumbnail of the image
            thumbnail = image.scaled(self.thumbnail_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_cache[img_path] = thumbnail

        return self.image_cache[img_path]

    def updateGrid(self):
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        start = self.page * self.page_size
        end = min(start + self.page_size, len(self.image_paths))

        container_width = self.grid.parent().width() or 500
        num_images_per_row = max(container_width // self.max_label_size, 1)

        for i, img_path in enumerate(self.image_paths[start:end], start=1):
            pixmap = self.load_image(img_path)
            label = ClickableLabel()
            
            # Maintain aspect ratio while fitting the image into max_label_size x max_label_size box
            scaled_pixmap = pixmap.scaled(self.max_label_size, self.max_label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(scaled_pixmap)

            # Set the label size to be square, but the image will maintain its aspect ratio
            label.setFixedSize(self.max_label_size, self.max_label_size)
            label.clicked.connect(lambda path=img_path: self.onImageClicked(path))
            row = (i - 1) // num_images_per_row
            col = (i - 1) % num_images_per_row
            self.grid.addWidget(label, row, col)


    def changePage(self, direction):
        new_page = self.page + direction
        max_page = (len(self.image_paths) - 1) // self.page_size
        if 0 <= new_page <= max_page:
            self.page = new_page
            self.updateGrid()
            self.page_number_label.setText(f"Page {self.page + 1}")

    def onImageClicked(self, img_path):
        self.address_field.setText(img_path)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    image_paths = ['a1.png', 'a2.png', 'a3.png', 'a1.png', 'a2.png', 'a3.png']*40  # List of image paths or URLs
    ex = ImageGrid(image_paths)
    ex.show()
    sys.exit(app.exec_())
