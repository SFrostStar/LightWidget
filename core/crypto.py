import sys
import os
import hmac
import hashlib
import base64
import secrets

def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(_get_base_dir(), "data")
KEY_FILE = os.path.join(DATA_DIR, ".secret.key")
PREFIX = "ENC:v1:"

def _get_or_create_key() -> bytes:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, "rb") as f:
                key = f.read()
                if len(key) == 32:
                    return key
        except Exception:
            pass
    
    new_key = secrets.token_bytes(32)
    try:
        with open(KEY_FILE, "wb") as f:
            f.write(new_key)
        os.chmod(KEY_FILE, 0o600)
    except Exception as e:
        print(f"[Crypto] Warning saving key: {e}")
    return new_key

_KEY = None

def _get_key() -> bytes:
    global _KEY
    if _KEY is None:
        _KEY = _get_or_create_key()
    return _KEY

def encrypt_value(plain_text: str) -> str:
    if not plain_text or not isinstance(plain_text, str):
        return plain_text
    
    if plain_text.startswith(PREFIX):
        return plain_text
    
    key = _get_key()
    iv = secrets.token_bytes(16)
    data = plain_text.encode("utf-8")
    
    ciphertext = bytearray()
    block_index = 0
    for offset in range(0, len(data), 32):
        block = data[offset:offset + 32]
        counter_bytes = block_index.to_bytes(4, byteorder="big")
        keystream = hmac.new(key, iv + counter_bytes, hashlib.sha256).digest()
        for i, b in enumerate(block):
            ciphertext.append(b ^ keystream[i])
        block_index += 1
        
    payload = iv + bytes(ciphertext)
    b64 = base64.b64encode(payload).decode("ascii")
    return f"{PREFIX}{b64}"

def decrypt_value(enc_text: str) -> str:
    if not enc_text or not isinstance(enc_text, str):
        return enc_text
    
    if not enc_text.startswith(PREFIX):
        return enc_text
    
    try:
        key = _get_key()
        raw_b64 = enc_text[len(PREFIX):]
        payload = base64.b64decode(raw_b64.encode("ascii"))
        if len(payload) < 16:
            return enc_text
        
        iv = payload[:16]
        ciphertext = payload[16:]
        
        plaintext = bytearray()
        block_index = 0
        for offset in range(0, len(ciphertext), 32):
            block = ciphertext[offset:offset + 32]
            counter_bytes = block_index.to_bytes(4, byteorder="big")
            keystream = hmac.new(key, iv + counter_bytes, hashlib.sha256).digest()
            for i, b in enumerate(block):
                plaintext.append(b ^ keystream[i])
            block_index += 1
            
        return bytes(plaintext).decode("utf-8")
    except Exception as e:
        print(f"[Crypto] Decryption error: {e}")
        return enc_text
