import json
import os
from prompts import create_json_prompt
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def extract_json(input_text):
    def find_json_objects(text):
        """Function to find all JSON objects in the given text"""
        json_objects = []
        brace_counter = 0
        start_index = None
        
        for i, char in enumerate(text):
            if char == '{':
                if brace_counter == 0:
                    start_index = i
                brace_counter += 1
            elif char == '}':
                brace_counter -= 1
                if brace_counter == 0 and start_index is not None:
                    json_objects.append((text[start_index:i + 1], start_index, i + 1))
                    start_index = None
        
        return json_objects

    # Extract JSON objects from the text along with their positions
    json_strings_with_positions = find_json_objects(input_text)
    
    differential_diagnosis = None
    critical_actions = None

    # Placeholder for modified text
    modified_text = input_text

    for json_string, start, end in json_strings_with_positions:
        try:
            data = json.loads(json_string)
            if "differential_diagnosis" in data:
                differential_diagnosis = data
            elif "critical_actions" in data:
                critical_actions = data
            # Remove JSON from the text
            modified_text = modified_text[:start] + modified_text[end:]
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")

    # Remove all text from the first 'JSON' to the last 'json'
    first_json_index = input_text.lower().find("json")
    last_json_index = input_text.lower().rfind("json")

    if first_json_index != -1 and last_json_index != -1:
        # Remove the text segment by slicing
        modified_text = input_text[:first_json_index]

    return differential_diagnosis, critical_actions, modified_text

def remove_json_artifact():

    # Remove all text from the first 'JSON' to the last 'json'
    first_json_index = input_text.lower().find("json")
    last_json_index = input_text.lower().rfind("json")

    if first_json_index != -1 and last_json_index != -1:
        # Remove the text segment by slicing
        modified_text = input_text[:first_json_index]

    return differential_diagnosis, critical_actions, modified_text

def create_json(text):
    
    # Summarize chat history (plain_text)  
    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": create_json_prompt + "```" + text + "```" ,
            }
        ],
        model="gpt-4o-mini",
        temperature=0.0
    )
    json_data = response.choices[0].message.content
    # print chat summary

    return json_data
 