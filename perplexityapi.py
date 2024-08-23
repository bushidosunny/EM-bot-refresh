import requests
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
import time
import json
from prompts import *
from colorama import Fore, Style, init

init()

# Set your API key
PERPLEXITY_API_KEY = "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"

system_instructions = ddx_emma_v2

import requests
import requests
import json

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"


# system_instructions = ddx_emma_v2
system_instructions = emma_system
chat_history = ""

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {PERPLEXITY_API_KEY}"
}

while True:
    user_prompt = input("Enter your prompt: ")
    # user_input = user_prompt
    user_input = f'<CHAT HISTORY>wha\n{chat_history}\n<CHAT HISTORY>' + '\n' + user_prompt + '\n'


    if user_prompt == "exit":
        break
    
    if user_prompt:
        payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": system_instructions,
                },
                {
                    "role": "user",
                    "content": user_input
                }
            ],
            "max_tokens": 0,
            "temperature": 0.2,
            "top_p": 0.9,
            "return_citations": True,
            "return_images": False,
            "return_related_questions": True,
            "top_k": 0,
            "stream": False,
            "presence_penalty": 0,
            "frequency_penalty": 1
        }

        response = requests.post(PERPLEXITY_URL, json=payload, headers=headers)

        # Load JSON
        data = response.json()

        # Extract assistant content
        assistant_content = data['choices'][0]['message']['content']

        

        chat_history += f'User: {user_prompt}\nAssistant: {assistant_content}'

        # Display the extracted assistant content
        print(Fore.GREEN + assistant_content + Style.RESET_ALL)

        print("\n\n")
        print(Fore.BLUE + f"CHAT HISTORY: \n{chat_history}\n" + Style.RESET_ALL)