"""
Main module for processing songs and extracting lyrics.

This module coordinates the process of fetching video information from YouTube,
extracting lyrics from various sources, and managing the overall flow of
the lyric extraction process.

The module provides functionality to:
- Fetch video data from YouTube
- Extract lyrics from YouTube transcripts
- Search for lyrics from external sources (Google and Yahoo)
- Handle errors and log the process

Dependencies:
- asyncio for asynchronous programming
- logging for application logging
"""

from typing import Union
from .youtube import Youtube
from .lyrics_google import GetLyricsFromGoogle
from .lyrics_yahoo import GetLyricsFromYahoo
from .lyrics_httpx import GetLyricsByHttpx
import logging

# Setup logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('process_song')

async def process_song(link: str) -> Union[str, None]:
    """
    Process a song by extracting its lyrics from various sources.

    This function attempts to extract lyrics for a given YouTube video link.
    It first tries to get the lyrics from the YouTube transcript, and if that
    fails, it searches for lyrics from external sources (Google and Yahoo).

    Args:
        link (str): The YouTube video link of the song.

    Returns:
        Union[str, None]: The extracted lyrics as a lowercase string if found,
                          None otherwise.
    """
    try:
        yt = Youtube()
        yt_html = await yt.get_data(link)
        if not yt_html:
            logger.warning(f"Failed to retrieve data from YouTube for link: {link}")
            return None

        title = await yt.get_title()
        if not title:
            logger.warning(f"Failed to retrieve title for link: {link}")
            return None

        video_id = await yt.get_video_id(link)
        if not video_id:
            logger.warning(f"Failed to retrieve video ID for link: {link}")
            return None

        youtube_transcript = await yt.get_lyrics(video_id)
        if youtube_transcript:
            return youtube_transcript.lower()

        logger.info("Trying external sources for lyrics...")

        external_sources = [
            GetLyricsByHttpx(),
            GetLyricsFromYahoo(),
            GetLyricsFromGoogle()
        ]

        for source in external_sources:
            try:
                if isinstance(source, GetLyricsByHttpx):
                    lyrics = await source.get_lyrics(title)
                else:
                    lyrics = await source.search_lyrics(title)

                if lyrics:
                    return lyrics.lower()
            except Exception as e:
                logger.warning(f"Error with {source.__class__.__name__}: {str(e)}")

        logger.warning(f"Lyrics not found for link: {link}")
        return None

    except Exception as e:
        logger.error(f"An error occurred while processing the song: {str(e)}")
        return None

if __name__ == "__main__":
    async def main():
        lyrics = await process_song("https://www.youtube.com/watch?v=ixdsZtRWO30")
        if lyrics:
            print(lyrics)
        else:
            print("Lyrics not found")

    import asyncio
    asyncio.run(main())
