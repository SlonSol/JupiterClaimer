import asyncio
import os
import random
import re
import traceback
from config import *
from playwright.async_api import async_playwright
from playwright.async_api._generated import Page

from utils import get_accounts, get_format_proxy, phantom_confirm_tx, retry, switch_to_page_by_title, logger


@retry(MAX_RETRY)
async def claim_jup_rewards(id, context, page: Page):

    await page.goto('https://vote.jup.ag/asr')

    await page.click(f'span:text("Connect Wallet")', timeout=5000)
    await asyncio.sleep(random.uniform(2, 3))
    await page.click('text="Phantom"', timeout=5000)
    
    extension = await switch_to_page_by_title(context, 'Phantom Wallet')
    await extension.click('button[type="submit"]', timeout=10000)
        
    await asyncio.sleep(random.uniform(2, 3))
    
    
    
    
@retry(MAX_RETRY)
async def retry_for_confirm(id, context, page: Page):
    try:
        await page.wait_for_selector('p.text-center.text-lg.font-semibold.text-v2-lily:has-text("No rewards")', timeout=2000)
        logger.error(f"{id} | Wallet not eligible")
        return
    except:
        pass
    row = await page.query_selector('tr:has-text("Staked JUP")')

    amount_element = await row.query_selector('td:nth-child(2) p')
    amount = await amount_element.inner_text()

    view_button = await row.query_selector('a:has-text("View")')
    if view_button:
        logger.warning(f"{id} | Wallet already claimed {amount} JUP")
        return

    claim_button = await row.query_selector("button:has-text('Claim')")
    await claim_button.click()
    
    await asyncio.sleep(random.uniform(1, 2))

    phantom_confirm = await phantom_confirm_tx(context)
    
    try:
        await asyncio.sleep(random.uniform(7, 10))
        row = await page.query_selector('tr:has-text("Staked JUP")')

        amount_element = await row.query_selector('td:nth-child(2) p')
        amount = await amount_element.inner_text()

        view_button = await row.query_selector('a:has-text("View")')
        if view_button:
            logger.success(f"{id} | Wallet claimed {amount} JUP")
            return
        else:
            raise ValueError("Transaction Failed")
    except:
        raise ValueError("Transaction Failed")
    
            

async def run(id, private_key, proxy, semaphore):
    async with semaphore:
        
        # 3 попытки зайти в кошелек
        for _ in range(3):
            try:
                logger.info(f"{id} | START")

                # Initialize the browser and context
                async with async_playwright() as playwright:
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        f"--disable-extensions-except={os.path.abspath('PhantomExtension')}",
                        f"--load-extension={os.path.abspath('PhantomExtension')}"
                    ]
                    if proxy is not None and USE_PROXY is True:
                        address, port, login, password = get_format_proxy(proxy)
                        context = await playwright.chromium.launch_persistent_context(
                            '',
                            headless=False,
                            user_agent=f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.{random.randint(0,10)}.0 YaBrowser/24.6.{random.randint(0,10)}.0 Safari/537.36',
                            proxy={
                            "server": f"http://{address}:{port}",
                            "username": login,
                            "password": password
                            },
                            args=args
                        )
                    else:
                        context = await playwright.chromium.launch_persistent_context(
                            '',
                            headless=False,
                            user_agent=f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.{random.randint(0,10)}.0 YaBrowser/24.6.{random.randint(0,10)}.0 Safari/537.36',
                            args=args
                        )
                    
                    await context.new_page()
    
                    page = await switch_to_page_by_title(context, 'Phantom Wallet')
                    extension_url = page.url.split('/')[2].strip()
                    
                    await page.goto(f'chrome-extension://{extension_url}/onboarding.html', timeout=5000)
                    try:
                        empty_page1 = await switch_to_page_by_title(context, '')
                        await empty_page1.close()
                        empty_page2 = await switch_to_page_by_title(context, '')
                        await empty_page2.close()
                    except:
                        pass
                    
                    await page.click('button[data-testid="create-wallet-button"]', timeout=5000)
                    await page.wait_for_selector('input', timeout=5000)
                    inputs = await page.query_selector_all('input')
                    await inputs[0].type("Password_12345")
                    await inputs[1].type("Password_12345")
                    await inputs[2].click()
                    await asyncio.sleep(random.uniform(0.5, 1))
                    await page.click('button[data-testid="onboarding-form-submit-button"]', timeout=5000)
                    await asyncio.sleep(random.uniform(0.5, 1))
                    await page.click('input[data-testid="onboarding-form-saved-secret-recovery-phrase-checkbox"]', timeout=5000)
                    await page.click('button[data-testid="onboarding-form-submit-button"]', timeout=5000)

                    await page.goto(f'chrome-extension://{extension_url}/popup.html')
                    await page.click('button[type="submit"]')
                    await page.click('div[data-testid="settings-menu-open-button"]', timeout=5000)
                    await page.click('div[data-testid="sidebar_menu-button-add_account"]', timeout=5000)
                    await page.click('//div[6]/div/div/div/div[4]', timeout=5000)
                    await page.fill('input[name="name"]', "wallet")
                    await page.fill('textarea[name="privateKey"]', private_key.strip())
                    await asyncio.sleep(random.uniform(1, 3))
                    await page.click('button[type="submit"]')
                    await asyncio.sleep(random.uniform(2, 4))
                    
                    
                    await claim_jup_rewards(id, context, page)
                    await retry_for_confirm(id, context, page)
                    
                                
                                        
                    logger.info(f"{id} | Wallet is finished work")
                    await asyncio.sleep(10)
                    
                    return
                
                
                
                
            except:
                logger.error(f"{id} | {traceback.format_exc()}") 
                await asyncio.sleep(1)
                logger.warning(f"{id} | Retry...")
            finally:
                try:
                    await context.close()
                except:
                    pass




async def main(accounts):
    semaphore = asyncio.Semaphore(THREADS_NUM)
    tasks = [run(id, private_key, proxy, semaphore) for id, private_key, proxy in accounts]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    accounts = get_accounts()
    logger.info(f"Loaded {len(accounts)} accounts")
    asyncio.run(main(accounts))
    logger.info("Wallet is finished")
    