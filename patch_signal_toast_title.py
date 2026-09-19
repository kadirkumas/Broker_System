import shutil
import os

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_signal_toast_title'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/3] Yedek: {JS_BAK}")

changes = 0

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# ============================================================
# 1. Sinyal toast'inda customTitle kullan (Hata -> SİNYAL)
# ============================================================
old1 = """window.showToast(`${evt.symbol} [${evt.strategy}] ${evt.signal}`, isLong ? 'success' : 'error', 5000);"""
new1 = """window.showToast(`${evt.symbol} [${evt.strategy}] ${evt.signal}`, isLong ? 'success' : 'error', 5000, isLong ? '📈 LONG SİNYAL' : '📉 SHORT SİNYAL');"""

if old1 in js:
    cnt = js.count(old1)
    js = js.replace(old1, new1)
    changes += 1
    print(f"[2/3] JS: Sinyal toast basligi guncellendi ({cnt} yerde)")
else:
    print("[2/3] JS: HATA - sinyal toast satiri bulunamadi!")
    exit(1)

# ============================================================
# 2. Kapanis toast'i da "Hata" yerine anlamli baslik gostersin
# ============================================================
old2 = """window.showToast(`${evt.symbol} KAPANDI ${sign}${evt.pnl_amount.toFixed(4)} USDT`, evt.pnl_amount >= 0 ? 'success' : 'error', 5000);"""
new2 = """window.showToast(`${evt.symbol} KAPANDI ${sign}${evt.pnl_amount.toFixed(4)} USDT`, evt.pnl_amount >= 0 ? 'success' : 'error', 5000, evt.pnl_amount >= 0 ? '✅ KÂR' : '🛑 ZARAR');"""

if old2 in js:
    cnt = js.count(old2)
    js = js.replace(old2, new2)
    changes += 1
    print(f"[3/3] JS: Kapanis toast basligi guncellendi ({cnt} yerde)")
else:
    print("[3/3] JS: UYARI - kapanis toast satiri bulunamadi (atlandi)")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - SHORT sinyal toast'i artik 'Hata' yerine 'SHORT SİNYAL' gosterir")
print("  - LONG sinyal toast'i 'LONG SİNYAL' gosterir")
print("  - Kapanis toast'i 'KÂR' / 'ZARAR' basligi gosterir")
print("  - Renkler AYNI kaldi (kirmizi=SHORT, yesil=LONG)")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {JS_SRC}.bak_signal_toast_title {JS_SRC} -Force")