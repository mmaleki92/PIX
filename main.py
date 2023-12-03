import sys
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QGridLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QLineEdit, QSlider, QCheckBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtWidgets import QSplitter

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
        self.max_label_size = 100
        self.thumbnail_size = QSize(self.max_label_size, self.max_label_size)
        self.image_cache = {}
        self.use_thumbnails = True  # Default to using thumbnails
        self.initUI(image_paths)

    def initUI(self, image_paths):
        # Main layout is now horizontal
                # Use QSplitter for resizable grid and sidebar
        main_layout = QHBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
                              

        # Container for the grid and its controls
        grid_container = QWidget()
        grid_layout = QVBoxLayout(grid_container)
        splitter.addWidget(grid_container)
        
        self.setGeometry(300, 300, 600, 400)
        self.setWindowTitle('Image Viewer')

        # Scroll Area for the thumbnails
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        grid_layout.addWidget(scroll_area)
        container = QWidget()
        scroll_area.setWidget(container)
        self.grid = QGridLayout(container)

        # Pagination controls
        self.page = 0
        self.page_size = 20
        self.image_paths = image_paths
        self.updateGrid()

        next_button = QPushButton('Next Page', self)
        next_button.clicked.connect(lambda: self.changePage(1))
        grid_layout.addWidget(next_button)

        prev_button = QPushButton('Previous Page', self)
        prev_button.clicked.connect(lambda: self.changePage(-1))
        grid_layout.addWidget(prev_button)

        # Page number label
        self.page_number_label = QLabel(f"Page {self.page + 1}", self)
        self.page_number_label.setAlignment(Qt.AlignCenter)
        grid_layout.addWidget(self.page_number_label)

        # Address field for the selected image
        self.address_field = QLineEdit(self)
        self.address_field.setReadOnly(True)
        grid_layout.addWidget(self.address_field)

        # Button to copy the image path to the clipboard
        self.copy_button = QPushButton("Copy to Clipboard", self)
        self.copy_button.clicked.connect(self.copyTextToClipboard)
        grid_layout.addWidget(self.copy_button)

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

        # Sidebar for full-size image display
        self.full_size_image_label = QLabel()
        self.full_size_image_label.setAlignment(Qt.AlignCenter)
        splitter.addWidget(self.full_size_image_label)

        # Set a minimum width for the sidebar
        # Optionally set a minimum size for the grid_container and full_size_image_label
        grid_container.setMinimumWidth(300)
        self.full_size_image_label.setMinimumWidth(200)

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

    def toggleThumbnails(self, state):
        self.use_thumbnails = bool(state)
        self.updateGrid()

    def onSliderValueChanged(self):
        self.max_label_size = self.zoom_slider.value()
        self.thumbnail_size = QSize(self.max_label_size, self.max_label_size)
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

            self.image_cache[img_path] = image

        return self.image_cache[img_path]


    def updateGrid(self):
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        start = self.page * self.page_size
        end = min(start + self.page_size, len(self.image_paths))

        container_width = self.grid.parent().width() or 500
        self.num_images_per_row = max(container_width // self.max_label_size, 1)

        for i, img_path in enumerate(self.image_paths[start:end], start=1):
            pixmap = self.load_image(img_path)

            # Determine if we should use thumbnails
            if self.use_thumbnails:
                # Resize according to the current zoom level
                scaled_pixmap = pixmap.scaled(self.max_label_size, self.max_label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                # Use the original size if not using thumbnails
                scaled_pixmap = pixmap

            label = ClickableLabel(img_path)
            label.setPixmap(scaled_pixmap)
            label.setFixedSize(self.max_label_size, self.max_label_size)
            label.clicked.connect(lambda path=img_path: self.onImageClicked(path))
            row = (i - 1) // self.num_images_per_row
            col = (i - 1) % self.num_images_per_row
            self.grid.addWidget(label, row, col)


    def changePage(self, direction):
        new_page = self.page + direction
        max_page = (len(self.image_paths) - 1) // self.page_size
        if 0 <= new_page <= max_page:
            self.page = new_page
            self.updateGrid()
            self.page_number_label.setText(f"Page {self.page + 1}")

    def onImageClicked(self, img_path):
        # Load the full-size image
        full_image = self.load_image(img_path)
        # Update the label in the sidebar with the full-size image
        self.full_size_image_label.setPixmap(full_image.scaled(self.full_size_image_label.width(), self.full_size_image_label.height(), Qt.KeepAspectRatio))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    image_paths = ['a1.png', 'a2.png', 'a3.png', 'a1.png', 'a2.png', 'a3.png']*40  # List of image paths or URLs
    ex = ImageGrid(image_paths)
    ex.show()
    sys.exit(app.exec_())
