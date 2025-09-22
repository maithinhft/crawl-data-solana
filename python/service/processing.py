import os
import random
from common import *
import multiprocessing
from .helper import load_json_file, check_exist_file, save_json_file
from .public import fetch_transaction_history_v2
import asyncio


async def single_process():
    RPC_URL = os.getenv('RPC_URL', '')
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
    volume_0_users = [user for user in list_users if user['volume'] == 0]
    volume_not_0_users = [user for user in list_users if user['volume'] != 0]
    list_users = random.sample(volume_0_users, 500) + \
        random.sample(volume_not_0_users, 500)
    random.shuffle(list_users)
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
            print(f"fetch data address: {address}")
            result['last_update_address'] = address
            if address not in result['txs']:
                result['txs'][address] = []

            before_sig = None
            if len(result['txs'][address]) != 0:
                before_sig = result['txs'][address][-1]['signature']

            fetch_txs = await fetch_transaction_history_v2(RPC_URL, address, timestamp - 30 * ONE_DAY_TIMESTAMP, before_sig)
            for tx in fetch_txs:
                result['txs'][address].append(tx)
            save_json_file('./data/transfrom_user.json', result)


def init_worker(all_rpc_urls):
    global worker_rpc_url
    process = multiprocessing.current_process()
    worker_index = process._identity[0] - 1
    assigned_rpc = all_rpc_urls[worker_index]
    worker_rpc_url = assigned_rpc


def wrap_fetch_transaction_history_v2(address: str, timestamp: int, before_sig: str | None = None):
    print(f"[Process {os.getpid()}] Fetch data address: {address}")
    fetched_txs = asyncio.run(fetch_transaction_history_v2(
        worker_rpc_url, address, timestamp, before_sig))

    return (address, fetched_txs)


def starmap_wrapper(args):
    return wrap_fetch_transaction_history_v2(*args)


async def multi_processing():
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
    volume_0_users = [user for user in list_users if user['volume'] == 0]
    volume_not_0_users = [user for user in list_users if user['volume'] != 0]
    list_users = random.sample(volume_0_users, 500) + \
        random.sample(volume_not_0_users, 500)
    random.shuffle(list_users)
    schema = load_json_file("./data/schema.json")
    timestamp = schema['timestamp']

    result = schema
    if check_exist_file('./data/transfrom_user.json'):
        result = load_json_file('./data/transfrom_user.json')

    RPC_URLS = os.getenv('RPC_URLS', 'rpc1,rpc2,rpc3,rpc4').split(',')
    num_processes = len(RPC_URLS)
    target_timestamp = timestamp - 30 * ONE_DAY_TIMESTAMP

    args_list = [
        (
            user['address'],
            target_timestamp,
            None
        )
        for user in list_users
        if user['address'] not in result['txs']
    ]

    processed_count = 0
    SAVE_BATCH_SIZE = 3

    with multiprocessing.Pool(
        processes=num_processes,
        initializer=init_worker,
        initargs=(RPC_URLS,)
    ) as pool:
        for address, query_user in pool.imap_unordered(starmap_wrapper, args_list):
            if address not in result['txs']:
                result['txs'][address] = []

            result['txs'][address].extend(query_user)
            processed_count += 1

            if processed_count % SAVE_BATCH_SIZE == 0:
                save_json_file('./data/transfrom_user.json', result)

    save_json_file('./data/transfrom_user.json', result)
