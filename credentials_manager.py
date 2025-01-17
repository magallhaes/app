import json
from cryptography.fernet import Fernet
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os

class CredentialsManager:
    def __init__(self, key_file='secret.key', credentials_file='credentials.enc'):
        self.key_file = key_file
        self.credentials_file = credentials_file
        self.key = self._load_or_create_key()
        self.fernet = Fernet(self.key)
        
    def _load_or_create_key(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as key_file:
                return key_file.read()
        else:
            # Gerar uma chave segura
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(b"SENHA_MESTRA_SEGURA"))  # Você deve alterar isso
            with open(self.key_file, 'wb') as key_file:
                key_file.write(key)
            return key
    
    def _load_credentials(self):
        if os.path.exists(self.credentials_file):
            with open(self.credentials_file, 'rb') as file:
                encrypted_data = file.read()
                decrypted_data = self.fernet.decrypt(encrypted_data)
                return json.loads(decrypted_data)
        return {}
    
    def _save_credentials(self, credentials):
        encrypted_data = self.fernet.encrypt(json.dumps(credentials).encode())
        with open(self.credentials_file, 'wb') as file:
            file.write(encrypted_data)
    
    def add_user(self, username, password, email="", name=""):
        credentials = self._load_credentials()
        if username in credentials:
            raise ValueError("Usuário já existe")
        
        credentials[username] = {
            "password": password,
            "email": email,
            "name": name
        }
        self._save_credentials(credentials)
    
    def verify_credentials(self, username, password):
        credentials = self._load_credentials()
        if username in credentials:
            return credentials[username]["password"] == password
        return False
    
    def get_user_info(self, username):
        credentials = self._load_credentials()
        return credentials.get(username, None)
    
    def remove_user(self, username):
        credentials = self._load_credentials()
        if username in credentials:
            del credentials[username]
            self._save_credentials(credentials)
            return True
        return False

# Script para inicializar os usuários padrão
def initialize_default_users():
    manager = CredentialsManager()
    try:
        manager.add_user("admin", "admin123", "admin@example.com", "Administrador")
        manager.add_user("user", "user123", "user@example.com", "Usuário Padrão")
        print("Usuários padrão criados com sucesso!")
    except ValueError as e:
        print(f"Aviso: {e}")

if __name__ == "__main__":
    initialize_default_users()