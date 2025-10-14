from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os
import urllib.parse
import uuid

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


def normalize_proxy_string(raw_proxy: str, default_protocol: str = "http") -> str:
    """Normalize various proxy formats into a valid proxy URL."""
    if not raw_proxy:
        return None

    rp = raw_proxy.strip()

    if rp.startswith(("http://", "https://", "socks5://", "socks5h://", "socks4://")):
        proto, rest = rp.split("://", 1)
        if "@" in rest:
            creds, host = rest.split("@", 1)
            if ":" in creds:
                user, pwd = creds.split(":", 1)
                user_enc = urllib.parse.quote(user, safe='')
                pwd_enc = urllib.parse.quote(pwd, safe='')
                return f"{proto}://{user_enc}:{pwd_enc}@{host}"
        return rp

    if "@" in rp:
        creds, host = rp.split("@", 1)
        if ":" in creds:
            user, pwd = creds.split(":", 1)
            user_enc = urllib.parse.quote(user, safe='')
            pwd_enc = urllib.parse.quote(pwd, safe='')
            return f"{default_protocol}://{user_enc}:{pwd_enc}@{host}"
        user_enc = urllib.parse.quote(creds, safe='')
        return f"{default_protocol}://{user_enc}@{host}"

    if ":" in rp:
        return f"{default_protocol}://{rp}"

    return None


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


@app.get("/download")
def download_youtube(
    url: str,
    type: str = Query("video", enum=["video", "audio"])
):
    """
    Directly downloads YouTube video/audio through yt-dlp
    using proxy from environment variable PROXY_URL.
    """
    try:
        proxy_env = os.getenv("PROXY_URL")
        proxy = normalize_proxy_string(proxy_env) if proxy_env else None

        if not proxy:
            raise HTTPException(status_code=500, detail="PROXY_URL not set or invalid.")

        # Unique filename for each download
        file_id = str(uuid.uuid4())
        out_dir = "downloads"
        os.makedirs(out_dir, exist_ok=True)

        if type == "video":
            output_path = os.path.join(out_dir, f"{file_id}.mp4")
            format_selector = 'best[ext=mp4]/best'
        else:
            output_path = os.path.join(out_dir, f"{file_id}.m4a")
            format_selector = 'bestaudio[ext=m4a]/bestaudio'

        ydl_opts = {
            'quiet': True,
            'proxy': proxy,
            'outtmpl': output_path,
            'format': format_selector,
            'http_headers': {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
                )
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Download failed.")

        # Return the file as direct download
        media_type = "video/mp4" if type == "video" else "audio/m4a"
        filename = os.path.basename(output_path)

        return FileResponse(
            output_path,
            media_type=media_type,
            filename=filename,
            background=lambda: os.remove(output_path)
        )

    except Exception as e:
        print(f"Error: {e}")
        if "confirm you’re not a bot" in str(e).lower():
            raise HTTPException(status_code=403, detail="YouTube blocked this proxy.")
        raise HTTPException(status_code=400, detail="Download failed. Proxy might be offline or blocked.")
