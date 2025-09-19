import os
import httpx
from .helper import sleep

async def fetch_data(query_id: int, page_size: int = 400) -> list:
    DUNE_API_KEY = os.getenv("DUNE_API_KEY", "")
    results = []
    offset = 0
    has_more = True
    headers = {'X-DUNE-API-KEY': DUNE_API_KEY}
    url = f"https://api.dune.com/api/v1/query/{query_id}/results"

    async with httpx.AsyncClient() as client:
        while has_more:
            params = {'limit': page_size, 'offset': offset}
            try:
                res = await client.get(url, headers=headers, params=params, timeout=30.0)
                res.raise_for_status() 

                data = res.json()
                rows = data.get("result", {}).get("rows")

                if rows is None:
                    print(f"Không có dữ liệu hoặc lỗi: {data}")
                    break

                results.extend(rows)
                print(f"Đã fetch {len(rows)} rows (offset={offset})")

                if len(rows) < page_size:
                    has_more = False
                else:
                    offset += page_size
                
                await sleep(1000)

            except httpx.HTTPStatusError as e:
                print(f"Lỗi HTTP khi gọi Dune API: {e.response.status_code} - {e.response.text}")
                break
            except Exception as e:
                print(f"Lỗi không xác định khi gọi Dune: {e}")
                break

    return results