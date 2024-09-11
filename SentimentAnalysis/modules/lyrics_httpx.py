"""
Lyrics Fetcher using HTTPX and Playwright

This module provides a class `GetLyricsByHttpx` to fetch lyrics from various lyrics websites.
It includes functionalities to:
- Fetch search results from Google using HTTPX.
- Extract and process lyrics from specific websites using predefined scrapers.
- Manage cookies required for the Google search using Playwright.

The class supports multiple lyrics websites and handles cookies for authenticated searches.
"""

import re
import json
import asyncio
import httpx
import sys
from bs4 import BeautifulSoup
from .lyrics_scraper import Tekstowo, AZLyrics, Teksciory, Groove, BaseLyricsScraper
from playwright.async_api import async_playwright
from typing import Optional, Dict, Type, List
import aiohttp
import logging

logger = logging.getLogger("httpx")

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

class GetLyricsByHttpx:
    SCRAPER_MAP: Dict[str, Type[BaseLyricsScraper]] = {
        "tekstowo.pl": Tekstowo,
        "groove.pl": Groove,
        "teksciory.interia.pl": Teksciory,
        "azlyrics.com": AZLyrics
    }

    def __init__(self):
        """
        Initializes the GetLyricsByHttpx class with default settings.
        Sets up the Google search URL and initializes cookie storage.
        """
        self.lyrics = None
        self.url = "https://www.google.pl/search?q=lyrics"
        self.cookies = None

    async def get_lyrics(self, title: str) -> Optional[str]:
        """
        Fetches lyrics for a given song title by querying Google and scraping specific websites.

        Parameters:
        title (str): The title of the song to fetch lyrics for.

        Returns:
        Optional[str]: The lyrics if found, otherwise None.
        """
        if not self.cookies:
            await self.load_cookies()

        async with httpx.AsyncClient(cookies=self.cookies) as client:
            query = f"https://www.google.pl/search?q={title}%20lyrics".replace(" ", "%20")
            try:
                response = await client.get(query, timeout=10.0)
                response.raise_for_status()
                links = self._extract_links(response.text)
                
                for link in links[:5]:
                    lyrics = await self._process_link(link)
                    if lyrics:
                        logging.info("Lyrics retrieved from external source - Httpx")
                        return lyrics

                logger.info(f"No lyrics found for {title}")
                return None
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred: {e}")
            except httpx.RequestError as e:
                logger.error(f"An error occurred while requesting {e.request.url!r}.")
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
            
            return None

    def _extract_links(self, html: str) -> List[str]:
        """
        Extracts relevant links from the Google search results.

        Parameters:
        html (str): The HTML content of the Google search results page.

        Returns:
        List[str]: A list of extracted links.
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/url?q='):
                href = href.split('/url?q=')[1].split('&')[0]
            if any(domain in href for domain in self.SCRAPER_MAP.keys()):
                links.append(href)
        return links[:5]  

    async def _process_link(self, link: str) -> Optional[str]:
        """
        Processes a link to extract lyrics using the appropriate scraper.

        Parameters:
        link (str): The URL to be processed.

        Returns:
        Optional[str]: The extracted lyrics if found, otherwise None.
        """
        for domain, scraper_class in self.SCRAPER_MAP.items():
            if domain in link:
                async with scraper_class() as scraper:
                    try:
                        await asyncio.wait_for(scraper.get_data(link), timeout=10)
                        lyrics = await scraper.get_lyrics()
                        if lyrics:
                            return lyrics
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout while scraping lyrics from {link}")
                    except aiohttp.ClientError as e:
                        logger.warning(f"Error scraping lyrics from {link}: {e}")
                    except Exception as e:
                        logger.error(f"Unexpected error while processing {link}: {e}")
        return None

    async def load_cookies(self):
        """
        Loads cookies from a file. If the file does not exist or is invalid, fetches new cookies using Playwright.
        """
        try:
            with open('modules/cookies.json', 'r') as f:
                cookie_list = json.load(f)
            self.cookies = {cookie['name']: cookie['value'] for cookie in cookie_list}
        except FileNotFoundError:
            logger.info("Cookies file not found. Fetching new cookies.")
            await self.fetch_cookies_playwright()
        except json.JSONDecodeError:
            logger.error("Error decoding cookies JSON. Fetching new cookies.")
            await self.fetch_cookies_playwright()

    async def fetch_cookies_playwright(self):
        """
        Fetches cookies using Playwright by navigating to the Google search URL and accepting cookies.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(self.url)

                # Accept all cookies
                accept_all_button = page.locator("button", has_text="Zaakceptuj wszystko")
                await accept_all_button.click()

                # Get cookies
                cookies = await page.context.cookies()

                cookie_list = [{"name": cookie["name"], "value": cookie["value"]} for cookie in cookies]

                with open('modules/cookies.json', 'w') as f:
                    json.dump(cookie_list, f, indent=2)

                self.cookies = {cookie['name']: cookie['value'] for cookie in cookie_list}
            except Exception as e:
                logger.error(f"Error fetching cookies with Playwright: {e}")
            finally:
                await browser.close()
