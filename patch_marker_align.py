import shutil
import os

JS_SRC = 'frontend/chart.js'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_SRC + '.bak_marker_align')
print(f"[1/4] Yedek: {JS_SRC}.bak_marker_align")

changes = 0

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# 1. symbolActive.forEach: entryTime hizala + _tfSec helper
old1 = """    symbolActive.forEach(pos => {
        const entryTime = pos.entry_time;"""
new1 = """    const _tfSec = window.getIntervalSeconds(cObj.interval || '5m') || 300;
    const _alignTf = (t) => t ? Math.floor(t / _tfSec) * _tfSec : t;
    
    symbolActive.forEach(pos => {
        const entryTime = _alignTf(pos.entry_time);"""

if 'const _alignTf = (t) =>' in js:
    print("[2/4] chart.js: _alignTf zaten var (atlandi)")
elif old1 in js:
    js = js.replace(old1, new1, 1)
    changes += 1
    print("[2/4] chart.js: symbolActive entryTime hizalandi")
else:
    print("[2/4] HATA: symbolActive blogu bulunamadi!")
    exit(1)

# 2. Aktif pozisyon cizgisi: -120/+120 -> -_tfSec/+_tfSec
old2 = """addLine(entryTime - 120, entryPrice, entryTime + 120, entryPrice, 'rgba(252,213,53,0.6)', 2, true);"""
new2 = """addLine(entryTime - _tfSec, entryPrice, entryTime + _tfSec, entryPrice, 'rgba(252,213,53,0.6)', 2, true);"""

if old2 in js:
    js = js.replace(old2, new2, 1)
    changes += 1
    print("[3/4] chart.js: aktif pozisyon cizgi offset guncellendi")
else:
    print("[3/4] UYARI: aktif cizgi offset bulunamadi (atlandi)")

# 3. DCA cizgisi: -120/+120 -> -_tfSec/+_tfSec
old3 = """addLine(entryTime - 120, dcaPrice, entryTime + 120, dcaPrice, 'rgba(252,213,53,0.5)', 1, true);"""
new3 = """addLine(entryTime - _tfSec, dcaPrice, entryTime + _tfSec, dcaPrice, 'rgba(252,213,53,0.5)', 1, true);"""

if old3 in js:
    js = js.replace(old3, new3, 1)
    changes += 1
    print("[3/4] chart.js: DCA cizgi offset guncellendi")
else:
    print("[3/4] UYARI: DCA cizgi offset bulunamadi (atlandi)")

# 4. symbolHistory: entryTime ve exitTime hizala
old4 = """    symbolHistory.forEach(trade => {
        const entryTime = trade.entry_time;
        const exitTime = trade.exit_time;"""
new4 = """    symbolHistory.forEach(trade => {
        const entryTime = _alignTf(trade.entry_time);
        const exitTime = _alignTf(trade.exit_time);"""

if old4 in js:
    js = js.replace(old4, new4, 1)
    changes += 1
    print("[4/4] chart.js: symbolHistory entryTime/exitTime hizalandi")
else:
    print("[4/4] HATA: symbolHistory blogu bulunamadi!")
    exit(1)

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print("  2. Chart'ta markerlar artik DOGRU mumda gorunmeli")
print("  3. Islem gecmisine tiklayip test et")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {JS_SRC}.bak_marker_align {JS_SRC} -Force")