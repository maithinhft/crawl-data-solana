import httpx
import json
from .helper import sleep, save_json_file
from common.constants import LENDING, PERPS_OR_MEME
import os

async def fetch_transaction_history(RPC_URL: str, address: str, timestamp: int, before_sig: str | None = None):
    result = []
    async with httpx.AsyncClient() as client:
        while (True):
            opts = {}
            batch_size = 50
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
                response = await client.post(RPC_URL, headers=headers, json=payload, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                await sleep(2000)

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
                    result.extend(await transform_transactions(RPC_URL, list_tx))
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

async def fetch_transaction_history_v2(RPC_URL: str, address: str, timestamp: int, before_sig: str | None = None):
    result = []
    async with httpx.AsyncClient() as client:
        while (True):
            opts = {}
            batch_size = 50
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
                response = await client.post(RPC_URL, headers=headers, json=payload, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                await sleep(2000)

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
                    result.extend(await transfrom_transactions_v2(RPC_URL, list_tx))
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

async def transfrom_transactions_v2(RPC_URL: str, list_transaction: list):
    result = []
    list_sig = []
    for tx in list_transaction:
        signature = tx['signature']
        confirmation_status = tx['confirmationStatus']
        if signature and confirmation_status == 'finalized':
            list_sig.append(signature)
    list_txs_info = await fetch_txs_info_v2(RPC_URL, list_sig)
    for index, tx_info in enumerate(list_txs_info):
        signature = list_transaction[index]['signature']
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


async def transform_transactions(RPC_URL: str,list_transaction: list):
    result = []
    for tx in list_transaction:
        signature = tx['signature']
        confirmation_status = tx['confirmationStatus']
        if signature and confirmation_status == 'finalized':
            tx_info = await fetch_txs_info(RPC_URL, signature)
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
    try:
        if tx_info['result'] and tx_info['result']['transaction'] and tx_info['result']['transaction']['message'] and tx_info['result']['transaction']['message']['accountKeys']:
            account_keys = tx_info['result']['transaction']['message']['accountKeys']
            for account_key in account_keys:
                result.append(account_key['pubkey'])
    except Exception:
        pass
    return result


async def fetch_txs_info_v2(RPC_URL: str, list_signature: list):
    headers = {
        "Content-Type": "application/json"
    }
    payloads = []
    for index, signature in enumerate(list_signature):
        payloads.append({
            "jsonrpc": "2.0",
            "id": index + 1,  
            "method": "getTransaction",
            "params": [
                signature,
                {
                    "encoding": "jsonParsed",
                    "maxSupportedTransactionVersion": 0
                }
            ]
        })
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(RPC_URL, headers=headers, json=payloads, timeout=60.0)
            response.raise_for_status()
            txs_info = response.json()
            await sleep(2000)
            data = [{} for i in range(0, len(txs_info))]
            for tx_info in txs_info:
                data[tx_info['id'] - 1] = tx_info
            return data
        except httpx.HTTPStatusError as e:
            print(f"Lỗi HTTP: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"Lỗi không xác định: {e}")


async def fetch_txs_info(RPC_URL: str, signature):
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
            response = await client.post(RPC_URL, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            await sleep(200)
            return data
        except httpx.HTTPStatusError as e:
            print(f"Lỗi HTTP: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"Lỗi không xác định: {e}")


def check_signer(tx_info, signer):
    try:
        if tx_info['result'] and tx_info['result']['transaction'] and tx_info['result']['transaction']['message'] and tx_info['result']['transaction']['message']['accountKeys']:
            account_keys = tx_info['result']['transaction']['message']['accountKeys']
            for account_key in account_keys:
                if account_key['signer'] == True and account_key['pubkey'] == signer:
                    return True
    except Exception:
        pass
    return False


async def check_bot_account(RPC_URL, list_user):
    users = []
    async with httpx.AsyncClient() as client:
        for user in list_user:
            opts = {}
            opts['limit'] = 25
            headers = {
                "Content-Type": "application/json"
            }
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [
                    user['address'],
                    opts
                ]
            }
            is_bot = False
            try:
                response = await client.post(RPC_URL, headers=headers, json=payload, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                await sleep(2000)

                txs = []
                for tx in data['result']:
                    signature = tx['signature']
                    tx_info = await fetch_txs_info(signature)
                    if check_signer(tx_info, user['address']):
                        txs.append(tx)

                for index in range(1, len(txs)):
                    if txs[index-1]['blockTime'] - txs[index]['blockTime'] < 5:
                        print(user['address'],
                              txs[index-1]['blockTime'] -
                              txs[index]['blockTime'],
                              txs[index]['signature'],
                              txs[index-1]['signature'])
                        is_bot = True
            except httpx.HTTPStatusError as e:
                print(
                    f"Lỗi HTTP: {e.response.status_code} - {e.response.text}")
                break
            except Exception as e:
                print(f"Lỗi không xác định: {e}")
                break

            if not is_bot:
                users.append(user)
    return users


async def get_account_info(RPC_URL, address: str):
    async with httpx.AsyncClient() as client:
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [
                address
            ]
        }

        try:
            response = await client.post(RPC_URL, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            await sleep(2000)
            return data
        except Exception as e:
            print(e)
