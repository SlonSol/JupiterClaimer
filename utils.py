import asyncio
import random
import pandas
from loguru import logger
from playwright.async_api._generated import Page

logger.add('log.log')

async def switch_to_page_by_title(context, title) -> Page:
    for _ in range(30):
        for page in context.pages:
            # print([await page.title()])
            if title == await page.title():
                await page.bring_to_front()  # Переключаемся на страницу
                # print(await page.title())
                return page
        await asyncio.sleep(0.5)
    return None  

async def phantom_confirm_tx(context):
    extension = await switch_to_page_by_title(context, 'Phantom Wallet')
    await asyncio.sleep(random.uniform(1, 2))
    await extension.click('button[data-testid="primary-button"]', timeout=20000)
    return True


def get_format_proxy(proxy):
    login_password, address_port = proxy.split('@')
    address, port = address_port.split(':')
    login, password = login_password.split(':')
    return address, port, login, password


def get_accounts():
    with open('Accounts.xlsx', 'rb') as file:
        try:
            wb = pandas.read_excel(file, sheet_name="Accounts")
        except Exception as ex:
            logger.error(ex)
            raise ex
        
        accounts_data = {}
        for index, row in wb.iterrows():
            private_key = row["Private Key"]
            proxy = row["Proxy"]
            accounts_data[int(index) + 1] = {
                "private_key": private_key,
                "proxy": proxy,
            }
                    
        accounts = []
        for k, v in accounts_data.items():
            accounts.append((
                k,
                v['private_key'], 
                v['proxy'] if isinstance(v['proxy'], str) else None,
            ))
        return accounts



from functools import wraps

def retry(max_retries):
    def decorator(func):
        @wraps(func)
        async def wrapper(id, context, page, *args, **kwargs):
            count_errors = 0
            for t in range(max_retries):
                if count_errors >= max_retries:
                    logger.error(f"{id} | Error rate of more than {max_retries} | Skip wallet...")
                    with open("failed.txt", "a") as f:
                        f.write(f"{id} | {func.__name__}")
                    return
                if count_errors > 0:
                    logger.info(f"{id} | Retry {t}/{max_retries}")
                try:
                    return await func(id, context, page, *args, **kwargs)
                except Exception as ex:
                    logger.warning(f'{id} | {ex}')
                    count_errors += 1
                    # try:
                    #     await extension.close()
                    # except:
                    #     pass
        return wrapper
    return decorator