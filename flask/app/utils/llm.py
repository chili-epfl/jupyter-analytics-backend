# Calls an online LLM to analyze the errors of a cell and provide feedback, examples and exercises.

import requests
import json
import re

def analyze_error_cell(api_url, model, api_key, code_input, traceback):
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    context = (
        "You are a Python programming tutor analyzing student work from a Jupyter notebook. "
        "Your task is to:\n"
        "1. Identify and explain errors about Python and any libraries used\n"
        "2. Provide corrected examples showcasing this kind of errors\n"
        "3. Suggest targeted exercises\n\n"
        "The student's work consists of a code cell with its output:"
    )

    format_instructions = (
        "You MUST format your response as JSON with exactly these fields:\n"
        "{\n"
        "  \"explanation\": \"<detailed error explanation>\",\n"
        "  \"examples\": [\"<corrected example 1>\", \"<corrected example 2>\"],\n"
        "  \"exercises\": [\"<practice exercise 1>\", \"<practice exercise 2>\"]\n"
        "}\n"
        "The JSON should be valid and parsable. Do not include any text outside the JSON structure."
    )

    messages = [
        {
            "role": "system",
            "content": "You are an experienced Python tutor specializing in explaining programming errors."
        },
        {
            "role": "system",
            "content": format_instructions
        },
        {
            "role": "user",
            "content": context
        },
        {
            "role": "user",
            "content": f"Code cell:\n{code_input}"
        },
        {
            "role": "assistant",
            "content": f"Output cell:\n{traceback}"
        },
        {
            "role": "user",
            "content": (
                "Based on this code, please:\n"
                "1. Identify and explain the error\n"
                "2. Provide 1-2 corrected code examples\n"
                "3. Suggest 1-2 related practice exercises\n"
                "Respond with ONLY the JSON format specified."
            )
        },
    ]

    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,  # Slightly creative for better explanations
        "response_format": {"type": "json_object"},  # Explicitly request JSON output
    }
    
    response = requests.post(api_url, headers=headers, json=data)
    
    if response.status_code == 200:
        try:
            content = response.json()['choices'][0]['message']['content']

            # Remove content between <think> tags (including the tags themselves)
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
            content = content.replace('<think>', '').replace('</think>', '')
            content = content.strip()            
            
            # Parse it to ensure it's valid JSON
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Failed to get analysis: {str(e)}. Please retry.")
    else:
        response.raise_for_status()