import json
import yt_dlp
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        url = body.get("url", "").strip()

        if not url:
            self._json({"error": "No URL provided"}, 400)
            return

        try:
            ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
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

            self._json({
                "title": info.get("title", "Unknown"),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration"),
                "uploader": info.get("uploader", ""),
                "view_count": info.get("view_count"),
                "formats": video_fmts + audio_fmts,
            })

        except Exception as e:
            self._json({"error": str(e)}, 500)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)
