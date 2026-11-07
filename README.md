# A1 - AI Agent Layanan & Prospek Awards (SIMULASI TES)

Bot Telegram: jawaban berbasis KB01-KB04 (Gemini + pagar aturan), prospek tanpa duplikasi, draf follow-up
yang menunggu persetujuan manusia. **Tidak ada pesan nyata yang dikirim ke siapa pun.**
Semua aturan KB hanya simulasi, bukan kebijakan resmi MSI/awards.

## Deploy gratis di Render (tanpa kartu kredit)
1. Telegram: chat @BotFather, `/newbot`, simpan token.
2. Google AI Studio: buat Gemini API key (free tier).
3. Upload folder ini ke repo GitHub (`.gitignore` sudah menyembunyikan `.env`). Jangan commit token/key.
4. Render: New > Blueprint (pilih repo, membaca `render.yaml`), atau New > Web Service: Build `pip install -r requirements.txt`, Start `python bot.py`, plan Free.
5. Isi env `TELEGRAM_BOT_TOKEN` dan `GEMINI_API_KEY` di dashboard Render (bukan di kode/laporan).
6. Deploy. Buka bot di Telegram, kirim `/start`.
   Jika bot diam: set env `WEBHOOK_BASE_URL` = URL `https://<nama>.onrender.com` lalu redeploy.

## Batasan hosting gratis (tulis jujur di laporan)
- Server tidur setelah 15 menit tanpa trafik; pesan pertama setelah itu bisa tertunda sekitar 1 menit (Telegram mencoba ulang).
- Penyimpanan sementara: data SQLite hilang saat tidur/redeploy. Data tiap chat terpisah.
- Kuota Gemini dibatasi (20 panggilan/chat/jam, 300/hari). Setelah habis bot tetap menjawab dari aturan KB ("mode: fallback").
- Jalankan lokal: `pip install -r requirements.txt`, isi `.env`, `python bot.py` (long polling).

## Skrip uji untuk penilai (kirim ke bot)
1. `Apakah saya harus sponsor?` -> rujukan KB03, tidak dieskalasi
2. `Apakah dijamin bintang 5?` -> KB04, dieskalasi
3. `Berapa harga dan tanggal wawancara?` -> KB04 + KB02, dieskalasi
4. `Apakah pendaftaran berbayar?` -> KB01
5. `/prospek Surya Reka | info@suryareka.test | 081234567890 | ESG` lalu ulangi 2x dengan format email/telepon berbeda -> `/jumlah` tetap 1
6. Tekan **Setujui (simulasi)** pada draf -> status berubah, tidak ada pesan terkirim. Tekan lagi -> ditolak (sudah diputuskan).

## Uji otomatis (offline, LLM dipalsukan)
`python test_a1.py` -> 22 uji: 4 pertanyaan wajib, kegagalan API/JSON rusak/KB palsu/klaim harga, duplikasi,
draf menunggu persetujuan, isolasi chat, kuota. Screenshot output ini sebagai bukti `A1-02`.

## Desain keamanan
- LLM hanya boleh merujuk KB yang ada; jawaban tanpa rujukan, berisi nominal/jaminan/tanggal, atau JSON rusak ditolak dan diganti jawaban aman + eskalasi.
- Pagar kata kunci (harga, jaminan, tanggal) memaksa eskalasi walau LLM salah.
- Tidak ada kode pengiriman email/WhatsApp. "Setujui" hanya menandai status `disetujui_simulasi`.

## Batasan
Hanya 4 aturan KB; deteksi kata kunci sederhana (bisa meleset di kalimat tak lazim); tidak ada autentikasi staf
sungguhan (di demo, tiap chat jadi pengguna sekaligus penyetuju); belum diuji pada pertanyaan acak skala besar.
Pengujian langsung Telegram dan Render belum dijalankan oleh pembuat kode ini; yang teruji hanya inti logika (offline).

## ID bukti
A1-01 kode (repo) | A1-02 output `test_a1.py` | A1-03 screenshot chat Telegram skrip uji | A1-04 rekaman demo (cadangan jika bot tidur)
