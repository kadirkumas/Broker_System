import shutil
import os

HTML_SRC = 'frontend/index.html'
JS_SRC = 'frontend/chart.js'
CSS_SRC = 'frontend/style.css'

for src in [HTML_SRC, JS_SRC, CSS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_partial_tp')
    print(f"[1/4] Yedek: {src}.bak_partial_tp")

changes = 0

# ============================================================
# 1. HTML: Her strateji paneline Kismi TP bolumu
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

strategies = [
    ('RSI_SCALPER', '1.5, 3, 5'),
    ('HULL_SRP', '2, 4, 6'),
    ('GRIDBOT', '1, 2, 3'),
]

for strat, steps_val in strategies:
    old_block = f'''                            <div class="cfg-row">
                                <span class="cfg-label">Düşüş Adımları (%)</span>
                                <input type="text" class="search-input strat-param" data-strategy="{strat}" data-param="steps" value="{steps_val}">
                            </div>
                        </div>
                    </div>'''

    new_block = f'''                            <div class="cfg-row">
                                <span class="cfg-label">Düşüş Adımları (%)</span>
                                <input type="text" class="search-input strat-param" data-strategy="{strat}" data-param="steps" value="{steps_val}">
                            </div>
                            <div class="cfg-subtitle">🎯 Kısmi TP (Partial Take Profit)</div>
                            <div class="cfg-row">
                                <span class="cfg-label">Kısmi TP Aktif</span>
                                <label class="switch switch-small">
                                    <input type="checkbox" class="strat-param" data-strategy="{strat}" data-param="partialTPEnabled">
                                    <span class="slider round"></span>
                                </label>
                            </div>
                            <div class="cfg-row">
                                <span class="cfg-label">Kapatma Oranı (%)</span>
                                <input type="number" class="search-input strat-param" data-strategy="{strat}" data-param="partialTPPercent" value="50" min="1" max="99" step="1">
                            </div>
                            <div class="cfg-row">
                                <span class="cfg-label">PT Sonrası DCA</span>
                                <label class="switch switch-small">
                                    <input type="checkbox" class="strat-param" data-strategy="{strat}" data-param="partialTPKeepDCA" checked>
                                    <span class="slider round"></span>
                                </label>
                            </div>
                        </div>
                    </div>'''

    if old_block in html:
        html = html.replace(old_block, new_block, 1)
        changes += 1
        print(f"[2/4] HTML: {strat} Kismi TP eklendi")
    else:
        print(f"[2/4] UYARI: {strat} blogu bulunamadi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. JS: PT rozeti + cardClass
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# 2a. volCell'e PT rozeti
old_vol = '''const volCell = `<span style="display:inline-flex; align-items:center; justify-content:flex-end; gap:8px;"><span style="min-width:68px; text-align:right; color:#EAECEF; font-weight:600;">${p.totalVol.toFixed(2)} USDT</span><span style="min-width:26px; text-align:right; color:#fcd535; font-weight:600; font-size:10px;">${leverage}x</span><span style="min-width:82px; text-align:right; color:#0ECB81; font-weight:600; font-size:10px;">Marjin: ${margin.toFixed(2)}</span><span style="min-width:44px; text-align:center; font-size:10px; font-weight:600; padding:1px 4px; border-radius:3px; ${dcaBg}">${p.dcaCount > 0 ? 'DCA:' + p.dcaCount : 'Ana'}</span></span>`;'''

new_vol = '''const ptBadge = p.ptDone ? `<span title="Kısmi TP alındı" style="min-width:34px; text-align:center; font-size:10px; font-weight:600; padding:1px 4px; border-radius:3px; background:rgba(252,213,53,0.15); color:#fcd535;">PT✓</span>` : '';
            const volCell = `<span style="display:inline-flex; align-items:center; justify-content:flex-end; gap:6px;"><span style="min-width:68px; text-align:right; color:#EAECEF; font-weight:600;">${p.totalVol.toFixed(2)} USDT</span><span style="min-width:26px; text-align:right; color:#fcd535; font-weight:600; font-size:10px;">${leverage}x</span><span style="min-width:82px; text-align:right; color:#0ECB81; font-weight:600; font-size:10px;">Marjin: ${margin.toFixed(2)}</span><span style="min-width:44px; text-align:center; font-size:10px; font-weight:600; padding:1px 4px; border-radius:3px; ${dcaBg}">${p.dcaCount > 0 ? 'DCA:' + p.dcaCount : 'Ana'}</span>${ptBadge}</span>`;'''

if old_vol in js:
    js = js.replace(old_vol, new_vol, 1)
    changes += 1
    print("[3/4] JS: volCell'e PT rozeti eklendi")

# 2b. posArray.push icine PT flag'leri
old_push = '''                strategyName: t.strategy_name || 'UNKNOWN',
                leverage: t.leverage || 1,
                currentPrice: currentPrice,
                pnl: netPnl,
                pnlPct: pnlPct,
            });'''

new_push = '''                strategyName: t.strategy_name || 'UNKNOWN',
                leverage: t.leverage || 1,
                currentPrice: currentPrice,
                pnl: netPnl,
                pnlPct: pnlPct,
                ptEnabled: t.pt_enabled || 0,
                ptDone: t.pt_done || 0,
                ptPercent: t.pt_percent || 50,
            });'''

if old_push in js:
    js = js.replace(old_push, new_push, 1)
    changes += 1
    print("[3/4] JS: posArray'e PT flag'leri eklendi")

# 2c. Canli Bildirimler'de 'KISMI TP' etiketi + kart rengi
old_lbl = '''                            <span class="signal-strategy">| ${reasonText} |</span>'''
new_lbl = '''                            <span class="signal-strategy">| ${evt.is_partial ? '🎯 KISMİ TP' : reasonText} |</span>'''
if old_lbl in js:
    js = js.replace(old_lbl, new_lbl, 1)
    changes += 1
    print("[3/4] JS: Kismi TP etiketi eklendi")

old_card = '''                const isStopLoss = (evt.close_reason || '').toUpperCase().includes('STOP');
                const cardClass = isStopLoss ? 'stop-item' : 'close-item';'''
new_card = '''                const isPartial = evt.is_partial == 1;
                const isStopLoss = (evt.close_reason || '').toUpperCase().includes('STOP');
                let cardClass = 'close-item';
                if (isPartial) cardClass = 'partial-tp-item';
                else if (isStopLoss) cardClass = 'stop-item';'''
if old_card in js:
    js = js.replace(old_card, new_card, 1)
    changes += 1
    print("[3/4] JS: partial-tp-item cardClass eklendi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

# ============================================================
# 3. CSS: PT rozet stilleri
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

new_css = '''

/* ============================================================
   KISMİ TP ROZETİ + BILDIRIM STILI
   ============================================================ */
.pt-badge {
    display: inline-block;
    padding: 1px 5px;
    margin-left: 4px;
    font-size: 9px;
    font-weight: bold;
    background: rgba(252, 213, 53, 0.15);
    color: #fcd535;
    border-radius: 3px;
    letter-spacing: 0.3px;
    vertical-align: middle;
}

.signal-item.partial-tp-item {
    border-left-color: #fcd535 !important;
}
.signal-item.partial-tp-item:hover {
    border-left-color: #e0b82c !important;
    background: #2a2e39;
}
'''

if '.pt-badge' not in css:
    css = css.rstrip() + new_css
    changes += 1
    print("[4/4] CSS: PT rozet stilleri eklendi")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("Geri donmek icin:")
for src in [HTML_SRC, JS_SRC, CSS_SRC]:
    print(f"  Copy-Item {src}.bak_partial_tp {src} -Force")