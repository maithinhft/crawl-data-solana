import asyncio
import base58

async def sleep(ms: int):
    await asyncio.sleep(ms / 1000.0)

def convert_base58_to_hex(base58_string: str) -> str:
    decoded_bytes = base58.b58decode(base58_string)
    hex_string = decoded_bytes.hex()
    print(hex_string)
    return hex_string