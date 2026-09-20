import shutil
import os

JS_SRC = 'frontend/chart.js'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_SRC + '.bak_marker_align_v2')
print(f"[1/5] Yedek: {JS_SRC}.bak_marker_align_v2")

changes = 0

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# ============================================================
# 1. _tfSec ve _alignTf helper'larini lastTime'dan SONRA ekle
# ============================================================
old1 = """        const now = Math.floor(Date.now() / 1000);
        const lastTime = (cObj.lastCandleTime && cObj.lastCandleTime > now) ? cObj.lastCandleTime : now;
"""
new1 = """        const now = Math.floor(Date.now() / 1000);
        const lastTime = (cObj.lastCandleTime && cObj.lastCandleTime > now) ? cObj.lastCandleTime : now;

        // ⚡ Marker hizalama: unix saniyeyi mum basina yuvarla
        const _tfSec = window.getIntervalSeconds(cObj.interval || '5m') || 300;
        const _alignTf = (t) => t ? Math.floor(t / _tfSec) * _tfSec : t;
"""

if 'const _alignTf = (t) =>' in js:
    print("[2/5] chart.js: _alignTf zaten var (atlandi)")
elif old1 in js:
    js = js.replace(old1, new1, 1)
    changes += 1
    print("[2/5] chart.js: _tfSec + _alignTf helper eklendi")
else:
    print("[2/5] HATA: 'const now + lastTime' blogu bulunamadi!")
    exit(1)

# ============================================================
# 2. addLine icinde t1/t2 hizala (tum cizgiler otomatik hizalanir)
# ============================================================
old2 = """                let t1 = time1, t2 = time2;
                if (t1 < firstCandleTime) t1 = firstCandleTime;"""
new2 = """                let t1 = _alignTf(time1), t2 = _alignTf(time2);
                if (t1 < firstCandleTime) t1 = firstCandleTime;"""

if 'let t1 = _alignTf(time1)' in js:
    print("[3/5] chart.js: addLine zaten hizali (atlandi)")
elif old2 in js:
    js = js.replace(old2, new2, 1)
    changes += 1
    print("[3/5] chart.js: addLine time hizalama eklendi")
else:
    print("[3/5] UYARI: addLine blogu bulunamadi (atlandi)")

# ============================================================
# 3. symbolActive: entryTime hizala
# ============================================================
old3 = """        symbolActive.forEach(pos => {
            const entryTime = pos.entry_time;"""
new3 = """        symbolActive.forEach(pos => {
            const entryTime = _alignTf(pos.entry_time);"""

if 'const entryTime = _alignTf(pos.entry_time)' in js:
    print("[4/5] chart.js: symbolActive zaten hizali (atlandi)")
elif old3 in js:
    js = js.replace(old3, new3, 1)
    changes += 1
    print("[4/5] chart.js: symbolActive entryTime hizalandi")
else:
    print("[4/5] HATA: symbolActive blogu bulunamadi!")
    exit(1)

# ============================================================
# 4. symbolHistory: entryTime + exitTime hizala
# ============================================================
old4 = """        symbolHistory.forEach(trade => {
            const entryTime = trade.entry_time;
            const exitTime = trade.exit_time;"""
new4 = """        symbolHistory.forEach(trade => {
            const entryTime = _alignTf(trade.entry_time);
            const exitTime = _alignTf(trade.exit_time);"""

if 'const entryTime = _alignTf(trade.entry_time)' in js:
    print("[5/5] chart.js: symbolHistory zaten hizali (atlandi)")
elif old4 in js:
    js = js.replace(old4, new4, 1)
    changes += 1
    print("[5/5] chart.js: symbolHistory entryTime + exitTime hizalandi")
else:
    print("[5/5] HATA: symbolHistory blogu bulunamadi!")
    exit(1)

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - Marker'lar artik MUM BASINA hizalanir")
print("  - entry_time = 21:21:28 -> 21:20 mumunda gorunur")
print("  - exit_time = 21:26:33 -> 21:25 mumunda gorunur")
print("  - Cizgiler (DCA/entry/exit) de mum sinirlarina hizali")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print("  2. Chart'ta bir sembole tikla, markerlari kontrol et")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {JS_SRC}.bak_marker_align_v2 {JS_SRC} -Force")