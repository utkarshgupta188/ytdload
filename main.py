from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os

app = FastAPI()

# Mount the 'static' directory to serve the index.html file
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_index():
    """Serves the main HTML page."""
    return FileResponse("static/index.html")


@app.get("/download")
def download_youtube(url: str, type: str = Query("video", enum=["video", "audio"])):
    """
    Extracts the direct download link from a YouTube URL and redirects the user.
    """
    try:
        # Set yt-dlp options, including a User-Agent to mimic a browser
        ydl_opts = {
            'quiet': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
            }
        }

        if type == "video":
            ydl_opts['format'] = 'best[ext=mp4]/best'
        else:  # audio
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info without downloading the file to the server
            info = ydl.extract_info(url, download=False)
            download_url = info.get('url', None)

            if not download_url:
                raise HTTPException(status_code=500, detail="Could not extract download URL.")

            # Redirect the user's browser to the direct download URL
            return RedirectResponse(url=download_url)

    except Exception as e:
        # Print the actual error to Vercel logs for debugging
        print(f"An error occurred: {e}")
        
        # Check if the error is due to YouTube's bot detection
        if "confirm you’re not a bot" in str(e):
             raise HTTPException(status_code=403, detail="YouTube is blocking this download. This can happen with popular videos. Please try a different one.")
        
        # Raise a generic error for other issues
        raise HTTPException(status_code=400, detail="Failed to process the URL. Please check the URL and try again.")
        
