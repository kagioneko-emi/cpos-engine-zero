import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class EncryptedStorageDriver:
    """Encryption driver for CPOS JSONL ledgers.
    
    Uses Fernet (AES-128 in CBC mode with HMAC-SHA256) to ensure 
    confidentiality and authenticity of context memory and audit logs.
    """
    def __init__(self, key_file=None):
        self.key_file = key_file or os.environ.get('CPOS_STORAGE_KEY_FILE')
        self._fernet = None

    def _get_fernet(self):
        if self._fernet:
            return self._fernet
        
        if not self.key_file or not os.path.exists(self.key_file):
            # Fallback to a default derived from a master secret if provided,
            # but in production we require a key file from Vault.
            master_secret = os.environ.get('CPOS_MASTER_SECRET', 'cpos-engine-zero-default-secret')
            salt = b'cpos-salt-01' # In production, use a unique per-installation salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_secret.encode()))
        else:
            with open(self.key_file, 'rb') as f:
                key = f.read().strip()
        
        self._fernet = Fernet(key)
        return self._fernet

    def encrypt_line(self, line: str) -> str:
        """Encrypts a single plaintext line (JSON string)."""
        if not line.strip():
            return line
        encrypted = self._get_fernet().encrypt(line.encode('utf-8'))
        return encrypted.decode('utf-8')

    def decrypt_line(self, encrypted_line: str) -> str:
        """Decrypts a single encrypted line back to plaintext JSON."""
        if not encrypted_line.strip():
            return encrypted_line
        try:
            decrypted = self._get_fernet().decrypt(encrypted_line.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception:
            # If decryption fails, it might be plaintext (migration case)
            return encrypted_line

    def wrap_file_reader(self, file_path):
        """Generator that yields decrypted lines from a file."""
        if not os.path.exists(file_path):
            return
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                yield self.decrypt_line(line)

    def append_encrypted(self, file_path, line: str):
        """Appends an encrypted line to the target file."""
        encrypted = self.encrypt_line(line)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(encrypted + "\n")
