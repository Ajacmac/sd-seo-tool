"""
This module contains the language models that are used in the project
and provides them as convenient methods to be called from other modules.

Contains only what's needed to send messages to each language model supported

Pricing is per million tokens input/output
------------------------------------------
GPT-4o-2024-05-13   $2.50 / $ 7.50
Claude 3.5 Sonnet   $3.00 / $15.00
Groq:
    - llama 3 8b    $0.05 / $ 0.08  ~1250 tokens/s
    - llama 3 70b   $0.59 / $ 0.79  ~330 tokens/s
    - Mixtral 8x7b  $0.24 / $ 0.24  ~575 tokens/s
    - Gemma 2 9b    $0.20 / $ 0.20  ~500 tokens/s

Add pricing for:
    - Mistral's La Platforme
    - Together.ai
    - Fireworks.ai

Currently waiting on pricing and full release of llama 3.1 models on Groq

FIXME: Setup better error handling and logging
    - Retry on various error codes for the different providers
    - Rate limit handling

--- All models tested and working ---

FIXME: setup rate limiting per provider and per model
"""

import logging
import os
import pprint
import time

import requests

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

logger = logging.getLogger(__name__)


def gpt4o(prompt: str, max_tokens: int = 1024) -> str:
    """
    Sends a prompt to OpenAI's GPT-4o model and returns the response
    """
    # Set up the API endpoint and headers
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }

    # Set up the request payload
    payload = {
        "model": "gpt-4o",
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    }

    # Make the API call
    response = requests.post(url, headers=headers, json=payload)
    response_json = response.json()

    # Check the response
    if response.status_code == 200:
        # pprint.pprint(f"Response: {response_json}")
        return response_json["choices"][0]["message"]["content"]
    else:
        pprint.pprint("Error:", response.status_code, response.text)
        return response.text


def sonnet(prompt: str, max_tokens: int = 1024) -> str:
    """
    Sends a prompt to Anthropics Claude 3.5 Sonnet and returns the response

    FIXME: abstract this so I can more easily handle anthropic errors when using
    different anthropic models

    When receiving a streaming response via SSE, it’s possible that an
    error can occur after returning a 200 response, in which case error
    handling wouldn’t follow the standard Anthropic mechanisms.

    Error shapes
    Errors are always returned as JSON, with a top-level error object
    that always includes a type and message value. For example:

    JSON

    {
    "type": "error",
    "error": {
        "type": "not_found_error",
        "message": "The requested resource could not be found."
    }
    }
    In accordance with our versioning policy, we may expand the values within
    these objects, and it is possible that the type values will grow over time.

    Request id
    Every API response includes a unique request-id header. This header contains
    a value such as req_018EeWyXxfu5pfWkrYcMdjWG. When contacting support about
    a specific request, please include this ID to help us quickly resolve your issue.
    """

    while True:
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": f"{ANTHROPIC_API_KEY}",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-3-5-sonnet-20240620",
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response_json = response.json()

            # Good reponse
            if response.status_code == 200:
                # logger.info(f"Response text: {response_json["content"][0]["text"]}")
                return response_json["content"][0]["text"]

            # Responses that should be retried after a delay
            elif response.status_code == 429:
                logger.error(
                    "429 - rate_limit_error: Your account has hit a rate limit."
                )
                logger.info("Retrying in 2 seconds...")
                time.sleep(2)
            elif response.status_code == 529:
                logger.error("API is temporarily overloaded. Please try again later.")
                logger.info("Retrying in 2 seconds...")
                time.sleep(2)
            # Other errors
            elif response.status_code == 400:
                logger.error(
                    "400 - invalid_request_error: There was an issue with the format or content of your request."
                )
                return
            elif response.status_code == 401:
                logger.error(
                    "401 - authentication_error: There’s an issue with your API key."
                )
                return
            elif response.status_code == 403:
                logger.error(
                    "403 - permission_error: Your API key does not have permission to use the specified resource."
                )
                return
            elif response.status_code == 404:
                logger.error(
                    "404 - not_found_error: The requested resource was not found."
                )
                return
            elif response.status_code == 413:
                logger.error(
                    "413 - request_too_large: Request exceeds the maximum allowed number of bytes."
                )
                return
            elif response.status_code == 500:
                logger.error(
                    "500 - api_error: An unexpected error has occurred internal to Anthropic’s systems."
                )
                return
            else:
                logger.error("Unknown error:", response.status_code, response.text)
                return response.text

        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            return


def groq(model: str, prompt: str) -> str:
    """
    Sends a prompt to a model hosted by Groq and returns the response
    """
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    body = {
        "messages": [{"role": "user", "content": prompt}],
        "model": model,
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body
    )
    json_response = response.json()

    if response.status_code == 200:
        return json_response["choices"][0]["message"]["content"]
    else:
        # try a few times and sleep for 2 seconds between each try
        for i in range(3):
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=body,
            )
            json_response = response.json()
            if response.status_code == 200:
                return json_response["choices"][0]["message"]["content"]
            else:
                time.sleep(2)
        pprint.pprint(f"Error: {response.status_code}, {response.text}")
        return response.text


def mixtral8x7b(prompt: str) -> str:
    """
    Sends a prompt to Groq's mixtral 8x7b model and returns the response
    """

    return groq("mixtral-8x7b-32768", prompt)


def gemma2_9b(prompt: str) -> str:
    """
    Sends a prompt to Groq's gemma 2 9b model and returns the response
    """

    return groq("gemma2-9b-it", prompt)


def llama3_8b(prompt: str) -> str:
    """
    Sends a prompt to Groq's llama 3 8b model and returns the response
    """

    return groq("llama3-8b-8192", prompt)


def llama3_70b(prompt: str) -> str:
    """
    Sends a prompt to Groq's llama 3 70b model and returns the response
    """

    return groq("llama3-70b-8192", prompt)


def llama3_1_8b(prompt: str) -> str:
    """
    Sends a prompt to Groq's llama 3.1 8b model and returns the response
    """

    return groq("llama-3.1-8b-instant", prompt)


def llama3_1_70b(prompt: str) -> str:
    """
    Sends a prompt to Groq's llama 3.1 70b model and returns the response
    """

    return groq("llama-3.1-70b-versatile", prompt)


def llama3_1_405b(prompt: str) -> str:
    """
    Sends a prompt to Groq's llama 3.1 405b model and returns the response
    """

    return groq("llama-3.1-405b-reasoning", prompt)


def nvidia_405b(prompt: str, max_tokens: int = 1024) -> str:
    """
    Sends a prompt to Llama 3.1 405b model on Nvidia's cloud and returns the response

    base_url = "https://integrate.api.nvidia.com/v1"
    """

    # Set up the API endpoint and headers
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
    }

    # Set up the request payload
    payload = {
        "model": "meta/llama-3.1-405b-instruct",
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "top_p": 0.7,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "stream": False,
    }

    # Make the API call
    response = requests.post(url, headers=headers, json=payload)
    response_json = response.json()

    # Check the response
    if response.status_code == 200:
        # pprint.pprint(f"Response: {response_json}")
        return response_json["choices"][0]["message"]["content"]
    else:
        pprint.pprint("Error:", response.status_code, response.text)
        return response.text


def la_platforme(model: str, prompt: str) -> str:
    """
    Sends a prompt to Mistral's la-platforme model and returns the response

    FIXME: Implement this
    """

    return NotImplementedError("Mistral's la-platforme is not yet supported")


def mistral_large_2407(prompt: str) -> str:
    """
    Sends a prompt to Groq's mistral-large-2407 model and returns the response

    FIXME: Implement this
    """

    return la_platforme("mistral-large-2407", prompt)


def mistral_nemo_2407(prompt: str) -> str:
    """
    Sends a prompt to Mistral's mistral-nemo-2407 model and returns the response
    """

    return la_platforme("open-mistral-nemo-2407", prompt)
