"""
This module is used for defining custom parsers to process and transform data 
into desired formats.
"""

# Set up a custom output parser

import json
import re

from typing import List

from langchain_core.messages import AIMessage


def extract_json(message: AIMessage) -> List[dict]:
    """Extracts JSON content from a string where JSON is embedded between \`\`\`json and \`\`\` tags.

    Parameters:
        text (str): The text containing the JSON content.

    Returns:
        list: A list of extracted JSON strings.
    """
    text = message.content
    # Define the regular expression pattern to match JSON blocks
    pattern = r"```json(.*?)```"

    # Find all non-overlapping matches of the pattern in the string
    matches = re.findall(pattern, text, re.DOTALL)

    # Return the list of matched JSON strings, stripping any leading or trailing whitespace
    output = []
    for match in matches:
        try:
            output.append(json.loads(match.strip()))
        except Exception as e:
            msg = f"Failed to parse: {text}\nException :: {e.__str__()}"
            print(msg)
            # output.append({'products': []})
    return output

def json_parser(message: AIMessage) -> dict:
    """Extracts JSON content from a string where JSON is embedded between \`\`\`json and \`\`\` tags.

    Parameters:
        text (str): The text containing the JSON content.

    Returns:
        dict: Extracted JSON strings as a python dict object.
    """
    result = extract_json(message=message)
    if result:
        return result[0]
    

