from flask import Flask, request, jsonify
import yt_dlp
import re
app = Flask(__name__)
def is_youtube_url(url):
    return bool(re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be|m\.youtube\.com)/", url))
@app.route("/api/yt-scrape", methods=["GET"])
def scrape():
    url = request.args.get("url", "")
    if not url:
        return jsonify({"error": "Parameter 'url' wajib diisi"}), 400
    if not is_youtube_url(url):
        return jsonify({"error": "URL harus link YouTube yang valid"}), 400
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
        # Berpura-pura jadi app Android YouTube, bukan browser web biasa —
        # client Android ini biasanya tidak kena pemeriksaan "sign in to
        # confirm you're not a bot" yang sering muncul dari IP server cloud.
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = info.get("formats", [])

        # Format "progresif" = video + audio jadi 1 file (paling gampang buat
        # didownload langsung, walau kualitas maksimalnya biasanya cuma 720p —
        # ini batasan dari YouTube sendiri, bukan batasan kode kita).
        progressive = [
            f for f in formats
            if f.get("acodec") != "none" and f.get("vcodec") != "none" and f.get("url")
        ]
        progressive.sort(key=lambda f: f.get("height") or 0, reverse=True)

        video_options = []
        seen_heights = set()
        for f in progressive:
            h = f.get("height")
            if h in seen_heights:
                continue
            seen_heights.add(h)
            video_options.append({
                "quality": f"{h}p" if h else (f.get("format_note") or "?"),
                "ext": f.get("ext"),
                "url": f.get("url"),
                "filesize": f.get("filesize") or f.get("filesize_approx"),
            })

        # Audio-only (buat opsi "download audio saja")
        audio_only = [
            f for f in formats
            if f.get("acodec") != "none" and f.get("vcodec") == "none" and f.get("url")
        ]
        audio_only.sort(key=lambda f: f.get("abr") or 0, reverse=True)
        best_audio = audio_only[0] if audio_only else None

        return jsonify({
            "title": info.get("title", ""),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration", 0),
            "video_options": video_options,
            "audio_option": ({
                "ext": best_audio.get("ext"),
                "url": best_audio.get("url"),
                "filesize": best_audio.get("filesize") or best_audio.get("filesize_approx"),
            } if best_audio else None),
        })
    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": "Gagal mengambil video. Cek link, atau videonya mungkin private/dibatasi wilayah.", "detail": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Terjadi kesalahan tak terduga.", "detail": str(e)}), 500
