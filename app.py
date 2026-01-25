from flask import Flask, render_template, request
import yt_dlp
import os

app = Flask(__name__)
# THis is route 
@app.route("/", methods=["GET", "POST"])
def index():
    video_formats = []
    audio_formats = []
    title = ""
    error = ""
    thumbnail = ""   # ALWAYS define

    if request.method == "POST":
        url = request.form.get("url")

        if not url or not url.startswith("http"):
            error = "Please enter a valid URL."
        else:
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "nocheckcertificate": True,
                "geo_bypass": True,
                "user_agent": "Mozilla/5.0",
            }

           try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        title = info.get("title", "Video")
        thumbnail = info.get("thumbnail", "")

       
except Exception as e:
    error = "Could not fetch video info (YouTube blocked or invalid URL)"
    thumbnail = ""  

            except Exception as e:
                error = "YouTube blocked this server. Try again later."

    return render_template(
        "index.html",
        title=title,
        video_formats=video_formats,
        audio_formats=audio_formats,
        thumbnail=thumbnail,
        error=error
    )



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
