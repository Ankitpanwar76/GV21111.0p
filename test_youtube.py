from dotenv import load_dotenv
import requests
import os
from config import Config

load_dotenv()  # ✅ Make sure environment variables are loaded

API_KEY = Config.YOUTUBE_API_KEY or os.getenv('YOUTUBE_API_KEY')
if not API_KEY:
    print("❌ NO API KEY SET")
    exit()

url = 'https://www.googleapis.com/youtube/v3/search'
params = {
    'part': 'snippet',
    'q': 'WEB DEVELOPMENT playlist',
    'type': 'playlist',
    'maxResults': 5,
    'key': API_KEY
}

r = requests.get(url, params=params)
data = r.json()
print(f"Status: {r.status_code}")
if 'error' in data:
    print(f"❌ ERROR: {data['error']['message']}")
elif data.get('items'):
    print("✅ SUCCESS! Sample results:")
    for item in data['items'][:2]:
        print(f"- {item['snippet']['title']}")
else:
    print("❌ No results - try a broader query or check quota")
