import asyncio
import base58
import json
from pathlib import Path

async def sleep(ms: int):
    await asyncio.sleep(ms / 1000.0)

def convert_base58_to_hex(base58_string: str) -> str:
    decoded_bytes = base58.b58decode(base58_string)
    hex_string = decoded_bytes.hex()
    print(hex_string)
    return hex_string

def load_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    
def save_json_file(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"Lỗi: Không thể ghi vào file. {e}")

def check_exist_file(file_path):
    file = Path(file_path)
    return file.exists()