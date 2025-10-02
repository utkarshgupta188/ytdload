from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os
import requests 

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


def get_proxy_from_api():
    """
    Fetches a list of proxies from 911proxy.com and returns the first one.
    """
    api_url = "https://www.911proxy.com/web_v1/free-proxy/list?page_size=5&page=1"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()

        proxy_list = response.json().get("data", {}).get("list", [])
        if not proxy_list:
            print("Proxy API returned no data.")
            return None

        # Use the first proxy from the list without any quality checks
        proxy_info = proxy_list[0]
        
        ip = proxy_info.get("ip")
        port = proxy_info.get("port")
        protocol_num = proxy_info.get("protocol")

        if protocol_num == 2:
            protocol_str = 'http'
        elif protocol_num == 4:
            protocol_str = 'socks5'
        else:
            print(f"Unknown protocol: {protocol_num}")
            return None

        proxy_url = f"{protocol_str}://{ip}:{port}"
        print(f"Using first available proxy: {proxy_url}")
        return proxy_url
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching proxy list: {e}")
        return None


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


@app.get("/download")
def download_youtube(url: str, type: str = Query("video", enum=["video", "audio"])):
    try:
        proxy = get_proxy_from_api()

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
        
