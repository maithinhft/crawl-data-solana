import asyncio
import os
from dotenv import load_dotenv
from tqdm import tqdm
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment
from solders.token.state import TokenAccount as TokenAccountState
from spl.token.constants import TOKEN_PROGRAM_ID
import argparse
import json
import time

from service.helper import sleep, save_json_file, load_json_file, check_exist_file
from service.dune import fetch_data
from service.helius import fetch_multi_account_infos
from service.public import fetch_transaction_history, fetch_txs_info

from common.constants import ONE_DAY_TIMESTAMP

QUERY_ID = {
    "top_holder_sol": 5783669,
    "top_holder_wsol": 5783651,
    "top_holder_usde": 5783639,
    "top_holder_usdt": 5783568,
    "top_holder_usdc": 5776530,
}


async def main():
    parser = argparse.ArgumentParser(
        description="Load environment variables from a specified file.")

    parser.add_argument(
        '--env-file',
        type=str,
        required=True,
        help="The path to the .env file to load."
    )

    args = parser.parse_args()

    path_to_env_file = args.env_file

    if not os.path.exists(path_to_env_file):
        print(
            f"Lỗi: File môi trường không tồn tại tại đường dẫn '{path_to_env_file}'")
        return

    load_dotenv(dotenv_path=path_to_env_file)
    user_dic = {}
    for key in QUERY_ID:
        transform_data = load_json_file(f"./data/transform_{key}.json")
        for user in transform_data:
            address = ''
            if key == 'top_holder_sol':
                address = user['address']
            else:
                address = user['token_balance_owner']

            if address not in user_dic:
                user_dic[address] = {
                    'address': address,
                    'balance': 0,
                    'volume': 0,
                }
            user_dic[address]['balance'] += user['usd_value']
            user_dic[address]['volume'] += user['volume']
    list_users = list(user_dic.values())

    schema = load_json_file("./data/schema.json")
    timestamp = schema['timestamp']

    result = schema
    if check_exist_file('./data/transfrom_user.json'):
        result = load_json_file('./data/transfrom_user.json')
    
    if len(result['account']) == 0:
        result['account'] = list_users

    is_start_fetch_data = False
    for user in list_users:
        address = user['address']
        if result['last_update_address'] == '' or address == result['last_update_address']:
            is_start_fetch_data = True

        if is_start_fetch_data:
            result['last_update_address'] = address
            if address not in result['txs']:
                result['txs'][address] = []

            before_sig = None
            if len(result['txs'][address]) != 0:
                before_sig = result['txs'][address][-1]['address']

            fetch_txs = await fetch_transaction_history(address, timestamp - 30 * ONE_DAY_TIMESTAMP, before_sig)
            for tx in fetch_txs:
                result['txs'][address].append(tx)
            save_json_file('./data/transfrom_user.json', result)
if __name__ == "__main__":
    asyncio.run(main())
