from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QGridLayout, QScrollArea
from PyQt6.QtGui import QPixmap, QIcon

class SubfolderButtonWidget(QWidget):
    def __init__(self, subfolder_names, root_folder, option, show_options_callback=None, display_images_callback=None):
        super().__init__()

        self.option = option
        self.show_options_callback = show_options_callback
        self.display_images_callback = display_images_callback
        
        main_layout = QVBoxLayout()
        
        self.thumbnails_scroll_area = QScrollArea()
        self.thumbnails_scroll_area.setWidgetResizable(True)
        
        grid_layout = QGridLayout()
        row = 0
        column = 0

        for subfolder_name in subfolder_names:
            if display_images_callback:
                button = QPushButton()
                image_path = f"outputs/{root_folder}/{subfolder_name}/{subfolder_name}.jpg"
                pixmap_ico = QPixmap(image_path)
                pixmap_ico = pixmap_ico.scaled(180, 280, Qt.AspectRatioMode.KeepAspectRatio)
                icon = QIcon(pixmap_ico)
                button.setIcon(icon)
                button.setIconSize(QSize(180, 280))
                button.setStyleSheet("background-color: transparent; border: none;")
                button.clicked.connect(lambda checked, subfolder=subfolder_name, root=root_folder: self.handle_image_buttons(subfolder, root))
                grid_layout.addWidget(button, row, column)
                
                column += 1
                
                if column>2:
                    column = 0
                    row += 1

        if show_options_callback:
            self.back_button = QPushButton("Back")
            self.back_button.clicked.connect(self.handle_back_button)
            
        thumbnails_widget = QWidget()
        thumbnails_widget.setLayout(grid_layout)
        self.thumbnails_scroll_area.setWidget(thumbnails_widget)
        main_layout.addWidget(self.thumbnails_scroll_area)
        
        main_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        
        self.setLayout(main_layout)

    def handle_back_button(self):
        if self.show_options_callback:
            self.show_options_callback()
            
    def handle_image_buttons(self, subfolder, root):
        if self.display_images_callback:
            self.display_images_callback(subfolder, self.option, root)