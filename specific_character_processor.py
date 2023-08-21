import time
import random
from PyQt6.QtCore import QThread, pyqtSignal
from functions_grimoire import get_single_character_info, save_image_to_character_folder, source_danbooru, source_safebooru, source_gelbooru, source_animepictures, source_deviantart, source_rule34xxx, invert_name, sanitize_string, get_anime_title_from_character_name, update_character_dictionary, look_up_character_dictionary
from config import AppConfig, AppState

class SpecificCharacterProcessor(QThread):
    overall_progress_signal = pyqtSignal(int)
    overall_description_signal = pyqtSignal(str)
    show_overall_progress_bar_signal = pyqtSignal()
    
    progress_signal = pyqtSignal(int)
    description_signal1 = pyqtSignal(str)
    description_signal2 = pyqtSignal(str)
    show_progress_bar_signal = pyqtSignal()
    
    nested_progress_signal = pyqtSignal(int)
    nested_description_signal = pyqtSignal(str)
    show_nested_progress_bar_signal = pyqtSignal()

    def __init__(self, character_number, parent=None):
        super().__init__(parent)
        self.character_number = character_number
        self.character = []
        self.anime_title = None
        self.anime_title_folder = None
        self.app_config = AppConfig()
        self.enabled_sources = self.app_config.count_enabled_sources()

    def run(self):
        self.character.clear()
        
        if self.enabled_sources > 1:
            self.show_overall_progress_bar_signal.emit()
            self.overall_progress_signal.emit(0)
            self.overall_description_signal.emit(f"<h3>Overall Progress</h3>")
        
        if self.app_config.state == AppState.DOWNLOAD_ONE_CHARACTER or self.app_config.state == AppState.DOWNLOAD_ALL_CHARACTERS:
            self.download_character()
        elif self.app_config.state == AppState.USE_LOCAL_IMAGES:
            self.use_local_images()
            
        if self.enabled_sources > 1:
            self.show_overall_progress_bar_signal.emit()
        
    def get_character_name(self):
        return self.character
    
    def get_anime_title(self):
        return self.anime_title_folder
    
    def use_local_images(self):
        try:
            int(self.character_number)
            print("Input value is number")
            self.character_number = look_up_character_dictionary(self.character_number)
        except ValueError:
            ## Print here just so this "except" works lmao
            print("Input value is text")
            
        self.anime_title_folder = None
        
        if self.character_number != None:
            self.anime_title_folder = get_anime_title_from_character_name(self.character_number)
            self.character = [self.character_number]
        
        if(self.anime_title_folder == None):
            self.description_signal1.emit(f"<h3>Anime - {self.anime_title}</h3>")
            self.description_signal2.emit(f"<h3>Waifu not found :(</h3>")
            time.sleep(random.uniform(2, 4))
            self.description_signal1.emit(f"<h3>Progress</h3>")
            self.description_signal2.emit(f"")
        
        self.progress_signal.emit(100)
        
    def download_character(self):
        character_info = self.get_character_info()
        
        self.process_character(character_info)
        
        self.progress_signal.emit(100)
            
    def get_character_info(self):
        character_name, image_url, self.anime_title, anime_title_english = get_single_character_info(self.character_number)
        return character_name, image_url, self.anime_title, anime_title_english
    
    def process_character(self, character_info):
        character_name, image_url, self.anime_title, anime_title_english = character_info
        if character_name and image_url:
            self.anime_title_folder = sanitize_string(self.anime_title)
            saved_image_filename = save_image_to_character_folder(image_url, self.anime_title_folder, character_name)
            self.character.append(character_name)
            
            if saved_image_filename:
                update_character_dictionary(character_name, self.character_number)
                self.description_signal1.emit(f"<h3>Anime - {self.anime_title}</h3>")
                self.description_signal2.emit(f"<h3>Waifu - {character_name}</h3>")
                self.process_additional_images(character_name, anime_title_english)
            else:
                self.handle_image_not_saved()
        else:
            self.handle_waifu_not_found()
            
    def process_additional_images(self, character_name, anime_title_english):
        processing = invert_name(character_name)
        processing = processing.replace(" ", "_")
        
        self.show_nested_progress_bar_signal.emit()
        self.nested_description_signal.emit(f"<h4>Additional Images Progress</h4>")
        
        search_term_a = processing
        search_term_b = (processing + "_(" + (self.anime_title.replace(" ", "_")) + ")")
        search_term_c = invert_name(processing.replace("_", " ")).replace(" ", "_")
        search_term_d = ((invert_name(processing.replace("_", " ")).replace(" ", "_")) + "_(" + (self.anime_title.replace(" ", "_")) + ")")
        
        retry_search_terms = [search_term_a, search_term_b, search_term_c, search_term_d]
        retry_search_terms_reduced = [search_term_d, search_term_b]
        
        if anime_title_english:
            extra_term_a = (processing + "_(" + (anime_title_english.replace(" ", "_")) + ")")
            extra_term_b = ((invert_name(processing.replace("_", " ")).replace(" ", "_")) + "_(" + (anime_title_english.replace(" ", "_")) + ")")
            
            retry_search_terms.extend([extra_term_a, extra_term_b])
            retry_search_terms_reduced.extend([extra_term_b, extra_term_a])
            
        retry_search_terms_per_source = {
            "danbooru": retry_search_terms,
            "safebooru": retry_search_terms,
            "animepictures": retry_search_terms,
            "gelbooru": retry_search_terms,
            "rule34xxx": retry_search_terms,
            "deviantart": retry_search_terms_reduced,
        }

        for index, source in enumerate(["danbooru", "safebooru", "animepictures", "gelbooru", "rule34xxx", "deviantart"]):
            if self.enabled_sources > 1:
                overall_progress_value = int((index + 1) / 6 * 100)
                self.overall_progress_signal.emit(overall_progress_value)
            
            if self.app_config.get_source_setting(source):
                self.description_signal2.emit(f"<h3>Waifu - {character_name} - Source: {source}</h3>")
                
                failed = True

                source_retry_search_terms = retry_search_terms_per_source.get(source, [])
                
                for retry_search_term in source_retry_search_terms:
                    source_function = globals()[f"source_{source}"]
                    if source_function(f"outputs\{self.anime_title_folder}", character_name, retry_search_term, self.nested_progress_signal, self.nested_description_signal):
                        failed = False
                        break
                    else:
                        self.nested_description_signal.emit(f"<h4>Retrying with the search term: {retry_search_term}.</h4>")

                if failed:
                    self.nested_description_signal.emit(f"<h4>Couldn't find images for this character in {source}.</h4>")
                    time.sleep(random.uniform(2, 4))
        
        self.show_nested_progress_bar_signal.emit()
        self.nested_description_signal.emit(f"")
        self.nested_progress_signal.emit(0)
    
    def handle_image_not_saved(self):
        self.description_signal1.emit(f"<h3>Image could not be saved</h3>")
        self.description_signal2.emit(f"<h3>:(</h3>")
        time.sleep(random.uniform(2, 4))

    def handle_waifu_not_found(self):
        self.description_signal1.emit(f"<h3>Anime - {self.anime_title}</h3>")
        self.description_signal2.emit(f"<h3>Waifu not found :(</h3>")
        time.sleep(random.uniform(2, 4))