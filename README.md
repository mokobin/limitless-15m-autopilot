# ⚡ Limitless 15-Minute Auto-Trader & Dual-Report Engine

Otomasi trading prediktif 15-menit di **Limitless Exchange** (Base Network) dengan browser session controller (Playwright via Chrome DevTools Protocol / CDP), zero private key on-disk, auto-claim rewards, kalkulasi TWAP / spot momentum divergence, dan modul instant withdrawal.

---

## 🌟 Fitur Utama

- **Zero-Key Storage Security:** Berjalan langsung di atas sesi Chromium aktif (`CDP :9223`) menggunakan Smart Account / Privy web session. Tidak ada private key yang tersimpan di disk.
- **Deterministic 15m Round Slots:** Sinkronisasi slot waktu otomatis berbasis pembagian menit jam UTC (slot :00-:15, :15-:30, :30-:45, :45-:00).
- **DOM-Accurate Position Tracking:** Memverifikasi status posisi aktif langsung dari tab resmi `Positions X` di dashboard Limitless SPA untuk mencegah *ghost-trading* atau false entry.
- **Auto Claiming:** Otomatis mendeteksi dan mengeklik tombol claim saat tiket ronde sebelumnya berstatus menang (Settled 100¢).
- **Dual-Report Generator:** Menghasilkan 2 laporan berurutan:
  1. `[LAPORAN ENTRY - RONDE X]` (Status order live saat ini)
  2. `[LAPORAN PnL - RONDE X-1]` (Hasil settlement resmi ronde sebelumnya)
- **Instant Base Withdrawal CLI:** Script satu baris untuk menarik seluruh sisa kas USDC langsung ke alamat EVM wallet di Base.

---

## 📁 Struktur Repositori

```text
limitless-15m-autopilot/
├── config.py             # Konfigurasi environment & parameter trading
├── data_feed.py          # Real-time Binance spot price, RSI & momentum feed
├── limitless_client.py   # Web3 Playwright controller (Portfolio, Market, Claim, Withdraw)
├── strategy.py           # Logika sinyal (TWAP divergence + 5m momentum)
├── main.py               # Runner utama (dipanggil via Cron atau CLI)
├── withdraw.py           # CLI penarikan dana instan ke wallet Base
├── requirements.txt      # Dependensi Python
├── .env.example          # Template konfigurasi environment
└── README.md             # Dokumentasi teknis
```

---

## 🚀 Panduan Setup & Menjalankan

### 1. Prasyarat Sistem
- Python 3.10+
- Google Chrome atau Chromium berjalan dengan remote debugging port:
  ```bash
  chromium-browser --remote-debugging-port=9223 --user-data-dir=/path/to/profile &
  ```
- Login ke akun Limitless Exchange di browser tersebut.

### 2. Instalasi Dependensi
```bash
git clone <url-repo-ini>
cd limitless-15m-autopilot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 3. Konfigurasi `.env`
Salin template konfigurasi:
```bash
cp .env.example .env
```
Sesuaikan parameter di file `.env` jika diperlukan (misal: port CDP, default recipient address).

---

## ⚙️ Eksekusi & Otomasi

### Menjalankan 1 Siklus Manual:
```bash
python3 main.py
```

### Format Output Laporan:
```text
🎯 [LAPORAN ENTRY - RONDE 35]
• Jam Sesi: 01:00 – 01:15 WIB
• Posisi: BUY UP
• Modal Masuk: $1.00 USDC
• Target Price to Beat: $2,684.21
• Spot Saat Entry: $2,684.76 (Gap: +0.55)
• Status Tiket: MATCHED / LIVE 🟢
• Sisa Kas Ready: $2.34

---

📊 [LAPORAN PnL - RONDE 34]
• Jam Sesi: 00:45 – 01:00 WIB
• Hasil Akhir: WIN (Settled 100¢) 🎯 - CLAIMED ✅
• Modal Masuk: $1.00 USDC
• Payout Masuk: $1.38 USDC
• Net PnL: +$0.38 USDC (+38.0%)
```

### Otomasi Menggunakan Cron (Tiap 15 Menit):
Jadwalkan eksekusi 2 menit setelah pergantian slot ronde:
```cron
2,17,32,47 * * * * /path/to/venv/bin/python3 /path/to/limitless-15m-autopilot/main.py >> /var/log/limitless.log 2>&1
```

---

## 💸 Menarik Dana ke Wallet (Withdraw)

Untuk menarik seluruh saldo kas USDC di Limitless ke alamat dompet EVM Base:
```bash
python3 withdraw.py 0xYourBaseAddressHere
```

---

## ⚠️ Catatan Risiko & Karakteristik Binary Options
- **Risk/Reward Asymmetry:** Binary options 15-menit memiliki payout menang rata-rata +15% s/d +40%, namun risiko kehilangan modal saat kalah adalah 100%. Disarankan memasang filter batas harga masuk (`MAX_CENTS_PRICE`) agar hanya mengeksekusi order dengan odds diskon / sepadan.

---

## 📄 Lisensi
MIT License. Bebas digunakan dan dikembangkan untuk keperluan edukasi dan riset otomasi Web3.
