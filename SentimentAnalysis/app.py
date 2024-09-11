"""
Flask application for sentiment analysis of song lyrics.

This module provides a web API for analyzing the sentiment of song lyrics
extracted from YouTube videos. It uses various modules to fetch video data,
extract lyrics, perform text analysis, and conduct sentiment analysis using
the Gemini API.

Main functionalities include:
- Extracting lyrics from YouTube videos
- Analyzing text for profanity
- Performing sentiment analysis on cleaned lyrics
- Providing a RESTful API endpoint for sentiment analysis requests

Dependencies:
- Flask for web application framework
- flask_cors for handling Cross-Origin Resource Sharing (CORS)
- asyncio for asynchronous programming
- logging for application logging
- os for environment variable access
- json for JSON manipulation
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, Union, List
import asyncio
import aiohttp
import os
import json
from itertools import cycle

from modules.youtube import Youtube
from modules.text_analysis import TextAnalyzer
from modules.main import process_song
from modules.logging_config import setup_logging
import logging

setup_logging()
logger = logging.getLogger("app.py")

app = Flask(__name__)
CORS(app)

text_analyzer = TextAnalyzer()
text_analyzer.initialize()

koyeb_urls = os.getenv("koyeb_urls").split(",")
koyeb_url_cycle = cycle(koyeb_urls)

key = os.getenv("koyeb_key")

@app.route("/sentiment", methods=["POST"])
async def analyze_sentiment() -> Dict[str, Union[float, str]]:
    """
    Analyzes the sentiment of song lyrics extracted from a YouTube video.

    This endpoint expects a POST request with a JSON payload containing a 
    YouTube video URL and optional logs flag. The song lyrics are extracted 
    and cleaned, then analyzed for profanity. If the lyrics pass the profanity 
    check, sentiment analysis is performed using the Gemini API.

    Args:
    None

    Returns:
    dict: A JSON response containing the sentiment score and possible error 
          messages. The sentiment score is 2 for errors, 1 for issues with 
          lyrics, and the actual sentiment score from the API if successful.
    """
    try:
        data = request.json
        link = data.get("URL")
        logs = data.get("LOGS", None)
        if not link:
            logging.error("No URL provided in the request")
            return jsonify({"sentiment": 2, "error": "No URL provided"}), 400

        logging.info(f"Received URL: {link}")

        youtube = Youtube()
        await youtube.get_data(link)
        title = await youtube.get_title()

        if not title:
            return jsonify({"sentiment": 2, "error": "Title issue"}), 200
        
        lyrics = await process_song(link)

        if not lyrics or len(lyrics) <= 100:
            return jsonify({"sentiment": 1, "error": "Lyrics issue"}), 200
        
        cleaned_lyrics = await text_analyzer.del_emoji(lyrics)
        vulgarity_check = await text_analyzer.analyze_profanity(cleaned_lyrics)

        if '6 swear words or less' in vulgarity_check or "Lyrics go to NLP model" in vulgarity_check:
            logging.info("Sentiment analysis initiated")
            
            sentiment_result = await analyze_sentiment_async(lyrics=cleaned_lyrics, title=title)

            logging.info(f"Sentiment result: {sentiment_result}")

            if logs == "Y":
                return jsonify(sentiment_result), 200
            else:
                return jsonify({"sentiment": sentiment_result['sentiment']}), 200

        elif 'language not supported' in vulgarity_check:
            logging.info("Language not supported")
            return jsonify({"sentiment": 2, "error": "Language not supported"}), 200
        else:
            logging.info("Too many swear words detected, unable to analyze sentiment")
            return jsonify({"sentiment": 2, "error": "Too many swear words"}), 200

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return jsonify({"sentiment": 2, "error": str(e)}), 500

async def analyze_sentiment_async(lyrics: str, title: str) -> Dict[str, Union[float, str]]:
    """
    Sends an asynchronous POST request to the sentiment analysis endpoint.

    This function sends the cleaned lyrics and song title to the sentiment 
    analysis API and handles potential errors. It retries with different URLs 
    if necessary.

    Args:
    lyrics (str): The song lyrics to be analyzed.
    title (str): The title of the song.

    Returns:
    dict: The sentiment analysis result if successful.
    None: If all attempts fail or an error occurs.
    """
    payload = {
        "lyrics": lyrics,
        "title": title,
        "key": key
    }

    for _ in range(len(koyeb_urls)):
        try:
            koyeb_url = next(koyeb_url_cycle)

            async with aiohttp.ClientSession() as session:
                async with session.post(koyeb_url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result != "null":
                            return result
                    else:
                        logger.error(f"Error: Received status code {response.status} from {koyeb_url}")
                        logger.info(f"Response content: {await response.text()}")

        except aiohttp.ClientError as e:
            logger.error(f"Request failed for {koyeb_url}: {e}")
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON response from {koyeb_url}")
        except Exception as e:
            logger.error(f"An unexpected error occurred with {koyeb_url}: {e}")

        logger.info(f"Trying next URL after failure with {koyeb_url}")

    logger.error("All URLs failed to return a valid response")
    return None
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
