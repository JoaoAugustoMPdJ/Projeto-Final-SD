from cryptography.fernet import Fernet
import base64
import json

class SecurityHandler:
    def __init__(self, node_id, secret_key):
        # Garante 32 bytes e codificação URL-safe
        key = secret_key.ljust(32)[:32].encode()
        self.key = base64.urlsafe_b64encode(key)
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data):
        """Aceita strings ou dicionários"""
        if isinstance(data, dict):
            data = json.dumps(data)
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data):
        """Sempre retorna string"""
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
        return self.cipher.decrypt(encrypted_data).decode()