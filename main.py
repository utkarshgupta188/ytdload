from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os

app = FastAPI()

# This is only needed to serve your HTML file
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


@app.get("/download")
def download_youtube(url: str, type: str = Query("video", enum=["video", "audio"])):
    try:
        # Get proxy from environment variables (optional, but good practice)
        proxy = os.environ.get("PROXY_URL")

        ydl_opts = {
            'quiet': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
            }
        }

        # Add proxy to options if it exists
        if proxy:
            ydl_opts['proxy'] = proxy
        
        if type == "video":
            ydl_opts['format'] = 'best[ext=mp4]/best'
        else:  # audio
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio'

        # 1. SERVER-SIDE: Extract the direct download link without downloading the file
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            download_url = info.get('url', None)

            if not download_url:
                raise HTTPException(status_code=500, detail="Could not extract download URL.")
            
            # 2. SERVER-SIDE: Send a redirect command to the browser
            return RedirectResponse(url=download_url)

    except Exception as e:
        # Handle errors, like YouTube blocking the request
        print(f"An error occurred: {e}")
        if "confirm you’re not a bot" in str(e):
             raise HTTPException(status_code=403, detail="YouTube is blocking this download. The proxy may also be blocked.")
        raise HTTPException(status_code=400, detail=f"Failed to process the URL. The proxy may be offline or blocked.")

# 3. BROWSER-SIDE: The browser receives the redirect and downloads the file
#    directly from the 'download_url', saving it to the user's computer.
#    Your server is no longer involved.
