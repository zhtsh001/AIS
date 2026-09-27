import requests
import time

url = "http://localhost:4040/api/tunnels"
max_retries = 5

for i in range(max_retries):
    try:
        response = requests.get(url)
        data = response.json()
        print(data['tunnels'][0]['public_url'])
        break
    except Exception as e:
        time.sleep(1)
