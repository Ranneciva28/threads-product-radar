# Threads Product Radar

Internal Streamlit dashboard untuk meriset produk digital yang mendapat engagement dan indikasi buying intent tinggi di Threads, dengan fokus awal Indonesia/Bahasa Indonesia.

## Status MVP

- Dashboard 10 menu dengan filter global.
- Collector resmi Threads yang modular dan configurable.
- Cleaning, deduplication, rule-based product classification, hook pattern, CTA pattern, dan buying-intent detection.
- Product Opportunity Score 0–100 beserta breakdown.
- SQLite terpisah untuk demo dan live data.
- Ekspor CSV dan workbook Excel tujuh sheet.
- Basic login, secret dari environment, logging, native systemd deployment, CyberPanel/OpenLiteSpeed guide, dan tests.

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

## 11. Production deployment: CyberPanel + systemd

Production tidak menggunakan Docker. Repository berada di
`/home/threads.avicennarabama.com/threads-product-radar`, dimiliki oleh user
website CyberPanel, dan aplikasi berjalan sebagai service `systemd` pada
`127.0.0.1:8501`.

Pastikan website `threads.avicennarabama.com` sudah dibuat di CyberPanel, lalu
jalankan bootstrap dari clone sementara:

```bash
cd /opt/threads-product-radar
git pull --ff-only origin main
chmod +x deployment/bootstrap-vps.sh
./deployment/bootstrap-vps.sh
```

Bootstrap akan mendeteksi user website dari ownership `public_html`, membuat
virtual environment Python, memasang dependency, membuat `.env`, memasang
service aplikasi dan timer auto-deploy, lalu menjalankan health check.

Gunakan perintah berikut untuk status dan log:

```bash
systemctl status threads-product-radar.service --no-pager
journalctl -u threads-product-radar.service -n 100 --no-pager
systemctl list-timers threads-product-radar-deploy.timer
```

## 12. OpenLiteSpeed, domain, dan SSL

Di OpenLiteSpeed WebAdmin, pada virtual host `threads.avicennarabama.com`:

1. Buat External App tipe `Web Server` bernama `threads_radar` dengan address
   `127.0.0.1:8501`.
2. Buat Proxy Context dengan URI `/` menuju `threads_radar`.
3. Buat WebSocket Proxy dengan URI `/_stcore/stream` dan address
   `127.0.0.1:8501`.
4. Lakukan graceful restart OpenLiteSpeed.
5. Issue SSL untuk domain melalui CyberPanel.

Verifikasi:

```bash
curl -fsS http://127.0.0.1:8501/_stcore/health
curl -fsS https://threads.avicennarabama.com/_stcore/health
```

Keduanya harus menghasilkan `ok`.

## 14. Security, firewall, backup, logging

- Gunakan password panjang dan unik; credential hanya di `.env` dengan permission `600`.
- App bind ke localhost; jangan expose port 8501 melalui firewall.
- UFW: izinkan OpenSSH dan port web milik OpenLiteSpeed; port `8501` tetap lokal.
- Database serta `.env` berada di luar `public_html`.
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
| Permission denied SQLite | Ownership direktori `data/` harus sama dengan user website CyberPanel |
| OpenLiteSpeed 503 | Status service dan bind `127.0.0.1:8501` |
| WebSocket disconnect | WebSocket Proxy `/_stcore/stream` pada virtual host |

## 16. Automatic deployment from GitHub

The production VPS polls the public `main` branch every minute. When it sees a
new fast-forward commit, it installs changed Python dependencies, restarts the
native Streamlit service, and checks health on `127.0.0.1:8501`.

Normal developer flow:

```bash
git pull --ff-only origin main
# make and test changes
git add .
git commit -m "Describe the change"
git push origin main
```

GitHub runs the automated test workflow on every push. The VPS deploys only
fast-forward updates and stops when tracked server files have local changes.
The bootstrap preserves `.env` and does not alter ports `80/443`, other virtual
hosts, MariaDB, or other hosted sites.

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
