import shutil
import os
import re

SE_SRC = 'backend/strategy_engine.py'
SE_BAK = 'backend/strategy_engine.py.bak_rate_v2'

if not os.path.exists(SE_SRC):
    print(f"[HATA] {SE_SRC} bulunamadi")
    exit(1)

shutil.copy2(SE_SRC, SE_BAK)
print(f"[1/4] Yedek: {SE_BAK}")

with open(SE_SRC, 'r', encoding='utf-8', newline='') as f:
    se = f.read().replace('\r\n', '\n')

changes = 0

# 1. Batch size 2 -> 1 (tamamen sirayla)
old = "        BATCH_SIZE = 2"
new = "        BATCH_SIZE = 1"
if old in se:
    se = se.replace(old, new, 1)
    changes += 1
    print("[2/4] Batch size: 2 -> 1 (seri tarama)")
else:
    print("[2/4] UYARI: batch size pattern")

# 2. Batch bekleme 0.8 -> 1.2 (daha nazik)
old = "            await asyncio.sleep(0.8)"
new = "            await asyncio.sleep(1.2)"
if old in se:
    se = se.replace(old, new, 1)
    changes += 1
    print("[3/4] Batch bekleme: 0.8 -> 1.2 sn")

# 3. Delist kontrolü: 5 dk -> 30 dk cache
old = "if _time.time() - getattr(self, '_delisted_cache_time', 0) > 300:"
new = "if _time.time() - getattr(self, '_delisted_cache_time', 0) > 1800:"
if old in se:
    se = se.replace(old, new, 1)
    changes += 1
    print("[4/4] Delist cache: 5 dk -> 30 dk")

with open(SE_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(se.replace('\n', '\r\n'))

# ============================================================
# BONUS: Frontend polling süreleri
# ============================================================
JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_rate_v2'
shutil.copy2(JS_SRC, JS_BAK)

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# Scanner 15 -> 30 sn
old = "setInterval(fetchStatus, 15000);"
new = "setInterval(fetchStatus, 30000);"
if old in js:
    js = js.replace(old, new, 1)
    print("Frontend: scanner 15 -> 30 sn")

# Watchlist REST 20 -> 30 sn
old = "if (Date.now() - wsWatchlistLastUpdate > 20000) window.updateWatchlistsRest();"
new = "if (Date.now() - wsWatchlistLastUpdate > 30000) window.updateWatchlistsRest();"
if old in js:
    js = js.replace(old, new, 1)
    print("Frontend: watchlist REST 20 -> 30 sn")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} backend + 2 frontend degisiklik")
print("=" * 60)
print()
print("ETKI:")
print("  - Tarama daha yavas ama rate limit guvenli")
print("  - 300 sembol x 2 strateji = 600 istek/tur")
print("  - Batch 1 + 1.2 sn bekleme = ~720 sn/tur")
print()
print("⚠️  ONEMLI: Tarama 400 sn'den UZUN suruyor artik!")
print("   Bot Ayarlari'ndan Tarama Suresini 900 sn yap!")
print()
print("KONTROL LISTESI:")
print("  1. Backend'i Ctrl+C ile durdur")
print("  2. py -m uvicorn backend.main:app --reload")
print("  3. Tarayici: Ctrl+Shift+R")
print("  4. Bot Ayarlari -> Tarama Suresi: 900, KAYDET")
print("  5. 5 dk bekle -> rate limit hatasi var mi?")
print()
print("Geri donmek icin:")
print(f"  copy /Y {SE_BAK} {SE_SRC}")
print(f"  copy /Y {JS_BAK} {JS_SRC}")