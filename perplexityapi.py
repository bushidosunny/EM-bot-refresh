import requests
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
import time

# Set your API key
api_key = "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"

prompt = input("Enter your prompt: ")

messages = [
    {
        "role": "system",
        "content": (
            "You are an artificial intelligence assistant and you need to "
            "engage in a helpful, detailed, polite conversation with a user."
        ),
    },
    {
        "role": "user",
        "content": (
            prompt
        ),
    },
]

client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")

# # chat completion without streaming
# response = client.chat.completions.create(
#     model="llama-3.1-sonar-huge-128k-online",
#     messages=messages,
# )
# response_content = response.choices[0].message.content

# Use rich to render the Markdown content
console = Console()

# chat completion with streaming
response_stream = client.chat.completions.create(
    model="llama-3.1-sonar-huge-128k-online",
    messages=messages,
    max_tokens=4000,
    stream=True,
)

# Initialize an empty string to accumulate the response content
response_content = ""

# Process each chunk of the response as it arrives
for response in response_stream:
    chunk = response.choices[0].delta.content  # Directly access the content attribute
    response_content += chunk
    
    # Clear the console and print the accumulated content
    console.clear()
    markdown = Markdown(response_content)
    console.print(markdown)
    
    # Sleep for a short duration to avoid spamming the terminal
    time.sleep(0.1)

# Print a newline at the end for better formatting
console.print("\n")