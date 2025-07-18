from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import csv
import time
from tqdm import tqdm
import os
import math
from pathlib import Path
import asyncio
import random

async def get_text_content(element):
    """Get text content from a Playwright element."""
    if element is None:
        return "N/A"
    content = await element.text_content()
    return content.strip() if content else "N/A"

def ensure_data_dir():
    """Ensure the data directory exists and return its path"""
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    return data_dir

def save_scraped_urls(scraped_urls, filename):
    data_dir = ensure_data_dir()
    with open(data_dir / filename, 'w', encoding='utf-8') as f:
        for url in scraped_urls:
            f.write(url + '\n')

def load_scraped_urls(filename):
    data_dir = ensure_data_dir()
    filepath = data_dir / filename
    if not filepath.exists():
        return set()
    with open(filepath, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)

def save_to_csv(data, filename):
    data_dir = ensure_data_dir()
    filepath = data_dir / filename
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Product', 'Price', 'Description', 'Source'])
        writer.writerows(data)
    return filepath

async def scrape_breakout(max_products=50, headless=True):
    scraped_urls = load_scraped_urls('breakout_scraped_urls.txt')
    products_data = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            await page.goto('https://breakout.com.pk/collections/men', wait_until='networkidle')
            await asyncio.sleep(2)
            product_urls = []
            
            # Pagination loop
            while len(product_urls) < max_products:
                await page.wait_for_selector('a.product-link.cstm-url', timeout=5000)
                links = await page.query_selector_all('a.product-link.cstm-url')
                
                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        if not href.startswith('http'):
                            href = f'https://breakout.com.pk{href}'
                        if href not in product_urls and href not in scraped_urls:
                            product_urls.append(href)
                            if len(product_urls) >= max_products:
                                break
                
                if len(product_urls) >= max_products:
                    break
                
                # Try to go to next page if available
                next_btn = await page.query_selector('a[aria-label="Next"]')
                if next_btn and await next_btn.is_enabled():
                    await next_btn.click()
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(1)
                else:
                    break

            # Process found URLs
            for url in tqdm(product_urls[:max_products], desc='Breakout Products'):
                for attempt in range(2):  # Lower retry count
                    try:
                        await page.goto(url, wait_until='networkidle', timeout=8000)  # Per-page timeout
                        await page.wait_for_selector('span[data-zoom-caption]', timeout=5000)
                        
                        title = await page.query_selector('span[data-zoom-caption]')
                        title_text = await get_text_content(title)
                        
                        price = await page.query_selector('span[data-product-price]')
                        price_text = await get_text_content(price)
                        
                        description = await page.query_selector('span[style="font-size:12px;"] p')
                        desc_text = await get_text_content(description)
                        
                        products_data.append([title_text, price_text, desc_text, "Breakout"])
                        scraped_urls.add(url)
                        print(f"Breakout - Processed: {title_text}")
                        break
                    except PlaywrightTimeoutError:
                        print(f"Timeout on {url}, retrying...")
                        await asyncio.sleep(2)
                    except Exception as e:
                        print(f"Error processing {url}: {str(e)}")
                        break
                else:
                    print(f"Failed to scrape {url} after retries. Skipping.")
                await asyncio.sleep(random.uniform(0.5, 1.5))  # Small random delay
            
            await browser.close()
            
    except Exception as e:
        print(f"Error in Breakout scraper: {str(e)}")
        
    save_scraped_urls(scraped_urls, 'breakout_scraped_urls.txt')
    return products_data

async def scrape_rastah(max_products=50, headless=True):
    scraped_urls = load_scraped_urls('rastah_scraped_urls.txt')
    products_data = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            await page.goto('https://pk.rastah.co/collections/all', wait_until='networkidle')
            await asyncio.sleep(2)
            product_urls = []
            
            # Pagination loop
            while len(product_urls) < max_products:
                await page.wait_for_selector('a[href^="/collections/all/products/"]', timeout=5000)
                links = await page.query_selector_all('a[href^="/collections/all/products/"]')
                
                for link in links:
                    href = await link.get_attribute('href')
                    if href:
                        if not href.startswith('http'):
                            href = f'https://pk.rastah.co{href}'
                        if href not in product_urls and href not in scraped_urls:
                            product_urls.append(href)
                            if len(product_urls) >= max_products:
                                break
                
                if len(product_urls) >= max_products:
                    break
                
                # Try to go to next page if available
                next_btn = await page.query_selector('a[aria-label="Next"]')
                if next_btn and await next_btn.is_enabled():
                    await next_btn.click()
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(1)
                else:
                    break

            # Process found URLs
            for url in tqdm(product_urls[:max_products], desc='Rastah Products'):
                for attempt in range(2):  # Lower retry count
                    try:
                        await page.goto(url, wait_until='networkidle', timeout=8000)  # Per-page timeout
                        await page.wait_for_selector('h1.product__title', timeout=5000)
                        
                        title = await page.query_selector('h1.product__title')
                        title_text = await get_text_content(title)
                        
                        sale_price = await page.query_selector('span[data-price]')
                        sale_price_text = await get_text_content(sale_price)
                        
                        description = await page.query_selector('#accordion-content-description p')
                        desc_text = await get_text_content(description)
                        
                        products_data.append([title_text, sale_price_text, desc_text, "Rastah"])
                        scraped_urls.add(url)
                        print(f"Rastah - Processed: {title_text}")
                        break
                    except PlaywrightTimeoutError:
                        print(f"Timeout on {url}, retrying...")
                        await asyncio.sleep(2)
                    except Exception as e:
                        print(f"Error processing {url}: {str(e)}")
                        break
                else:
                    print(f"Failed to scrape {url} after retries. Skipping.")
                await asyncio.sleep(random.uniform(0.5, 1.5))  # Small random delay
            
            await browser.close()
            
    except Exception as e:
        print(f"Error in Rastah scraper: {str(e)}")
        
    save_scraped_urls(scraped_urls, 'rastah_scraped_urls.txt')
    return products_data

async def scrape_all_products(total_products=100, headless=True):
    """
    Scrape products from both sources with a combined total limit.
    Distributes the total evenly between sources.
    """
    try:
        # Calculate products per source (rounded up to ensure we get enough)
        per_source = math.ceil(total_products / 2)
        
        print("Starting scraping process...")
        print(f"Target: {total_products} total products ({per_source} per source)")
        
        # Scrape from both sources concurrently
        breakout_task = asyncio.create_task(scrape_breakout(max_products=per_source, headless=True))
        rastah_task = asyncio.create_task(scrape_rastah(max_products=per_source, headless=True))
        
        # Wait for both tasks to complete
        breakout_data, rastah_data = await asyncio.gather(breakout_task, rastah_task)
        
        # Combine and trim to total limit
        all_data = breakout_data + rastah_data
        final_data = all_data[:total_products]
        
        # Generate filenames with job ID
        breakout_file = 'breakout_products.csv'
        rastah_file = 'rastah_products.csv'
        all_file = 'all_products.csv'
        
        # Save data files
        save_to_csv(breakout_data, breakout_file)
        save_to_csv(rastah_data, rastah_file)
        save_to_csv(final_data, all_file)
        return {
            'total_scraped': len(final_data),
            'breakout_count': len(breakout_data),
            'rastah_count': len(rastah_data),
            'data': final_data,
            'files': {
                'breakout': str(Path('data') / breakout_file),
                'rastah': str(Path('data') / rastah_file),
                'all': str(Path('data') / all_file)
            }
        }
    except Exception as e:
        print(f"Scraping error: {str(e)}")
        raise

def main():
    result = asyncio.run(scrape_all_products(total_products=50, headless=False))
    print("\nScraping completed!")
    print(f"Total products scraped: {result['total_scraped']}")
    print(f"Breakout products: {result['breakout_count']}")
    print(f"Rastah products: {result['rastah_count']}")
    print("\nFiles saved:")
    for source, path in result['files'].items():
        print(f"{source}: {path}")

if __name__ == "__main__":
    main()
