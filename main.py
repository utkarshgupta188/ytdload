from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


@app.get("/download")
def download_youtube(url: str, type: str = Query("video", enum=["video", "audio"])):
    try:
        # Get the proxy URL from the environment variables (e.g., from Vercel/Render settings)
        proxy = os.environ.get("PROXY_URL")

        ydl_opts = {
            'quiet': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
            }
        }

        # If a proxy is set in the environment, add it to the yt-dlp options
        if proxy:
            print(f"Attempting to use proxy: {proxy}") # This log will help you confirm it's working
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
             raise HTTPException(status_code=403, detail="YouTube is blocking this download. The proxy may also be blocked.")
        raise HTTPException(status_code=400, detail=f"Failed to process the URL. The proxy may be offline or blocked.")

