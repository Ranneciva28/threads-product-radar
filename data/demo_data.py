from __future__ import annotations

from datetime import datetime, timedelta, timezone


SEEDS = [
    ("Finance Spreadsheet", "budget planner", "Capek gaji cuma numpang lewat? Spreadsheet budget planner ini bikin semua pengeluaran kelihatan.", 1840, 126, 312, 44, ["link dong kak", "berapa harganya?", "mau", "spill linknya"]),
    ("Excel Template", "template excel", "Gue bikin dashboard Excel otomatis buat UMKM—tinggal input transaksi, laporan langsung jadi.", 1510, 98, 244, 31, ["ada link?", "beli dimana", "mau versi excel", "keren"]),
    ("Google Sheets Template", "google sheets template", "Kalau cashflow bisnismu masih dicatat manual, coba Google Sheets template yang gue pakai ini.", 1270, 87, 205, 24, ["boleh minta link?", "cara beli", "tertarik"]),
    ("Notion Template", "notion template", "Notion second brain gue akhirnya rapi setelah 3 tahun trial and error. Template lengkapnya sudah tersedia.", 1120, 73, 184, 21, ["link dong", "available?", "how much"]),
    ("AI Prompt / Prompt Pack", "prompt AI", "50 prompt AI untuk bikin konten 30 hari tanpa blank ide. Tinggal copy, paste, dan sesuaikan niche.", 1040, 94, 167, 26, ["mau", "berapa harganya", "ada link?"]),
    ("CV / Resume Template", "CV template", "Sudah kirim 40 lamaran tapi sepi panggilan? Coba format CV ATS yang lolos screening ini.", 980, 112, 151, 18, ["template-nya dimana", "boleh minta link?", "mau kak"]),
    ("Canva Template", "template canva", "Bikin carousel edukasi cuma 10 menit pakai 120 template Canva ini.", 860, 62, 139, 16, ["spill", "cara beli", "info dong"]),
    ("Ebook", "ebook", "Kesalahan pertama gue jual produk digital: bikin produk dulu, cari market belakangan. Gue rangkum semuanya di ebook ini.", 740, 56, 121, 14, ["mau baca", "beli dimana", "link?"]),
    ("Mini Course", "mini course", "Mini course 90 menit: dari nol sampai punya produk digital pertama yang siap dijual.", 690, 43, 92, 11, ["tertarik", "how much", "checkout dimana"]),
    ("Digital Planner", "digital planner", "Planner digital ini bukan bikin kamu sibuk—ini bikin tiga prioritas penting benar-benar selesai.", 620, 39, 87, 9, ["available?", "mau", "link dong"]),
    ("Education Worksheet", "worksheet", "Worksheet printable untuk anak belajar angka tanpa screen time berlebihan.", 580, 48, 102, 12, ["mau", "berapa harganya?", "ada link?"]),
    ("Social Media Template", "content calendar", "30 hari content calendar untuk bisnis kuliner—lengkap dengan hook dan CTA.", 520, 35, 78, 8, ["spill link", "cara beli", "tertarik"]),
]


def generate_demo_posts() -> list[dict]:
    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    angles = [
        "Versi creator: fokus pada hasil praktis untuk pemula.",
        "Studi kasus baru: dipakai selama empat minggu oleh usaha rumahan.",
        "Update terbaru: workflow disederhanakan dan contoh datanya diperbanyak.",
    ]
    for index in range(36):
        category, keyword, text, likes, replies, reposts, quotes, reply_texts = SEEDS[index % len(SEEDS)]
        factor = 1 - (index // len(SEEDS)) * 0.22
        created = now - timedelta(days=(index * 2) % 58, hours=index % 9)
        username = f"creator_{(index % 17) + 1:02d}"
        rows.append({
            "post_id": f"demo-{index + 1:03d}",
            "username": username,
            "display_name": username.replace("_", " ").title(),
            "post_text": text if index < len(SEEDS) else f"{angles[index // len(SEEDS)]} {text}",
            "created_at": created.isoformat(),
            "permalink": f"https://www.threads.net/@{username}/post/demo{index + 1}",
            "like_count": int(likes * factor),
            "reply_count": int(replies * factor),
            "repost_count": int(reposts * factor),
            "quote_count": int(quotes * factor),
            "views": None,
            "keyword_source": keyword,
            "search_type": "TOP" if index % 3 == 0 else "RECENT",
            "language": "id",
            "crawl_timestamp": now.isoformat(),
            "data_source": "DEMO",
            "replies_text": reply_texts if index % 5 != 0 else None,
        })
    return rows
