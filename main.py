from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os
import requests # New import for making HTTP requests

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


def get_latest_proxy():
    """
    Fetches the latest proxy from the geonode API.
    Returns the formatted proxy URL or None if it fails.
    """
    api_url = "https://proxylist.geonode.com/api/proxy-list?limit=1&page=1&sort_by=lastChecked&sort_type=desc"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        data = response.json().get("data", [])
        if not data:
            print("Proxy API returned no data.")
            return None

        proxy_info = data[0]
        ip = proxy_info.get("ip")
        port = proxy_info.get("port")
        protocol = proxy_info.get("protocols", ["http"])[0]

        if ip and port and protocol:
            proxy_url = f"{protocol}://{ip}:{port}"
            print(f"Fetched latest proxy: {proxy_url}")
            return proxy_url
        else:
            print("Failed to parse proxy details from API response.")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching proxy: {e}")
        return None


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


@app.get("/download")
def download_youtube(url: str, type: str = Query("video", enum=["video", "audio"])):
    try:
        # Fetch a new proxy for each download attempt
        proxy = get_latest_proxy()

        ydl_opts = {
            'quiet': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
            }
        }

        # If the proxy was successfully fetched, add it to the options
        if proxy:
            ydl_opts['proxy'] = proxy
        
        if type == "video":
            ydl_opts['format'] = 'best[ext=mp4]/best'
        else:  # audio
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            download_url = info.get('url', None)

            if not download_url:
                raise HTTPException(status_code=500, detail="Could not extract download URL.")
            
            return RedirectResponse(url=download_url)

    except Exception as e:
        print(f"An error occurred: {e}")
        if "confirm you’re not a bot" in str(e):
             raise HTTPException(status_code=403, detail="YouTube is blocking this download. The fetched proxy is also blocked.")
        raise HTTPException(status_code=400, detail=f"Failed to process the URL. The fetched proxy may be offline or blocked.")
        
