// api/ig-proxy.js
// Serverless function (Vercel) — jadi perantara antara frontend dan RapidAPI.
// RAPIDAPI_KEY TIDAK ditulis di sini, tapi diambil dari Environment Variable
// yang diset di dashboard Vercel, jadi tidak pernah muncul di source code
// maupun di browser user.

const RAPIDAPI_HOST = "instagram-downloader-scraper-reels-igtv-posts-stories.p.rapidapi.com";

export default async function handler(req, res) {
  // Hanya izinkan GET
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { url } = req.query;
  if (!url || typeof url !== "string") {
    return res.status(400).json({ error: "Parameter 'url' wajib diisi" });
  }

  // Validasi dasar: hanya izinkan link Instagram, biar endpoint ini
  // tidak disalahgunakan orang lain jadi proxy scraper bebas.
  if (!/^https?:\/\/(www\.)?instagram\.com\//i.test(url)) {
    return res.status(400).json({ error: "URL harus link Instagram yang valid" });
  }

  const RAPIDAPI_KEY = process.env.RAPIDAPI_KEY;
  if (!RAPIDAPI_KEY) {
    return res.status(500).json({ error: "Server belum dikonfigurasi (RAPIDAPI_KEY kosong)" });
  }

  try {
    const endpoint = `https://${RAPIDAPI_HOST}/scraper?url=${encodeURIComponent(url)}`;
    const rapidRes = await fetch(endpoint, {
      method: "GET",
      headers: {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
      },
    });

    const data = await rapidRes.json();

    if (!rapidRes.ok) {
      return res.status(rapidRes.status).json(data);
    }

    // Cache singkat di edge biar hemat kuota kalau ada request berulang
    // untuk link yang sama dalam waktu dekat (opsional, boleh dihapus).
    res.setHeader("Cache-Control", "s-maxage=60, stale-while-revalidate=300");

    return res.status(200).json(data);
  } catch (err) {
    return res.status(502).json({ error: "Gagal menghubungi layanan scraper", detail: err.message });
  }
}
