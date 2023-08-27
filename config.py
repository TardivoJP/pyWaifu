import json
import os
from enum import Enum
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

CONFIG_FILE = "config.json"

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
            "safebooru": {
                "enabled": True,
                "use_api": False,
            },
            "animepictures": {
                "enabled": False,
                "use_api": False,
            },
            "danbooru": {
                "enabled": False,
                "use_api": False,
            },
            "gelbooru": {
                "enabled": False,
                "use_api": False,
            },
            "rule34xxx": {
                "enabled": False,
                "use_api": False,
            },
            "deviantart": {
                "enabled": False,
                "use_api": False,
            },
        }
        self.api_authentication = {
            "danbooru": {
                "login": "",
                "api_key": ""
            }
        }
        self._initialized = True

    def set_state(self, state):
        self.state = state
        
    def is_first_run(self):
        return not os.path.exists(CONFIG_FILE)
    
    def change_passphrase(self, old_passphrase, new_passphrase):
        try:
            self.load_config(old_passphrase)
            self.save_config(new_passphrase)
            return True
        except:
            return False
        
    def load_config(self, passphrase):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "rb") as f:
                encrypted_data = f.read()
            decrypted_data = self._decrypt(encrypted_data, passphrase)
            config = json.loads(decrypted_data)
            self.state = AppState(int(config.get("state", 1)))
            self.source_settings = config.get("source_settings", self.source_settings)
            self.api_authentication = config.get("api_authentication", self.api_authentication)

    def save_config(self, passphrase):
        config = {
            "state": self.state.value,
            "source_settings": self.source_settings,
            "api_authentication": self.api_authentication
        }
        encrypted_data = self._encrypt(json.dumps(config), passphrase)
        with open(CONFIG_FILE, "wb") as f:
            f.write(encrypted_data)
            
    def _derive_key(self, passphrase, salt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            iterations=100000,
            salt=salt,
            length=32,
            backend=default_backend()
        )
        return kdf.derive(passphrase.encode())

    def _encrypt(self, data, passphrase):
        salt = os.urandom(16)
        key = self._derive_key(passphrase, salt)

        cipher = Cipher(algorithms.AES(key), modes.CFB8(salt), backend=default_backend())
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(128).padder()

        padded_data = padder.update(data.encode()) + padder.finalize()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        return salt + encrypted_data

    def _decrypt(self, data, passphrase):
        salt = data[:16]
        encrypted_data = data[16:]
        key = self._derive_key(passphrase, salt)

        cipher = Cipher(algorithms.AES(key), modes.CFB8(salt), backend=default_backend())
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(128).unpadder()

        decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        unpadded_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()

        return unpadded_data.decode()
        
    def change_source_setting_state(self, source, setting):
        if source in self.source_settings and setting in self.source_settings[source]:
            self.source_settings[source][setting] = not self.get_source_setting(source, setting)
            
    def get_source_setting(self, source, setting):
        if source in self.source_settings and setting in self.source_settings[source]:
            return self.source_settings[source][setting]
        return None
    
    def count_enabled_sources(self):
        enabled_count = sum(1 for source_settings in self.source_settings.values() if source_settings["enabled"])
        return enabled_count
    
    def set_api_credentials(self, source, login, api_key):
        if source in self.api_authentication:
            self.api_authentication[source] = {
                "login": login,
                "api_key": api_key
            }
    
    def get_api_credentials(self, source):
        if source in self.api_authentication:
            return self.api_authentication[source]
        return None