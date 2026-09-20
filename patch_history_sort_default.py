import shutil
import os

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_history_sort_default'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_BAK)
print(f"[1/4] Yedek: {JS_BAK}")

changes = 0

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# ============================================================
# 1. localStorage key'i _v2 yap (eski 'asc' degeri ignore edilsin)
# ============================================================
old1 = """let scanQueue = [], historySortDir = localStorage.getItem('cryptoHistorySortDir') || 'desc';"""
new1 = """let scanQueue = [], historySortDir = localStorage.getItem('cryptoHistorySortDir_v2') || 'desc';"""

if old1 in js:
    js = js.replace(old1, new1, 1)
    changes += 1
    print("[2/4] localStorage key _v2 yapildi (eski deger sifirlandi)")
else:
    print("[2/4] HATA: historySortDir bulunamadi!")
    exit(1)

# ============================================================
# 2. toggleHistorySort -> yeni key'e yaz
# ============================================================
old2 = """window.toggleHistorySort = function() { historySortDir = historySortDir === 'desc' ? 'asc' : 'desc'; localStorage.setItem('cryptoHistorySortDir', historySortDir); window.lastHistoryHash = ""; window.histPage = 1; window.renderHistoricalTrades(); };"""
new2 = """window.toggleHistorySort = function() { historySortDir = historySortDir === 'desc' ? 'asc' : 'desc'; localStorage.setItem('cryptoHistorySortDir_v2', historySortDir); window.lastHistoryHash = ""; window.histPage = 1; window.renderHistoricalTrades(); };"""

if old2 in js:
    js = js.replace(old2, new2, 1)
    changes += 1
    print("[3/4] toggleHistorySort key guncellendi")
else:
    print("[3/4] UYARI: toggleHistorySort bulunamadi (atlandi)")

# ============================================================
# 3. Siralamayi entry_time'dan exit_time'a cevir
# ============================================================
old3 = """trades.sort((a, b) => historySortDir === 'asc' ? a.entry_time - b.entry_time : b.entry_time - a.entry_time);"""
new3 = """trades.sort((a, b) => historySortDir === 'asc' ? a.exit_time - b.exit_time : b.exit_time - a.exit_time);"""

if old3 in js:
    js = js.replace(old3, new3, 1)
    changes += 1
    print("[4/4] Siralama exit_time'a gore yapildi")
else:
    print("[4/4] HATA: siralam satiri bulunamadi!")
    exit(1)

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - Islem Gecmisi default olarak BITIS TARIHINE gore (exit_time)")
print("    buyukten kucuge (desc) siralanir")
print("  - Eski localStorage degeri (_v2 key) sifirlandi, eski 'asc'")
print("    degeri artik yuklenmez")
print("  - Siralama sutununa tiklaninca desc<->asc degisir (aynen kalir)")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R (sadece frontend)")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {JS_SRC}.bak_history_sort_default {JS_SRC} -Force")