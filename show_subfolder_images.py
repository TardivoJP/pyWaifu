import glob
import os
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QGridLayout, QDialog, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QApplication, QHBoxLayout, QStackedLayout, QScrollArea
from PyQt6.QtGui import QPixmap, QIcon, QPainter
from video_player import VideoPlayer

class ThumbnailPreloadThread(QThread):
    thumbnail_loaded = pyqtSignal(QPixmap, int)

    def __init__(self, thumbnail_paths):
        super().__init__()
        self.thumbnail_paths = thumbnail_paths

    def run(self):
        for index, thumbnail_path in enumerate(self.thumbnail_paths):
            pixmap = QPixmap(thumbnail_path)
            pixmap = pixmap.scaled(180, 280, Qt.AspectRatioMode.KeepAspectRatio)
            self.thumbnail_loaded.emit(pixmap, index)

class ImageDisplayWidget(QWidget):
    def __init__(self, subfolder_name, anime_name, show_waifu_grid_callback=None):
        super().__init__()
        self.show_waifu_grid_callback = show_waifu_grid_callback

        main_layout = QVBoxLayout()
        
        self.thumbnails_scroll_area = QScrollArea()
        self.thumbnails_scroll_area.setWidgetResizable(True)
        
        if show_waifu_grid_callback:
            self.back_button = QPushButton("Back")
            self.back_button.clicked.connect(self.handle_back_button)
            
        self.grid_layout = QGridLayout()
        
        current_path = f"outputs/{anime_name}/{subfolder_name}/"
        self.display_paths = self.get_display_paths_in_subfolder(current_path, subfolder_name)
        self.thumbnail_paths = self.generate_thumbnail_paths(self.display_paths)
        
        self.preload_thread = ThumbnailPreloadThread(self.thumbnail_paths)
        self.preload_thread.thumbnail_loaded.connect(self.add_thumbnail_button)
        self.preload_thread.start()
            
        thumbnails_widget = QWidget()
        thumbnails_widget.setLayout(self.grid_layout)
        self.thumbnails_scroll_area.setWidget(thumbnails_widget)
        main_layout.addWidget(self.thumbnails_scroll_area)
        
        main_layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

        self.setLayout(main_layout)

    def handle_back_button(self):
        if self.show_waifu_grid_callback:
            self.show_waifu_grid_callback()
            
    def add_thumbnail_button(self, pixmap, index):
        button_img = QPushButton()
        icon_img = QIcon(pixmap)
        button_img.setIcon(icon_img)
        button_img.setIconSize(QSize(180, 280))
        button_img.setStyleSheet("background-color: transparent; border: none;")

        def create_lambda(idx):
            return lambda checked: self.open_full_size_image(idx)

        button_img.clicked.connect(create_lambda(index))
        self.grid_layout.addWidget(button_img, index // 3, index % 3)
            
    def get_display_paths_in_subfolder(self, current_path, subfolder_name):
        file_extensions = ["*.jpg", "*.jpeg", "*.svg", "*.png", "*.webp", "*.gif", "*.mp4", "*.avi", "*.mkv", "*.webm"]
        
        folder_image_name = f"{subfolder_name}.jpg"

        display_paths = (
            path
            for ext in file_extensions
            for path in glob.glob(os.path.join(current_path, ext))
            if os.path.basename(path) != folder_image_name and "_thumbnail" not in os.path.basename(path)
        )
        
        return list(display_paths)
    
    def generate_thumbnail_paths(self, image_paths):
        thumbnail_paths = []
        animated_extensions = {".mp4", ".avi", ".mkv", "*.webm"}
        
        for image_path in image_paths:
            base_path, ext = os.path.splitext(image_path)
            if ext in animated_extensions:
                ext = ".png"
            thumbnail_path = f"{base_path}_thumbnail{ext}"
            thumbnail_paths.append(thumbnail_path)
        
        return thumbnail_paths
    
    def open_full_size_image(self, index):
        screen = QApplication.primaryScreen()
        self.screen_geometry = screen.availableGeometry()

        self.full_size_dialog = QDialog(self)
        self.full_size_dialog.setWindowTitle("Full Size Display")
        self.full_size_dialog_layout = QVBoxLayout()
        self.full_size_dialog_stacked_layout = QStackedLayout()
        
        self.current_display_index = index
        self.current_file_extension = os.path.splitext(self.display_paths[self.current_display_index])[1].lower()

        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")

        self.navigation_layout = QHBoxLayout()
        self.navigation_layout.addWidget(self.prev_button)
        self.navigation_layout.addWidget(self.next_button)
        
        self.graphics_view = QGraphicsView()
        self.graphics_view.setInteractive(True)
        self.graphics_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        
        self.pixmap = QPixmap()
        self.pixmap_item = QGraphicsPixmapItem(self.pixmap)
        self.graphics_scene.addItem(self.pixmap_item)
        self.full_size_dialog_stacked_layout.addWidget(self.graphics_view)
        
        self.media_player = VideoPlayer()
        self.full_size_dialog_stacked_layout.addWidget(self.media_player)

        def update_display():
            nonlocal self
            
            self.media_player.stop_video()
            
            if self.current_file_extension in ['.mp4', '.avi', '.mkv', '.webm', '.gif']:
                video_path = self.display_paths[self.current_display_index]
                
                self.video_width, self.video_height = self.media_player.open_video(video_path)
                
                self.adjusted_width = min(self.video_width, int(self.screen_geometry.width() * 0.9))
                self.adjusted_height = min(self.video_height, int(self.screen_geometry.height() * 0.9))
                self.full_size_dialog.setGeometry(
                    (self.screen_geometry.width() - self.adjusted_width) // 2,
                    (self.screen_geometry.height() - self.adjusted_height) // 2,
                    self.adjusted_width, self.adjusted_height
                )
                
                self.full_size_dialog_stacked_layout.setCurrentWidget(self.media_player)
                    
            else:
                self.graphics_view.resetTransform()
                self.pixmap = QPixmap(self.display_paths[self.current_display_index])
                self.adjusted_width = min(self.pixmap.width(), int(self.screen_geometry.width() * 0.9))
                self.adjusted_height = min(self.pixmap.height(), int(self.screen_geometry.height() * 0.9))
                self.full_size_dialog.setGeometry(
                    (self.screen_geometry.width() - self.adjusted_width) // 2,
                    (self.screen_geometry.height() - self.adjusted_height) // 2,
                    self.adjusted_width, self.adjusted_height
                )
                
                width_scale = self.screen_geometry.width() * 0.85 / self.pixmap.width()
                height_scale = self.screen_geometry.height() * 0.85 / self.pixmap.height()
                scale_factor = min(width_scale, height_scale)
                self.graphics_view.scale(scale_factor, scale_factor)
                
                self.pixmap_item.setPixmap(self.pixmap) 
                self.graphics_view.setSceneRect(0, 0, self.pixmap.width(), self.pixmap.height())
                self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                self.full_size_dialog_stacked_layout.setCurrentWidget(self.graphics_view)

        def show_previous_display():
            nonlocal self
            self.current_display_index = (self.current_display_index - 1) % len(self.display_paths)
            self.current_file_extension = os.path.splitext(self.display_paths[self.current_display_index])[1].lower()
            update_display()

        def show_next_display():
            nonlocal self
            self.current_display_index = (self.current_display_index + 1) % len(self.display_paths)
            self.current_file_extension = os.path.splitext(self.display_paths[self.current_display_index])[1].lower()
            update_display()
            
        def handle_dialog_close():
            self.media_player.stop_video()

        self.prev_button.clicked.connect(show_previous_display)
        self.next_button.clicked.connect(show_next_display)

        self.full_size_dialog_layout.addLayout(self.full_size_dialog_stacked_layout)
        self.full_size_dialog_layout.addLayout(self.navigation_layout)
        self.full_size_dialog.setLayout(self.full_size_dialog_layout)

        update_display()
        
        self.graphics_view.wheelEvent = self.zoom_full_size_image

        self.full_size_dialog.finished.connect(handle_dialog_close)
        self.full_size_dialog.exec()
        
    def zoom_full_size_image(self, event):
        factor = 1.2

        if event.angleDelta().y() > 0:
            self.graphics_view.scale(factor, factor)
        else:
            self.graphics_view.scale(1 / factor, 1 / factor)