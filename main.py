import asyncio
import aiohttp
from typing import List, Optional, Literal, Union
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
from urllib.parse import urljoin

@dataclass(frozen=True, slots=True)
class OwnershipHistory:
    price: Union[float, str]
    date: str
    buyer: str

@dataclass(slots=True)
class GiftInfo:
    id: int
    type: str
    owner: str
    model: str
    backdrop: str
    symbol: str
    issued: List[str]
    ton_price: Optional[float]
    usd_price: Optional[float]
    is_sale: bool
    history: List[OwnershipHistory]

@dataclass(slots=True)
class Gift:
    id: int
    name: str
    type: str
    price: Optional[float]
    url: str
    is_sale: bool
    _parser: 'FragmentClient' = field(repr=False)

    async def get_info(self) -> GiftInfo:
        return await self._parser.get_gift_info(self.url, self.id, self.type)

class FragmentClient:
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session
        self._own_session = False
        self.base_url = "https://fragment.com"

    async def __aenter__(self):
        if not self._session:
            self._session = aiohttp.ClientSession()
            self._own_session = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._own_session and self._session:
            await self._session.close()

    async def _request(self, method: str, path: str, **kwargs) -> str:
        url = urljoin(self.base_url, path)
        async with self._session.request(method, url, **kwargs) as resp:
            return await resp.text()

    async def get_gifts(
        self, 
        type_gift: Optional[str] = None,
        filter: Literal['auction', 'all', 'sold', 'sale'] = 'all',
        sort: Optional[Literal['price_desc', 'price_asc', 'listed', 'ending']] = None
    ) -> List[Gift]:
        params = {'filter': filter}
        if sort:
            params['sort'] = sort
        
        path = f"gifts/{type_gift}" if type_gift else "gifts"
        html = await self._request("POST", path, params=params)
        soup = BeautifulSoup(html, 'lxml')
        
        items = soup.select('.tm-grid-item')
        result = []
        
        for item in items:
            href = item.get('href', '')
            g_type = href.split('/')[-1].split('-')[0]
            g_id = int(item.select_one('.item-num').text.strip()[1:])
            name = item.select_one('.item-name').text.strip()
            
            raw_price = item.select_one('.icon-ton')
            price = None
            is_sale = False
            
            if raw_price:
                try:
                    price = float(raw_price.get_text(strip=True).replace(',', ''))
                    is_sale = True
                except ValueError:
                    pass
            
            result.append(Gift(
                id=g_id,
                name=name,
                type=g_type,
                price=price,
                url=urljoin(self.base_url, href),
                is_sale=is_sale,
                _parser=self
            ))
            
        return result

    async def get_gift_info(self, url: str, gift_id: int, type_gift: str) -> GiftInfo:
        html = await self._request("GET", url)
        soup = BeautifulSoup(html, 'lxml')
        
        info_table = {}
        for row in soup.select('.tm-table-fixed tr'):
            cells = row.select('td')
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True).lower()
                info_table[key] = cells[1]

        def clean_val(key: str) -> str:
            val = info_table.get(key)
            if val is None: return "Unknown"
            text = val.get_text(strip=True)
            return text.rsplit(' ', 1)[0] if ' ' in text else text

        issued_data = info_table.get('issued')
        issued_list = issued_data.get_text(strip=True).split()[0::2] if issued_data else []

        ton_price = None
        usd_price = None
        is_sale = False

        price_box = soup.select_one('.tm-section-bid-info')
        if price_box:
            ton_el = price_box.select_one('.tm-value')
            usd_el = price_box.select_one('.tm-usd-value')
            
            if ton_el:
                try:
                    ton_raw = ton_el.find(string=True, recursive=False)
                    if ton_raw:
                        ton_price = float(ton_raw.strip().replace(',', ''))
                        is_sale = True
                except (ValueError, TypeError):
                    pass
            
            if usd_el:
                try:
                    usd_raw = usd_el.get_text(strip=True)
                    usd_price = float(usd_raw.replace('$', '').replace(',', '').replace('~', ''))
                except ValueError:
                    pass

        history = []
        for row in soup.select('.tm-table-wrap tbody tr'):
            cols = row.select('td')
            if len(cols) >= 3:
                history.append(OwnershipHistory(
                    price=cols[0].get_text(strip=True),
                    date=cols[1].get_text(strip=True),
                    buyer=cols[2].get_text(strip=True)
                ))

        return GiftInfo(
            id=gift_id,
            type=type_gift,
            owner=info_table.get('owner', BeautifulSoup('', 'lxml')).get_text(strip=True) or "Unknown",
            model=clean_val('model'),
            backdrop=clean_val('backdrop'),
            symbol=clean_val('symbol'),
            issued=issued_list,
            ton_price=ton_price,
            usd_price=usd_price,
            is_sale=is_sale,
            history=history
        )
    
async def main():
    async with FragmentClient() as client:
        gifts = await client.get_gifts(type_gift='plushpepe', filter='sale')
        
        for gift in gifts[:3]:
            info = await gift.get_info()
            print(f"{gift.name} #{gift.id}: {gift.price} TON | Owner: {info.owner}")

if __name__ == "__main__":
    asyncio.run(main())