import urllib.request
import json

url = "https://dge.dgetechs.com/service_category/categories/"
req = urllib.request.Request(url)
req.add_header("X-API-KEY", "vo59nkWcjkAtpPosuyqkaF3PDO1llaTT0QQA4JH0ECw3gLDDm9/awTin+wyPvgXLR7iLhTRuXvzs0KcuTe12xw==")

try:
    with urllib.request.urlopen(req) as response:
        html = response.read()
        data = json.loads(html)
        print("Success!")
        print(f"Number of categories returned: {len(data)}")
        for idx, cat in enumerate(data):
            print(f"  [{idx}] Name: {cat.get('name')} | ID: {cat.get('id')}")
except Exception as e:
    print("Error:", e)
