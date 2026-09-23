# Threads Product Radar

Internal Streamlit dashboard untuk meriset produk digital yang mendapat engagement dan indikasi buying intent tinggi di Threads, dengan fokus awal Indonesia/Bahasa Indonesia.

## Status MVP

- Dashboard 10 menu dengan filter global.
- Collector resmi Threads yang modular dan configurable.
- Cleaning, deduplication, rule-based product classification, hook pattern, CTA pattern, dan buying-intent detection.
- Product Opportunity Score 0–100 beserta breakdown.
- SQLite terpisah untuk demo dan live data.
- Ekspor CSV dan workbook Excel tujuh sheet.
- Basic login, secret dari environment, logging, Docker, systemd, Nginx, SSL guide, dan tests.

> Demo data selalu berlabel **DEMO DATA** dan disimpan di `data/demo_threads_radar.db`. Data live memakai database berbeda yang ditentukan oleh `DATABASE_PATH`.

## 1. Installation

Persyaratan: Python 3.11+ (disarankan 3.12).

```bash
git clone <repository-url> threads-product-radar
cd threads-product-radar
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`, terutama login dashboard dan credential Threads. Jangan commit `.env`.

## 2. Running locally

```bash
source .venv/bin/activate
streamlit run app.py
```

Buka `http://localhost:8501`. Bila `APP_USERNAME` dan `APP_PASSWORD` dikosongkan pada mode development, login lokal dilewati. Mode production selalu mewajibkan keduanya.

## 3. Database setup

Database dibuat otomatis saat aplikasi dimulai. Inisialisasi manual:

```bash
python scripts/init_db.py
```

SQLite memakai WAL mode, unique constraint pada `post_id` dan `permalink`, serta transaksi rollback saat operasi gagal.

### Reset database

Hentikan aplikasi, backup bila perlu, lalu hapus file database yang spesifik:

```bash
rm data/threads_product_radar.db
```

Jangan menghapus seluruh direktori `data`. Database akan dibuat ulang saat app dimulai.

## 4. Threads API configuration

Isi:

```dotenv
THREADS_ACCESS_TOKEN=your-token
THREADS_API_BASE_URL=https://graph.threads.net/v1.0
THREADS_SEARCH_ENDPOINT=/keyword_search
```

Meta menambahkan public-post keyword search pada Threads API pada 2025. Ketersediaan endpoint, field, search type, dan reply text tetap bergantung pada versi API, izin aplikasi, app review, serta perubahan kebijakan Meta. Karena itu base URL dan endpoint dibuat configurable.

Collector hanya memakai API resmi, memiliki timeout, menangani respons kosong/error, dan tidak mengarang metric yang tidak dikirim API. Jika `views`, follower count, atau reply text tidak tersedia, nilainya tetap kosong. Buying-intent menjadi `UNAVAILABLE` bila reply text tidak tersedia.

## 5. Data pipeline

Urutan pipeline:

1. Collector menghasilkan record dengan interface standar.
2. Cleaner menormalkan whitespace, memfilter spam dasar, mendeteksi bahasa, dan deduplicate ID/permalink/kemiripan teks.
3. Classifier rule-based menentukan kategori, subkategori, dan confidence.
4. Buying-intent detector memeriksa reply text yang benar-benar tersedia.
5. Scoring menghitung metric post dan agregasi kategori.
6. SQLite menyimpan record bersih dan mencegah duplicate insert.

Menambahkan collector baru cukup dengan membuat class turunan `BaseCollector`; dashboard dan analytics tidak perlu diubah selama output memakai contract field yang sama.

## 6. Opportunity Score

Bobot V1:

| Component | Weight | Method |
|---|---:|---|
| Engagement | 30% | Min-max weighted engagement: like×1, reply×2, repost×3, quote×3 |
| Buying intent | 25% | Persentase reply yang cocok dengan frasa intent; 0 bila unavailable, status tetap ditampilkan |
| Recency / growth | 20% | Time-decay dengan half-life 30 hari |
| Demand frequency | 15% | Frekuensi post kategori, dinormalisasi |
| Competition gap | 10% | Demand per creator unik; nilai lebih tinggi berarti demand relatif padat terhadap creator |

Semua komponen dibatasi 0–100. Normalisasi mengikuti dataset aktif sehingga score bersifat alat ranking relatif, bukan estimasi penjualan absolut.

## 7. Classification

Rules berada di `processors/classifier.py`. Tambahkan rule sebelum kategori yang lebih umum karena classifier memilih rule dengan kecocokan terbanyak. Arsitektur output (`product_category`, `product_subcategory`, `classification_confidence`) sengaja dibuat stabil agar nantinya dapat diganti LLM classifier.

## 8. Keyword management

Buka **Settings → Keyword management**, masukkan keyword, lalu Save. Keyword tersimpan di tabel `keywords`. Untuk menjalankan collection, isi form di bagian **Run official collection**.

## 9. Export

Buka **Dataset**, terapkan filter/search, kemudian pilih:

- Download CSV — UTF-8 BOM agar mudah dibuka di Excel.
- Download Excel — sheet Overview, Product Ranking, Top Threads, Keywords, Creators, Buying Intent, Raw Data; termasuk header, filter, freeze pane, dan lebar kolom.

## 10. Testing

```bash
pytest -q
python scripts/smoke_test.py
```

Cakupan MVP: database initialization, duplicate handling, empty API response, API error, missing engagement values, classifier, buying-intent availability, scoring, filter, dan Excel export.

## 11. Docker deployment

```bash
cp .env.example .env
# set APP_ENV=production, login kuat, token, dan database path
docker compose up -d --build
docker compose ps
```

Service hanya dipublish ke `127.0.0.1:8501`, sehingga tidak terekspos langsung ke internet. Nginx menjadi public entry point.

## 12. Ubuntu + systemd deployment

```bash
sudo adduser --system --group --home /opt/threads-product-radar radar
sudo rsync -a ./ /opt/threads-product-radar/
sudo chown -R radar:radar /opt/threads-product-radar
sudo -u radar python3 -m venv /opt/threads-product-radar/.venv
sudo -u radar /opt/threads-product-radar/.venv/bin/pip install -r /opt/threads-product-radar/requirements.txt
sudo cp deployment/threads-product-radar.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now threads-product-radar
```

Gunakan `systemctl status threads-product-radar` dan `journalctl -u threads-product-radar` untuk status/log.

## 13. Nginx, domain, SSL

1. Arahkan DNS `radar.example.com` ke IP VPS. Ganti placeholder hanya setelah domain final tersedia.
2. Copy `deployment/nginx.conf` ke `/etc/nginx/sites-available/threads-product-radar`.
3. Aktifkan dan uji:

```bash
sudo ln -s /etc/nginx/sites-available/threads-product-radar /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

4. Install SSL:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d radar.example.com
sudo certbot renew --dry-run
```

Cloudflare bersifat opsional. Jika dipakai, gunakan SSL mode Full (strict).

## 14. Security, firewall, backup, logging

- Gunakan password panjang dan unik; credential hanya di `.env` dengan permission `600`.
- App bind ke localhost; jangan expose port 8501 melalui firewall.
- UFW: izinkan OpenSSH dan `Nginx Full`, lalu enable.
- Database serta `.env` berada di luar document root Nginx.
- Tambahkan Nginx rate limit bila dashboard dibuka ke banyak user.
- Backup harian aman dengan SQLite Online Backup API atau `sqlite3 ... '.backup ...'`, lalu simpan terenkripsi/offsite.
- Retensi contoh: 7 backup harian, 4 mingguan, 6 bulanan; lakukan restore drill berkala.
- Log aplikasi masuk ke systemd journal; gunakan `logrotate` bila dialihkan ke file.
- Untuk traffic/concurrent writes yang makin besar, ganti repository layer `database/db.py` dengan PostgreSQL tanpa mengubah collector, processor, atau dashboard contract.

## 15. Troubleshooting

| Symptom | Check |
|---|---|
| API “not configured” | `THREADS_ACCESS_TOKEN` terisi dan service direstart |
| API permission/error | App review, token scope/expiry, base URL, endpoint, dan versi API |
| Dashboard kosong | Data source LIVE vs DEMO dan filter global |
| Intent unavailable | API tidak menyediakan reply text; ini perilaku yang benar |
| Permission denied SQLite | Ownership direktori `data/` untuk user `radar` |
| Nginx 502 | Status service dan bind `127.0.0.1:8501` |
| WebSocket disconnect | Header Upgrade/Connection di Nginx config |

## 16. Automatic deployment from GitHub

The production VPS can poll the public `main` branch every minute. When it sees
a new fast-forward commit, it rebuilds the Docker image, restarts the service,
and checks Streamlit health on `127.0.0.1:8501`.

One-time server setup after cloning the repository to
`/opt/threads-product-radar`:

```bash
cd /opt/threads-product-radar
chmod +x deployment/auto-deploy.sh
cp deployment/threads-product-radar-deploy.service /etc/systemd/system/
cp deployment/threads-product-radar-deploy.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now threads-product-radar-deploy.timer
systemctl list-timers threads-product-radar-deploy.timer
```

Normal developer flow:

```bash
git pull --ff-only origin main
# make and test changes
git add .
git commit -m "Describe the change"
git push origin main
```

GitHub runs the automated test workflow on every push. The VPS deploys only
fast-forward updates, preventing server-side edits from being overwritten.

### One-command VPS bootstrap

On the production VPS, clone the repository and run the interactive bootstrap:

```bash
cd /opt
git clone https://github.com/Ranneciva28/threads-product-radar.git
cd /opt/threads-product-radar
chmod +x deployment/bootstrap-vps.sh
./deployment/bootstrap-vps.sh
```

The bootstrap preserves an existing `.env`, refuses to overwrite a non-Git
application directory, checks port `8501`, and does not modify ports `80/443`,
CyberPanel, OpenLiteSpeed, Traefik, MariaDB, or other hosted sites.

## Structure

```text
threads-product-radar/
├── app.py
├── pipeline.py
├── analytics/
├── collectors/
├── config/
├── data/
├── database/
├── deployment/
├── exporters/
├── processors/
├── scoring/
├── scripts/
└── tests/
```
