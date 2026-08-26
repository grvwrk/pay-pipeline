import base64, os, sys

def save(filepath, b64_str):
    dirname = os.path.dirname(filepath)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(base64.b64decode(b64_str))
    print(f'OK: {filepath}')

if __name__ == '__main__':
    save(sys.argv[1], sys.argv[2])
