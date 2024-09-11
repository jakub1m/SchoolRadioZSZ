"""
TextAnalyzer Module

This module provides the `TextAnalyzer` class which is used to analyze text content for profanities and perform language detection.
It uses Aho-Corasick automata for efficient profanity detection and supports both Polish and English languages.
Additionally, it includes methods for removing emojis from text and detecting the language of the input text.

Modules:
- `re`: Regular expressions for pattern matching.
- `typing`: Type hinting for better code clarity.
- `langdetect`: For detecting the language of the text.
- `ahocorasick`: For efficient string matching using Aho-Corasick algorithm.
- `logging`: For logging messages and errors.
- `time` and `asyncio`: For handling timing and asynchronous operations.

Classes:
- `TextAnalyzer`: The main class that provides methods to initialize profanities, remove emojis, count profanity occurrences, analyze text for profanities, and detect language.
"""

import re
from typing import List, Dict, Set
from langdetect import detect
from ahocorasick import Automaton
import logging
import asyncio

# Setup basic logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("text_analysis")

class TextAnalyzer:
    """
    A class to analyze text content for profanities and perform language detection.

    Attributes:
        profanity_pl_automaton (Automaton): Aho-Corasick automaton for Polish profanities.
        profanity_en_automaton (Automaton): Aho-Corasick automaton for English profanities.
        emoji_unicode_ranges (Set[int]): A set of Unicode code points representing emojis and special characters.

    Methods:
        initialize(): Loads profanity words into the automaton for Polish and English.
        _load_words_into_automaton(filename: str, automaton: Automaton): Loads words from a file into the Aho-Corasick automaton.
        _create_emoji_unicode_ranges() -> Set[int]: Creates a set of Unicode ranges for emojis and special characters.
        del_emoji(lyrics: str) -> str: Removes emojis from the given text.
        _count_occurrences(text: str, automaton: Automaton) -> Dict[str, int]: Counts occurrences of profane words in the text.
        analyze_profanity(text: str) -> str: Analyzes the text for profanities and returns a message based on the count.
        _language_detection(text: str) -> str: Detects the language of the given text.
    """
    
    def __init__(self) -> None:
        """
        Initializes the TextAnalyzer with empty Aho-Corasick automatons and emoji Unicode ranges.
        """
        self.profanity_pl_automaton = Automaton()
        self.profanity_en_automaton = Automaton()
        self.emoji_unicode_ranges = self._create_emoji_unicode_ranges()
        
    def initialize(self) -> None:
        """
        Loads profanity words into the Aho-Corasick automaton for Polish and English.
        """
        self._load_words_into_automaton("modules/wulgaryzmy_pl.txt", self.profanity_pl_automaton)
        self._load_words_into_automaton("modules/wulgaryzmy_en.txt", self.profanity_en_automaton)

    def _load_words_into_automaton(self, filename: str, automaton: Automaton) -> None:
        """
        Loads words from a file into an Aho-Corasick automaton.

        Parameters:
            filename (str): The path to the file containing the words.
            automaton (Automaton): The Aho-Corasick automaton to add words to.
        """
        try:
            with open(filename, "r", encoding='utf-8') as file:
                for line in file:
                    word = line.strip().lower()
                    automaton.add_word(word, word)
            automaton.make_automaton()
        except FileNotFoundError:
            logger.error(f"File not found: {filename}")

    @staticmethod
    def _create_emoji_unicode_ranges() -> Set[int]:
        """
        Creates a set of Unicode ranges for emojis and special characters.

        Returns:
            Set[int]: A set of Unicode code points representing emojis and special characters.
        """
        emoji_ranges = [
            (0x1F600, 0x1F64F),  # emoticons
            (0x1F300, 0x1F5FF),  # symbols & pictographs
            (0x1F680, 0x1F6FF),  # transport & map symbols
            (0x1F1E0, 0x1F1FF),  # flags (iOS)
            (0x2702, 0x27B0),
            (0x24C2, 0x1F251),
            (0x1F926, 0x1F937),
            (0x10000, 0x10FFFF),
            (0x2640, 0x2642), 
            (0x2600, 0x2B55),
            (0x200d, 0x200d),
            (0x23cf, 0x23cf),
            (0x23e9, 0x23e9),
            (0x231a, 0x231a),
            (0xfe0f, 0xfe0f),  # dingbats
            (0x3030, 0x3030)
        ]
        return {code_point for start, end in emoji_ranges for code_point in range(start, end + 1)}

    async def del_emoji(self, lyrics: str) -> str:
        """
        Removes emojis from the given text.

        Parameters:
            lyrics (str): The input text containing emojis.

        Returns:
            str: The text with emojis removed.
        """
        return ''.join(char for char in lyrics if ord(char) not in self.emoji_unicode_ranges)

    async def _count_occurrences(self, text: str, automaton: Automaton) -> Dict[str, int]:
        """
        Counts occurrences of profane words in the given text using the Aho-Corasick automaton.

        Parameters:
            text (str): The input text to search for profanities.
            automaton (Automaton): The Aho-Corasick automaton containing profane words.

        Returns:
            Dict[str, int]: A dictionary with profane words as keys and their counts as values.
        """
        counts = {}
        for end_index, word in automaton.iter(text):
            start_index = end_index - len(word) + 1
            if (start_index == 0 or not text[start_index - 1].isalnum()) and (end_index + 1 == len(text) or not text[end_index + 1].isalnum()):
                counts[word] = counts.get(word, 0) + 1
        return counts

    async def analyze_profanity(self, text: str) -> str:
        """
        Analyzes the text for profanities and returns a message based on the count.

        Parameters:
            text (str): The input text to analyze for profanities.

        Returns:
            str: A message indicating the level of profanity detected.
        """
        text_lower = text.lower()
        language = await self._language_detection(text_lower)
        if language not in ["pl", "en"]:
            return "Language not supported"

        profanity_pl = await self._count_occurrences(text_lower, self.profanity_pl_automaton)
        profanity_en = await self._count_occurrences(text_lower, self.profanity_en_automaton)

        combined_results = {**profanity_pl, **profanity_en}
        profanity_counter = sum(combined_results.values())

        if combined_results:
            if profanity_pl or profanity_counter > 5:
                logger.info({"profanity_pl": profanity_pl, "profanity_en": profanity_en, "message": "Too many swear words"})
                return "Too many swear words"
            else:
                logger.info({"profanity_pl": profanity_pl, "profanity_en": profanity_en, "message": "6 swear words or less"})
                return "6 swear words or less"
        else:
            logger.info("Lyrics go to NLP model")
            return "Lyrics go to NLP model"

    @staticmethod
    async def _language_detection(text: str) -> str:
        """
        Detects the language of the given text.

        Parameters:
            text (str): The input text for language detection.

        Returns:
            str: The detected language code or "unknown" if detection fails.
        """
        try:
            return detect(text)
        except Exception:
            logger.error(f"Language detection failed: {text[:50]}")
            return "unknown"
