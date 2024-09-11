"""
Get Lyrics from Yahoo using AIOHTTP and Scrapers

This module provides a class `GetLyricsFromYahoo` to fetch lyrics from various lyrics websites by querying Yahoo search.
It includes functionalities to:
- Perform Yahoo search for lyrics.
- Extract and process lyrics from specific websites using predefined scrapers.

The class supports multiple lyrics websites and handles timeouts and errors gracefully.
"""

import urllib.parse
from bs4 import BeautifulSoup
from typing import Optional, Dict, Type, List
from .lyrics_scraper import BaseLyricsScraper, Tekstowo, AZLyrics, Groove, Teksciory
import aiohttp
import asyncio
import logging

# Configure logging
logger = logging.getLogger('Yahoo')

class GetLyricsFromYahoo:
    SCRAPER_MAP: Dict[str, Type[BaseLyricsScraper]] = {
        "tekstowo.pl": Tekstowo,
        "groove.pl": Groove,
        "teksciory.interia.pl": Teksciory,
        "azlyrics.com": AZLyrics
    }

    async def search_lyrics(self, title: str) -> Optional[str]:
        """
        Searches for lyrics of a given song title by querying Yahoo and scraping specific websites.

        Parameters:
        title (str): The title of the song to fetch lyrics for.

        Returns:
        Optional[str]: The lyrics if found, otherwise None.
        """
        url = f"https://search.yahoo.com/search?p={urllib.parse.quote(title + ' lyrics tekstowo groove teksciory AZLyrics')}"
        headers = {'User-Agent': 'Mozilla/5.0'}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')

                    links = self._extract_links(soup)
                    return await self._process_links(links)

        except aiohttp.ClientError as e:
            logger.error(f"Error fetching search results for '{title}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error while searching for lyrics of '{title}': {e}")
        
        return None

    def _extract_links(self, soup: BeautifulSoup) -> List[str]:
        """
        Extracts relevant links from the Yahoo search results.

        Parameters:
        soup (BeautifulSoup): The parsed HTML content of the Yahoo search results page.

        Returns:
        List[str]: A list of extracted links.
        """
        links = []
        for link in soup.find_all('a'):
            url = link.get('href')
            decoded_url = self._decode_yahoo_url(url)
            if decoded_url:
                links.append(decoded_url)
        return links[:5]  # Limit to first 5 links

    def _decode_yahoo_url(self, url: str) -> Optional[str]:
        """
        Decodes and extracts URLs from Yahoo's redirect format.

        Parameters:
        url (str): The raw URL from Yahoo search results.

        Returns:
        Optional[str]: The decoded URL if valid, otherwise None.
        """
        try:
            fields = url.split('/')
            for part in fields:
                if part.startswith('RU='):
                    decoded_url = urllib.parse.unquote(part.split('=')[1])
                    if any(domain in decoded_url for domain in self.SCRAPER_MAP.keys()):
                        return decoded_url
        except Exception as e:
            logger.warning(f"Error decoding URL {url}: {e}")
        return None

    async def _process_links(self, urls: List[str]) -> Optional[str]:
        """
        Processes multiple URLs to extract lyrics.

        Parameters:
        urls (List[str]): A list of URLs to be processed.

        Returns:
        Optional[str]: The extracted lyrics if found, otherwise None.
        """
        tasks = [self._process_link(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return next((result for result in results if isinstance(result, str)), None)

    async def _process_link(self, url: str) -> Optional[str]:
        """
        Processes a single URL to extract lyrics using the appropriate scraper.

        Parameters:
        url (str): The URL to be processed.

        Returns:
        Optional[str]: The extracted lyrics if found, otherwise None.
        """
        for domain, scraper_class in self.SCRAPER_MAP.items():
            if domain in url:
                async with scraper_class() as scraper:
                    try:
                        await asyncio.wait_for(scraper.get_data(url), timeout=10)
                        lyrics = await scraper.get_lyrics()
                        if lyrics:
                            logging.info("Lyrics retrieved from external source - Yahoo")
                            return lyrics
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout while scraping lyrics from {url}")
                    except aiohttp.ClientError as e:
                        logger.warning(f"Error scraping lyrics from {url}: {e}")
        return None
