from flask import Flask, request, jsonify
import instaloader
import re

app = Flask(__name__)

# Instaloader tanpa login — cuma bisa baca konten PUBLIK.
# Tanpa login, Instagram sering nge-rate-limit lebih cepat & ketat
# dibanding API berbayar (baca catatan di README soal ini).
L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
)


def extract_shortcode(url):
    """Ambil 'shortcode' dari link IG, contoh:
    https://www.instagram.com/reel/Dar24hhgjXe/ -> Dar24hhgjXe
    """
    match = re.search(r"/(p|reel|tv)/([^/?]+)", url)
    if not match:
        raise ValueError("Link Instagram tidak valid. Harus mengandung /p/, /reel/, atau /tv/")
    return match.group(2)


@app.route("/api/ig-scrape", methods=["GET"])
def scrape():
    url = request.args.get("url", "")

    if not url:
        return jsonify({"error": "Parameter 'url' wajib diisi"}), 400

    if not re.match(r"^https?://(www\.)?instagram\.com/", url):
        return jsonify({"error": "URL harus link Instagram yang valid"}), 400

    try:
        shortcode = extract_shortcode(url)
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        media = []
        if post.typename == "GraphSidecar":
            # Carousel (banyak foto/video dalam 1 post)
            for node in post.get_sidecar_nodes():
                media.append({
                    "type": "video" if node.is_video else "image",
                    "url": node.video_url if node.is_video else node.display_url,
                })
        else:
            media.append({
                "type": "video" if post.is_video else "image",
                "url": post.video_url if post.is_video else post.url,
            })

        return jsonify({
            "caption": post.caption or "",
            "media": media,
        })

    except instaloader.exceptions.ConnectionException as e:
        return jsonify({"error": "Instagram menolak/membatasi permintaan (rate limit).", "detail": str(e)}), 429
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Gagal mengambil data post.", "detail": str(e)}), 500


# Vercel otomatis mendeteksi variabel 'app' ini sebagai entry point WSGI.
