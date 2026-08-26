import os, json, uuid, datetime
from typing import List, Optional, Dict, Any
from enum import Enum

def write(filepath, content):
    d = os.path.dirname(filepath)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Was-created: {filepath}')
