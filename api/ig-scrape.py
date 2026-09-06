from flask import Flask, request, jsonify
import instaloader
import os
import re
app = Flask(__name__)
# Username & password TIDAK ditulis di sini — diambil dari
# Environment Variables Vercel (Settings > Environment Variables):
#   IG_USERNAME = username akun IG baru/dummy kamu
#   IG_PASSWORD = password akun itu
# JANGAN pernah pakai akun utama kamu untuk ini.
IG_USERNAME = os.environ.get("IG_USERNAME")
IG_PASSWORD = os.environ.get("IG_PASSWORD")
L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
)
_logged_in = False
def ensure_login():
    """Login sekali per 'warm instance'. Vercel serverless bisa
    cold-start kapan saja, jadi login ini bisa terjadi berkali-kali
    dalam sehari — ini yang bikin risiko checkpoint lebih tinggi."""
    global _logged_in
    if _logged_in:
        return
    if not IG_USERNAME or not IG_PASSWORD:
        raise RuntimeError("IG_USERNAME / IG_PASSWORD belum diset di Environment Variables Vercel")
    L.login(IG_USERNAME, IG_PASSWORD)
    _logged_in = True
def extract_shortcode(url):
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
        ensure_login()

        shortcode = extract_shortcode(url)
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        media = []
        if post.typename == "GraphSidecar":
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

    except instaloader.exceptions.TwoFactorAuthRequiredException:
        return jsonify({"error": "Akun ini pakai 2FA. Matikan dulu 2FA di akun IG tersebut, lalu coba lagi."}), 401
    except instaloader.exceptions.BadCredentialsException:
        return jsonify({"error": "Username/password salah. Cek IG_USERNAME & IG_PASSWORD di Environment Variables."}), 401
    except instaloader.exceptions.ConnectionException as e:
        return jsonify({"error": "Instagram menolak/membatasi permintaan (rate limit atau checkpoint login).", "detail": str(e)}), 429
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Gagal mengambil data post.", "detail": str(e)}), 500
# Vercel otomatis mendeteksi variabel 'app' ini sebagai entry point WSGI.
