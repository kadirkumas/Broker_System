import shutil
import os

HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_liq_table'
JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_liq_table'
CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_liq_table'

for src in [HTML_SRC, JS_SRC, CSS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_liq_table')
    print(f"[1/4] Yedek: {src}.bak_liq_table")

changes = 0

# ============================================================
# 1. HTML: thead'e LIQ sütunu ekle (Anlık Fiyat'tan sonra)
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

old = '''                                    <th class="right sortable" style="width:11%;" onclick="window.togglePosSort('currentPrice')">Anlık Fiyat <span class="sort-icon" id="psort-currentPrice"></span></th>'''

new = '''                                    <th class="right sortable" style="width:10%;" onclick="window.togglePosSort('currentPrice')">Anlık Fiyat <span class="sort-icon" id="psort-currentPrice"></span></th>
                                    <th class="right" style="width:11%; color:#F6465D;">💥 LIQ Fiyatı</th>'''

if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[2/4] HTML: LIQ sütunu eklendi")
else:
    print("[2/4] UYARI: Anlık Fiyat th pattern bulunamadi")

# colspan'lari 9 -> 10 yap (boş mesajlar)
html = html.replace(
    'colspan="9" style="text-align:center; color:#848e9c; padding:30px; border:none;">Açık işlem bulunmuyor.',
    'colspan="10" style="text-align:center; color:#848e9c; padding:30px; border:none;">Açık işlem bulunmuyor.'
)
print("[2/4] colspan 9 -> 10 (HTML)")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. JS: renderBottomTrades - LIQ hesabı ve td
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# Satır render'ında currentPrice td'sinden sonra LIQ td ekle
old = '''<td class="right">${window.formatPrice(p.currentPrice)}</td><td class="right" style="color:${pnlColor}; font-weight:bold;">'''

new = '''<td class="right">${window.formatPrice(p.currentPrice)}</td><td class="right" style="color:#F6465D; font-weight:600; font-size:11px;">${liqPrice > 0 ? window.formatPrice(liqPrice) : '—'}</td><td class="right" style="color:${pnlColor}; font-weight:bold;">'''

if old in js:
    js = js.replace(old, new, 1)
    changes += 1
    print("[3/4] JS: LIQ td eklendi")
else:
    print("[3/4] UYARI: currentPrice td pattern bulunamadi")

# Liq hesabını forEach başına ekle (posArray.forEach içinde, p objesi için)
old = '''            const isActiveRow = (p.displaySymbol === activeSymbol) ? 'active-coin-row' : '';
            const diffSec = Math.max(0, Math.floor(Date.now() / 1000) - p.entryTime);'''

new = '''            const isActiveRow = (p.displaySymbol === activeSymbol) ? 'active-coin-row' : '';
            
            // ⚡ LIQ fiyatı hesabı (kaldıraç bazlı, yaklaşık)
            const _lev = p.leverage || 1;
            const _MAINT = 0.005;  // %0.5 maintenance margin (yaklaşık)
            let liqPrice = 0;
            if (_lev > 1 && p.avgPrice > 0) {
                if (p.type === 'LONG') {
                    liqPrice = p.avgPrice * (1 - 1/_lev + _MAINT);
                } else {
                    liqPrice = p.avgPrice * (1 + 1/_lev - _MAINT);
                }
                if (liqPrice <= 0) liqPrice = 0;
            }
            
            const diffSec = Math.max(0, Math.floor(Date.now() / 1000) - p.entryTime);'''

if old in js:
    js = js.replace(old, new, 1)
    changes += 1
    print("[3/4] JS: LIQ hesabı eklendi")
else:
    print("[3/4] UYARI: isActiveRow pattern bulunamadi")

# colspan 9 -> 10 (JS boş mesajlar)
js = js.replace(
    'colspan="9" style="text-align:center; color:#848e9c; padding:40px; border-bottom:none;">Açık işlem bulunmuyor.',
    'colspan="10" style="text-align:center; color:#848e9c; padding:40px; border-bottom:none;">Açık işlem bulunmuyor.'
)
js = js.replace(
    'colspan="9" style="text-align:center; color:#f23645; padding:40px; border-bottom:none;">Backend bağlantı hatası',
    'colspan="10" style="text-align:center; color:#f23645; padding:40px; border-bottom:none;">Backend bağlantı hatası'
)
print("[3/4] colspan 9 -> 10 (JS)")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

# ============================================================
# 3. CSS: LIQ hücresi için stil (opsiyonel)
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

new_css = '''

/* ============================================================
   LIQ SÜTUNU
   ============================================================ */
.btp-table td.liq-cell {
    color: #F6465D !important;
    font-weight: 600 !important;
    font-size: 11px !important;
    font-variant-numeric: tabular-nums !important;
}
'''

if '.liq-cell' not in css:
    css = css.rstrip() + new_css
    changes += 1
    print("[4/4] CSS: LIQ hücre stili eklendi")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI SUTUN: Anlik Fiyat | 💥 LIQ Fiyatı | Kâr/Zarar")
print()
print("ORNEKLER:")
print("  5x LONG,  entry 0.0006990 -> LIQ ~0.0005694")
print("  3x SHORT, entry 0.02641   -> LIQ ~0.03523")
print()
print("HESAP FORMULU:")
print("  LONG : liq = entry x (1 - 1/lev + 0.005)")
print("  SHORT: liq = entry x (1 + 1/lev - 0.005)")
print()
print("NOT: Bu yaklasik bir degerdir. Binance tam likidasyonu")
print("     pozisyon boyutu ve maintenance margin'e gore hesaplar.")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
for src in [HTML_SRC, JS_SRC, CSS_SRC]:
    print(f"  copy /Y {src}.bak_liq_table {src}")