"""
Youtube Data Fetcher

This module provides a class `Youtube` to fetch and process data from YouTube videos. It includes functionalities to:
- Fetch HTML data from a YouTube video URL.
- Extract and process the video title, ensuring it does not contain any blacklisted words.
- Extract the video ID from a YouTube URL.
- Retrieve the manually created transcript of a YouTube video.

The class also manages a blacklist of words/phrases that should not appear in video titles.
"""
import os
import re
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import Optional, List
from youtube_transcript_api import YouTubeTranscriptApi
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Youtube')

class Youtube:
    def __init__(self) -> None:
        """
        Initializes the Youtube class with default settings.
        Loads the blacklist from predefined files.
        """
        self.data: Optional[BeautifulSoup] = None
        self.blacklist: List[str] = self._load_blacklist() 
    
    async def get_data(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetches HTML data from a YouTube video URL.

        Parameters:
        url (str): The URL of the YouTube video.

        Returns:
        Optional[BeautifulSoup]: Parsed HTML data or None if an error occurs.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    html = await response.text()
                    self.data = BeautifulSoup(html, "html.parser")
                    return self.data
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching data from {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching data from {url}: {e}")
            return None
        
    def _load_blacklist(self) -> List[str]:
        """
        Loads blacklisted words from predefined files.

        Returns:
        List[str]: A list of blacklisted words.
        """
        blacklist = []
        files = ['modules/wulgaryzmy_pl.txt', 'modules/wulgaryzmy_en.txt', 'modules/title_blacklist.txt']
        for file in files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    blacklist.extend([line.strip() for line in f])
            except FileNotFoundError:
                logger.warning(f"Blacklist file not found: {file}")
        return blacklist

    async def get_title(self) -> Optional[str]:
        """
        Extracts and processes the video title from the HTML data.

        Returns:
        Optional[str]: The processed video title or None if an error occurs or the title contains blacklisted words.
        """
        if not self.data:
            logger.warning("No data available. Call get_data() first.")
            return None
        
        try:
            title = self.data.title.string
            modified_title = re.sub(r"\[.*?\]|\(.*?\)| - YouTube|&amp;", "", title.split('|')[0]).strip()

            if any(re.search(rf'\b{re.escape(word)}\b', modified_title, re.IGNORECASE) for word in self.blacklist):
                logger.info(f"Title contains blacklisted word: {modified_title}")
                return None 

            return modified_title
        except AttributeError:
            logger.error("Title not found in the HTML data")
            return None
        except Exception as e:
            logger.error(f"Error processing title: {e}")
            return None

    
    async def get_video_id(self, link: str) -> Optional[str]:
        """
        Extracts the video ID from a YouTube URL.

        Parameters:
        link (str): The URL of the YouTube video.

        Returns:
        Optional[str]: The video ID or None if an error occurs.
        """
        try:
            video_id = re.search(r"v=([a-zA-Z0-9_-]{11})", link)
            return video_id.group(1) if video_id else None
        except Exception as e:
            logger.error(f"Error extracting video ID from {link}: {e}")
            return None

    async def get_lyrics(self, video_id: str) -> Optional[str]:
        """
        Retrieves the manually created transcript of a YouTube video.

        Parameters:
        video_id (str): The ID of the YouTube video.

        Returns:
        Optional[str]: The transcript text or None if an error occurs or no manual transcript is available.
        """
        if not video_id:
            logger.warning("No video ID provided")
            return None
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_manually_created_transcript(['en', 'pl'])
            text = ' '.join([fragment['text'] for fragment in transcript.fetch()])
            logger.info(f"Manual transcript found - video_id:{video_id}, language:{transcript.language_code}\n {text[:50]}")
            return text
        except Exception as e:
            logger.info(f"No manual transcript available for the video_id: {video_id}")
            return None
