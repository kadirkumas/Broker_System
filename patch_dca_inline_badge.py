import shutil
import os

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_dca_inline_badge'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/3] Yedek: {JS_BAK}")

changes = 0

# ============================================================
# 1. JS: renderHistoricalTrades + renderDailyTrades icindeki
#    dcaBadge mantigini "satir kirma" yerine "inline rozet" yap
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# --- 1a. dcaBadge tanimini volCell'e cevir (iki fonksiyonda ayni string var) ---
old_badge = """            const dcaBadge = t.dca_count > 0 ? `<br><span style="font-size:10px; color:#fcd535;">DCA:${t.dca_count}</span>` : '';"""

new_badge = """            const volCell = t.dca_count > 0
                ? `<span style="display:inline-flex; align-items:center; justify-content:flex-end; gap:6px;"><span>${t.total_vol.toFixed(2)} USDT</span><span style="font-size:10px; color:#fcd535; font-weight:600; padding:1px 5px; background:rgba(252,213,53,0.12); border-radius:3px; white-space:nowrap;">DCA:${t.dca_count}</span></span>`
                : `${t.total_vol.toFixed(2)} USDT`;"""

if old_badge in js:
    # replace() tum eslesmeleri degistirir - hem historical hem daily
    count_before = js.count(old_badge)
    js = js.replace(old_badge, new_badge)
    changes += 1
    print(f"[2/3] JS: dcaBadge -> volCell ({count_before} yerde)")
else:
    print("[2/3] JS: HATA - dcaBadge satiri bulunamadi!")
    exit(1)

# --- 1b. td icindeki kullanimi guncelle ---
old_td = """<td class="right">${t.total_vol.toFixed(2)} USDT${dcaBadge}</td>"""
new_td = """<td class="right">${volCell}</td>"""

if old_td in js:
    count_before = js.count(old_td)
    js = js.replace(old_td, new_td)
    changes += 1
    print(f"[3/3] JS: td kullanimi guncellendi ({count_before} yerde)")
else:
    print("[3/3] JS: HATA - td satiri bulunamadi!")
    exit(1)

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - Islem Gecmisi + Gunluk Islemler tablolarinda")
print("    DCA rozeti artik AYNI satirda sagda gorunur")
print("  - Satir yuksekligi ARTMAZ (pozisyon tablosu ile tutarli)")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R (sadece frontend degisti)")
print()
print("Geri donmek icin:")
print("  Copy-Item frontend\\chart.js.bak_dca_inline_badge frontend\\chart.js -Force")