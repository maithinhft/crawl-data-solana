import httpx
import json
from .helper import sleep
from common.constants import LENDING, PERPS_OR_MEME
import os

async def fetch_transaction_history(address: str, timestamp: int, before_sig: str | None = None):
    ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY", "")
    URL = f"https://solana-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
    result = []
    async with httpx.AsyncClient() as client:
        while (True):
            opts = {}
            batch_size = 25
            opts['limit'] = batch_size
            opts['before'] = before_sig
            headers = {
                "Content-Type": "application/json"
            }
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    address,
                    opts
                ]
            }
            try:
                response = await client.post(URL, headers=headers, json=payload, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                await sleep(1000)

                if isinstance(data['result'], list):
                    is_stop_fetch = False
                    list_tx = []
                    for tx in data['result']:
                        before_sig = tx['signature']
                        if tx['blockTime'] >= timestamp:
                            list_tx.append(tx)
                        else:
                            is_stop_fetch = True
                            break
                    result.extend(await transform_transactions(list_tx))
                    if is_stop_fetch:
                        break
            except httpx.HTTPStatusError as e:
                print(
                    f"Lỗi HTTP: {e.response.status_code} - {e.response.text}")
                break
            except Exception as e:
                print(f"Lỗi không xác định: {e}")
                break
    return result


async def transform_transactions(list_transaction: list):
    result = []
    for tx in list_transaction:
        signature = tx['signature']
        confirmation_status = tx['confirmationStatus']
        if signature and confirmation_status == 'finalized':
            tx_info = await fetch_txs_info(signature)
            account_keys = load_account_from_tx_info(tx_info)
            is_lending = any(key in LENDING for key in account_keys)
            is_perps_or_meme = any(
                key in PERPS_OR_MEME for key in account_keys)
            tx_transform = {
                'signature': signature,
                'is_lending': is_lending,
                'is_perps_or_meme': is_perps_or_meme
            }

            result.append(tx_transform)
    return result


def load_account_from_tx_info(tx_info):
    result = []
    if tx_info['result'] and tx_info['result']['transaction'] and tx_info['result']['transaction']['message'] and tx_info['result']['transaction']['message']['accountKeys']:
        account_keys = tx_info['result']['transaction']['message']['accountKeys']
        for account_key in account_keys:
            result.append(account_key['pubkey'])
    return result


async def fetch_txs_info(signature):
    ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY", "")
    URL = f"https://solana-mainnet.g.alchemy.com/v2/{ALCHEMY_API_KEY}"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {
                "encoding": "jsonParsed",
                "maxSupportedTransactionVersion": 0
            }
        ]
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(URL, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            await sleep(200)
            return data
        except httpx.HTTPStatusError as e:
            print(f"Lỗi HTTP: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"Lỗi không xác định: {e}")
