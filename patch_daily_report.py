import shutil
import os

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_daily_report'
HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_daily_report'

for src in [JS_SRC, HTML_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_daily_report')
    print(f"[1/3] Yedek: {src}.bak_daily_report")

changes = 0

# ============================================================
# 1. HTML: Modal'ı yeniden yapılandır
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

old = '''    <div id="daily-report-modal" class="modal-overlay">
        <div class="modal-content" style="width: 450px; height: 500px; background: #0b0e14; border: 1px solid #2b3139;">
            <div class="modal-header" style="background: #181a20;">
                <h2>📅 Günlük Kâr / Zarar Takvimi</h2>
                <span class="modal-close" onclick="closeDailyReportModal()">✕</span>
            </div>
            <div class="modal-body" style="padding: 0; display: flex; flex-direction: column; overflow-y: auto;">
                <table class="btp-table" style="width: 100%;">
                    <thead style="position: sticky; top: 0; z-index: 5;">
                        <tr>
                            <th class="left" style="background: #181a20;">Tarih</th>
                            <th class="center" style="background: #181a20;">İşlem Sayısı</th>
                            <th class="right" style="background: #181a20;">Net Kâr / Zarar</th>
                        </tr>
                    </thead>
                    <tbody id="daily-report-tbody"></tbody>
                </table>
            </div>
        </div>
    </div>'''

new = '''    <div id="daily-report-modal" class="modal-overlay">
        <div class="modal-content" style="width: 750px; max-width: 95vw; height: 600px; background: #0b0e14; border: 1px solid #2b3139;">
            <div class="modal-header" style="background: #181a20; border-bottom: 1px solid #2b3139;">
                <h2>📅 Bugünün İşlem Raporu</h2>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span id="daily-modal-summary" style="font-size: 13px; font-weight: bold; color: #0ECB81;">+0.00 USDT</span>
                    <span class="modal-close" onclick="closeDailyReportModal()">✕</span>
                </div>
            </div>
            <div class="modal-body" style="padding: 0; display: flex; flex-direction: column; overflow-y: auto;">
                <table class="btp-table" style="width: 100%;">
                    <thead style="position: sticky; top: 0; z-index: 5; background: #181a20;">
                        <tr>
                            <th class="left" style="background: #181a20; width: 6%;">#</th>
                            <th class="left" style="background: #181a20; width: 14%;">Sembol</th>
                            <th class="left" style="background: #181a20; width: 8%;">Yön</th>
                            <th class="right" style="background: #181a20; width: 11%;">Giriş</th>
                            <th class="right" style="background: #181a20; width: 11%;">Çıkış</th>
                            <th class="right" style="background: #181a20; width: 15%;">Kâr / Zarar</th>
                            <th class="right" style="background: #181a20; width: 12%;">Net USDT</th>
                            <th class="right" style="background: #181a20; width: 10%;">Sebep</th>
                            <th class="right" style="background: #181a20; width: 13%;">Saat</th>
                        </tr>
                    </thead>
                    <tbody id="daily-report-tbody"></tbody>
                </table>
            </div>
            <div style="padding: 12px 20px; border-top: 1px solid #2b3139; background: #181a20; display: flex; justify-content: space-between; align-items: center; font-size: 13px;">
                <span style="color: #848e9c;">Kapanan işlem sayısı: <b id="daily-modal-count" style="color: #EAECEF;">0</b></span>
                <div style="display: flex; gap: 20px;">
                    <span style="color: #0ECB81;">Kârlı: <b id="daily-modal-wins">0</b></span>
                    <span style="color: #F6465D;">Zararlı: <b id="daily-modal-losses">0</b></span>
                    <span style="color: #fcd535;">Win Rate: <b id="daily-modal-winrate">0%</b></span>
                </div>
            </div>
        </div>
    </div>'''

if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[2/3] HTML: daily-report-modal yenilendi")
else:
    # Kısmi eşleşme dene
    if 'daily-report-modal' in html and 'daily-report-tbody' in html:
        print("[2/3] UYARI: tam eşleşme yok, manuel düzeltme gerekli")
    else:
        print("[2/3] HATA: daily-report-modal bulunamadi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. JS: openDailyReportModal ve closeDailyReportModal
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# Varsa eski fonksiyonları sil
import re
js = re.sub(r'window\.openDailyReportModal = function\(\)\s*\{.*?\n\};', '', js, flags=re.DOTALL)
js = re.sub(r'window\.closeDailyReportModal = function\(\)\s*\{.*?\n\};', '', js, flags=re.DOTALL)

new_js = '''

// =============================================================
// BUGÜNÜN İŞLEM RAPORU MODALI
// =============================================================
window.openDailyReportModal = async function() {
    const modal = document.getElementById('daily-report-modal');
    const tbody = document.getElementById('daily-report-tbody');
    if (!modal || !tbody) return;
    
    modal.classList.add('active');
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:#848e9c; padding:30px;">Yükleniyor...</td></tr>';
    
    try {
        const res = await fetch('/api/trade/history?limit=1000');
        let trades = await res.json();
        if (!Array.isArray(trades)) trades = [];
        
        // Bugün (TR saati) filtresi
        const todayStr = new Date().toDateString();
        let todayTrades = trades.filter(function(t) {
            return new Date(t.exit_time * 1000).toDateString() === todayStr;
        });
        
        // Saat sıralaması: en yeni en üstte
        todayTrades.sort(function(a, b) { return b.exit_time - a.exit_time; });
        
        // Özet
        let totalPnl = 0, wins = 0, losses = 0;
        todayTrades.forEach(function(t) {
            totalPnl += t.pnl_amount;
            if (t.pnl_amount >= 0) wins++; else losses++;
        });
        
        const totalSign = totalPnl >= 0 ? '+' : '';
        const totalColor = totalPnl >= 0 ? '#0ECB81' : '#F6465D';
        
        const summaryEl = document.getElementById('daily-modal-summary');
        if (summaryEl) {
            summaryEl.innerText = totalSign + totalPnl.toFixed(2) + ' USDT';
            summaryEl.style.color = totalColor;
        }
        
        const countEl = document.getElementById('daily-modal-count');
        if (countEl) countEl.innerText = todayTrades.length;
        
        const winsEl = document.getElementById('daily-modal-wins');
        if (winsEl) winsEl.innerText = wins;
        
        const lossesEl = document.getElementById('daily-modal-losses');
        if (lossesEl) lossesEl.innerText = losses;
        
        const winrateEl = document.getElementById('daily-modal-winrate');
        if (winrateEl) {
            const wr = todayTrades.length > 0 ? (wins / todayTrades.length * 100).toFixed(1) : '0';
            winrateEl.innerText = wr + '%';
        }
        
        // Bugün kapanan işlem yoksa
        if (todayTrades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:#848e9c; padding:40px;">Bugün kapanan işlem yok.</td></tr>';
            return;
        }
        
        // Satırlar
        let html = '';
        let running = 0;  // kümülatif kâr
        // Eskiden yeniye göre kümülatif hesaplama için ters sırala
        const chrono = [...todayTrades].reverse();
        const cumMap = {};
        chrono.forEach(function(t) {
            running += t.pnl_amount;
            cumMap[t.id] = running;
        });
        
        todayTrades.forEach(function(t, i) {
            const isLong = t.trade_type === 'BUY';
            const tagClass = isLong ? 'pos-long' : 'pos-short';
            const tagText = isLong ? '▲ LONG' : '▼ SHORT';
            const isProfit = t.pnl_amount >= 0;
            const pnlColor = isProfit ? '#0ECB81' : '#F6465D';
            const sign = isProfit ? '+' : '';
            const cum = cumMap[t.id] || 0;
            const cumSign = cum >= 0 ? '+' : '';
            const cumColor = cum >= 0 ? '#0ECB81' : '#F6465D';
            
            // Saat
            const d = new Date(t.exit_time * 1000);
            const timeStr = String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0');
            
            // Sebep kısalt
            let reasonShort = '—';
            const reason = (t.close_reason || '').toUpperCase();
            if (reason.includes('TRAILING')) reasonShort = 'T';
            else if (reason.includes('STOP')) reasonShort = 'SL';
            else if (reason.includes('TAKE')) reasonShort = 'TP';
            else if (reason.includes('DELIST')) reasonShort = 'DEL';
            
            // DCA rozeti
            const dcaBadge = t.dca_count > 0 ? ' <span style="color:#fcd535; font-size:10px;">DCA:' + t.dca_count + '</span>' : '';
            
            const rowNum = todayTrades.length - i;
            
            html += '<tr style="border-bottom:1px solid #1e222d;">'
                + '<td class="left" style="color:#848e9c;">#' + rowNum + '</td>'
                + '<td class="left" style="font-weight:600;">' + t.symbol + dcaBadge + '</td>'
                + '<td class="left ' + tagClass + '">' + tagText + '</td>'
                + '<td class="right">' + window.formatPrice(t.entry_price) + '</td>'
                + '<td class="right">' + window.formatPrice(t.exit_price) + '</td>'
                + '<td class="right" style="color:' + pnlColor + '; font-weight:bold;">' + sign + t.pnl_pct.toFixed(2) + '%</td>'
                + '<td class="right" style="color:' + pnlColor + '; font-weight:bold;">' + sign + t.pnl_amount.toFixed(4) + ' USDT'
                + ' <span style="color:' + cumColor + '; font-size:10px;">(Σ ' + cumSign + cum.toFixed(4) + ')</span></td>'
                + '<td class="right"><span title="' + (t.close_reason || '') + '" style="font-size:10px; padding:2px 5px; background:rgba(252,213,53,0.1); color:#fcd535; border-radius:3px; cursor:help;">' + reasonShort + '</span></td>'
                + '<td class="right" style="color:#848e9c; font-size:11px;">' + timeStr + '</td>'
                + '</tr>';
        });
        
        tbody.innerHTML = html;
        
    } catch(e) {
        console.error('[DailyReport] Hata:', e);
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:#F6465D; padding:30px;">Hata: ' + e.message + '</td></tr>';
    }
};

window.closeDailyReportModal = function() {
    const modal = document.getElementById('daily-report-modal');
    if (modal) modal.classList.remove('active');
};

// ESC ile kapatma
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const m = document.getElementById('daily-report-modal');
        if (m && m.classList.contains('active')) {
            m.classList.remove('active');
        }
    }
});
'''

js = js.rstrip() + new_js
changes += 1
print("[3/3] JS: openDailyReportModal + closeDailyReportModal eklendi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIKLER:")
print("  - 'Bugün' kutucuğuna basınca modal açılır")
print("  - Üstte toplam kâr/zarar özeti")
print("  - Altta: işlem sayısı / kârlı / zararlı / win rate")
print("  - Her satırda: # / Sembol / Yön / Giriş / Çıkış / PNL% / Net+Toplam / Sebep / Saat")
print("  - Kümülatif kâr (Σ) gösterilir")
print("  - Bugün kapanan işlemler en yeni en üstte")
print("  - ESC ile kapatılır")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {JS_BAK} {JS_SRC}")
print(f"  copy /Y {HTML_BAK} {HTML_SRC}")