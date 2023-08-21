# pyWaifu
## _A rather inefficient image grabber_

![N|Solid](https://i.imgur.com/OGwjR3p.png)

[Image](https://www.pixiv.net/en/artworks/108180903) credit: [Muson](https://www.pixiv.net/en/users/60300947)

pyWaifu is a desktop application built with python which combines web scraping and API calls to find and download images of specific characters depending on the parameters set by the user and [MyAnimeList's](https://myanimelist.net/) database.
It stores the images on the user's computer but also shows them on its GUI built with PyQt6.

![N|Solid](https://i.imgur.com/i1Xu8iH.png)

## Features

- Search and download images for waifus from a user's entire list
- Search and download images for waifus from a specifc anime
- Search and download images for a specific waifu
- 3 different modes, single, all and local
-- Single: downloads the first waifu found for any given anime
-- All: downloads all waifus found for any given anime
-- Local: shows what's currently stored in the user's computer
- Supports 6 different sources
-- Anime Pictures net
-- Safebooru
-- Danbooru
-- Gelbooru
-- Rule34 xxx
-- DeviantArt

## Usage

- Input just the name of a myanimelist user, anime id or character id in their respective fields and click "Find waifus" to begin the process.
- Click on the "Waifus" button to show everything the application has ever downloaded.
- Click on "Options" to modify the application's behavior.
- The actual name of an anime or character can be used to perform a search if the application's behavior is set to local images and some already exist for that search query.

## Packages used

pyWaifu was only made possible because of these amazing packages.

| Library | Link |
| ------ | ------ |
| PyQt6 | https://pypi.org/project/PyQt6/ |
| Requests | https://pypi.org/project/requests/ |
| BeautifulSoup4 | https://pypi.org/project/beautifulsoup4/ |
| Pillow | https://pypi.org/project/Pillow/ |
| OpenCV | https://pypi.org/project/opencv-python/ |
| Feedparser | https://pypi.org/project/feedparser/ |
| tqdm | https://pypi.org/project/tqdm/ |
| PyInstaller | https://pypi.org/project/pyinstaller/ |


## Future development

pyWaifu may have some more features added depending on circumstances which may include:

- More sources
- Browsing multiple source results and managing files
- Storage of image tags
- Search query improvements
