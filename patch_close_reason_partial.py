import shutil
import os

MAIN_SRC = 'backend/main.py'
JS_SRC = 'frontend/chart.js'

for src in [MAIN_SRC, JS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_close_reason_partial')
    print(f"[1/4] Yedek: {src}.bak_close_reason_partial")

changes = 0

# ============================================================
# 1. BACKEND: main.py - close-reasons SQL CASE guncelle
# ============================================================
with open(MAIN_SRC, 'r', encoding='utf-8', newline='') as f:
    main = f.read().replace('\r\n', '\n')

old_case = '''            CASE 
                WHEN close_reason LIKE '%TRAILING%' THEN 'TRAILING'
                WHEN close_reason LIKE '%STOP%' THEN 'STOP LOSS'
                WHEN close_reason LIKE '%TAKE%' THEN 'TAKE PROFIT'
                WHEN close_reason LIKE '%DELIST%' THEN 'DELISTED'
                ELSE 'DIGER'
            END as reason,'''

new_case = '''            CASE 
                WHEN close_reason LIKE '%PARTIAL%' THEN 'PARTIAL TP'
                WHEN close_reason LIKE '%TRAILING%' THEN 'TRAILING'
                WHEN close_reason LIKE '%STOP%' THEN 'STOP LOSS'
                WHEN close_reason LIKE '%DELIST%' THEN 'DELISTED'
                WHEN close_reason LIKE '%TIME%' THEN 'TIME LIMIT'
                WHEN close_reason LIKE '%TAKE%' THEN 'TAKE PROFIT'
                ELSE 'DIGER'
            END as reason,'''

if 'PARTIAL%\' THEN \'PARTIAL TP' in main:
    print("[2/4] main.py: SQL zaten guncel (atlandi)")
elif old_case in main:
    main = main.replace(old_case, new_case, 1)
    changes += 1
    print("[2/4] main.py: SQL CASE guncellendi (PARTIAL TP eklendi)")
else:
    print("[2/4] UYARI: SQL CASE blogu bulunamadi (farkli yazilmis olabilir)")

with open(MAIN_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(main.replace('\n', '\r\n'))

# ============================================================
# 2. FRONTEND: chart.js - renderReasonStats emoji guncelle
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

old_emoji = '''        const reasonEmoji = {
            'TRAILING': '🎯',
            'STOP LOSS': '🛑',
            'TAKE PROFIT': '✅',
            'DELISTED': '🚫',
            'DIGER': '❓'
        };'''

new_emoji = '''        const reasonEmoji = {
            'PARTIAL TP': '⚡',
            'TRAILING': '🎯',
            'STOP LOSS': '🛑',
            'DELISTED': '🚫',
            'TIME LIMIT': '⏰',
            'TAKE PROFIT': '✅',
            'DIGER': '❓'
        };'''

if "'PARTIAL TP': '⚡'" in js:
    print("[3/4] chart.js: emoji zaten guncel (atlandi)")
elif old_emoji in js:
    js = js.replace(old_emoji, new_emoji, 1)
    changes += 1
    print("[3/4] chart.js: PARTIAL TP emojisi eklendi")
else:
    print("[3/4] UYARI: reasonEmoji blogu bulunamadi (atlandi)")

# Siralama da guncelle: PARTIAL TP basa gelsin
old_order = """        FROM trade_history
        WHERE ABS(pnl_amount) < (total_vol * 5)
        GROUP BY reason
        ORDER BY total_pnl DESC"""

# Bu backend'de, main.py'de olmali. Frontend'de siralama SQL'den gelir.

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print("[4/4] Kaydedildi")
print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - 'PARTIAL TP' artik ayri bir kategori (DIGER degil)")
print("  - Emoji: ⚡ PARTIAL TP")
print("  - Siralama: Toplam PnL'e gore (PARTIAL TP ustte olabilir)")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend --reload otomatik yukler")
print("  2. Ctrl+Shift+R")
print("  3. 📊 Istatistik -> Kapanis Sebepleri sekmesini kontrol et")
print()
print("Geri donmek icin:")
for src in [MAIN_SRC, JS_SRC]:
    print(f"  Copy-Item {src}.bak_close_reason_partial {src} -Force")