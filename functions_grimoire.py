import os
import time
import random
import json
import re
import requests
import cv2
import sqlite3
import feedparser
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from PIL import Image
from tqdm import tqdm
from urllib.parse import urlparse
from PyQt6.QtCore import pyqtSignal

## Yes, I know this is a spaghetti mess

def create_thumbnail(local_file_path, thumbnail_file_path):
    video_extensions = ('.mp4', '.avi', '.mkv', '.webm')
    invalid_extensions = ('.zip', '.rar')
    
    if any(local_file_path.endswith(ext) for ext in video_extensions):
        cap = cv2.VideoCapture(local_file_path)
        ret, frame = cap.read()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        
        thumbnail_size = (180, 280)
        img.thumbnail(thumbnail_size)
        
        thumbnail_file_path = os.path.splitext(thumbnail_file_path)[0] + ".png"
        img.save(thumbnail_file_path)
        
        cap.release()
    elif any(local_file_path.endswith(ext) for ext in invalid_extensions):
        print(f"Thumbnail creation skipped, invalid file extension detected.")
    else:
        img = Image.open(local_file_path)
        thumbnail_size = (180, 280)
        try:
            img.thumbnail(thumbnail_size)
            img.save(thumbnail_file_path)
        except:
            try:
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                    
                thumbnail_size = (180, 280)
                img.thumbnail(thumbnail_size)
                img.save(thumbnail_file_path)
            except:
                print("Thumbnail couldn't be created!")

def extract_titles(title_text):
    title_text = title_text.strip()
    pattern = r"^(.*?)\s*(\((.*?)\))?\s*-\s*MyAnimeList\.net$"
    match = re.match(pattern, title_text)
    if match:
        main_title = match.group(1)
        alternate_title = match.group(3)
        return main_title, alternate_title
    return None, None

def remove_parentheses(input_string):
    while "(" in input_string:
        start = input_string.index("(")
        input_string = input_string[:start]
    return input_string.strip()

def invert_name(name):
    words = name.split()
    inverted_name = " ".join(reversed(words))
    return inverted_name

def sanitize_string(string):
    invalid_chars_pattern = r'[\/:*?<>|"]'
    sanitized_string = re.sub(invalid_chars_pattern, '_', string)
    return sanitized_string

def extract_anime_info(user_name):
    character_names = []
    anime_titles = []

    try:
        connection = sqlite3.connect(f"outputs/user_anime_data.db")
        cursor = connection.cursor()

        user_id_query = "SELECT id FROM users WHERE username = ?"
        user_id = cursor.execute(user_id_query, (user_name,)).fetchone()

        if user_id:
            anime_query = """
                SELECT a.title, c.character_name
                FROM anime a
                INNER JOIN characters c ON a.id = c.anime_id
                WHERE c.user_id = ?
            """
            cursor.execute(anime_query, (user_id[0],))

            for row in cursor.fetchall():
                anime_title, character_name = row
                sanitized_name = sanitize_string(anime_title)

                if sanitized_name not in anime_titles:
                    anime_titles.append(sanitized_name)

                if character_name not in character_names:
                    character_names.append(character_name)

        else:
            print(f"User '{user_name}' not found.")

        connection.close()
        return anime_titles, character_names

    except sqlite3.Error as e:
        print("SQLite error:", e)
        return None, None

    except Exception as e:
        print("Error:", e)
        return None, None
    
def get_character_names_from_anime_folder(anime_title):
    character_names = []

    sanitized_name = sanitize_string(anime_title)
    
    anime_folder_path = os.path.join("outputs", sanitized_name)

    if not os.path.exists(anime_folder_path):
        print(f"Anime folder '{sanitized_name}' not found.")
        return character_names

    anime_title_folders = os.listdir(anime_folder_path)
    for character_folder in anime_title_folders:
        character_names.append(character_folder)

    return character_names

def get_anime_title_from_character_name(character_name):
    found_in_anime_titles = None

    outputs_folder = "outputs"

    anime_title_folders = [item for item in os.listdir(outputs_folder) if os.path.isdir(os.path.join(outputs_folder, item))]
    for anime_title in anime_title_folders:
        anime_folder_path = os.path.join(outputs_folder, anime_title)
        
        character_folders = os.listdir(anime_folder_path)
        if character_name in character_folders:
            found_in_anime_titles = anime_title
            break

    return found_in_anime_titles

def generate_collage(user_name):
    folder_name = user_name.replace(" ", "_")
    
    image_files = [file for file in os.listdir(folder_name) if file.endswith(".jpg")]
    
    if not image_files:
        print("No image files found in the folder.")
        return
    
    images = [Image.open(os.path.join(folder_name, image_file)) for image_file in image_files]
    
    num_images = len(images)
    collage_width = 3
    collage_height = (num_images + collage_width - 1) // collage_width
    
    image_width, image_height = images[0].size
    collage = Image.new("RGB", (collage_width * image_width, collage_height * image_height))
    
    for i, image in enumerate(images):
        x = (i % collage_width) * image_width
        y = (i // collage_width) * image_height
        collage.paste(image, (x, y))
    
    collage.save(f"{folder_name}_collage.jpg")

def create_user_folder(user_name):
    folder_name = "outputs\\" + user_name
    os.makedirs(folder_name, exist_ok=True)
    return folder_name

def get_completed_anime_list(user_name):
    list_url = f"https://myanimelist.net/animelist/{user_name}?status=2"
    response = requests.get(list_url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        list_table = soup.find("table", class_="list-table")
        
        if list_table:
            anime_items = list_table.get("data-items")
            
            folder_name = create_user_folder(user_name)
            anime_items = json.loads(anime_items)
            
            progress_bar = tqdm(anime_items, desc="Processing", unit="anime")
            
            for anime_info in progress_bar:
                show_number = anime_info["anime_id"]
                character_name, image_url = get_main_female_character_info(show_number)
                
                if character_name and image_url:
                    anime_title = anime_info["anime_title"]

                    saved_image_filename = save_image_and_info(folder_name, anime_title, character_name, image_url)
                    if saved_image_filename:
                        progress_bar.set_description(f"Processing - {anime_title} - Main Female Character - {character_name}")
                    else:
                        print("Image could not be saved.")
                else:
                    print(f"Character information not found for {anime_info['anime_title']}")
                
                delay = random.uniform(2, 4)
                time.sleep(delay)
                
            progress_bar.close()
    
    elif response.status_code == 429:
        print("You are currently being rate limited.")
    else:
        print("Anime list not found.")
            
    return None

def is_female_description(description):
    male_keywords = ["boy", "man", "male", "he", "he's", "his"]
    female_keywords = ["girl", "woman", "female", "she", "she's", "her"]
    
    description = description.lower()
    words = description.split()
    
    for word in words:
        if word in male_keywords:
            return False
        elif word in female_keywords:
            return True
    
    return False

def get_main_female_character_info(show_number, opt=None):
    show_url = f"https://myanimelist.net/anime/{show_number}"
    response = requests.get(show_url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        character_section = soup.find("h2", string="Characters & Voice Actors")
        
        if opt is not None:
            title_tag = soup.find("title")
            title_text = title_tag.get_text()
            main_title, alternate_title = extract_titles(title_text)
        
        if character_section:
            characters_list = character_section.find_next("div", class_="detail-characters-list")
            character_tags = characters_list.find_all("a", href=lambda x: x and "/character/" in x)
            
            for i in range(0, len(character_tags), 2):
                character = character_tags[i]
                character_url = character["href"]
                character_name = character_url.rsplit('/', 1)[-1]
                character_code = character_url.split('/')[-2]
                character_response = requests.get(character_url)
                
                if character_response.status_code == 200:
                    character_soup = BeautifulSoup(character_response.content, "html.parser")
                    character_heading = character_soup.find("h2", class_="normal_header")
                    
                    if character_heading:
                        character_name = character_heading.get_text(strip=True)
                        
                        character_description = ""
                        sibling = character_heading.next_sibling
                        element = sibling.next_element
                        paragraph = str(sibling) + str(element)
                        
                        if(len(paragraph)<1500):
                            next_child = element.next_element
                            paragraph = paragraph + str(next_child)
                            while(len(paragraph)<3000):
                                next_child = next_child.next_element
                                paragraph = paragraph + str(next_child)
                        
                        target_string = '<div style="padding: 20px 40px;display: inline-block;">'
                        target_index = paragraph.find(target_string)
                        if target_index != -1:
                            paragraph = paragraph[:target_index]
                        
                        character_description = paragraph.strip()
                        
                        if character_description and is_female_description(character_description):
                            character_image = character_soup.find("img", class_="portrait-225x350")
                            if character_image:
                                image_url = character_image.get("data-src")
                                character_name = remove_parentheses(character_name)
                                if opt is None:
                                    return character_name, image_url, character_code
                                else:
                                    return character_name, image_url, main_title, alternate_title, character_code
    elif response.status_code == 429:
        print("You are currently being rate limited.")
    
    if opt is None:
        return None, None, None
    else:
        return None, None, None, None, None

def get_all_female_character_info(show_number, opt=None, progress_callback=None):
    show_url = f"https://myanimelist.net/anime/{show_number}"
    response = requests.get(show_url)
    female_characters = []
    main_title = None
    alternate_title = None
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        character_section = soup.find("h2", string="Characters & Voice Actors")
        
        if opt is not None:
            title_tag = soup.find("title")
            title_text = title_tag.get_text()
            main_title, alternate_title = extract_titles(title_text)
        
        if character_section:
            characters_list = character_section.find_next("div", class_="detail-characters-list")
            character_tags = characters_list.find_all("a", href=lambda x: x and "/character/" in x)
            
            for i in range(0, len(character_tags), 2):
                character = character_tags[i]
                character_url = character["href"]
                character_name = character_url.rsplit('/', 1)[-1]
                character_code = character_url.split('/')[-2]
                character_response = requests.get(character_url)
                
                if character_response.status_code == 200:
                    character_soup = BeautifulSoup(character_response.content, "html.parser")
                    character_heading = character_soup.find("h2", class_="normal_header")
                    
                    if character_heading:
                        character_name = character_heading.get_text(strip=True)
                        
                        character_description = ""
                        sibling = character_heading.next_sibling
                        element = sibling.next_element
                        paragraph = str(sibling) + str(element)
                        
                        if(len(paragraph)<1500):
                            next_child = element.next_element
                            paragraph = paragraph + str(next_child)
                            while(len(paragraph)<3000):
                                next_child = next_child.next_element
                                paragraph = paragraph + str(next_child)
                        
                        target_string = '<div style="padding: 20px 40px;display: inline-block;">'
                        target_index = paragraph.find(target_string)
                        if target_index != -1:
                            paragraph = paragraph[:target_index]
                        
                        character_description = paragraph.strip()
                        
                        if character_description and is_female_description(character_description):
                            character_image = character_soup.find("img", class_="portrait-225x350")
                            if character_image:
                                image_url = character_image.get("data-src")
                                character_name = remove_parentheses(character_name)
                                female_characters.append({
                                    "name": character_name,
                                    "image_url": image_url,
                                    "code": character_code
                                })               
                elif response.status_code == 429:
                    print("You are being rate limited.") 
                
                delay = random.uniform(4, 6)
                time.sleep(delay)
                print("Processed a request...")
                
                if progress_callback:
                    progress_callback(i, len(character_tags), character_name)
    
    elif response.status_code == 429:
        print("You are being rate limited.")               
            
    if opt is None:
        return female_characters
    else:
        return female_characters, main_title, alternate_title

def get_single_character_info(character_number):
    character_url = f"https://myanimelist.net/character/{character_number}"
    
    character_response = requests.get(character_url)
    
    if character_response.status_code == 200:
        character_soup = BeautifulSoup(character_response.content, "html.parser")
        
        animeography_table = character_soup.find("div", class_="normal_header", string="Animeography")
        if animeography_table:
            anime_links = animeography_table.find_next("table").find_all("a", href=lambda x: x and "/anime/" in x)
            
            if anime_links:
                first_anime_link = anime_links[0]["href"]
                show_number = first_anime_link.split("/")[4]
                show_url = f"https://myanimelist.net/anime/{show_number}"
                show_response = requests.get(show_url)
                
                if show_response.status_code == 200:
                    soup = BeautifulSoup(show_response.content, "html.parser")
                    title_tag = soup.find("title")
                    title_text = title_tag.get_text()
                    main_title, alternate_title = extract_titles(title_text) 
                    
                elif character_response.status_code == 429:
                    print("Couldn't access character's anime. You are currently being rate limited.")
        
        character_heading = character_soup.find("h2", class_="normal_header")
        if character_heading:
            character_name = character_heading.get_text(strip=True)
            
            character_description = ""
            sibling = character_heading.next_sibling
            element = sibling.next_element
            paragraph = str(sibling) + str(element)
            
            if(len(paragraph)<1500):
                next_child = element.next_element
                paragraph = paragraph + str(next_child)
                while(len(paragraph)<3000):
                    next_child = next_child.next_element
                    paragraph = paragraph + str(next_child)
            
            target_string = '<div style="padding: 20px 40px;display: inline-block;">'
            target_index = paragraph.find(target_string)
            if target_index != -1:
                paragraph = paragraph[:target_index]
            
            character_description = paragraph.strip()
            
            if character_description and is_female_description(character_description):
                character_image = character_soup.find("img", class_="portrait-225x350")
                if character_image:
                    image_url = character_image.get("data-src")
                    character_name = remove_parentheses(character_name)
                    return character_name, image_url, main_title, alternate_title
    
    elif character_response.status_code == 429:
        print("Couldn't access character's page. You are currently being rate limited.")
                    
    return None, None, None, None

def save_image_to_folder(image_url, character_name):
    response = requests.get(image_url)
    
    if response.status_code == 200:
        image_filename = f"images/{character_name}.jpg"
        with open(image_filename, "wb") as image_file:
            image_file.write(response.content)
        return image_filename
    
    return None

def save_image_to_character_folder(image_url, anime_title, character_name):
    response = requests.get(image_url)
    
    if response.status_code == 200:
        character_folder = f"outputs\{anime_title}\{character_name}"
        os.makedirs(character_folder, exist_ok=True)
        
        image_filename = f"{character_folder}/{character_name}.jpg"
        with open(image_filename, "wb") as image_file:
            image_file.write(response.content)
        
        return image_filename
    
    elif response.status_code == 429:
        print("You are being rate limited.") 
    
    return None

def save_image_and_info(folder_name, anime_title, character_name, image_url, user_name):
    character_folder = os.path.join(folder_name, character_name)
    os.makedirs(character_folder, exist_ok=True)
    
    response = requests.get(image_url)
    
    if response.status_code == 200:
        image_filename = f"{character_folder}/{character_name}.jpg"
        with open(image_filename, "wb") as image_file:
            image_file.write(response.content)
        
        connection = sqlite3.connect(f"outputs/user_anime_data.db")

        create_users_table_query = """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE
            );
        """

        create_anime_table_query = """
            CREATE TABLE IF NOT EXISTS anime (
                id INTEGER PRIMARY KEY,
                title TEXT UNIQUE
            );
        """

        create_characters_table_query = """
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                anime_id INTEGER,
                character_name TEXT,
                UNIQUE(user_id, anime_id, character_name),
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (anime_id) REFERENCES anime (id)
            );
        """
        
        connection.execute(create_users_table_query)
        connection.execute(create_anime_table_query)
        connection.execute(create_characters_table_query)
        connection.commit()

        insert_user_query = "INSERT OR IGNORE INTO users (username) VALUES (?)"
        connection.execute(insert_user_query, (user_name,))
        connection.commit()

        insert_anime_query = "INSERT OR IGNORE INTO anime (title) VALUES (?)"
        connection.execute(insert_anime_query, (anime_title,))
        connection.commit()
        
        user_id_query = "SELECT id FROM users WHERE username = ?"
        anime_id_query = "SELECT id FROM anime WHERE title = ?"
        user_id = connection.execute(user_id_query, (user_name,)).fetchone()[0]
        anime_id = connection.execute(anime_id_query, (anime_title,)).fetchone()[0]
        
        insert_character_query = """
            INSERT OR IGNORE INTO characters (user_id, anime_id, character_name)
            VALUES (?, ?, ?)
        """
        connection.execute(insert_character_query, (user_id, anime_id, character_name))
        connection.commit()
        
        connection.close()
            
        return image_filename
    
    return None

def update_character_dictionary(character_name, character_code):
    connection = sqlite3.connect(f"outputs/character_data.db")
    
    create_table_query = """
        CREATE TABLE IF NOT EXISTS characters (
            code TEXT PRIMARY KEY,
            name TEXT
        );
    """
    
    connection.execute(create_table_query)
    
    select_query = "SELECT name FROM characters WHERE code = ?;"
    
    result = connection.execute(select_query, (character_code,))
    character_query = result.fetchone()
    
    if character_query:
        print(f"Character name for code {character_code}: {character_query[0]} already exists.")
    else:
        print(f"No character found for code {character_code}, inserting data.")
        insert_query = "INSERT INTO characters (code, name) VALUES (?, ?);"
        data = (character_code, character_name)
        connection.execute(insert_query, data)
        connection.commit()
    
    connection.close()
    
def look_up_character_dictionary(character_name):
    connection = sqlite3.connect(f"outputs/character_data.db")
    
    select_query = "SELECT name FROM characters WHERE code = ?;"

    result = connection.execute(select_query, (character_name,))
    character_code = result.fetchone()

    if character_code:
        print(f"Character name for code {character_name}: {character_code[0]}.")
        connection.close()
        return character_code[0]
    else:
        print(f"{character_name} not found in database.")
        connection.close()
        return None
    
def update_anime_dictionary(anime_title, anime_code):
    connection = sqlite3.connect(f"outputs/anime_data.db")
    
    create_table_query = """
        CREATE TABLE IF NOT EXISTS anime_titles (
            code TEXT PRIMARY KEY,
            title TEXT
        );
    """
    
    connection.execute(create_table_query)
    
    select_query = "SELECT title FROM anime_titles WHERE code = ?;"
    
    result = connection.execute(select_query, (anime_code,))
    anime_query = result.fetchone()
    
    if anime_query:
        print(f"Anime title for code {anime_code}: {anime_query[0]} already exists.")
    else:
        print(f"No anime found for code {anime_code}, inserting data.")
        insert_query = "INSERT INTO anime_titles (code, title) VALUES (?, ?);"
        data = (anime_code, anime_title)
        connection.execute(insert_query, data)
        connection.commit()
    
    connection.close()
    
def look_up_anime_dictionary(anime_title):
    connection = sqlite3.connect(f"outputs/anime_data.db")
    
    select_query = "SELECT title FROM anime_titles WHERE code = ?;"

    result = connection.execute(select_query, (anime_title,))
    anime_code = result.fetchone()

    if anime_code:
        print(f"Anime title for code {anime_title}: {anime_code[0]}.")
        connection.close()
        return anime_code[0]
    else:
        print(f"{anime_title} not found in database.")
        connection.close()
        return None

def source_danbooru(folder_name, character_name, search_tag, nested_progress_signal, nested_description_signal):
    save_dir = os.path.join(folder_name, character_name)
    
    url = "https://danbooru.donmai.us/"
    params = {
        "tags": search_tag,
        "z": "5"
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        posts_div = soup.find('div', id='posts')
        
        nested_description_signal.emit(f"<h4>Searching...</h4>")
        
        if posts_div:
            links = posts_div.find_all('a')
            
            href_list = [link.get('href') for link in links if 'page=' not in link.get('href') and link.get('href').startswith('/posts/')]
            nested_description_signal.emit(f"<h4>Parsing possible links...</h4>")
            
            for index, href in enumerate(href_list):
                post_url = url + href
                post_number = href.split('/')[2].split('?')[0]
                nested_progress_value = int((index + 1) / len(href_list) * 100)
                
                skip_delay = False
                
                post_response = requests.get(post_url)
                
                if post_response.status_code == 200:
                    post_soup = BeautifulSoup(post_response.text, 'html.parser')
                    download_li = post_soup.find('li', {'id': 'post-option-download'})
                    
                    if download_li:
                        img_url = download_li.a['href']
                        img_url = img_url.replace('?download=1', '')
                        file_extension = img_url.split('.')[-1]
                        ul_element = post_soup.find('ul', class_='artist-tag-list')
                        
                        if ul_element:
                            artist_names = []
                            li_elements = ul_element.find_all('li')
                            
                            for li in li_elements[:3]:
                                tag_name = li.get('data-tag-name')
                                if tag_name:
                                    artist_names.append(tag_name)
                            
                            concatenated_artists = '_&_'.join(artist_names)
                            img_name = f"{search_tag}_danbooru_by_{concatenated_artists}_{post_number}.{file_extension}"
                            thumbnail_name = f"{search_tag}_danbooru_by_{concatenated_artists}_{post_number}_thumbnail.{file_extension}"
                        else:
                            img_name = f"{search_tag}_danbooru_by_unknown_artist_{post_number}.{file_extension}"
                            thumbnail_name = f"{search_tag}_danbooru_by_unknown_artist_{post_number}_thumbnail.{file_extension}"
                        
                        local_file_path = os.path.join(save_dir, img_name)
                        thumbnail_file_path = os.path.join(save_dir, thumbnail_name)
                        
                        if os.path.exists(local_file_path):
                            skip_delay = True
                            nested_progress_signal.emit(nested_progress_value)
                            nested_description_signal.emit(f"<h4>Image {img_name} already exists. Skipping download.</h4>")
                            if os.path.exists(thumbnail_file_path):
                                nested_description_signal.emit(f"<h4>Thumbnail {thumbnail_name} already exists.</h4>")
                            else:
                                nested_description_signal.emit(f"<h4>Creating thumbnail for {img_name}.</h4>")
                                create_thumbnail(local_file_path, thumbnail_file_path)
                        else:
                            img_response = requests.get(img_url)
                        
                            if img_response.status_code == 200:
                                with open(local_file_path, 'wb') as img_file:
                                    img_file.write(img_response.content)
                                    nested_progress_signal.emit(nested_progress_value)
                                    nested_description_signal.emit(f"<h4>Saved image: {img_name}</h4>")
                                    
                                    create_thumbnail(local_file_path, thumbnail_file_path)
                                    
                            elif response.status_code == 429:
                                nested_progress_signal.emit(nested_progress_value)
                                nested_description_signal.emit(f"<h4>Failed to download image: {img_name}. You are currently being rate limited.</h4>")
                            else:
                                nested_progress_signal.emit(nested_progress_value)
                                nested_description_signal.emit(f"<h4>Failed to download image: {img_name}</h4>")
                    else:
                        nested_description_signal.emit(f"<h4>Download link not found.</h4>")
                    
                    if not skip_delay:
                        time.sleep(random.uniform(5, 8))
                    else:
                        time.sleep(random.uniform(2, 3))
                        skip_delay = False
                elif response.status_code == 429:
                    nested_progress_signal.emit(nested_progress_value)
                    nested_description_signal.emit(f"<h4>Failed to fetch post: {post_url}. You are currently being rate limited.</h4>")
                else:
                    nested_progress_signal.emit(nested_progress_value)
                    nested_description_signal.emit(f"<h4>Failed to fetch post: {post_url}</h4>")
                    
            if(len(href_list)==0):
                nested_description_signal.emit(f"<h4>No posts found for the search term: {search_tag}.</h4>")
                return False
            
        else:
            nested_description_signal.emit(f"<h4>No <div id='posts'> found.</h4>")
    elif response.status_code == 429:
        nested_description_signal.emit(f"<h4>Search failed. You are currently being rate limited.</h4>")
    else:
        nested_description_signal.emit(f"<h4>Search failed. Status code: {response.status_code}</h4>")
        
    return True

def source_safebooru(folder_name, character_name, search_tag, nested_progress_signal, nested_description_signal):
    save_dir = os.path.join(folder_name, character_name)
    
    url = "https://safebooru.org/"
    endpoint = "/index.php?page=dapi&s=post&q=index"

    params = {
        "limit": 20,
        "pid": 1,
        "tags": search_tag,
    }
    
    nested_description_signal.emit(f"<h4>Searching...</h4>")

    response = requests.get(url + endpoint, params=params)

    if response.status_code == 200:
        xml_data = response.content
        root = ET.fromstring(xml_data)

        os.makedirs(save_dir, exist_ok=True)
        
        nested_description_signal.emit(f"<h4>Parsing possible links...</h4>")
        
        for index, post in enumerate(root.findall("post")):
            nested_progress_value = int((index + 1) / len(root.findall("post")) * 100)
            nested_progress_signal.emit(nested_progress_value)
            
            post_id = post.get("id")
            file_url = post.get("file_url")
            file_extension = os.path.splitext(file_url)[1]
            image_filename = f"{search_tag}_safebooru_{post_id}{file_extension}"
            thumbnail_filename = f"{search_tag}_safebooru_{post_id}_thumbnail{file_extension}"
            
            local_file_path = os.path.join(save_dir, image_filename)
            thumbnail_file_path = os.path.join(save_dir, thumbnail_filename)
            
            wackybullshit1 = save_dir+"\\"+image_filename
            wackybullshit2 = save_dir+"\\"+thumbnail_filename
            
            if os.path.exists(local_file_path):
                nested_description_signal.emit(f"<h4>Image {image_filename} already exists. Skipping download.</h4>")
                if os.path.exists(thumbnail_file_path):
                    nested_description_signal.emit(f"<h4>Thumbnail {thumbnail_filename} already exists.</h4>")
                else:
                    nested_description_signal.emit(f"<h4>Creating thumbnail for {image_filename}.</h4>")
                    create_thumbnail(wackybullshit1, wackybullshit2)
            else:
                with open(local_file_path, "wb") as image_file:
                    image_response = requests.get(file_url)
                    if image_response.status_code == 200:
                        image_file.write(image_response.content)
                        nested_description_signal.emit(f"<h4>Saved image: {image_filename}</h4>")
                        
                        create_thumbnail(wackybullshit1, wackybullshit2)
                        
                    elif image_response.status_code == 429:
                        nested_description_signal.emit(f"<h4>Failed to download image: {image_filename}. You are currently being rate limited.</h4>")
                    else:
                        nested_description_signal.emit(f"<h4>Failed to download image: {image_filename}.</h4>")
        if(len(root.findall("post"))==0):
                nested_description_signal.emit(f"<h4>No posts found for the search term: {search_tag}.</h4>")
                return False
    elif response.status_code == 429:
        nested_description_signal.emit(f"<h4>API request failed. You are being rate limited. Status code: {response.status_code}.</h4>")
    else:
        nested_description_signal.emit(f"<h4>API request failed. Status code: {response.status_code}.</h4>")
        
    return True

def source_gelbooru(folder_name, character_name, search_tag, nested_progress_signal, nested_description_signal):
    save_dir = os.path.join(folder_name, character_name)
    
    url = "https://gelbooru.com"
    endpoint = "/index.php?page=dapi&s=post&q=index"

    params = {
        "limit": 20,
        "pid": 1,
        "tags": search_tag,
    }
    
    nested_description_signal.emit(f"<h4>Searching...</h4>")

    response = requests.get(url + endpoint, params=params)

    if response.status_code == 200:
        xml_data = response.content
        root = ET.fromstring(xml_data)

        os.makedirs(save_dir, exist_ok=True)
        
        nested_description_signal.emit(f"<h4>Parsing possible links...</h4>")
        
        for index, post in enumerate(root.findall("post")):
            nested_progress_value = int((index + 1) / len(root.findall("post")) * 100)
            nested_progress_signal.emit(nested_progress_value)
            
            post_id = post.find("id").text
            file_url = post.find("file_url").text
            
            file_extension = os.path.splitext(file_url)[1]
            image_filename = f"{search_tag}_gelbooru_{post_id}{file_extension}"
            thumbnail_filename = f"{search_tag}_gelbooru_{post_id}_thumbnail{file_extension}"
            
            local_file_path = os.path.join(save_dir, image_filename)
            thumbnail_file_path = os.path.join(save_dir, thumbnail_filename)
            
            wackybullshit1 = save_dir+"\\"+image_filename
            wackybullshit2 = save_dir+"\\"+thumbnail_filename
            
            if os.path.exists(local_file_path):
                nested_description_signal.emit(f"<h4>Image {image_filename} already exists. Skipping download.</h4>")
                if os.path.exists(thumbnail_file_path):
                    nested_description_signal.emit(f"<h4>Thumbnail {thumbnail_filename} already exists.</h4>")
                else:
                    nested_description_signal.emit(f"<h4>Creating thumbnail for {image_filename}.</h4>")
                    create_thumbnail(wackybullshit1, wackybullshit2)
            else:
                with open(local_file_path, "wb") as image_file:
                    image_response = requests.get(file_url)
                    if image_response.status_code == 200:
                        image_file.write(image_response.content)
                        nested_description_signal.emit(f"<h4>Saved image: {image_filename}</h4>")
                        
                        create_thumbnail(wackybullshit1, wackybullshit2)
                        
                    elif image_response.status_code == 429:
                        nested_description_signal.emit(f"<h4>Failed to download image: {image_filename}. You are currently being rate limited.</h4>")
                    else:
                        nested_description_signal.emit(f"<h4>Failed to download image: {image_filename}.</h4>")
        if(len(root.findall("post"))==0):
                nested_description_signal.emit(f"<h4>No posts found for the search term: {search_tag}.</h4>")
                return False
    elif response.status_code == 429:
        nested_description_signal.emit(f"<h4>API request failed. You are being rate limited. Status code: {response.status_code}.</h4>")
    else:
        nested_description_signal.emit(f"<h4>API request failed. Status code: {response.status_code}.</h4>")
        
    return True

def source_rule34xxx(folder_name, character_name, search_tag, nested_progress_signal, nested_description_signal):
    save_dir = os.path.join(folder_name, character_name)
    
    url = "https://api.rule34.xxx/index.php?page=dapi&s=post&q=index"

    params = {
        "limit": 20,
        "pid": 1,
        "tags": search_tag,
    }
    
    nested_description_signal.emit(f"<h4>Searching...</h4>")

    response = requests.get(url, params=params)

    if response.status_code == 200:
        xml_data = response.content
        root = ET.fromstring(xml_data)

        os.makedirs(save_dir, exist_ok=True)
        
        nested_description_signal.emit(f"<h4>Parsing possible links...</h4>")
        
        for index, post in enumerate(root.findall("post")):
            nested_progress_value = int((index + 1) / len(root.findall("post")) * 100)
            nested_progress_signal.emit(nested_progress_value)
            
            post_id = post.get("id")
            file_url = post.get("file_url")
            file_extension = os.path.splitext(file_url)[1]
            image_filename = f"{search_tag}_rule34xxx_{post_id}{file_extension}"
            thumbnail_filename = f"{search_tag}_rule34xxx_{post_id}_thumbnail{file_extension}"
            
            local_file_path = os.path.join(save_dir, image_filename)
            thumbnail_file_path = os.path.join(save_dir, thumbnail_filename)
            
            wackybullshit1 = save_dir+"\\"+image_filename
            wackybullshit2 = save_dir+"\\"+thumbnail_filename
            
            if os.path.exists(local_file_path):
                nested_description_signal.emit(f"<h4>Image {image_filename} already exists. Skipping download.</h4>")
                if os.path.exists(thumbnail_file_path):
                    nested_description_signal.emit(f"<h4>Thumbnail {thumbnail_filename} already exists.</h4>")
                else:
                    nested_description_signal.emit(f"<h4>Creating thumbnail for {image_filename}.</h4>")
                    create_thumbnail(wackybullshit1, wackybullshit2)
            else:
                with open(local_file_path, "wb") as image_file:
                    image_response = requests.get(file_url)
                    if image_response.status_code == 200:
                        image_file.write(image_response.content)
                        nested_description_signal.emit(f"<h4>Saved image: {image_filename}</h4>")
                        
                        create_thumbnail(wackybullshit1, wackybullshit2)
                        
                    elif image_response.status_code == 429:
                        nested_description_signal.emit(f"<h4>Failed to download image: {image_filename}. You are currently being rate limited.</h4>")
                    else:
                        nested_description_signal.emit(f"<h4>Failed to download image: {image_filename}.</h4>")
        if(len(root.findall("post"))==0):
                nested_description_signal.emit(f"<h4>No posts found for the search term: {search_tag}.</h4>")
                return False
    elif response.status_code == 429:
        nested_description_signal.emit(f"<h4>API request failed. You are being rate limited. Status code: {response.status_code}.</h4>")
    else:
        nested_description_signal.emit(f"<h4>API request failed. Status code: {response.status_code}.</h4>")
        
    return True

def source_animepictures(folder_name, character_name, search_tag, nested_progress_signal, nested_description_signal):
    save_dir = os.path.join(folder_name, character_name)
    
    url = f"https://anime-pictures.net/posts?search_tag={search_tag}&lang=en&page=0"

    nested_description_signal.emit(f"<h4>Searching...</h4>")
    
    response = requests.get(url)

    if response.status_code == 200:
        nested_description_signal.emit(f"<h4>Parsing possible links...</h4>")
        
        os.makedirs(save_dir, exist_ok=True)
        
        soup = BeautifulSoup(response.content, "html.parser")

        anchor_tags = soup.find_all("a", {"data-sveltekit-preload-data": "hover"})

        post_paths = []
        for anchor in anchor_tags:
            
            if anchor.find_parent("div", class_="svelte-enxrex") is None:
                
                href = anchor.get("href")
                if href:
                    clean_href = href.split("?")[0]
                    post_paths.append(clean_href)
                    
        if(len(post_paths) > 0):
            for index, post in enumerate(post_paths):
                nested_progress_value = int((index + 1) / 20 * 100)
                nested_progress_signal.emit(nested_progress_value)
                
                if index >= 20:
                    break
                
                post_url = f"https://anime-pictures.net{post}"
                
                image_post_response = requests.get(post_url)

                if image_post_response.status_code == 200:
                    image_post_soup = BeautifulSoup(image_post_response.content, "html.parser")
                    
                    download_anchor = image_post_soup.find("a", class_="download_icon")
                    file_url = download_anchor.get("href")
                    
                    if file_url:
                        post_id = post_url.split("/")[-1]
                        parsed_url = urlparse(file_url)
                        path = parsed_url.path
                        file_extension = os.path.splitext(path)[1]
                        
                        image_filename = f"{search_tag}_animepictures_{post_id}{file_extension}"
                        thumbnail_filename = f"{search_tag}_animepictures_{post_id}_thumbnail{file_extension}"
                        
                        local_file_path = os.path.join(save_dir, image_filename)
                        thumbnail_file_path = os.path.join(save_dir, thumbnail_filename)
                        
                        wackybullshit1 = save_dir+"\\"+image_filename
                        wackybullshit2 = save_dir+"\\"+thumbnail_filename
                        
                        if os.path.exists(local_file_path):
                            nested_description_signal.emit(f"<h4>Image {image_filename} already exists. Skipping download.</h4>")
                            if os.path.exists(thumbnail_file_path):
                                nested_description_signal.emit(f"<h4>Thumbnail {thumbnail_filename} already exists.</h4>")
                            else:
                                nested_description_signal.emit(f"<h4>Creating thumbnail for {image_filename}.</h4>")
                                create_thumbnail(wackybullshit1, wackybullshit2)
                        else:
                            with open(local_file_path, "wb") as image_file:
                                image_response = requests.get(file_url)
                                if image_response.status_code == 200:
                                    image_file.write(image_response.content)
                                    nested_description_signal.emit(f"<h4>Saved image: {image_filename}</h4>")
                                    
                                    create_thumbnail(wackybullshit1, wackybullshit2)
                                    
                                elif image_response.status_code == 429:
                                    nested_description_signal.emit(f"<h4>Failed to download image: {image_filename}. You are currently being rate limited.</h4>")
                                else:
                                    nested_description_signal.emit(f"<h4>Failed to download image: {image_filename}.</h4>")
                    else:
                        nested_description_signal.emit(f"<h4>Failed to fetch image url from the post.</h4>")
                
                elif response.status_code == 429:
                    nested_description_signal.emit(f"<h4>Post request failed. You are being rate limited. Status code: {response.status_code}.</h4>")
                else:
                    nested_description_signal.emit(f"<h4>Post request failed. Status code: {response.status_code}.</h4>")
                
                time.sleep(random.uniform(1, 2))
        else:
            nested_description_signal.emit(f"<h4>No posts found for the search term: {search_tag}.</h4>")
            return False
            
    elif response.status_code == 429:
        nested_description_signal.emit(f"<h4>Request failed. You are being rate limited. Status code: {response.status_code}.</h4>")
    else:
        nested_description_signal.emit(f"<h4>Request failed. Status code: {response.status_code}.</h4>")
        
    return True

def source_deviantart(folder_name, character_name, search_tag, nested_progress_signal, nested_description_signal):
    save_dir = os.path.join(folder_name, character_name)
    
    rss_url = f"https://backend.deviantart.com/rss.xml?type=deviation&q=boost%3Apopular+in%3Adigitalart%2Fdrawings+{search_tag}"
    nested_description_signal.emit(f"<h4>Searching...</h4>")
    
    try:
        feed = feedparser.parse(rss_url)
        
    except:
        nested_description_signal.emit(f"<h4>Request failed. Couldn't parse the RSS url.</h4>")
    else:
        os.makedirs(save_dir, exist_ok=True)
        nested_description_signal.emit(f"<h4>Parsing possible links...</h4>")
        
        for index, entry in enumerate(feed.entries):
            nested_progress_value = int((index + 1) / 20 * 100)
            nested_progress_signal.emit(nested_progress_value)
            
            if index >= 20:
                break
            
            artist = entry.media_credit[0]['content']
            url = entry.link
            post_id = url.rsplit('-', 1)[-1]
            
            response = requests.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                try:
                    div_tag = soup.find("div", class_="_2SlAD")
                    image_tag = div_tag.find("img")
                    image_url = image_tag["src"]
                    
                    parsed_url = urlparse(image_url)
                    path = parsed_url.path
                    file_extension = os.path.splitext(path)[1]
                except:
                    nested_description_signal.emit(f"<h4>Couldn't find image url in the post {post_id} HTML.</h4>")
                else:
                    image_response = requests.get(image_url)
                    
                    if image_response.status_code == 200:
                        image_filename = f"{search_tag}_deviantart_by_{artist}_{post_id}{file_extension}"
                        thumbnail_filename = f"{search_tag}_deviantart_by_{artist}_{post_id}_thumbnail{file_extension}"
                        
                        local_file_path = os.path.join(save_dir, image_filename)
                        thumbnail_file_path = os.path.join(save_dir, thumbnail_filename)
                        
                        wackybullshit1 = save_dir+"\\"+image_filename
                        wackybullshit2 = save_dir+"\\"+thumbnail_filename
                        
                        if os.path.exists(local_file_path):
                            nested_description_signal.emit(f"<h4>Image {image_filename} already exists. Skipping download.</h4>")
                            if os.path.exists(thumbnail_file_path):
                                nested_description_signal.emit(f"<h4>Thumbnail {thumbnail_filename} already exists.</h4>")
                            else:
                                nested_description_signal.emit(f"<h4>Creating thumbnail for {image_filename}.</h4>")
                                create_thumbnail(wackybullshit1, wackybullshit2)
                        else:
                            with open(local_file_path, "wb") as image_file:
                                image_file.write(image_response.content)
                                nested_description_signal.emit(f"<h4>Saved image: {image_filename}</h4>")
                                
                                create_thumbnail(wackybullshit1, wackybullshit2)
                    elif response.status_code == 429:
                        nested_description_signal.emit(f"<h4>Failed to download image: {image_filename}. You are currently being rate limited.</h4>")
                    else:
                        nested_description_signal.emit(f"<h4>Failed to download image: {image_filename}.</h4>")
                        
            elif response.status_code == 429:
                nested_description_signal.emit(f"<h4>Request failed. You are being rate limited. Status code: {response.status_code}.</h4>")
            else:
                nested_description_signal.emit(f"<h4>Request failed. Status code: {response.status_code}.</h4>")
                
            time.sleep(random.uniform(1, 2))
    
    ## No false condition for this one
    ## Deviantart seach is pretty broken
    ## It will always return some bullshit
    ## No matter what weird string of characters you input
    ## This is why it's a "use it at your own risk" situation
    return True