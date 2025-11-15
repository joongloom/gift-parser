
# Установка

```
pip install aiohttp beautifulsoup4 lxml
git clone 
```

# Параметры get_gifts()

| **Параметр**    | **Значения**                                             |
| --------------- | -------------------------------------------------------- |
| **`type_gift`** | plushpepe, swisswatch, lootbag... (любой слаг коллекции) |
| **`filter`**    | all, auction, sold, sale (по дефолту all)                |
| **`sort`**      | price_asc, price_desc, listed, ending                    |

# Доступные данные

При вызове get_info() возвращается объект со следующими атрибутами:
- model, backdrop, symbol - атрибуты
- ton_price, usd_price - стоимость
- owner - текущий владелец
- history - список объектов OwnershipHistory (цена, дата, покупатель).

# Быстрый старт

```
import asyncio
from fragment_parser import FragmentClient

async def main():
    async with FragmentClient() as client:
        gifts = await client.get_gifts(type_gift='plushpepe', filter='sale')
        
        for gift in gifts[:3]:
            info = await gift.get_info()
            print(f"{gift.name} #{gift.id}: {gift.price} TON | Owner: {info.owner}")

if __name__ == "__main__":
    asyncio.run(main())
```