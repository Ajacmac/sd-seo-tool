"""
This module handles getting keyword data from the different providers
Currently only Twinword is supported, but more providers will be added
in the future.

This module handles rate limiting, with individual provider modules
providing the rate limit value for their API.
"""

import json
import logging
import time
from typing import Any, Dict, List

import keywords.db as db
from keywords.embedding import embedding_service

from .providers import twinword

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Generic, dead simple rate limiter class
    Limiting is done on a requests/minute basis

    Cannot handle multiple separate clients using the same provider simultaneously

    TODO: Maybe at some point I could implement exponential backoff
    """

    def __init__(self, calls_per_minute):
        self.calls_per_minute = calls_per_minute
        self.last_call_time = 0

    def wait(self):
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        time_to_wait = 60 / self.calls_per_minute - time_since_last_call

        if time_to_wait > 0:
            time.sleep(time_to_wait)

        self.last_call_time = time.time()


twinword_rate_limiter = RateLimiter(calls_per_minute=twinword.TWINWORD_RATE_LIMIT)

PROVIDER_TO_USE = "twinword"


def get_similar(keyword, location="CA") -> Dict[str, Any]:
    """Gets related search keywords to the provided keyword

    keyword: str    - The keyword to get similar keywords for
    location: str   - The location to get the keyword data from

    location is a two-letter country code

    sample dictionary object: {
        "bin trailer": {
            "similarity": 1,
            "search volume": "90",
            "cpc": "",
            "paid competition": "0.87"
        },
        "Bin trailer": {
            "similarity": 1,
            "search volume": "90",
            "cpc": "",
            "paid competition": "0.87"
        }
    }
    """

    cached_data = db.get_similar_keyword_search(keyword, location)
    data = None
    if cached_data:
        # logging.info(f"Using cached data for keyword '{keyword}'")
        data = json.loads(cached_data["response_json"])
    elif PROVIDER_TO_USE == "twinword":
        twinword_rate_limiter.wait()
        data = twinword.get_similar(keyword, location)
        if not data:
            logger.error(
                f"Error getting similar keywords for '{keyword}: No data returned'"
            )
            data = {}
        if not cache_data(keyword, data, location):
            logger.error(f"Failed to cache data for '{keyword}'")
    else:
        if not PROVIDER_TO_USE or PROVIDER_TO_USE.isspace():
            raise ValueError("No keyword API provider specified.")
        raise NotImplementedError(
            f"Keyword API provider '{PROVIDER_TO_USE}' is not implemented."
        )

    return data


def get_similar_multi(keywords: List, location: str = "CA") -> Dict[str, Any]:
    """
    ### Get keywords for multiple keywords with rate limiting
    returns: {
        "keyword1": get_similar(keyword1, location) (get_similar() returns a dictionary),
        "keyword2": { ... },
    }
    """

    results = {}
    for keyword in keywords:
        results[keyword] = get_similar(keyword, location)
    return results


def cache_data(keyword: str, keywords: Dict[str, Any], location: str = "CA"):
    """
    keyword: str        - The original keyword that was searched for
    keywords: List[str] - The list of keywords similar to original
    location: str       - The location the data was retrieved for

    Stores everything in the keyword cache db for later retrieval and use

    Different providers will return data differently, but for twinword
    this is supposed to take the "keywords" field from the json response

    FIXME: How should I handle errors here?
    """

    if not db.insert_similar_keyword_search(keyword, keywords, location):
        logger.error(f"Failed to cache similar keyword search for '{keyword}'")
        return False

    for kw, data in keywords.items():
        try:
            db.insert_keyword(kw, data, location)
        except Exception as e:
            logger.error(f"Error caching keyword data for '{kw}': {str(e)}")

    return True


def filter_similar_keywords(
    seed_keywords: List[str], potential_keywords: List[str], threshold: float = 0.5
) -> List[str]:
    """
    Filter potential keywords based on their similarity to seed keywords.
    """
    similar_keywords = set()
    for seed in seed_keywords:
        similar = embedding_service.find_similar_keywords(
            seed, potential_keywords, threshold
        )
        similar_keywords.update(similar)
    return list(similar_keywords)


def get_and_filter_similar(
    seed_keywords: List[str], location: str = "CA", similarity_threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Get similar keywords for multiple seed keywords and filter based on similarity.
    """
    all_similar = get_similar_multi(seed_keywords, location)
    filtered_results = {}

    for seed, similar_data in all_similar.items():
        potential_keywords = list(similar_data.keys())
        filtered_keywords = filter_similar_keywords(
            [seed], potential_keywords, similarity_threshold
        )
        filtered_results[seed] = {kw: similar_data[kw] for kw in filtered_keywords}

    return filtered_results
