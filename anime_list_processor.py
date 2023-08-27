import time
import json
import requests
import random
from bs4 import BeautifulSoup
from tqdm import tqdm
from PyQt6.QtCore import QThread, pyqtSignal
from functions_grimoire import extract_useful_bit_from_link, create_user_folder, get_main_female_character_info, get_all_female_character_info, save_image_and_info, source_danbooru, source_danbooru_api, source_safebooru, source_gelbooru, source_animepictures, source_deviantart, source_rule34xxx, invert_name, sanitize_string, extract_anime_info, update_anime_dictionary, update_character_dictionary
from config import AppConfig, AppState

class AnimeListProcessor(QThread):
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

    def __init__(self, user_name, parent=None):
        super().__init__(parent)
        self.user_name = user_name
        self.character_names = set()
        self.anime_titles = set()
        self.app_config = AppConfig()

    def run(self):
        if self.app_config.state == AppState.DOWNLOAD_ONE_CHARACTER or self.app_config.state == AppState.DOWNLOAD_ALL_CHARACTERS:
            self.user_name = extract_useful_bit_from_link(self.user_name, "list")
            self.get_list_info()
        elif self.app_config.state == AppState.USE_LOCAL_IMAGES:
            self.use_local_images()
            
    def get_character_names(self):
        if self.app_config.state == AppState.DOWNLOAD_ONE_CHARACTER or self.app_config.state == AppState.DOWNLOAD_ALL_CHARACTERS:
            return list(self.character_names)
        elif self.app_config.state == AppState.USE_LOCAL_IMAGES:
            return self.subfolder_names
    
    def get_anime_titles(self):
        if self.anime_titles != None:
            return list(self.anime_titles)
        else:
            return None
        
    def use_local_images(self):
        self.anime_titles, self.subfolder_names = extract_anime_info(self.user_name)
            
        if(self.subfolder_names == None):
            self.handle_list_not_found()

    def get_list_info(self):
        list_url = f"https://myanimelist.net/animelist/{self.user_name}?status=2"
        response = requests.get(list_url)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            list_table = soup.find("table", class_="list-table")
            
            if list_table:
                anime_items = list_table.get("data-items")          
                anime_items = json.loads(anime_items)
                
                progress_bar = tqdm(anime_items, desc="Processing", unit="anime")
                
                if self.app_config.state == AppState.DOWNLOAD_ALL_CHARACTERS:
                    self.show_overall_progress_bar_signal.emit()
                    self.overall_description_signal.emit(f"<h3>Overall Progress</h3>")
                
                for index, anime_info in enumerate(progress_bar):
                    progress_value = int((index + 1) / len(anime_items) * 100)
                    
                    show_number = anime_info["anime_id"]
                    anime_title = anime_info["anime_title"]
                    anime_title_english = anime_info["anime_title_eng"]
                    
                    anime_title_folder = sanitize_string(anime_title)
                    folder_name = create_user_folder(anime_title_folder)
                    
                    if self.app_config.state == AppState.DOWNLOAD_ONE_CHARACTER:
                        self.one_char_per_anime(show_number, anime_title, anime_title_english, anime_title_folder, folder_name, progress_value)
                    elif self.app_config.state == AppState.DOWNLOAD_ALL_CHARACTERS:
                        self.all_chars_per_anime(index, show_number, anime_title, anime_title_folder, folder_name, progress_value)
                
                if self.app_config.state == AppState.DOWNLOAD_ALL_CHARACTERS:    
                    self.show_overall_progress_bar_signal.emit()    
                
                progress_bar.close()
                
        elif response.status_code == 429:
            self.handle_rate_limiting()
        else:
            self.handle_list_not_found()
        
    def one_char_per_anime(self, show_number, anime_title, anime_title_english, anime_title_folder, folder_name, progress_value):
        character_name, image_url, character_code = get_main_female_character_info(show_number)
        
        self.handle_character_logic(character_name, character_code, image_url, anime_title, anime_title_english, anime_title_folder, folder_name, show_number, progress_value)
        
        time.sleep(random.uniform(1, 3))
                
    def all_chars_per_anime(self, index, show_number, anime_title, anime_title_folder, folder_name, progress_value):
        self.overall_progress_signal.emit(progress_value)
        
        self.description_signal1.emit(f"<h3>Parsing character data...</h3>")
        self.description_signal2.emit(f"<h3>Anime - {anime_title}</h3>")
        
        all_female_characters, anime_title, anime_title_english = get_all_female_character_info(show_number, "yes", progress_callback=self.update_progress)
        
        if all_female_characters:
            self.description_signal1.emit(f"<h3>Character data parsed for {anime_title}</h3>")
            self.description_signal2.emit(f"<h3>Starting download process...</h3>")
            
            for index,character in enumerate(all_female_characters):                        
                nested_progress_value = int((index + 1) / len(all_female_characters) * 100)
                
                self.handle_character_logic(character['name'], character['code'], character['image_url'], anime_title, anime_title_english, anime_title_folder, folder_name, show_number, nested_progress_value)
                
            time.sleep(random.uniform(1, 3))
                
        else:
            self.handle_no_characters()
            
    def handle_character_logic(self, character_name, character_code, image_url, anime_title, anime_title_english, anime_title_folder, folder_name, show_number, progress_value):
        if character_name and image_url:
            if character_name not in self.character_names:
                self.character_names.add(character_name)
                
                if anime_title_folder not in self.anime_titles:
                    self.anime_titles.add(anime_title_folder)
                
                update_anime_dictionary(anime_title, show_number)
                update_character_dictionary(character_name, character_code)
                
                saved_image_filename = save_image_and_info(folder_name, anime_title, character_name, image_url, self.user_name)
                
                if saved_image_filename:
                    self.get_character_images(progress_value, folder_name, character_name, anime_title, anime_title_english)
                else:
                    self.handle_image_not_saved(progress_value)
            else:
                self.handle_image_already_saved(progress_value)
        else:
            self.handle_waifu_not_found(anime_title, progress_value)
        
    def get_character_images(self, progress_value, folder_name, character_name, anime_title, anime_title_english):
        self.progress_signal.emit(progress_value)
        self.description_signal1.emit(f"<h3>Anime - {anime_title}</h3>")
        self.description_signal2.emit(f"<h3>Waifu - {character_name}</h3>")
        
        processing = invert_name(character_name)
        processing = processing.replace(" ", "_")
        
        self.show_nested_progress_bar_signal.emit()
        self.nested_description_signal.emit(f"<h4>Additional Images Progress</h4>")
        
        search_term_a = processing
        search_term_b = (processing + "_(" + (anime_title.replace(" ", "_")) + ")")
        search_term_c = invert_name(processing.replace("_", " ")).replace(" ", "_")
        search_term_d = ((invert_name(processing.replace("_", " ")).replace(" ", "_")) + "_(" + (anime_title.replace(" ", "_")) + ")")
        
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

        for source in ["danbooru", "safebooru", "animepictures", "gelbooru", "rule34xxx", "deviantart"]:
            if self.app_config.get_source_setting(source, "enabled"):
                self.description_signal2.emit(f"<h3>Waifu - {character_name} - Source: {source}</h3>")
                
                failed = True

                source_retry_search_terms = retry_search_terms_per_source.get(source, [])
                
                for retry_search_term in source_retry_search_terms:
                    
                    if self.app_config.get_source_setting(source, "use_api"):
                        source_function = globals()[f"source_{source}_api"]
                    else:
                        source_function = globals()[f"source_{source}"]
                        
                    if source_function(folder_name, character_name, retry_search_term, self.nested_progress_signal, self.nested_description_signal):
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
        
    def update_progress(self, current_item, total_items, current_character):
        progress = (current_item + 1) / total_items * 100
        self.progress_signal.emit(int(progress))
        self.description_signal2.emit(f"<h3>Character - {current_character}</h3>")
        
    def handle_image_not_saved(self, progress_value):
        self.progress_signal.emit(progress_value)
        self.description_signal1.emit(f"<h3>Image could not be saved</h3>")
        self.description_signal2.emit(f"<h3>:(</h3>")
        
    def handle_image_already_saved(self, progress_value):
        self.progress_signal.emit(progress_value)
        self.description_signal1.emit(f"<h3>Images already saved for this character</h3>")
        self.description_signal2.emit(f"<h3>Skipping duplicate requests</h3>")

    def handle_waifu_not_found(self, anime_title, progress_value):
        self.progress_signal.emit(progress_value)
        self.description_signal1.emit(f"<h3>Anime - {anime_title}</h3>")
        self.description_signal2.emit(f"<h3>Waifu not found :(</h3>")
        
    def handle_no_characters(self, anime_title):
        self.progress_signal.emit(0)
        self.description_signal1.emit(f"<h3>Anime - {anime_title}</h3>")
        self.description_signal2.emit(f"<h3>No waifus found :(</h3>")
        time.sleep(random.uniform(2, 4))
        
    def handle_list_not_found(self):
        self.show_progress_bar_signal.emit()
        self.description_signal1.emit(f"<h3>Anime list not found.</h3>")
        self.description_signal2.emit(f"<h3>:(</h3>")
        time.sleep(random.uniform(2, 4))
        self.show_progress_bar_signal.emit()
        self.description_signal1.emit(f"<h3>Progress</h3>")
        self.description_signal2.emit(f"")
        
    def handle_rate_limiting(self):
        self.show_progress_bar_signal.emit()
        self.description_signal1.emit(f"<h3>You are currently being rate limited.</h3>")
        self.description_signal2.emit(f"<h3>:(</h3>")
        time.sleep(random.uniform(2, 4))
        self.show_progress_bar_signal.emit()
        self.description_signal1.emit(f"<h3>Progress</h3>")
        self.description_signal2.emit(f"")