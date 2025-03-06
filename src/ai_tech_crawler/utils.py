import json
import re
import os
import logging
import tiktoken
from typing import List

from langchain_core.messages import AIMessage


def count_tokens(input_string: str) -> int:
    tokenizer = tiktoken.get_encoding("cl100k_base")
    tokens = tokenizer.encode(input_string)
    return len(tokens)

def jsonify(container, filename, obj):
    base_dir = 'output'
    int_dir = 'json_contents'
    results_dir = os.path.join(base_dir, int_dir, container)
    os.makedirs(results_dir, exist_ok=True)
    file_name = f'{filename}.json'
    file_path = os.path.join(results_dir, file_name) 
                                    
    with open(file_path, 'w') as f:
        f.write(json.dumps(obj, indent=4))
    print(f'\nStored results at `{file_path}`.\n')

def store_web_reader_contents(filename, contents):
    base_dir = 'output'
    int_dir = 'scraped_contents'
    folder_path = os.path.join(base_dir, int_dir)
    os.makedirs(folder_path, exist_ok= True)
    file_path = os.path.join(folder_path, filename)
    with open(file_path, 'w') as f:
        f.write(contents)
    logging.info(f'\n📝 Stored Scraped Contents at `{file_path}`.\n')
