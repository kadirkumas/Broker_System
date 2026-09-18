import shutil
import os

HTML_SRC = 'frontend/index.html'
HTML_BAK = 'frontend/index.html.bak_calendar'
CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_calendar'
JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_calendar'

for src in [HTML_SRC, CSS_SRC, JS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_calendar')
    print(f"[1/4] Yedek: {src}.bak_calendar")

changes = 0

# ============================================================
# 1. HTML: Takvim modalı + modal-body'ye buton
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

# Mevcut daily-report-modal'ın hemen ardına takvim modalı ekle
old = '''    <div id="indicator-modal" class="modal-overlay">'''

new = '''    <div id="calendar-modal" class="modal-overlay">
        <div class="modal-content" style="width: 900px; max-width: 95vw; height: auto; max-height: 90vh; background: #0b0e14; border: 1px solid #2b3139;">
            <div class="modal-header" style="background: #181a20; border-bottom: 1px solid #2b3139;">
                <h2>📆 Kâr / Zarar Takvimi</h2>
                <div style="display: flex; align-items: center; gap: 12px;">
                    <span id="cal-month-total" style="font-size: 13px; font-weight: bold; color: #848e9c;">0.00 USDT</span>
                    <span class="modal-close" onclick="closeCalendarModal()">✕</span>
                </div>
            </div>

            <div class="calendar-controls">
                <button class="cal-nav-btn" onclick="calPrevMonth()">◀ Önceki Ay</button>
                <div class="cal-month-title" id="cal-month-title">Eylül 2026</div>
                <button class="cal-nav-btn" onclick="calNextMonth()">Sonraki Ay ▶</button>
                <button class="cal-nav-btn cal-today-btn" onclick="calGoToday()">📅 Bugüne Dön</button>
            </div>

            <div class="calendar-body">
                <div class="cal-weekdays">
                    <div>Pzt</div>
                    <div>Sal</div>
                    <div>Çar</div>
                    <div>Per</div>
                    <div>Cum</div>
                    <div>Cmt</div>
                    <div>Paz</div>
                </div>
                <div class="cal-grid" id="cal-grid"></div>
            </div>

            <div class="calendar-footer">
                <div class="cal-legend">
                    <span><span class="cal-legend-dot" style="background:#0ECB81;"></span> Kârlı</span>
                    <span><span class="cal-legend-dot" style="background:#F6465D;"></span> Zararlı</span>
                    <span><span class="cal-legend-dot" style="background:#848e9c;"></span> İşlem Yok</span>
                </div>
                <div class="cal-summary">
                    <span>Toplam İşlem: <b id="cal-sum-trades" style="color: #EAECEF;">0</b></span>
                    <span>Kârlı Gün: <b id="cal-sum-wins" style="color: #0ECB81;">0</b></span>
                    <span>Zararlı Gün: <b id="cal-sum-losses" style="color: #F6465D;">0</b></span>
                </div>
            </div>
        </div>
    </div>

    <div id="indicator-modal" class="modal-overlay">'''

if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[2/4] HTML: takvim modalı eklendi")
else:
    print("[2/4] UYARI: indicator-modal bulunamadi")

# Bugün kutucuğunun yanına "Takvim" butonu ekle
old = '''<span id="daily-pnl-header" onclick="openDailyReportModal()" style="display: inline-block; cursor: pointer; background: rgba(41, 98, 255, 0.1); border: 1px solid #2962ff; padding: 3px 8px; border-radius: 4px; color: #EAECEF; font-weight: bold; font-size: 12px; margin-right: 15px;">
                                Bugün: <span id="daily-total-pnl">0.00$</span> 📅
                            </span>'''

new = '''<span id="daily-pnl-header" onclick="openDailyReportModal()" style="display: inline-block; cursor: pointer; background: rgba(41, 98, 255, 0.1); border: 1px solid #2962ff; padding: 3px 8px; border-radius: 4px; color: #EAECEF; font-weight: bold; font-size: 12px; margin-right: 8px;">
                                Bugün: <span id="daily-total-pnl">0.00$</span> 📅
                            </span>
                            <span id="calendar-btn" onclick="openCalendarModal()" title="Aylık Takvim" style="display: inline-block; cursor: pointer; background: rgba(252, 213, 53, 0.1); border: 1px solid #fcd535; padding: 3px 8px; border-radius: 4px; color: #fcd535; font-weight: bold; font-size: 12px; margin-right: 15px;">
                                📆 Takvim
                            </span>'''

if old in html:
    html = html.replace(old, new, 1)
    changes += 1
    print("[2/4] HTML: Takvim butonu eklendi")
else:
    print("[2/4] UYARI: daily-pnl-header pattern bulunamadi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. CSS: Takvim stilleri
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

new_css = '''

/* ============================================================
   KÂR / ZARAR TAKVİMİ
   ============================================================ */
.calendar-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 20px;
    border-bottom: 1px solid #2b3139;
    background: #131722;
    gap: 10px;
}

.cal-nav-btn {
    background: #1e222d;
    border: 1px solid #2a2e39;
    color: #d1d4dc;
    padding: 6px 14px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
    white-space: nowrap;
}

.cal-nav-btn:hover {
    background: #2a2e39;
    color: #fff;
    border-color: #363c4e;
}

.cal-today-btn {
    background: rgba(41, 98, 255, 0.15);
    border-color: rgba(41, 98, 255, 0.4);
    color: #79a0ff;
    margin-left: auto;
}

.cal-today-btn:hover {
    background: rgba(41, 98, 255, 0.3);
    color: #fff;
}

.cal-month-title {
    font-size: 16px;
    font-weight: 700;
    color: #EAECEF;
    flex: 1;
    text-align: center;
    letter-spacing: 0.5px;
}

.calendar-body {
    padding: 15px 20px;
    overflow-y: auto;
    max-height: 55vh;
}

.cal-weekdays {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 6px;
    margin-bottom: 8px;
}

.cal-weekdays > div {
    text-align: center;
    font-size: 11px;
    font-weight: 700;
    color: #848e9c;
    padding: 6px 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 6px;
}

.cal-day {
    background: #131722;
    border: 1px solid #2a2e39;
    border-radius: 6px;
    padding: 8px 6px;
    min-height: 72px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: all 0.15s;
    position: relative;
}

.cal-day.cal-empty {
    background: transparent;
    border-color: transparent;
    pointer-events: none;
}

.cal-day.cal-day-profit {
    background: rgba(14, 203, 129, 0.12);
    border-color: rgba(14, 203, 129, 0.4);
}

.cal-day.cal-day-loss {
    background: rgba(246, 70, 93, 0.12);
    border-color: rgba(246, 70, 93, 0.4);
}

.cal-day.cal-day-today {
    border: 2px solid #2962ff;
    box-shadow: 0 0 12px rgba(41, 98, 255, 0.4);
}

.cal-day.cal-day-clickable {
    cursor: pointer;
}

.cal-day.cal-day-clickable:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}

.cal-day-num {
    font-size: 12px;
    font-weight: 700;
    color: #d1d4dc;
}

.cal-day-pnl {
    font-size: 12px;
    font-weight: 700;
    text-align: right;
    font-variant-numeric: tabular-nums;
}

.cal-day-pnl.profit { color: #0ECB81; }
.cal-day-pnl.loss { color: #F6465D; }
.cal-day-pnl.empty { color: #5d6471; font-weight: 400; }

.cal-day-count {
    font-size: 9px;
    color: #848e9c;
    text-align: right;
}

.calendar-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 20px;
    border-top: 1px solid #2b3139;
    background: #181a20;
    gap: 20px;
    flex-wrap: wrap;
}

.cal-legend {
    display: flex;
    gap: 16px;
    font-size: 11px;
    color: #848e9c;
}

.cal-legend > span {
    display: flex;
    align-items: center;
    gap: 5px;
}

.cal-legend-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 2px;
}

.cal-summary {
    display: flex;
    gap: 18px;
    font-size: 11px;
    color: #848e9c;
}

.cal-summary b {
    font-size: 12px;
    font-weight: 700;
}
'''

if 'KÂR / ZARAR TAKVİMİ' not in css:
    css = css.rstrip() + new_css
    changes += 1
    print("[3/4] CSS: takvim stilleri eklendi")
else:
    print("[3/4] CSS: zaten var")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

# ============================================================
# 3. JS: Takvim fonksiyonları
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

new_js = '''

// =============================================================
// KÂR / ZARAR TAKVİMİ (AY GÖRÜNÜMÜ)
// =============================================================
window.calData = {};           // {YYYY-MM-DD: {trades, net_pnl}}
window.calCurrentMonth = null; // Date objesi

window.openCalendarModal = async function() {
    const modal = document.getElementById('calendar-modal');
    if (!modal) return;
    
    if (!window.calCurrentMonth) {
        window.calCurrentMonth = new Date();
    }
    
    modal.classList.add('active');
    await window.loadCalendarData();
};

window.closeCalendarModal = function() {
    const modal = document.getElementById('calendar-modal');
    if (modal) modal.classList.remove('active');
};

window.loadCalendarData = async function() {
    try {
        const res = await fetch('/api/stats/daily?days=365');
        const data = await res.json();
        
        window.calData = {};
        if (Array.isArray(data)) {
            data.forEach(function(row) {
                window.calData[row.date] = {
                    trades: row.trades || 0,
                    net_pnl: row.net_pnl || 0,
                    wins: row.wins || 0,
                    losses: row.losses || 0,
                };
            });
        }
        window.renderCalendar();
    } catch(e) {
        console.error('[CAL] Veri yüklenemedi:', e);
    }
};

window.renderCalendar = function() {
    if (!window.calCurrentMonth) window.calCurrentMonth = new Date();
    
    const year = window.calCurrentMonth.getFullYear();
    const month = window.calCurrentMonth.getMonth();
    
    // Ay başlığı
    const months_tr = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];
    const titleEl = document.getElementById('cal-month-title');
    if (titleEl) titleEl.innerText = months_tr[month] + ' ' + year;
    
    // Ay başı ve son günü
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const totalDays = lastDay.getDate();
    
    // Pazartesi başlangıç: JS getDay() 0=Pazar, 1=Pazartesi...
    // Pazartesi=0 olacak şekilde offset
    let startOffset = firstDay.getDay() - 1;
    if (startOffset < 0) startOffset = 6; // Pazar -> 6
    
    // Bugün
    const now = new Date();
    const trNow = new Date(now.getTime() + (3 * 60 * 60 * 1000));
    const todayKey = trNow.getUTCFullYear() + '-' +
                     String(trNow.getUTCMonth() + 1).padStart(2, '0') + '-' +
                     String(trNow.getUTCDate()).padStart(2, '0');
    
    // Grid oluştur
    const grid = document.getElementById('cal-grid');
    if (!grid) return;
    grid.innerHTML = '';
    
    // Boş günler
    for (let i = 0; i < startOffset; i++) {
        const empty = document.createElement('div');
        empty.className = 'cal-day cal-empty';
        grid.appendChild(empty);
    }
    
    // Ay içi günler
    let monthTotal = 0;
    let monthTrades = 0;
    let monthWins = 0;
    let monthLosses = 0;
    
    for (let d = 1; d <= totalDays; d++) {
        const dateKey = year + '-' + String(month + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
        const dayData = window.calData[dateKey] || null;
        
        const dayEl = document.createElement('div');
        dayEl.className = 'cal-day';
        
        // Bugün mü?
        if (dateKey === todayKey) {
            dayEl.classList.add('cal-day-today');
        }
        
        // Veri varsa kâr/zarar class'ı
        let pnlClass = 'empty';
        let pnlText = '—';
        let countText = '';
        
        if (dayData && dayData.trades > 0) {
            const pnl = dayData.net_pnl;
            if (pnl >= 0) {
                dayEl.classList.add('cal-day-profit');
                pnlClass = 'profit';
            } else {
                dayEl.classList.add('cal-day-loss');
                pnlClass = 'loss';
            }
            const sign = pnl >= 0 ? '+' : '';
            pnlText = sign + pnl.toFixed(2);
            countText = dayData.trades + ' işlem';
            dayEl.classList.add('cal-day-clickable');
            
            monthTotal += pnl;
            monthTrades += dayData.trades;
            if (pnl >= 0) monthWins++;
            else monthLosses++;
            
            // Tıklama: o günün işlemlerini göster
            dayEl.onclick = function() {
                window.showDayDetails(dateKey, dayData);
            };
        }
        
        dayEl.innerHTML =
            '<div class="cal-day-num">' + d + '</div>' +
            '<div class="cal-day-pnl ' + pnlClass + '">' + pnlText + '</div>' +
            '<div class="cal-day-count">' + countText + '</div>';
        
        grid.appendChild(dayEl);
    }
    
    // Ay toplamı
    const totalEl = document.getElementById('cal-month-total');
    if (totalEl) {
        const sign = monthTotal >= 0 ? '+' : '';
        totalEl.innerText = sign + monthTotal.toFixed(2) + ' USDT';
        totalEl.style.color = monthTotal >= 0 ? '#0ECB81' : '#F6465D';
    }
    
    // Footer özet
    const tradesEl = document.getElementById('cal-sum-trades');
    const winsEl = document.getElementById('cal-sum-wins');
    const lossesEl = document.getElementById('cal-sum-losses');
    if (tradesEl) tradesEl.innerText = monthTrades;
    if (winsEl) winsEl.innerText = monthWins;
    if (lossesEl) lossesEl.innerText = monthLosses;
};

window.calPrevMonth = function() {
    if (!window.calCurrentMonth) window.calCurrentMonth = new Date();
    window.calCurrentMonth.setMonth(window.calCurrentMonth.getMonth() - 1);
    window.renderCalendar();
};

window.calNextMonth = function() {
    if (!window.calCurrentMonth) window.calCurrentMonth = new Date();
    window.calCurrentMonth.setMonth(window.calCurrentMonth.getMonth() + 1);
    window.renderCalendar();
};

window.calGoToday = function() {
    window.calCurrentMonth = new Date();
    window.renderCalendar();
};

// Gün detaylarını göster (basit toast + detay modalı)
window.showDayDetails = async function(dateKey, dayData) {
    // Basit yaklaşım: detaylı işlemleri fetch et ve küçük bir modal göster
    try {
        const res = await fetch('/api/trade/history?limit=1000');
        let trades = await res.json();
        if (!Array.isArray(trades)) trades = [];
        
        // O günün işlemleri (TR saati ile)
        const [y, m, d] = dateKey.split('-').map(Number);
        const dayTrades = trades.filter(function(t) {
            const exitDate = new Date(t.exit_time * 1000);
            const trDate = new Date(exitDate.getTime() + (3 * 60 * 60 * 1000));
            return trDate.getUTCFullYear() === y &&
                   (trDate.getUTCMonth() + 1) === m &&
                   trDate.getUTCDate() === d;
        });
        
        // Toast mesajı
        const sign = dayData.net_pnl >= 0 ? '+' : '';
        window.showToast(
            dateKey + ' | ' + dayData.trades + ' işlem | ' + sign + dayData.net_pnl.toFixed(2) + ' USDT',
            dayData.net_pnl >= 0 ? 'success' : 'error',
            4000
        );
        
        // İlk 3 işlemi konsola yaz (debug için)
        console.log('[CAL] ' + dateKey + ' işlemleri:', dayTrades.slice(0, 5));
        
    } catch(e) {
        console.error('[CAL] Gün detayı hatası:', e);
    }
};

// ESC ile kapatma
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const m = document.getElementById('calendar-modal');
        if (m && m.classList.contains('active')) {
            m.classList.remove('active');
        }
    }
});
'''

if 'KÂR / ZARAR TAKVİMİ (AY GÖRÜNÜMÜ)' not in js:
    js = js.rstrip() + new_js
    changes += 1
    print("[4/4] JS: takvim fonksiyonları eklendi")
else:
    print("[4/4] JS: zaten var")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - Alt panelde 'Bugün' kutucuğunun yanında '📆 Takvim' butonu")
print("  - Tıklayınca ay görünümü açılır")
print("  - Her gün renkli kutu:")
print("    YESIL = kârlı gün")
print("    KIRMIZI = zararlı gün")
print("    GRİ = işlem yok")
print("    MAVİ ÇERÇEVE = bugün")
print("  - Üstte ay toplamı")
print("  - Altta: toplam işlem / kârlı gün / zararlı gün")
print("  - Ay gezintisi: ◀ Önceki / Sonraki ▶ / Bugüne Dön")
print("  - Gün tıklanınca toast mesajı")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
for src in [HTML_SRC, CSS_SRC, JS_SRC]:
    print(f"  copy /Y {src}.bak_calendar {src}")