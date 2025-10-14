from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import os
import urllib.parse

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


def normalize_proxy_string(raw_proxy: str, default_protocol: str = "http") -> str:
    """
    Normalize a proxy string into a valid proxy URL.
    """
    if not raw_proxy:
        return None

    rp = raw_proxy.strip()

    # Already includes protocol
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

    # user:pass@host:port
    if "@" in rp:
        creds, host = rp.split("@", 1)
        if ":" in creds:
            user, pwd = creds.split(":", 1)
            user_enc = urllib.parse.quote(user, safe='')
            pwd_enc = urllib.parse.quote(pwd, safe='')
            return f"{default_protocol}://{user_enc}:{pwd_enc}@{host}"
        user_enc = urllib.parse.quote(creds, safe='')
        return f"{default_protocol}://{user_enc}@{host}"

    # host:port only
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
    Downloads or redirects to YouTube video/audio stream.
    Uses the proxy defined in the environment variable PROXY_URL.
    """
    try:
        proxy_env = os.getenv("PROXY_URL")
        proxy = normalize_proxy_string(proxy_env) if proxy_env else None

        if not proxy:
            raise HTTPException(status_code=500, detail="PROXY_URL environment variable is not set or invalid.")

        ydl_opts = {
            'quiet': True,
            'proxy': proxy,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
            }
        }

        if type == "video":
            ydl_opts['format'] = 'best[ext=mp4]/best'
        else:
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            download_url = info.get('url')

            if not download_url:
                raise HTTPException(status_code=500, detail="Could not extract download URL.")

            return RedirectResponse(url=download_url)

    except Exception as e:
        err = str(e)
        print(f"Error: {err}")
        if "confirm you’re not a bot" in err.lower() or "captcha" in err.lower():
            raise HTTPException(status_code=403, detail="YouTube blocked the proxy. Try another PROXY_URL.")
        raise HTTPException(status_code=400, detail="Failed to process the URL. Proxy may be offline or blocked.")
