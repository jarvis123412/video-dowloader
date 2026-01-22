from flask import Flask, render_template, request
import yt_dlp

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    video_formats = []
    audio_formats = []
    title = ""
    error = ""

    if request.method == "POST":
        url = request.form.get("url")

        if not url or not url.startswith("http"):
            error = "Please enter a valid URL."
        else:
            ydl_opts = {
                "quiet": True,
                "skip_download": True
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get("title", "Video")
                    thumbnail = info.get("thumbnail", "")  # Get thumbnail image

                    # ---------------------------
                    # Process video formats
                    # ---------------------------
                    video_dict = {}
                    for f in info.get("formats", []):
                        size = f.get("filesize") or f.get("filesize_approx")
                        if not size:
                            continue

                        height = f.get("height")
                        if not height:
                            continue

                        # Keep largest file per resolution
                        if height not in video_dict or size > video_dict[height]["size_bytes"]:
                            video_dict[height] = {
                                "resolution": f"{height}p",
                                "ext": f["ext"],
                                "size": round(size / (1024 * 1024), 2),
                                "size_bytes": size,
                                "url": f["url"],
                                "has_audio": f.get("acodec") != "none"  # mark if it has audio
                            }

                    video_formats = list(video_dict.values())
                    video_formats.sort(key=lambda x: int(x["resolution"].replace("p", "")), reverse=True)

                    # ---------------------------
                    # Process audio-only formats
                    # ---------------------------
                    for f in info.get("formats", []):
                        size = f.get("filesize") or f.get("filesize_approx")
                        if not size:
                            continue

                        if f.get("vcodec") == "none" and f.get("acodec") != "none":
                            audio_formats.append({
                                "ext": f["ext"],
                                "size": round(size / (1024 * 1024), 2),
                                "url": f["url"]
                            })

            except Exception as e:
                error = f"Error: {str(e)}"

    else:
        thumbnail = ""

    return render_template(
        "index.html",
        title=title,
        video_formats=video_formats,
        audio_formats=audio_formats,
        thumbnail=thumbnail,
        error=error
    )

if __name__ == "__main__":
    app.run(debug=True)
