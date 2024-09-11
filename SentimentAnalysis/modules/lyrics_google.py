"""
Get Lyrics from Google using Playwright and Scrapers

This module provides a class `GetLyricsFromGoogle` to fetch lyrics from various lyrics websites via Google search.
It includes functionalities to:
- Perform Google search using Playwright.
- Extract and process lyrics from specific websites using predefined scrapers.

The class supports multiple lyrics websites and handles timeouts and errors gracefully.
"""

import asyncio
from typing import Optional, Dict, Type, List
from .lyrics_scraper import BaseLyricsScraper, Tekstowo, AZLyrics, Teksciory, Groove
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import aiohttp
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger('Google')

class GetLyricsFromGoogle:
    SCRAPER_MAP: Dict[str, Type[BaseLyricsScraper]] = {
        "tekstowo.pl": Tekstowo,
        "groove.pl": Groove,
        "teksciory.interia.pl": Teksciory,
        "azlyrics.com": AZLyrics
    }

    async def search_lyrics(self, title: str) -> Optional[str]:
        """
        Fetches lyrics for a given song title by querying Google and scraping specific websites.

        Parameters:
        title (str): The title of the song to fetch lyrics for.

        Returns:
        Optional[str]: The lyrics if found, otherwise None.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(f"https://www.google.pl/search?q={title} lyrics".replace(" ", "%20"), timeout=10000)
                response = await page.content()
                links = self._extract_links(response)

                lyrics = await self._process_links(links[:5])  # Process only first 5 links
                if lyrics:
                    logging.info("Lyrics retrieved from external source - Google")
                    return lyrics

                logger.info(f"No lyrics found for {title}")
                return None

            except PlaywrightTimeoutError:
                logger.error(f"Timeout error while searching for lyrics of '{title}'")
                return None
            except Exception as e:
                logger.error(f"An unexpected error occurred while searching for lyrics of '{title}': {e}")
                return None
            finally:
                if browser:
                    await browser.close()

    def _extract_links(self, response: str) -> List[str]:
        """
        Extracts relevant links from the Google search results.

        Parameters:
        response (str): The HTML content of the Google search results page.

        Returns:
        List[str]: A list of extracted links.
        """
        soup = BeautifulSoup(response, 'html.parser')
        return [a['href'] for a in soup.find_all('a', href=True) if any(domain in a['href'] for domain in self.SCRAPER_MAP.keys())]

    async def _process_links(self, links: List[str]) -> Optional[str]:
        """
        Processes multiple links to extract lyrics.

        Parameters:
        links (List[str]): A list of URLs to be processed.

        Returns:
        Optional[str]: The extracted lyrics if found, otherwise None.
        """
        tasks = [self._process_link(link) for link in links]
        results = await asyncio.gather(*tasks)
        return next((lyrics for lyrics in results if lyrics), None)

    async def _process_link(self, link: str) -> Optional[str]:
        """
        Processes a single link to extract lyrics using the appropriate scraper.

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
        return None
