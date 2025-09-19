import asyncio
from playwright.async_api import async_playwright, Browser, Page
from tqdm.asyncio import tqdm

class BotService:
    browser: Browser = None
    page: Page = None

    async def _init(self):
        if not self.browser:
            p = await async_playwright().start()
            self.browser = await p.chromium.launch(headless=True)
        if not self.page:
            self.page = await self.browser.new_page()

    async def get_gmgn_users_status(self, users: list[str], chain_symbol: str = 'sol') -> dict:
        await self._init()
        await self.page.goto('https://gmgn.ai/', wait_until='networkidle', timeout=60000)
        
        users_infos = {}

        async def fetch_user_data(user):
            api_url = f"https://gmgn.ai/api/v1/wallet_stat/{chain_symbol}/{user}/7d"
            try:
                result = await self.page.evaluate(f"fetch('{api_url}').then(res => res.json())")
                await asyncio.sleep(0.2) 
                if result.get("message") == "success":
                    return result.get("data", {}).get("tags")
            except Exception as e:
                return None
            return None

        for user in tqdm(users, desc="Fetching gmgn status"):
            tags = await fetch_user_data(user)
            if tags is not None:
                users_infos[user] = tags
        
        return users_infos

    async def get_volume_gmgn_users(self, users: list[str], chain_symbol: str = 'sol') -> dict:
        await self._init()
        await self.page.goto('https://gmgn.ai/', wait_until='networkidle', timeout=60000)

        users_infos = {}

        async def fetch_user_volume(user):
            api_url = f"https://gmgn.ai/pf/api/v1/wallet/{chain_symbol}/{user}/profit_stat/30d"
            try:
                result = await self.page.evaluate(f"fetch('{api_url}').then(res => res.json())")
                await asyncio.sleep(0.2) 
                if result.get("message") == "success":
                    total_bought = int(result.get("data", {}).get("total_bought_cost", 0))
                    total_sold = int(result.get("data", {}).get("total_sold_income", 0))
                    return total_bought + total_sold
            except Exception as e:
                return None
            return None

        for user in tqdm(users, desc="Fetching gmgn volume"):
            volume = await fetch_user_volume(user)
            if volume is not None:
                users_infos[user] = volume
        
        return users_infos

    async def close(self):
        if self.browser:
            await self.browser.close()
            BotService.browser = None
            BotService.page = None