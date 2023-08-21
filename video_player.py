import os
import sys
from PyQt6.QtCore import Qt, QUrl, QTime, QPropertyAnimation, QEasingCurve, QEvent
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QVBoxLayout, QPushButton, QWidget, QProgressBar, QHBoxLayout, QLabel
from PyQt6.QtMultimedia import QMediaPlayer, QMediaMetaData, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

class VideoPlayer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout()

        self.video_widget = QVideoWidget()
        layout.addWidget(self.video_widget)

        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setLoops(QMediaPlayer.Loops.Infinite)
        
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        controls_box = QHBoxLayout()
        
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        
        self.backwards_icon = QIcon(os.path.join(base_path, 'resources', 'Backwards-BTN.svg'))
        self.backwards_icon_clicked = QIcon(os.path.join(base_path, 'resources', 'Backwards-BTN-CLK.svg'))
        self.forwards_icon = QIcon(os.path.join(base_path, 'resources', 'Forwards-BTN.svg'))
        self.forwards_icon_clicked  = QIcon(os.path.join(base_path, 'resources', 'Forwards-BTN-CLK.svg'))
        self.pause_icon = QIcon(os.path.join(base_path, 'resources', 'Pause-BTN.svg'))
        self.pause_icon_clicked = QIcon(os.path.join(base_path, 'resources', 'Pause-BTN-CLK.svg'))
        self.play_icon = QIcon(os.path.join(base_path, 'resources', 'Play-BTN.svg'))
        self.play_icon_clicked = QIcon(os.path.join(base_path, 'resources', 'Play-BTN-CLK.svg'))
        self.stop_icon = QIcon(os.path.join(base_path, 'resources', 'Stop-BTN.svg'))
        self.stop_icon_clicked = QIcon(os.path.join(base_path, 'resources', 'Stop-BTN-CLK.svg'))

        self.pause_button = QPushButton()
        self.pause_button.setIcon(self.pause_icon_clicked)
        self.pause_button.setStyleSheet("background-color: transparent; border: none;")
        self.setup_button_animation(self.pause_button)
        self.pause_button.clicked.connect(self.pause_video)
        controls_box.addWidget(self.pause_button)

        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.stop_icon_clicked)
        self.stop_button.setStyleSheet("background-color: transparent; border: none;")
        self.setup_button_animation(self.stop_button)
        self.stop_button.clicked.connect(self.stop_video)
        controls_box.addWidget(self.stop_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMouseTracking(True)
        
        self.progress_bar.setStyleSheet(
            "QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop: 0 blue, stop: 1 green); }"
        )
        
        self.progress_bar.mousePressEvent = self.progress_bar_mouse_press_event
        controls_box.addWidget(self.progress_bar)
        
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        
        self.time_label = QLabel()
        self.time_label.setText("00:00 / 00:00")
        self.time_label.setFixedHeight(10)
        controls_box.addWidget(self.time_label)
        
        layout.addLayout(controls_box)
        
        self.setLayout(layout)

    def open_video(self, path):
        if path:
            video_url = QUrl.fromLocalFile(path)
            empty_url = QUrl.fromLocalFile("")
            self.media_player.setSource(empty_url)
            self.media_player.setSource(video_url)
            
            video_resolution = self.media_player.metaData().value(QMediaMetaData.Key.Resolution)
            video_width = video_resolution.width()
            video_height = video_resolution.height()

            self.media_player.play()
            
            return video_width, video_height

    def pause_video(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.pause_button.setIcon(self.play_icon_clicked)
        elif self.media_player.playbackState() == QMediaPlayer.PlaybackState.PausedState or QMediaPlayer.PlaybackState.StoppedState:
            self.media_player.play()
            self.pause_button.setIcon(self.pause_icon_clicked)

    def stop_video(self):
        self.media_player.setPosition(0)
        self.pause_button.setIcon(self.play_icon_clicked)
        self.media_player.stop()

    def position_changed(self, position):
        self.progress_bar.setValue(position)
        
        current_time = QTime(0, position // 60000, (position // 1000) % 60)
        total_time = QTime(0, self.media_player.duration() // 60000, (self.media_player.duration() // 1000) % 60)
        self.time_label.setText(f"{current_time.toString('mm:ss')} / {total_time.toString('mm:ss')}")

    def duration_changed(self, duration):
        self.progress_bar.setMaximum(duration)

    def progress_bar_mouse_press_event(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            position = event.pos().x() / self.progress_bar.width() * self.media_player.duration()
            self.media_player.setPosition(int(position))
            self.pause_button.setIcon(self.pause_icon_clicked)
            self.media_player.play()
            
    def setup_button_animation(self, button):
        hover_animation = QPropertyAnimation(button, b"iconSize")
        hover_animation.setStartValue(button.iconSize())
        hover_animation.setEndValue(button.iconSize() * 1.3)
        hover_animation.setDuration(100)
        hover_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        button.installEventFilter(self)

        revert_hover_animation = QPropertyAnimation(button, b"iconSize")
        revert_hover_animation.setStartValue(button.iconSize()* 1.3)
        revert_hover_animation.setEndValue(button.iconSize())
        revert_hover_animation.setDuration(100)
        revert_hover_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        button.revert_hover_animation = revert_hover_animation

        click_animation = QPropertyAnimation(button, b"iconSize")
        click_animation.setDuration(150)
        click_animation.setStartValue(button.iconSize())
        click_animation.setEndValue(button.iconSize() * 1.5)
        click_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        button.clicked.connect(lambda: click_animation.start())

        button.hover_animation = hover_animation
        button.click_animation = click_animation

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            obj.hover_animation.start()
        elif event.type() == QEvent.Type.Leave:
            obj.revert_hover_animation.start()
        return super().eventFilter(obj, event)