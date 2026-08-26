import base64, sys
b64_str = sys.argv[1]
code = base64.b64decode(b64_str).decode('utf-8')
exec(code)
