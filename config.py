from enum import Enum

class AppState(Enum):
    DOWNLOAD_ONE_CHARACTER = 1
    DOWNLOAD_ALL_CHARACTERS = 2
    USE_LOCAL_IMAGES = 3

class AppConfig:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.state = AppState.DOWNLOAD_ONE_CHARACTER
        self.source_settings = {
            "safebooru": True,
            "animepictures": False,
            "danbooru": False,
            "gelbooru": False,
            "rule34xxx": False,
            "deviantart": False,
        }
        self._initialized = True

    def set_state(self, state):
        self.state = state
        
    def change_source_setting_state(self, source):
        if source in self.source_settings:
            self.source_settings[source] = not self.get_source_setting(source)
            
    def get_source_setting(self, source):
        if source in self.source_settings:
            return self.source_settings[source]
        return None
    
    def count_enabled_sources(self):
        enabled_count = sum(value for value in self.source_settings.values())
        return enabled_count