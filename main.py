from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os
import requests 

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


def get_google_proxy():
    """
    Fetches a list of 10 proxies, finds the first one that has been
    verified to work with Google, and returns it.
    """
    # Fetches 10 proxies, sorted by the most recently checked
    api_url = "https://proxylist.geonode.com/api/proxy-list?limit=10&page=1&sort_by=lastChecked&sort_type=desc"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()

        data = response.json().get("data", [])
        if not data:
            print("Proxy API returned no data.")
            return None

        # Loop through the list of proxies
        for proxy_info in data:
            # Check if the 'google' key is true
            if proxy_info.get("google") is True:
                ip = proxy_info.get("ip")
                port = proxy_info.get("port")
                protocol = proxy_info.get("protocols", ["http"])[0]

                if ip and port and protocol:
                    proxy_url = f"{protocol}://{ip}:{port}"
                    print(f"Found Google-compatible proxy: {proxy_url}")
                    return proxy_url # Return the first one we find

        print("No Google-compatible proxy found in the top 10.")
        return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching proxy list: {e}")
        return None


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


@app.get("/download")
def download_youtube(url: str, type: str = Query("video", enum=["video", "audio"])):
    try:
        # Fetch a Google-compatible proxy for the download attempt
        proxy = get_google_proxy()

        ydl_opts = {
            'quiet': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
            }
        }

        if proxy:
            ydl_opts['proxy'] = proxy
        
        if type == "video":
            ydl_opts['format'] = 'best[ext=mp4]/best'
        else:
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
        
