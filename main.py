from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os

app = FastAPI()

# No need to create a downloads folder, as we won't be saving files.
# app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    # Make sure your HTML file is named 'index.html' and is in a 'static' directory
    return FileResponse("static/index.html")

@app.get("/download")
def download_youtube(url: str, type: str = Query("video", enum=["video", "audio"])):
    try:
        if type == "video":
            ydl_opts = {
                'format': 'best[ext=mp4]/best', # Prioritize mp4 for better compatibility
                'quiet': True,
            }
        else: # audio
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio', # m4a is often higher quality and available
                'quiet': True,
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # We set download=False to only extract info
            info = ydl.extract_info(url, download=False)
            
            # Find the direct URL from the extracted info
            download_url = info.get('url', None)

            if not download_url:
                raise HTTPException(status_code=500, detail="Could not extract download URL.")
            
            # Redirect the user's browser to the direct download URL
            return RedirectResponse(url=download_url)

    except Exception as e:
        # It's good practice to log the error for debugging
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to process the URL: {str(e)}")
