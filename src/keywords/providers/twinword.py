"""
Generates similar keywords for a given keyword using the Twinword API

Includes the ability to pass multiple keywords at once
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

TWINWORD_API_KEY = os.getenv("TWINWORD_API_KEY")

# 9 requests per minute. Limit is supposedly 12, but had rate limit errors at 12 and then at 10.
TWINWORD_RATE_LIMIT = 9


def get_similar(keyword, location="CA"):
    """
    keyword: str    - The keyword to get similar keywords for
    location: str   - The location to get the keyword data from

    location is a two-letter country code
    """

    url = "https://twinword-keyword-suggestion-v1.p.rapidapi.com/suggest/"

    querystring = {"phrase": keyword, "lang": "en", "loc": location}

    headers = {
        "x-rapidapi-key": TWINWORD_API_KEY,
        "x-rapidapi-host": "twinword-keyword-suggestion-v1.p.rapidapi.com",
    }

    response = requests.get(url, headers=headers, params=querystring)

    if response.status_code != 200:
        logger.error(f"Error getting similar keywords for '{keyword}': {response.text}")
        return None
    elif response.json()["result_code"] != "200":
        logger.error(
            f"Error getting similar keywords for '{keyword}': {response.json()['result_msg']}"
        )
        return None

    return response.json()["keywords"]
