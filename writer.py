import base64, os, sys

def write_file(path, b64_content):
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(path, 'wb') as fer:
        fer.write(base64.b64decode(b64_content))
    print(f'Written: {path}')
