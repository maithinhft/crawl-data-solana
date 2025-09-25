import os
import random
import asyncio
import argparse
from common import *
from service import *
from dotenv import load_dotenv

see_value = 42
random.seed(see_value)

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
    if not fetch_transform_user_file():
        return
    # await single_process()
    await multi_processing()
if __name__ == "__main__":
    asyncio.run(main())
