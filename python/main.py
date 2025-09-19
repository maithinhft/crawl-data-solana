import asyncio
import json
import os
from dotenv import load_dotenv
from tqdm import tqdm
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment
from solders.token.state import TokenAccount as TokenAccountState
from spl.token.constants import TOKEN_PROGRAM_ID
import argparse

from service.helper import sleep
from service.dune import fetch_data
from service.helius import fetch_multi_account_infos
from service.BotService import BotService

QUERY_ID = {
    "top_holder_sol": 5783669,
    "top_holder_wsol": 5783651,
    "top_holder_usde": 5783639,
    "top_holder_usdt": 5783568,
    "top_holder_usdc": 5776530,
}

def load_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

async def main():
    parser = argparse.ArgumentParser(description="Load environment variables from a specified file.")
    
    parser.add_argument(
        '--env-file', 
        type=str, 
        required=True,  
        help="The path to the .env file to load."
    )
    
    args = parser.parse_args()
    
    path_to_env_file = args.env_file
    
    if not os.path.exists(path_to_env_file):
        print(f"Lỗi: File môi trường không tồn tại tại đường dẫn '{path_to_env_file}'")
        return

    print(f"Đang nạp biến môi trường từ: {path_to_env_file}")
    load_dotenv(dotenv_path=path_to_env_file)
    
    HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
    HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
    connection = AsyncClient(HELIUS_RPC_URL)

    
    bot_service = BotService()

    # --- Phần 1: Tải dữ liệu từ Dune (bỏ comment nếu cần chạy lại) ---
    for key, query_id in QUERY_ID.items():
        print(f"Bắt đầu fetch data cho {key}...")
        data = await fetch_data(query_id)
        with open(f'data/{key}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Đã fetch và lưu xong data cho {key}")
        await sleep(1000)

    # --- Phần 2: Xử lý top_holder_sol ---
    print("\n--- Bắt đầu xử lý top_holder_sol ---")
    list_address_sol = load_json_file('data/top_holder_sol.json')
    users_sol = [item['address'] for item in list_address_sol[1:]] 

    print("Lấy thông tin bot status từ GMGN...")
    users_infos_sol = await bot_service.get_gmgn_users_status(users_sol)
    for item in list_address_sol:
        if item.get('address') in users_infos_sol:
            tags = users_infos_sol[item['address']]
            if tags and any('bot' in tag for tag in tags):
                item['isBot'] = True

    print("Lấy thông tin volume từ GMGN...")
    users_volume_sol = await bot_service.get_volume_gmgn_users(users_sol)
    for item in list_address_sol:
        item['volume'] = users_volume_sol.get(item.get('address'))

    transform_top_holder_sol = []
    batch_size = 100
    for i in tqdm(range(1, len(list_address_sol), batch_size), desc="Processing SOL holders"):
        batch = list_address_sol[i : i + batch_size]
        batch_addresses = [item['address'] for item in batch]
        
        try:
            account_infos = await fetch_multi_account_infos(batch_addresses)
            await sleep(100)
            
            for idx, info in enumerate(account_infos):
                original_item = batch[idx]
                if (info and info['owner'] == str(TOKEN_PROGRAM_ID) and 
                    Pubkey.from_string(original_item['address']).is_on_curve() and 
                    not original_item.get('isBot')):
                    transform_top_holder_sol.append(original_item)
        except Exception as e:
            print(f"Lỗi ở batch bắt đầu từ index {i}: {e}")

    with open('data/transform_top_holder_sol.json', 'w', encoding='utf-8') as f:
        json.dump(transform_top_holder_sol, f, ensure_ascii=False, indent=2)
    print(f"Hoàn thành transform top_holder_sol, còn lại: {len(transform_top_holder_sol)} holders")


    # --- Phần 3: Xử lý các token khác ---
    load_files = {
        "top_holder_wsol": load_json_file('data/top_holder_wsol.json'),
        "top_holder_usdc": load_json_file('data/top_holder_usdc.json'),
        "top_holder_usde": load_json_file('data/top_holder_usde.json'),
        "top_holder_usdt": load_json_file('data/top_holder_usdt.json'),
    }

    for key, list_address in load_files.items():
        print(f"\n--- Bắt đầu xử lý {key} ---")
        
        # Lấy owner nếu chưa có
        for item in tqdm(list_address, desc=f"Getting owners for {key}"):
            if not item.get('token_balance_owner'):
                try:
                    acc_info_res = await connection.get_account_info(Pubkey.from_string(item['address']))
                    if acc_info_res.value:
                        unpacked_acc = TokenAccountState.decode(acc_info_res.value.data)
                        item['token_balance_owner'] = str(unpacked_acc.owner)
                    await sleep(100)
                except Exception:
                    continue
        
        users = [item['token_balance_owner'] for item in list_address[1:] if item.get('token_balance_owner')]
        
        print(f"Lấy thông tin bot status cho {key}...")
        users_infos = await bot_service.get_gmgn_users_status(users)
        for item in list_address:
            owner = item.get('token_balance_owner')
            if owner in users_infos:
                tags = users_infos[owner]
                if tags and any('bot' in tag for tag in tags):
                    item['isBot'] = True
        
        print(f"Lấy thông tin volume cho {key}...")
        users_volumes = await bot_service.get_volume_gmgn_users(users)
        for item in list_address:
            owner = item.get('token_balance_owner')
            item['volume'] = users_volumes.get(owner)
            
        # Lọc
        transform = []
        for i in tqdm(range(1, len(list_address), batch_size), desc=f"Processing {key} holders"):
            batch = list_address[i : i + batch_size]
            batch_owners = [item['token_balance_owner'] for item in batch if item.get('token_balance_owner')]
            
            try:
                account_infos = await fetch_multi_account_infos(batch_owners)
                await sleep(100)
                for idx, info in enumerate(account_infos):
                    original_item = batch[idx]
                    if (info and info['owner'] == str(TOKEN_PROGRAM_ID) and
                        Pubkey.from_string(original_item['token_balance_owner']).is_on_curve() and
                        not original_item.get('isBot')):
                        transform.append(original_item)
            except Exception as e:
                print(f"Lỗi ở batch {key} bắt đầu từ index {i}: {e}")
        
        with open(f'data/transform_{key}.json', 'w', encoding='utf-8') as f:
            json.dump(transform, f, ensure_ascii=False, indent=2)
        print(f"Hoàn thành transform {key}, còn lại: {len(transform)} holders")
        await sleep(10000)

    await bot_service.close()
    await connection.close()

if __name__ == "__main__":
    asyncio.run(main())