"""
Module for scraping song lyrics from various websites.

This module contains classes for fetching song lyrics from services such as
Tekstowo, AZLyrics, Teksciory, and Groove. It utilizes asynchronous
processing for efficient data retrieval.
"""

from bs4 import BeautifulSoup
import aiohttp
from abc import ABC, abstractmethod
from typing import Optional
import re

# Configure logging
import logging
logger = logging.getLogger('Lyrics_Scraper')

class BaseLyricsScraper(ABC):
    """
    Base abstract class for lyrics scrapers.

    This class defines the basic structure and behavior for all
    lyrics scrapers. It provides common methods for fetching
    and processing HTML data.

    Attributes:
        session (Optional[aiohttp.ClientSession]): aiohttp session for making HTTP requests.
        data (Optional[BeautifulSoup]): BeautifulSoup object containing parsed HTML data.
    """

    def __init__(self) -> None:
        """Initialize the scraper with empty session and data attributes."""
        self.session: Optional[aiohttp.ClientSession] = None
        self.data: Optional[BeautifulSoup] = None

    async def __aenter__(self):
        """Create a new aiohttp session when entering the context."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, excc_tb):
        """Close the aiohttp session when exiting the context"""
        if self.session:
            await self.session.close()

    async def get_data(self, url: str) -> None:
        """
        Fetch HTML data from the given URL and parse it into a BeautifulSoup object.

        Args:
            url (str): The URL of the lyrics page.

        Raises:
            RuntimeError: If the session is not initialized or an error occurs during data fetching.
        """
        if not self.session:
            logger.error("Session not initialized. Use 'async with' context manager.")
            raise RuntimeError("Session not initialized. Use 'async with' context manager.")
        try:
            async with self.session.get(url) as response:
                html = await response.text()
                self.data = BeautifulSoup(html, 'html.parser')
                logger.info(f"Data extracted from {url}")
        except aiohttp.ClientError as e:
            logger.warning(f"Failed to fetch data: {str(e)}")
            raise RuntimeError(f"Failed to fetch data: {str(e)}")
        
    @abstractmethod
    async def get_lyrics(self) -> str:
        """
        Abstract method to extract lyrics from the parsed HTML data.

        Returns:
            str: The song lyrics or an error message.

        This method must be implemented by inheriting classes.
        """
        pass

class Tekstowo(BaseLyricsScraper):
    """Scraper for the Textowo service"""

    async def get_lyrics(self) -> str:
        """
        Extract lyric from the Tekstowo webpage.

        Returns:
            str: the song lyrics or an error message.
        """
        try:
            if not self.data:
                logger.warning("No data fetched. Call get_data() first. - Tekstowo")
                return None
            lyrics_div = self.data.find('div', class_='inner-text')
            if lyrics_div:
                lyrics = re.sub(r'\s+', ' ',"\n".join(line.strip() for line in lyrics_div.get_text().split("\n") if line.strip())).strip()
                logger.info(f"Lyrics found on Tekstowo: {lyrics[:50]}")
                return lyrics
        except Exception as e: 
            logger.warning(f"Lyrics not extracted properly from Tekstowo: {e}")
            return None
    
class AZLyrics(BaseLyricsScraper):
    """Scraper for the AZLyrics service."""

    async def get_lyrics(self) -> str:
        """
        Extract lyrics from the AZLyrics webpage.

        Returns:
            str: The song lyrics or an error message.
        """
        try:
            if not self.data:
                logger.warning("No data fetched. Call get_data() first. - AZLyrics")
                return None
            lyrics_div = self.data.find('div', class_='col-xs-12 col-lg-8 text-center')
            if lyrics_div:
                lyrics = [line.strip() for line in lyrics_div.stripped_strings if line.strip()][3:]
                try:
                    submit_corrections_index = lyrics.index("Submit Corrections")
                    lyrics = lyrics[:submit_corrections_index]
                except ValueError:
                    pass
            lyrics = re.sub(r'\s+', ' ', "\n".join(lyrics)).strip()
            logger.info(f"Lyrics found on AZLyrics: {lyrics[:50]}")
            return lyrics

        except Exception as e: 
            logger.warning(f"Lyrics not extracted properly from AZLyrics: {e}")
            return None

class Teksciory(BaseLyricsScraper):
    """Scraper for the Teksciory service."""

    async def get_lyrics(self) -> str:
        """
        Extract lyrics from the Teksciory webpage.

        Returns:
            str: The song lyrics or an error message.
        """
        try:
            if not self.data:
                logger.warning("No data fetched. Call get_data() first. - Teksciory")
                return None
            lyrics_div = self.data.find('div', class_='lyrics--text')
            if lyrics_div:
                lyrics = re.sub(r'\s+', ' ', lyrics_div.get_text(separator='\n')).strip()
                logger.info(f"Lyrics found on Teksciory: {lyrics[:50]}")
                return lyrics
        except Exception as e: 
            logger.warning(f"Lyrics not extracted properly from Teksciory: {e}")
            return None
        
class Groove(BaseLyricsScraper):
    """Scraper for the Groove service."""

    async def get_lyrics(self) -> str:
        """
        Extract lyrics from the Groove webpage.

        Returns:
            str: The song lyrics or an error message.
        """
        try:
            if not self.data:
                logger.warning("No data fetched. Call get_data() first. - Groove")
                return None
            lyrics_div = self.data.find('div', class_='mid-content-content song-description')
            if lyrics_div:
                lyrics =  re.sub(r'\s+', ' ', lyrics_div.get_text(separator='\n')).strip()
                logger.info(f"Lyrics found on Groove: {lyrics[:50]}")
                return lyrics
        except Exception as e: 
            logger.warning(f"Lyrics not extracted properly from Groove: {e}")
            return None
        