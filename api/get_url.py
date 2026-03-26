import json
import yt_dlp

def handler(request):
    if request.method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": cors_headers(),
            "body": ""
        }

    if request.method != "POST":
        return response({"error": "Method not allowed"}, 405)

    try:
        body = json.loads(request.body or "{}")
        url = body.get("url", "").strip()

        if not url:
            return response({"error": "No URL provided"}, 400)

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        seen = set()

        for f in info.get("formats", []):
            if not f.get("url"):
                continue

            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            height = f.get("height")
            abr = f.get("abr")
            ext = f.get("ext", "")
            filesize = f.get("filesize") or f.get("filesize_approx")

            if vcodec != "none" and acodec != "none" and height:
                label = f"{height}p combined ({ext})"
                ftype = "video"
            elif vcodec != "none" and height:
                label = f"{height}p video-only ({ext})"
                ftype = "video"
            elif acodec != "none" and vcodec == "none":
                label = f"Audio {int(abr or 0)}kbps ({ext})" if abr else f"Audio ({ext})"
                ftype = "audio"
            else:
                continue

            if label in seen:
                continue
            seen.add(label)

            formats.append({
                "label": label,
                "type": ftype,
                "ext": ext,
                "url": f["url"],
                "filesize": filesize,
                "height": height,
                "abr": abr,
                "combined": vcodec != "none" and acodec != "none",
            })

        video_fmts = sorted(
            [f for f in formats if f["type"] == "video"],
            key=lambda x: (x.get("combined", False), x.get("height") or 0),
            reverse=True
        )

        audio_fmts = sorted(
            [f for f in formats if f["type"] == "audio"],
            key=lambda x: x.get("abr") or 0,
            reverse=True
        )

        return response({
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "uploader": info.get("uploader"),
            "view_count": info.get("view_count"),
            "formats": video_fmts + audio_fmts
        })

    except Exception as e:
        return response({"error": str(e)}, 500)


# Helper functions
def response(data, status=200):
    return {
        "statusCode": status,
        "headers": cors_headers(),
        "body": json.dumps(data)
    }

def cors_headers():
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
    }
