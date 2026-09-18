import shutil
import os

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_liq_line'
CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_liq_line'

for src in [JS_SRC, CSS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_liq_line')
    print(f"[1/4] Yedek: {src}.bak_liq_line")

changes = 0

# ============================================================
# 1. JS: showSymbolTrades - aktif pozisyona likidasyon çizgisi ekle
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# Aktif pozisyon entry çizgisinin hemen altına likidasyon bloğunu ekle
old = '''            // ⚡ KISA yatay çizgi: giriş mumun ±2 mum
            addLine(entryTime - 120, entryPrice, entryTime + 120, entryPrice, 'rgba(252,213,53,0.6)', 2, true);'''

new = '''            // ⚡ KISA yatay çizgi: giriş mumun ±2 mum
            addLine(entryTime - 120, entryPrice, entryTime + 120, entryPrice, 'rgba(252,213,53,0.6)', 2, true);
            
            // ⚡ LİKİDASYON ÇİZGİSİ (kaldıraç bazlı, kırmızı kalın)
            const _lev = pos.leverage || 1;
            if (_lev > 1) {
                const MAINT_MARGIN = 0.005;  // %0.5 (yaklaşık, küçük pozisyonlar için)
                let liqPrice;
                if (isLong) {
                    liqPrice = entryPrice * (1 - (1 / _lev) + MAINT_MARGIN);
                } else {
                    liqPrice = entryPrice * (1 + (1 / _lev) - MAINT_MARGIN);
                }
                
                if (liqPrice > 0) {
                    // Likidasyon çizgisi: girişten son mumun ötesine
                    const liqEndTime = (lastTime && lastTime > entryTime) ? lastTime : entryTime + 300;
                    addLine(entryTime - 60, liqPrice, liqEndTime, liqPrice, '#F6465D', 2, true);
                    
                    // LIQ etiketi
                    tradeLabels.push({
                        time: liqEndTime,
                        price: liqPrice,
                        linePrice: liqPrice,
                        text: `💥 LIQ ${window.formatPrice(liqPrice)}`,
                        type: isLong ? 'LONG' : 'SHORT',
                        isExit: false,
                        position: 'onLine',
                        colorClass: 'liq-label'
                    });
                }
            }'''

if old in js:
    js = js.replace(old, new, 1)
    changes += 1
    print("[2/4] JS: aktif pozisyon için likidasyon çizgisi eklendi")
else:
    print("[2/4] UYARI: entry çizgisi pattern bulunamadi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

# ============================================================
# 2. CSS: LIQ etiketi stili
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

new_css = '''

/* ============================================================
   LİKİDASYON ETİKETİ
   ============================================================ */
.trade-label.liq-label {
    background-color: #F6465D !important;
    color: #fff !important;
    font-weight: bold !important;
    border: 1px solid #fff !important;
    box-shadow: 0 0 12px rgba(246, 70, 93, 0.8) !important;
    padding: 2px 7px !important;
    font-size: 10px !important;
    letter-spacing: 0.3px !important;
    animation: liqPulse 2s infinite;
}

@keyframes liqPulse {
    0%, 100% { box-shadow: 0 0 12px rgba(246, 70, 93, 0.8); }
    50% { box-shadow: 0 0 20px rgba(246, 70, 93, 1); }
}

.trade-line.liq-label {
    display: none !important;
}
'''

if '.trade-label.liq-label' not in css:
    css = css.rstrip() + new_css
    changes += 1
    print("[3/4] CSS: liq-label stili eklendi")
else:
    print("[3/4] CSS: liq-label zaten var")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("LIKIDASYON HESABI (yaklasik):")
print("  LONG  için: liq = entry x (1 - 1/kaldirac + 0.005)")
print("  SHORT için: liq = entry x (1 + 1/kaldirac - 0.005)")
print()
print("ORNEKLER:")
print("  5x LONG, entry 0.0007958  -> liq ~0.0006366")
print("  3x LONG, entry 0.02641    -> liq ~0.01761")
print("  10x SHORT, entry 100      -> liq ~110.50")
print()
print("NOT: Formül yaklaşıktır, gerçek likidasyon Binance'te")
print("     pozisyon büyüklüğüne göre maintenance margin ile değişir.")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {JS_BAK} {JS_SRC}")
print(f"  copy /Y {CSS_BAK} {CSS_SRC}")