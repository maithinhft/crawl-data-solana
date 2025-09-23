import os
import httpx
import math
from .helper import sleep


async def static_data(data):
    accounts = data['account']
    txs = data['txs']
    values = []
    for account in accounts:
        address = account['address']
        balance = format_significant(account['balance'], 2)
        total_txs = 0
        lending = 0
        perp_or_meme = 0
        volume = account['volume']
        if address in txs:
            for tx in txs[address]:
                if tx['is_lending'] == True:
                    lending += 1
                if tx['is_perps_or_meme'] == True:
                    perp_or_meme += 1
            row = [address, balance, total_txs, lending, perp_or_meme, volume]
            values.append(row)
    await update_sheet('Data', 2, 1, values)


async def update_sheet(sheet_name, start_row, start_col, values):
    GOOGLE_APP_SCRIPT = os.getenv(
        'GOOGLE_APP_SCRIPT', 'https://script.google.com')
    payload = {
        "sheetName": sheet_name,
        "startRow": start_row,
        "startCol": start_col,
        "values": values
    }
    async with httpx.AsyncClient() as client:
        try:
            resonse = await client.post(GOOGLE_APP_SCRIPT, json=payload, timeout=60.0, follow_redirects=True)
            resonse.raise_for_status()
            data = resonse.json()
            print(f"update sheet {data['status']}")
            await sleep(2000)
        except httpx.HTTPStatusError as e:
            print(
                f"Lỗi HTTP: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"Lỗi không xác định: {e}")


def format_significant(number, sig_figs):
    if number == 0:
        return "0"

    order_of_magnitude = math.floor(math.log10(abs(number)))

    decimal_places = - (order_of_magnitude - (sig_figs - 1))

    if decimal_places < 0:
        factor = 10 ** -decimal_places
        rounded_number = round(number / factor) * factor
        return f"{rounded_number:.0f}"

    return f"{number:.{decimal_places}f}"
