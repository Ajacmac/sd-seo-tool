'''
    Generates similar keywords for a given keyword using the Twinword API

    Includes the ability to pass multiple keywords at once
    Handles very basic rate limiting
'''

import requests
import time

class RateLimiter:
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

# Create a RateLimiter instance
rate_limiter = RateLimiter(calls_per_minute=12)

def get_keywords(keyword, location="CA"):
    '''
        keyword: str    - The keyword to get similar keywords for
        location: str   - The location to get the keyword data from

        location is a two-letter country code
    '''
    rate_limiter.wait()  # Wait before making the API call

    url = "https://twinword-keyword-suggestion-v1.p.rapidapi.com/suggest/"

    querystring = {"phrase": keyword, "lang": "en", "loc": location}

    headers = {
        "x-rapidapi-key": "6a19c4ceecmsh39c0d43c2dce9c3p1d96d1jsnf477773be48a",
        "x-rapidapi-host": "twinword-keyword-suggestion-v1.p.rapidapi.com",
    }

    response = requests.get(url, headers=headers, params=querystring)

    return response.json()

def get_keywords_multi(phrases):
    '''
    Get keywords for multiple phrases with rate limiting
    '''
    results = {}
    for phrase in phrases:
        results[phrase] = get_keywords(phrase)
    return results