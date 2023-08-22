import os
import sys
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QElapsedTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QStackedLayout, QProgressBar, QRadioButton, QButtonGroup, QSpacerItem, QSizePolicy, QCheckBox
from PyQt6.QtGui import QPixmap, QGuiApplication, QIcon
from anime_list_processor import AnimeListProcessor
from specific_anime_processor import SpecificAnimeProcessor
from specific_character_processor import SpecificCharacterProcessor
from show_subfolders import SubfolderButtonWidget
from show_subfolder_images import ImageDisplayWidget
from show_all_subfolders import AllSubfolderButtonWidget
from config import AppConfig, AppState

## This somehow avoids a crash that only happens when the generated executable from pyInstaller is ran if it had the "--noconsole" argument when creating it
## Don't ask me how or why does that even work, I'm as baffled as you are reading this

## You may remove or comment this if you're running the scripts themselves instead of the built application

# Redirect stdout and stderr to a log file before anything else is done in the application
log_file = open('application_log.log', 'w')
sys.stdout = log_file
sys.stderr = log_file

class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        ## Some PyInstaller file path handler stuff
        if getattr(sys, 'frozen', False):
            # Running as a PyInstaller executable
            base_path = sys._MEIPASS
        else:
            # Running as a script
            base_path = os.path.abspath(".")
        
        self.subfolder_widget = None
        self.subfolder_images_widget = None
        
        self.app_config = AppConfig()

        self.setWindowTitle("pyWaifu")
        self.setWindowIcon(QIcon(os.path.join(base_path, 'resources', 'waifu.png')))
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout(self.central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter) 

        # Application Header
        title_label = QLabel("<h1>pyWaifu</h1>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)


        # Hero image layout
        ## (Note: I don't know if this is a hero image or not, just pulling fancy terms out of my ass)
        image_label = QLabel()
        pixmap = QPixmap(os.path.join(base_path, 'resources', 'img.png'))
        screen = QGuiApplication.primaryScreen()
        screen_size = screen.availableSize()
        image_width = int(screen_size.width() * 0.35)
        image_height = int(screen_size.height() * 0.30)
        self.scaled_pixmap = pixmap.scaled(image_width, image_height, Qt.AspectRatioMode.KeepAspectRatio)
        image_label.setPixmap(self.scaled_pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        
        # Stacked layout
        self.stacked_layout = QStackedLayout()
        
        # First stacked view: Main Menu
        ## Body/Content Vbox
        ## Anime list input
        choices_layout = QVBoxLayout()
        choices_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        choices_layout.addWidget(QLabel("Complete list"))
        self.choice1_input = QLineEdit()
        self.choice1_input.setPlaceholderText("https://myanimelist.net/animelist/[USER_NAME]")
        choices_layout.addWidget(self.choice1_input)
        self.button_script_anime_list = QPushButton("Find waifus")
        self.button_script_anime_list.clicked.connect(self.run_script_anime_list)
        choices_layout.addWidget(self.button_script_anime_list)    
        choices_layout.addSpacing(20)
        
        ## Specific anime input
        choices_layout.addWidget(QLabel("Specific show"))
        self.choice2_input = QLineEdit()
        self.choice2_input.setPlaceholderText("https://myanimelist.net/anime/[ANIME_ID]")
        choices_layout.addWidget(self.choice2_input)
        self.button_script_specific_show = QPushButton("Find waifu")
        self.button_script_specific_show.clicked.connect(self.run_script_specific_show)
        choices_layout.addWidget(self.button_script_specific_show)
        choices_layout.addSpacing(20)
        
        ## Specific character input
        choices_layout.addWidget(QLabel("Specific character"))
        self.choice3_input = QLineEdit()
        self.choice3_input.setPlaceholderText("https://myanimelist.net/character/[CHARACTER_ID]")
        choices_layout.addWidget(self.choice3_input)
        self.button_script_specific_character = QPushButton("Find waifu")
        self.button_script_specific_character.clicked.connect(self.run_script_specific_character)
        choices_layout.addWidget(self.button_script_specific_character)
        choices_layout.addSpacing(20)
        
        ## Footer
        choices_bottom = QHBoxLayout()
        choices_bottom.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.button_script_show_all_waifus = (QPushButton("Waifus"))
        self.button_script_show_all_waifus.clicked.connect(self.run_script_show_all_waifus)
        choices_bottom.addWidget(self.button_script_show_all_waifus)
        self.button_script_show_options_menu = (QPushButton("Options"))
        self.button_script_show_options_menu.clicked.connect(self.show_options_menu)
        choices_bottom.addWidget(self.button_script_show_options_menu)
        choices_layout.addLayout(choices_bottom)
        
        
        ## Finalizing main menu layout into a widget
        self.main_menu_container = QWidget()
        self.main_menu_container.setLayout(choices_layout)
        self.main_menu_container.setFixedWidth(int(self.scaled_pixmap.width() * 1.2))
        
        
        # Second stacked view: Progress bar
        progress_bar_layout = QVBoxLayout()
        progress_bar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        ## Elapsed timer
        self.elapsed_time_label = QLabel("Elapsed time - 00:00:00")
        self.elapsed_time_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        progress_bar_layout.addWidget(self.elapsed_time_label)
        
        self.elapsed_timer = QElapsedTimer()
        self.elapsed_time_timer = QTimer()
        self.elapsed_time_timer.timeout.connect(self.update_elapsed_time)
        
        ## Overall progress bar (only shown in certain behaviors)
        self.overall_description_label = QLabel()
        self.overall_description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_bar_layout.addWidget(self.overall_description_label)
        self.overall_description_label.setVisible(False)
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.overall_progress_bar.setMinimum(0)
        self.overall_progress_bar.setMaximum(100)
        progress_bar_layout.addWidget(self.overall_progress_bar)
        self.overall_progress_bar.setVisible(False)
        progress_bar_layout.addSpacing(10)
        
        ## Progress bar (almost always shown)
        self.description_label1 = QLabel()
        self.description_label1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_bar_layout.addWidget(self.description_label1)
        self.description_label2 = QLabel()
        self.description_label2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_bar_layout.addWidget(self.description_label2)
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        progress_bar_layout.addWidget(self.progress_bar)
        progress_bar_layout.addSpacing(10)
        
        ## Nested progress bar (conditionally shown depending on operations)
        self.nested_description_label = QLabel()
        self.nested_description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nested_description_label.setVisible(False)
        progress_bar_layout.addWidget(self.nested_description_label)
        self.nested_progress_bar = QProgressBar()
        self.nested_progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nested_progress_bar.setMinimum(0)
        self.nested_progress_bar.setMaximum(100)
        self.nested_progress_bar.setVisible(False)
        progress_bar_layout.addWidget(self.nested_progress_bar)
        
        
        ## Finalizing progress bar layout into a widget
        self.progress_bar_container = QWidget()
        self.progress_bar_container.setLayout(progress_bar_layout)
        self.progress_bar_container.setFixedWidth(int(self.scaled_pixmap.width() * 1.2))
        
        
        # Third stacked view: Options Menu
        ## Header
        options_menu_layout = QVBoxLayout()
        options_menu_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        options_menu_label1 = QLabel("<h3>Options</h3>")
        options_menu_label1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        options_menu_layout.addWidget(options_menu_label1)
        options_menu_layout.addSpacing(20)
        
        ## Body/Content Hbox
        options_menu_settings_container = QWidget()
        options_menu_settings_layout = QHBoxLayout()
        options_menu_settings_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        ## Download behavior options
        options_menu_download_behavior_container = QWidget()
        options_menu_download_behavior_layout = QVBoxLayout()
        options_menu_download_behavior_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        options_menu_behavior_label = QLabel("<h4>Download Behavior</h4>")
        options_menu_behavior_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        options_menu_download_behavior_layout.addWidget(options_menu_behavior_label)
        options_menu_download_behavior_layout.addSpacing(10)
        
        self.download_one_character_button = QRadioButton("First female character per show")
        self.download_one_character_button.setChecked(True)
        self.download_all_characters_button = QRadioButton("All female characters per show")
        self.use_local_images_button = QRadioButton("Skip downloads and use local images")
        
        self.toggle_group = QButtonGroup()
        self.toggle_group.addButton(self.download_one_character_button)
        self.toggle_group.addButton(self.download_all_characters_button)
        self.toggle_group.addButton(self.use_local_images_button)

        self.download_one_character_button.clicked.connect(lambda: self.app_config.set_state(AppState.DOWNLOAD_ONE_CHARACTER))
        self.download_all_characters_button.clicked.connect(lambda: self.app_config.set_state(AppState.DOWNLOAD_ALL_CHARACTERS))
        self.use_local_images_button.clicked.connect(lambda: self.app_config.set_state(AppState.USE_LOCAL_IMAGES))

        options_menu_download_behavior_layout.addWidget(self.download_one_character_button)
        options_menu_download_behavior_layout.addWidget(self.download_all_characters_button)
        options_menu_download_behavior_layout.addWidget(self.use_local_images_button)
        
        options_menu_download_behavior_container.setLayout(options_menu_download_behavior_layout)
        options_menu_settings_layout.addWidget(options_menu_download_behavior_container)
        
        ## Download sources options
        options_menu_download_sources_container = QWidget()
        options_menu_download_sources_layout = QVBoxLayout()
        options_menu_download_sources_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        options_menu_sources_label = QLabel("<h4>Sources</h4>")
        options_menu_sources_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        options_menu_download_sources_layout.addWidget(options_menu_sources_label)
        options_menu_download_sources_layout.addSpacing(10)
        
        self.source_A_check_box = QCheckBox("Safebooru")
        self.source_A_check_box.setChecked(True)
        self.source_B_check_box = QCheckBox("Anime-Pictures net")
        
        self.options_menu_sources_nsfw_warning_label = ClickableLabel("<h4>NSFW?</h4>")
        self.options_menu_sources_nsfw_warning_label.setStyleSheet("color: black;")
        self.options_menu_sources_nsfw_warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.source_C_check_box = QCheckBox("Danbooru")
        self.source_C_check_box.setVisible(False)
        self.source_D_check_box = QCheckBox("Gelbooru")
        self.source_D_check_box.setVisible(False)
        self.source_E_check_box = QCheckBox("Rule34 XXX")
        self.source_E_check_box.setVisible(False)
        self.source_F_check_box = QCheckBox("DeviantArt")
        self.source_F_check_box.setVisible(False)

        self.source_A_check_box.clicked.connect(lambda: self.app_config.change_source_setting_state("safebooru"))
        self.source_B_check_box.clicked.connect(lambda: self.app_config.change_source_setting_state("animepictures"))
        self.source_C_check_box.clicked.connect(lambda: self.app_config.change_source_setting_state("danbooru"))
        self.source_D_check_box.clicked.connect(lambda: self.app_config.change_source_setting_state("gelbooru"))
        self.source_E_check_box.clicked.connect(lambda: self.app_config.change_source_setting_state("rule34xxx"))
        self.source_F_check_box.clicked.connect(lambda: self.app_config.change_source_setting_state("deviantart"))
        
        self.options_menu_sources_nsfw_warning_label.clicked.connect(self.change_nsfw_sources_visibility)

        options_menu_download_sources_layout.addWidget(self.source_A_check_box)
        options_menu_download_sources_layout.addWidget(self.source_B_check_box)
        options_menu_download_sources_layout.addSpacing(5)
        options_menu_download_sources_layout.addWidget(self.options_menu_sources_nsfw_warning_label)
        options_menu_download_sources_layout.addSpacing(5)
        options_menu_download_sources_layout.addWidget(self.source_C_check_box)
        options_menu_download_sources_layout.addWidget(self.source_D_check_box)
        options_menu_download_sources_layout.addWidget(self.source_E_check_box)
        options_menu_download_sources_layout.addWidget(self.source_F_check_box)
        
        options_menu_download_sources_container.setLayout(options_menu_download_sources_layout)
        options_menu_settings_layout.addWidget(options_menu_download_sources_container)
        
        options_menu_settings_container.setLayout(options_menu_settings_layout)
        options_menu_layout.addWidget(options_menu_settings_container)
        options_menu_layout.addSpacing(20)
        
        ## Footer
        options_menu_back_button = QPushButton("Back")
        options_menu_back_button.clicked.connect(self.show_main_menu)
        options_menu_layout.addWidget(options_menu_back_button)
        
        
        ## Finalizing options menu layout into a widget
        self.options_menu_layout_container = QWidget()
        self.options_menu_layout_container.setLayout(options_menu_layout)
        self.options_menu_layout_container.setFixedWidth(int(self.scaled_pixmap.width() * 1.2))
        
        
        ## Adding all 3 views to stacked layout
        self.stacked_layout.addWidget(self.main_menu_container)
        self.stacked_layout.addWidget(self.progress_bar_container)
        self.stacked_layout.addWidget(self.options_menu_layout_container)
        self.stacked_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        ## Finalizing stacked layout into a widget
        self.stacked_layout_widget = QWidget()
        self.stacked_layout_widget.setLayout(self.stacked_layout)


        ## Finalizing widgets into main application layout
        self.main_application_layout = QHBoxLayout()
        
        left_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.main_application_layout.addItem(left_spacer)
        
        self.main_application_layout.addWidget(image_label)
        self.main_application_layout.addWidget(self.stacked_layout_widget)
        
        right_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.main_application_layout.addItem(right_spacer)
        self.main_application_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addLayout(self.main_application_layout)
        
        self.show()
        self.center_on_screen()
    
    ## Functions (mostly related to what the user sees)
    ## (Note: I'm feeling a little lazy to go over every single one of them but they should be self explanatory enough)
    def center_on_screen(self):
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        
        center_x = int((screen_geometry.width() - self.width()) / 2)
        center_y = int((screen_geometry.height() - self.height()) / 2.5)
        
        self.move(center_x, center_y)
    
    def show_progress_bar(self):
        self.stacked_layout.setCurrentWidget(self.progress_bar_container)
        self.elapsed_timer.start()
        self.elapsed_time_timer.start(1000)

    def show_main_menu(self):
        self.stacked_layout.setCurrentWidget(self.main_menu_container)
        self.destroy_subfolder_widget()
        self.destroy_subfolder_image_display_widget()
        self.reset_progress_bar_labels()
        
    def show_waifu_grid(self):
        self.stacked_layout.setCurrentWidget(self.subfolder_widget)
        
    def show_options_menu(self):
        self.stacked_layout.setCurrentWidget(self.options_menu_layout_container)
        
    def update_elapsed_time(self):
        elapsed_time_msecs = self.elapsed_timer.elapsed()
        hours = elapsed_time_msecs // 3600000
        minutes = (elapsed_time_msecs % 3600000) // 60000
        seconds = (elapsed_time_msecs % 60000) // 1000
        elapsed_time_str = f"Elapsed time - {hours:02}:{minutes:02}:{seconds:02}"
        self.elapsed_time_label.setText(elapsed_time_str)
        
    def change_nsfw_sources_visibility(self):
        if(self.source_C_check_box.isVisible()):
            self.options_menu_sources_nsfw_warning_label.setText("<h4>NSFW?</h4>")
            self.options_menu_sources_nsfw_warning_label.setStyleSheet("color: black;")
        else:
            self.options_menu_sources_nsfw_warning_label.setText("<h4>NSFW!</h4>")
            self.options_menu_sources_nsfw_warning_label.setStyleSheet("color: red;")
        self.source_C_check_box.setVisible(not self.source_C_check_box.isVisible())
        self.source_D_check_box.setVisible(not self.source_D_check_box.isVisible())
        self.source_E_check_box.setVisible(not self.source_E_check_box.isVisible())
        self.source_F_check_box.setVisible(not self.source_F_check_box.isVisible())
        
    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)
        
    def update_description_label1(self, description):
        self.description_label1.setText(description)
        
    def update_description_label2(self, description):
        self.description_label2.setText(description)
        
    def change_progress_bar_state(self):
        self.progress_bar.setVisible(not self.progress_bar.isVisible())
        
    def update_nested_progress_bar(self, value):
        self.nested_progress_bar.setValue(value)
        
    def update_nested_description_label(self, description):
        self.nested_description_label.setText(description)
        
    def change_nested_progress_bar_state(self):
        self.nested_description_label.setVisible(not self.nested_description_label.isVisible())
        self.nested_progress_bar.setVisible(not self.nested_progress_bar.isVisible())
        
    def update_overall_progress_bar(self, value):
        self.overall_progress_bar.setValue(value)
        
    def update_overall_description_label(self, description):
        self.overall_description_label.setText(description)
        
    def change_overall_progress_bar_state(self):
        self.overall_description_label.setVisible(not self.overall_description_label.isVisible())
        self.overall_progress_bar.setVisible(not self.overall_progress_bar.isVisible())
        
    def reset_progress_bar_labels(self):
        self.overall_progress_bar.setValue(0)
        self.progress_bar.setValue(0)
        self.nested_progress_bar.setValue(0)
        self.overall_description_label.setText("")
        self.description_label1.setText("")
        self.description_label2.setText("")
        self.nested_description_label.setText("")
        
    def run_script(self, processor_class, button_widget_class, input_field_text):
        self.show_progress_bar()
        self.progress_bar.setValue(0)
        
        self.processor = processor_class(input_field_text)
        
        if processor_class != AnimeListProcessor:
            self.progress_bar.setVisible(False)
            
        self.processor.overall_progress_signal.connect(self.update_overall_progress_bar)
        self.processor.overall_description_signal.connect(self.update_overall_description_label)
        self.processor.show_overall_progress_bar_signal.connect(self.change_overall_progress_bar_state)
        self.processor.progress_signal.connect(self.update_progress_bar)
        self.processor.description_signal1.connect(self.update_description_label1)
        self.processor.description_signal2.connect(self.update_description_label2)
        self.processor.show_progress_bar_signal.connect(self.change_progress_bar_state)
        self.processor.nested_progress_signal.connect(self.update_nested_progress_bar)
        self.processor.nested_description_signal.connect(self.update_nested_description_label)
        self.processor.show_nested_progress_bar_signal.connect(self.change_nested_progress_bar_state)
            
        self.processor.finished.connect(lambda: self.script_finished(processor_class, button_widget_class))
        self.processor.start()

    def script_finished(self, processor_class, button_widget_class):
        self.destroy_subfolder_widget()
        
        if processor_class != AnimeListProcessor:
            self.progress_bar.setVisible(True)
            subfolder_name = self.processor.get_character_name()
            anime_title = self.processor.get_anime_title()
            
            if(len(subfolder_name) == 0 or anime_title == None):
                self.show_main_menu()
                return
            
            self.subfolder_widget = button_widget_class(subfolder_name, anime_title, 2, self.show_main_menu, self.display_subfolder_images)
        else:
            subfolder_names = self.processor.get_character_names()
            anime_titles = self.processor.get_anime_titles()
                
            if(subfolder_names == None):
                self.show_main_menu()
                return
                
            if(len(subfolder_names) == 0):
                self.show_main_menu()
                return
            
            self.subfolder_widget = button_widget_class(subfolder_names, anime_titles, 3, self.show_main_menu, self.display_subfolder_images)
            
        self.subfolder_widget.setFixedWidth(int(180 * 3.5))
        
        self.stacked_layout.addWidget(self.subfolder_widget)
        self.stacked_layout.setCurrentWidget(self.subfolder_widget)

    def run_script_anime_list(self):
        self.run_script(AnimeListProcessor, AllSubfolderButtonWidget, self.choice1_input.text())

    def run_script_specific_show(self):
        self.run_script(SpecificAnimeProcessor, SubfolderButtonWidget, self.choice2_input.text())

    def run_script_specific_character(self):
        self.run_script(SpecificCharacterProcessor, SubfolderButtonWidget, self.choice3_input.text())
        
    def run_script_show_all_waifus(self):
        anime_titles = []

        if os.path.exists("outputs") and os.path.isdir("outputs"):
            anime_titles = [anime_title for anime_title in os.listdir("outputs") if os.path.isdir(os.path.join("outputs", anime_title))]
        
        subfolder_set = set()
        
        for subfolder_name in anime_titles:
            subfolder_path = os.path.join("outputs", subfolder_name)
            if os.path.exists(subfolder_path) and os.path.isdir(subfolder_path):
                subfolders = [name for name in os.listdir(subfolder_path) if os.path.isdir(os.path.join(subfolder_path, name))]
                subfolder_set.update(subfolders)
        
        subfolder_list = list(subfolder_set)
        
        if(len(anime_titles) == 0 or len(subfolder_list) == 0):
            self.show_main_menu()
            return
        
        self.subfolder_widget = AllSubfolderButtonWidget(subfolder_list, anime_titles, 3, self.show_main_menu, self.display_subfolder_images)
        self.subfolder_widget.setFixedWidth(int(180 * 3.5))
        
        self.stacked_layout.addWidget(self.subfolder_widget)
        self.stacked_layout.setCurrentWidget(self.subfolder_widget)
    
    def destroy_subfolder_widget(self):
        if self.subfolder_widget:
            self.subfolder_widget.deleteLater()
            self.stacked_layout.removeWidget(self.subfolder_widget)
            self.subfolder_widget.deleteLater()
            self.subfolder_widget = None
            
    def display_subfolder_images(self, subfolder_name, opt, root_name=None):
        self.destroy_subfolder_image_display_widget()
        
        match opt:
            case 2:
                self.subfolder_images_widget = ImageDisplayWidget(subfolder_name, root_name, self.show_waifu_grid)
            case 3:
                self.subfolder_images_widget = ImageDisplayWidget(subfolder_name, root_name, self.show_waifu_grid)
        
        self.subfolder_images_widget.setFixedWidth(int(180 * 3.5))
        
        self.stacked_layout.addWidget(self.subfolder_images_widget)
        self.stacked_layout.setCurrentWidget(self.subfolder_images_widget)

    def destroy_subfolder_image_display_widget(self):
        if self.subfolder_images_widget:
            self.subfolder_images_widget.deleteLater()
            self.stacked_layout.removeWidget(self.subfolder_images_widget)
            self.subfolder_images_widget.deleteLater()
            self.subfolder_images_widget = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())