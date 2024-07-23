'''
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

    FIXME: Setup better error handling and logging
        - Retry on various error codes for the different providers
        - Rate limit handling

    --- All models tested and working ---
'''

from dotenv import load_dotenv
import os
import requests
from typing import List, Dict
import pprint

load_dotenv()

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

def gpt4o(prompt: str, max_tokens: int = 1024) -> str:
    '''
        Sends a prompt to OpenAI's GPT-4o model and returns the response
    '''
    # Set up the API endpoint and headers
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    # Set up the request payload
    payload = {
        "model": "gpt-4o",
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    # Make the API call
    response = requests.post(url, headers=headers, json=payload)
    response_json = response.json()

    # Check the response
    if response.status_code == 200:
        #pprint.pprint(f"Response: {response_json}")
        return response_json['choices'][0]['message']['content']
    else:
        pprint.pprint("Error:", response.status_code, response.text)
        return response.text

def sonnet(prompt: str, max_tokens: int = 1024) -> str:
    '''
        Sends a prompt to Anthropics Claude 3.5 Sonnet and returns the response
    '''
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": f"{ANTHROPIC_API_KEY}",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        },
        json={
            "model": "claude-3-5-sonnet-20240620",
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user", 
                    "content": prompt
                    }
            ]
        }
    )

    response_json = response.json()

    if response.status_code == 200:
        #pprint.pprint(f"Response: {response_json}")
        return response_json['content'][0]['text']
    else:
        pprint.pprint("Error:", response.status_code, response.text)
        return response.text

def groq(model: str, prompt: str) -> str:
    '''
        Sends a prompt to a model hosted by Groq and returns the response
    '''
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }],
            "model": model,
        }
    )
    json_response = response.json()

    if response.status_code == 200:
        return json_response['choices'][0]['message']['content']
    else:
        pprint.pprint(f"Error: {response.status_code}, {response.text}")
        return response.text

def llama3_8b(prompt: str) -> str:
    '''
        Sends a prompt to Groq's llama 3 8b model and returns the response
    '''

    return groq("llama3-8b-8192", prompt)

def llama3_70b(prompt: str) -> str:
    '''
        Sends a prompt to Groq's llama 3 70b model and returns the response
    '''
    
    return groq("llama3-70b-8192", prompt)

def mixtral8x7b(prompt: str) -> str:
    '''
        Sends a prompt to Groq's mixtral 8x7b model and returns the response
    '''

    return groq("mixtral-8x7b-32768", prompt)

def gemma2_9b(prompt: str) -> str:
    '''
        Sends a prompt to Groq's gemma 2 9b model and returns the response
    '''

    return groq("gemma2-9b-it", prompt)
