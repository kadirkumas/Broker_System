import shutil
import os

HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_stats_modal'
CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_stats_modal'
JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_stats_modal'
MAIN_SRC = 'backend/main.py'
MAIN_BAK = 'backend/main.py.bak_stats_modal'

for src in [HTML_SRC, CSS_SRC, JS_SRC, MAIN_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_stats_modal')
    print(f"[1/5] Yedek: {src}.bak_stats_modal")

changes = 0

# ============================================================
# 1. BACKEND: Yeni endpoint'ler
# ============================================================
with open(MAIN_SRC, 'r', encoding='utf-8', newline='') as f:
    main = f.read().replace('\r\n', '\n')

new_endpoints = '''

# ----------------------------------------------------------------------
# İSTATİSTİK - Sembol bazlı analiz
# ----------------------------------------------------------------------
@app.get("/api/stats/symbols")
async def get_symbol_stats(min_trades: int = 1):
    """Sembol başına kâr/zarar istatistikleri."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT 
            symbol,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl_amount > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl_amount <= 0 THEN 1 ELSE 0 END) as losses,
            ROUND(SUM(pnl_amount), 4) as total_pnl,
            ROUND(AVG(pnl_pct), 4) as avg_pnl_pct,
            ROUND(MAX(pnl_amount), 4) as best,
            ROUND(MIN(pnl_amount), 4) as worst
        FROM trade_history
        WHERE ABS(pnl_amount) < (total_vol * 5)
        GROUP BY symbol
        HAVING COUNT(*) >= ?
        ORDER BY total_pnl DESC
    """, (min_trades,)).fetchall()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        total = d["trades"] or 0
        wins = d["wins"] or 0
        d["win_rate"] = round((wins / total) * 100, 2) if total > 0 else 0
        result.append(d)
    return result


# ----------------------------------------------------------------------
# İSTATİSTİK - Kapanış sebebi analizi
# ----------------------------------------------------------------------
@app.get("/api/stats/close-reasons")
async def get_close_reason_stats():
    """Kapanış sebeplerine göre analiz (TP/Trailing/SL)."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT 
            CASE 
                WHEN close_reason LIKE '%TRAILING%' THEN 'TRAILING'
                WHEN close_reason LIKE '%STOP%' THEN 'STOP LOSS'
                WHEN close_reason LIKE '%TAKE%' THEN 'TAKE PROFIT'
                WHEN close_reason LIKE '%DELIST%' THEN 'DELISTED'
                ELSE 'DIGER'
            END as reason,
            COUNT(*) as trades,
            SUM(CASE WHEN pnl_amount > 0 THEN 1 ELSE 0 END) as wins,
            ROUND(SUM(pnl_amount), 4) as total_pnl,
            ROUND(AVG(pnl_pct), 4) as avg_pnl_pct
        FROM trade_history
        WHERE ABS(pnl_amount) < (total_vol * 5)
        GROUP BY reason
        ORDER BY total_pnl DESC
    """).fetchall()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        total = d["trades"] or 0
        wins = d["wins"] or 0
        d["win_rate"] = round((wins / total) * 100, 2) if total > 0 else 0
        result.append(d)
    return result
'''

if '/api/stats/symbols' not in main:
    main = main.rstrip() + new_endpoints
    changes += 1
    print("[2/5] main.py: /api/stats/symbols + /api/stats/close-reasons eklendi")

with open(MAIN_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(main.replace('\n', '\r\n'))

# ============================================================
# 2. HTML: İstatistik modalı + Ayarlar butonu yanına "📊 İstatistik"
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

# Top bar'a buton ekle
old = '''<button class="bot-settings-btn" onclick="openChartSettingsModal()" title="Grafik Ayarları">⚙️ Ayarlar</button>'''

new = '''<button class="bot-settings-btn" onclick="openStatsModal()" style="border-color: #fcd535; color: #fcd535;" title="İstatistikler">📊 İstatistik</button>
                <button class="bot-settings-btn" onclick="openChartSettingsModal()" title="Grafik Ayarları">⚙️ Ayarlar</button>'''

if old in html and 'openStatsModal()' not in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[3/5] HTML: 📊 İstatistik butonu eklendi")

# Modal HTML'i (indicator-modal'ın öncesine ekle)
modal_html = '''
    <div id="stats-modal" class="modal-overlay">
        <div class="modal-content" style="width: 1100px; max-width: 96vw; height: 700px; max-height: 92vh; background: #0b0e14; border: 1px solid #2b3139;">
            <div class="modal-header" style="background: #181a20; border-bottom: 1px solid #2b3139;">
                <h2>📊 Trading İstatistikleri</h2>
                <span class="modal-close" onclick="closeStatsModal()">✕</span>
            </div>

            <div class="stats-tabs">
                <div class="stats-tab active" data-tab="strategy" onclick="switchStatsTab('strategy')">📈 Strateji Performansı</div>
                <div class="stats-tab" data-tab="symbol" onclick="switchStatsTab('symbol')">💰 En Kârlı Semboller</div>
                <div class="stats-tab" data-tab="reason" onclick="switchStatsTab('reason')">📉 Kapanış Sebepleri</div>
            </div>

            <div class="stats-summary-bar">
                <div class="stats-summary-item">
                    <span class="lbl">Toplam İşlem</span>
                    <span class="val" id="stats-total-trades">0</span>
                </div>
                <div class="stats-summary-item">
                    <span class="lbl">Toplam PnL</span>
                    <span class="val" id="stats-total-pnl">0.00 USDT</span>
                </div>
                <div class="stats-summary-item">
                    <span class="lbl">Genel Win Rate</span>
                    <span class="val" id="stats-total-wr">0%</span>
                </div>
                <div class="stats-summary-item">
                    <span class="lbl">Kârlı / Zararlı Gün</span>
                    <span class="val" id="stats-days">0 / 0</span>
                </div>
            </div>

            <div class="stats-body">
                <div id="stats-content" style="padding: 15px 20px; overflow-y: auto; flex: 1;">
                    <div style="text-align: center; color: #848e9c; padding: 40px;">Yükleniyor...</div>
                </div>
            </div>
        </div>
    </div>
'''

old = '    <div id="indicator-modal" class="modal-overlay">'
if old in html and 'stats-modal' not in html:
    html = html.replace(old, modal_html + '\n' + old, 1)
    changes += 1
    print("[3/5] HTML: stats-modal eklendi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 3. CSS: İstatistik stilleri
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

new_css = '''

/* ============================================================
   İSTATİSTİK MODAL
   ============================================================ */
.stats-tabs {
    display: flex;
    gap: 0;
    background: #131722;
    border-bottom: 1px solid #2b3139;
    padding: 0 20px;
}

.stats-tab {
    padding: 14px 24px;
    color: #848e9c;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    border-bottom: 3px solid transparent;
    transition: all 0.15s;
    user-select: none;
}

.stats-tab:hover {
    color: #EAECEF;
    background: rgba(255, 255, 255, 0.02);
}

.stats-tab.active {
    color: #fcd535;
    border-bottom-color: #fcd535;
}

.stats-summary-bar {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1px;
    background: #2b3139;
    border-bottom: 1px solid #2b3139;
}

.stats-summary-item {
    background: #131722;
    padding: 14px 20px;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.stats-summary-item .lbl {
    font-size: 10px;
    color: #848e9c;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

.stats-summary-item .val {
    font-size: 18px;
    font-weight: 700;
    color: #EAECEF;
    font-variant-numeric: tabular-nums;
}

.stats-body {
    flex: 1;
    overflow: hidden;
    display: flex;
    background: #0b0e14;
}

/* Tablolar */
.stats-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}

.stats-table th {
    background: #131722;
    color: #848e9c;
    font-weight: 600;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 10px 12px;
    text-align: right;
    border-bottom: 1px solid #2b3139;
    position: sticky;
    top: 0;
    z-index: 5;
}

.stats-table th:first-child,
.stats-table th.left {
    text-align: left;
}

.stats-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #1e222d;
    color: #d1d4dc;
    font-variant-numeric: tabular-nums;
    text-align: right;
}

.stats-table td:first-child,
.stats-table td.left {
    text-align: left;
    font-weight: 600;
    color: #EAECEF;
}

.stats-table tr:hover td {
    background: rgba(255, 255, 255, 0.03);
}

/* Win rate bar */
.wr-bar {
    position: relative;
    display: inline-block;
    width: 60px;
    height: 6px;
    background: #2a2e39;
    border-radius: 3px;
    overflow: hidden;
    vertical-align: middle;
    margin-right: 8px;
}

.wr-bar > div {
    position: absolute;
    left: 0;
    top: 0;
    height: 100%;
    border-radius: 3px;
}

.wr-bar.good > div { background: #0ECB81; }
.wr-bar.mid > div { background: #fcd535; }
.wr-bar.bad > div { background: #F6465D; }

/* PnL Renk */
.pnl-pos { color: #0ECB81; font-weight: 700; }
.pnl-neg { color: #F6465D; font-weight: 700; }

/* Rank badge */
.rank-badge {
    display: inline-block;
    width: 22px;
    height: 22px;
    line-height: 22px;
    text-align: center;
    border-radius: 50%;
    background: #1e222d;
    color: #848e9c;
    font-size: 10px;
    font-weight: 700;
    margin-right: 8px;
}

.rank-badge.gold { background: rgba(252, 213, 53, 0.2); color: #fcd535; }
.rank-badge.silver { background: rgba(132, 142, 156, 0.2); color: #b2b5be; }
.rank-badge.bronze { background: rgba(205, 127, 50, 0.2); color: #cd7f32; }
'''

if '.stats-tabs' not in css:
    css = css.rstrip() + new_css
    changes += 1
    print("[4/5] CSS: istatistik stilleri eklendi")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

# ============================================================
# 4. JS: Stats modal fonksiyonları
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

new_js = '''

// =============================================================
// İSTATİSTİK MODAL
// =============================================================
window.statsCurrentTab = 'strategy';
window.statsData = { strategy: null, symbol: null, reason: null };

window.openStatsModal = function() {
    const modal = document.getElementById('stats-modal');
    if (!modal) return;
    modal.classList.add('active');
    window.switchStatsTab('strategy');
};

window.closeStatsModal = function() {
    const modal = document.getElementById('stats-modal');
    if (modal) modal.classList.remove('active');
};

window.switchStatsTab = function(tab) {
    window.statsCurrentTab = tab;
    
    document.querySelectorAll('.stats-tab').forEach(function(el) {
        if (el.dataset.tab === tab) el.classList.add('active');
        else el.classList.remove('active');
    });
    
    window.loadStatsContent(tab);
};

window.loadStatsContent = async function(tab) {
    const content = document.getElementById('stats-content');
    if (!content) return;
    content.innerHTML = '<div style="text-align:center; color:#848e9c; padding:40px;">Yükleniyor...</div>';
    
    try {
        // ⚡ ÖZET BAR: her zaman tüm verilerden hesapla
        const histRes = await fetch('/api/trade/history?limit=2000');
        const allTrades = await histRes.json();
        
        if (Array.isArray(allTrades) && allTrades.length > 0) {
            const validTrades = allTrades.filter(function(t) {
                return Math.abs(t.pnl_amount) < (t.total_vol * 5);
            });
            
            let totalTrades = validTrades.length;
            let totalPnl = 0;
            let wins = 0;
            validTrades.forEach(function(t) {
                totalPnl += t.pnl_amount;
                if (t.pnl_amount >= 0) wins++;
            });
            let wr = totalTrades > 0 ? (wins / totalTrades * 100) : 0;
            
            document.getElementById('stats-total-trades').innerText = totalTrades;
            const pnlEl = document.getElementById('stats-total-pnl');
            pnlEl.innerText = (totalPnl >= 0 ? '+' : '') + totalPnl.toFixed(2) + ' USDT';
            pnlEl.style.color = totalPnl >= 0 ? '#0ECB81' : '#F6465D';
            document.getElementById('stats-total-wr').innerText = wr.toFixed(1) + '%';
            
            // Gün sayısı
            const dailyRes = await fetch('/api/stats/daily?days=365');
            const dailyData = await dailyRes.json();
            let winDays = 0, lossDays = 0;
            if (Array.isArray(dailyData)) {
                dailyData.forEach(function(d) {
                    if (d.net_pnl > 0) winDays++;
                    else if (d.net_pnl < 0) lossDays++;
                });
            }
            document.getElementById('stats-days').innerText = winDays + ' / ' + lossDays;
        }
        
        // ⚡ TAB İÇERİĞİ
        if (tab === 'strategy') {
            const res = await fetch('/api/stats/strategies');
            const data = await res.json();
            if (!Array.isArray(data) || data.length === 0) {
                content.innerHTML = '<div style="text-align:center; color:#848e9c; padding:40px;">Henüz yeterli veri yok.</div>';
                return;
            }
            content.innerHTML = window.renderStrategyStats(data);
            
        } else if (tab === 'symbol') {
            const res = await fetch('/api/stats/symbols?min_trades=1');
            const data = await res.json();
            if (!Array.isArray(data) || data.length === 0) {
                content.innerHTML = '<div style="text-align:center; color:#848e9c; padding:40px;">Henüz yeterli veri yok.</div>';
                return;
            }
            content.innerHTML = window.renderSymbolStats(data);
            
        } else if (tab === 'reason') {
            const res = await fetch('/api/stats/close-reasons');
            const data = await res.json();
            if (!Array.isArray(data) || data.length === 0) {
                content.innerHTML = '<div style="text-align:center; color:#848e9c; padding:40px;">Henüz yeterli veri yok.</div>';
                return;
            }
            content.innerHTML = window.renderReasonStats(data);
        }
        
    } catch(e) {
        console.error('[STATS] Hata:', e);
        content.innerHTML = '<div style="text-align:center; color:#F6465D; padding:40px;">Hata: ' + e.message + '</div>';
    }
};

window.wrBar = function(wr) {
    const cls = wr >= 60 ? 'good' : (wr >= 40 ? 'mid' : 'bad');
    return '<span class="wr-bar ' + cls + '"><div style="width:' + Math.min(100, wr) + '%"></div></span>' + wr.toFixed(1) + '%';
};

window.renderStrategyStats = function(data) {
    let html = '<table class="stats-table"><thead><tr>'
        + '<th class="left">Strateji</th>'
        + '<th>İşlem</th>'
        + '<th>Kârlı</th>'
        + '<th>Zararlı</th>'
        + '<th>Win Rate</th>'
        + '<th>Toplam PnL</th>'
        + '<th>Ort. PnL %</th>'
        + '<th>En İyi</th>'
        + '<th>En Kötü</th>'
        + '<th>Ort. DCA</th>'
        + '</tr></thead><tbody>';
    
    data.forEach(function(d) {
        const pnlCls = d.total_pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
        const sign = d.total_pnl >= 0 ? '+' : '';
        html += '<tr>'
            + '<td class="left">' + (d.strategy_name || 'UNKNOWN') + '</td>'
            + '<td>' + d.total_trades + '</td>'
            + '<td style="color:#0ECB81;">' + d.wins + '</td>'
            + '<td style="color:#F6465D;">' + d.losses + '</td>'
            + '<td>' + window.wrBar(d.win_rate) + '</td>'
            + '<td class="' + pnlCls + '">' + sign + d.total_pnl.toFixed(4) + '</td>'
            + '<td>' + (d.avg_pnl_pct >= 0 ? '+' : '') + d.avg_pnl_pct.toFixed(2) + '%</td>'
            + '<td style="color:#0ECB81;">+' + d.best_trade.toFixed(4) + '</td>'
            + '<td style="color:#F6465D;">' + d.worst_trade.toFixed(4) + '</td>'
            + '<td>' + (d.avg_dca || 0).toFixed(2) + '</td>'
            + '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
};

window.renderSymbolStats = function(data) {
    let html = '<table class="stats-table"><thead><tr>'
        + '<th class="left">#</th>'
        + '<th class="left">Sembol</th>'
        + '<th>İşlem</th>'
        + '<th>Kârlı</th>'
        + '<th>Zararlı</th>'
        + '<th>Win Rate</th>'
        + '<th>Toplam PnL</th>'
        + '<th>Ort. PnL %</th>'
        + '<th>En İyi</th>'
        + '<th>En Kötü</th>'
        + '</tr></thead><tbody>';
    
    data.forEach(function(d, i) {
        const pnlCls = d.total_pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
        const sign = d.total_pnl >= 0 ? '+' : '';
        let rankCls = '';
        if (i === 0) rankCls = 'gold';
        else if (i === 1) rankCls = 'silver';
        else if (i === 2) rankCls = 'bronze';
        
        html += '<tr>'
            + '<td class="left"><span class="rank-badge ' + rankCls + '">' + (i + 1) + '</span></td>'
            + '<td class="left">' + d.symbol + '</td>'
            + '<td>' + d.trades + '</td>'
            + '<td style="color:#0ECB81;">' + d.wins + '</td>'
            + '<td style="color:#F6465D;">' + d.losses + '</td>'
            + '<td>' + window.wrBar(d.win_rate) + '</td>'
            + '<td class="' + pnlCls + '">' + sign + d.total_pnl.toFixed(4) + '</td>'
            + '<td>' + (d.avg_pnl_pct >= 0 ? '+' : '') + d.avg_pnl_pct.toFixed(2) + '%</td>'
            + '<td style="color:#0ECB81;">+' + d.best.toFixed(4) + '</td>'
            + '<td style="color:#F6465D;">' + d.worst.toFixed(4) + '</td>'
            + '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
};

window.renderReasonStats = function(data) {
    let html = '<table class="stats-table"><thead><tr>'
        + '<th class="left">Kapanış Sebebi</th>'
        + '<th>İşlem</th>'
        + '<th>Kârlı</th>'
        + '<th>Win Rate</th>'
        + '<th>Toplam PnL</th>'
        + '<th>Ort. PnL %</th>'
        + '</tr></thead><tbody>';
    
    data.forEach(function(d) {
        const pnlCls = d.total_pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
        const sign = d.total_pnl >= 0 ? '+' : '';
        const reasonEmoji = {
            'TRAILING': '🎯',
            'STOP LOSS': '🛑',
            'TAKE PROFIT': '✅',
            'DELISTED': '🚫',
            'DIGER': '❓'
        };
        const emoji = reasonEmoji[d.reason] || '❓';
        
        html += '<tr>'
            + '<td class="left">' + emoji + ' ' + d.reason + '</td>'
            + '<td>' + d.trades + '</td>'
            + '<td style="color:#0ECB81;">' + d.wins + '</td>'
            + '<td>' + window.wrBar(d.win_rate) + '</td>'
            + '<td class="' + pnlCls + '">' + sign + d.total_pnl.toFixed(4) + '</td>'
            + '<td>' + (d.avg_pnl_pct >= 0 ? '+' : '') + d.avg_pnl_pct.toFixed(2) + '%</td>'
            + '</tr>';
    });
    
    html += '</tbody></table>';
    return html;
};

// ESC ile kapat
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const m = document.getElementById('stats-modal');
        if (m && m.classList.contains('active')) m.classList.remove('active');
    }
});
'''

if 'İSTATİSTİK MODAL' not in js:
    js = js.rstrip() + new_js
    changes += 1
    print("[5/5] JS: stats modal fonksiyonları eklendi")
else:
    print("[5/5] JS: zaten var")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - Ust barda '📊 İstatistik' butonu")
print("  - Modal icinde 3 sekme:")
print("    1. Strateji Performansı (RSI/HULL/GRIDBOT karşılaştırma)")
print("    2. En Kârlı Semboller (altin/gumus/bronz rozet)")
print("    3. Kapanış Sebepleri (TP/Trailing/SL analizi)")
print("  - Ust ozet bari: Toplam işlem / PnL / Win Rate / Gun")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend'i Ctrl+C ile durdur")
print("  2. py -m uvicorn backend.main:app --reload")
print("  3. Ctrl+Shift+R")
print("  4. Ust barda 📊 İstatistik butonuna bas")
print()
print("Geri donmek icin:")
for src in [HTML_SRC, CSS_SRC, JS_SRC, MAIN_SRC]:
    print(f"  Copy-Item frontend\\{os.path.basename(src)}.bak_stats_modal {src} -Force")