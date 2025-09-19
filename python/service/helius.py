import os
import httpx
from .helper import sleep

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

async def fetch_token_holder(
    mint: str,
    limit: int | None = None,
    after_address: str | None = None,
) -> list:
    TOKEN_ACC_SIZE = 165
    accounts = []
    pagination_key = ""

    if after_address:
        pagination_key = after_address
    
    async with httpx.AsyncClient() as client:
        while True:
            filters = {
                "dataSlice": {"offset": 32, "length": 32},
                "filters": [
                    {"dataSize": TOKEN_ACC_SIZE},
                    {"memcmp": {"offset": 0, "bytes": mint}},
                ],
            }
            if pagination_key:
                filters["paginationKey"] = pagination_key

            json_body = {
                "jsonrpc": "2.0",
                "id": "1",
                "method": "getProgramAccountsV2",
                "params": [TOKEN_PROGRAM_ID, filters],
            }

            try:
                response = await client.post(URL, json=json_body, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                await sleep(1000)

                result = data.get("result", {})
                received_accounts = result.get("accounts", [])

                if received_accounts:
                    for account in received_accounts:
                        pubkey = account.get("pubkey")
                        pagination_key = pubkey
                        
                        if not limit or len(accounts) < limit:
                            accounts.append({
                                "ata": pubkey,
                                "owner": account.get("account", {}).get("data"),
                            })
                        else:
                            break
                
                print(f"Fetched {len(received_accounts)} accounts...")

                if not received_accounts or len(received_accounts) <= 1:
                    break
                if limit and len(accounts) >= limit:
                    break

            except httpx.HTTPStatusError as e:
                print(f"Lỗi HTTP: {e.response.status_code} - {e.response.text}")
                break
            except Exception as e:
                print(f"Lỗi không xác định: {e}")
                break

    return accounts

async def fetch_multi_account_infos(list_public_key: list[str]) -> list:
    async with httpx.AsyncClient() as client:
        json_body = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "getMultipleAccounts",
            "params": [list_public_key],
        }
        try:
            response = await client.post(URL, json=json_body, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise Exception(data["error"])
            return data.get("result", {}).get("value", [])
        except Exception as e:
            print(f"Lỗi khi fetch multi account infos: {e}")
            return []