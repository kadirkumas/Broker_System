// ============================================================
// BROKER MOBILE - Mobil Dashboard JS
// ============================================================

let _activeTrades = [];
let _selectedSymbol = null;

// ---------- YARDIMCI ----------
const fmtNum = (n, d = 2) => {
    n = parseFloat(n) || 0;
    return n.toLocaleString('tr-TR', { minimumFractionDigits: d, maximumFractionDigits: d });
};

const fmtPrice = (p) => {
    p = parseFloat(p) || 0;
    if (p >= 1000) return p.toFixed(2);
    if (p >= 1) return p.toFixed(4);
    return p.toFixed(6);
};

// ---------- VERİ ÇEKME ----------
async function fetchWallet() {
    try {
        const r = await fetch('/api/wallet');
        const d = await r.json();
        const bal = parseFloat(d.balance) || 0;
        document.getElementById('wallet-balance').textContent = '$' + fmtNum(bal);
        return bal;
    } catch(e) {
        document.getElementById('wallet-balance').textContent = 'HATA';
        return 0;
    }
}

async function fetchDaily() {
    try {
        const r = await fetch('/api/stats/daily?days=1');
        const d = await r.json();
        const today = d.today || d[0] || {};
        const pnl = parseFloat(today.net_pnl || today.pnl || today.total_pnl || 0);
        const el = document.getElementById('daily-pnl');
        el.textContent = (pnl >= 0 ? '+' : '') + fmtNum(pnl) + ' $';
        el.classList.remove('green', 'red');
        el.classList.add(pnl >= 0 ? 'green' : 'red');

        document.getElementById('daily-count').textContent = today.trades || today.count || 0;
        document.getElementById('daily-wins').textContent = today.wins || 0;
        document.getElementById('daily-losses').textContent = today.losses || 0;
    } catch(e) {
        console.warn('daily hata', e);
    }
}

async function fetchTrades() {
    try {
        const r = await fetch('/api/trade/active-with-pnl');
        const d = await r.json();
        _activeTrades = Array.isArray(d) ? d : [];
        renderPositions(_activeTrades);
        renderRisk(_activeTrades);
    } catch(e) {
        document.getElementById('pos-list').innerHTML = '<div class="empty">Bağlantı hatası</div>';
    }
}

async function fetchClosed() {
    try {
        const r = await fetch('/api/trade/history?limit=15');
        const d = await r.json();
        renderClosed(Array.isArray(d) ? d : []);
    } catch(e) {
        const el = document.getElementById('closed-list');
        if (el) el.innerHTML = '<div class="empty">Bağlantı hatası</div>';
    }
}

async function fetchSignals() {
    try {
        const r = await fetch('/api/engine/recent-signals?limit=10');
        const d = await r.json();
        renderSignals(Array.isArray(d) ? d : []);
    } catch(e) {
        document.getElementById('sig-list').innerHTML = '<div class="empty">Bağlantı hatası</div>';
    }
}

async function fetchBotStatus() {
    try {
        const r = await fetch('/api/engine/status');
        const d = await r.json();
        const running = d.running && d.config && d.config.active;
        const dot = document.getElementById('bot-dot');
        const txt = document.getElementById('bot-text');
        const btn = document.getElementById('bot-toggle');

        if (running) {
            dot.className = 'status-dot active';
            txt.textContent = 'Bot AKTİF - ' + (d.symbols_count || 0) + ' sembol';
            btn.textContent = 'DURDUR';
            btn.className = 'bot-toggle active';
        } else {
            dot.className = 'status-dot passive';
            txt.textContent = 'Bot KAPALI';
            btn.textContent = 'BAŞLAT';
            btn.className = 'bot-toggle passive';
        }
    } catch(e) {
        document.getElementById('bot-text').textContent = 'Bağlantı yok';
    }
}

// ---------- RENDER: RİSK ----------
function renderRisk(trades) {
    const balance = parseFloat(document.getElementById('wallet-balance').textContent.replace('$','').replace(/[.\s]/g,'').replace(',','.')) || 0;
    let used = 0, totalPos = 0, longs = 0, shorts = 0, levSum = 0, totalPnl = 0;
    trades.forEach(t => {
        const vol = parseFloat(t.total_vol) || 0;
        const lev = parseInt(t.leverage) || 1;
        used += vol / lev;
        totalPos += vol;
        levSum += lev;
        totalPnl += parseFloat(t.unrealized_pnl) || 0;
        if (t.trade_type === 'BUY') longs++;
        else if (t.trade_type === 'SELL') shorts++;
    });
    const ratio = balance > 0 ? (used / balance) * 100 : 0;
    const free = balance - used;
    // Likit mesafe = serbest marj - acik zarar (sadece zarar varsa)
    const liqDistance = totalPnl < 0 ? (free - Math.abs(totalPnl)) : free;

    let level = 'safe';
    if (ratio >= 80) level = 'critical';
    else if (ratio >= 60) level = 'high';
    else if (ratio >= 40) level = 'warning';

    const card = document.getElementById('risk-card');
    card.classList.remove('safe','warning','high','critical');
    card.classList.add(level);

    const badge = document.getElementById('risk-badge');
    badge.classList.remove('safe','warning','high','critical');
    badge.classList.add(level);
    const levelText = { safe: 'GÜVENLİ', warning: 'ORTA', high: 'YÜKSEK', critical: 'KRİTİK' };
    badge.textContent = levelText[level] + ' ' + ratio.toFixed(0) + '%';

    document.getElementById('risk-bar').style.width = Math.min(ratio, 100) + '%';
    document.getElementById('risk-used').textContent = fmtNum(used) + ' $';
    document.getElementById('risk-free').textContent = fmtNum(free) + ' $';
    document.getElementById('risk-liq').textContent = fmtNum(liqDistance) + ' $';

    document.getElementById('pos-count').textContent = trades.length;
}

// ---------- RENDER: POZİSYONLAR ----------
function renderPositions(trades) {
    const list = document.getElementById('pos-list');
    if (!trades || trades.length === 0) {
        list.innerHTML = '<div class="empty">Açık pozisyon yok</div>';
        return;
    }

    // ⚡ [SORT-BY-PNL] En karli ustte, en zararli altta
    trades = trades.slice().sort((a, b) => {
        const pa = parseFloat(a.unrealized_pnl) || 0;
        const pb = parseFloat(b.unrealized_pnl) || 0;
        return pb - pa;  // buyukten kucuge
    });
    list.innerHTML = trades.map(t => {
        const sym = (t.symbol || '').replace('.P','');
        const isLong = t.trade_type === 'BUY';
        const dir = isLong ? 'LONG' : 'SHORT';
        const dirClass = isLong ? 'long' : 'short';
        const pnl = parseFloat(t.unrealized_pnl || t.pnl || 0);
        const pnlPct = parseFloat(t.unrealized_pnl_pct || t.pnl_pct || 0);
        const dca = t.dca_count || 0;
        const lev = t.leverage || 1;
        const vol = parseFloat(t.total_vol) || 0;

        const pnlClass = pnl >= 0 ? 'green' : 'red';
        const pnlTxt = (pnl >= 0 ? '+' : '') + fmtNum(pnl) + ' $';

        return `
            <div class="list-item ${dirClass}" onclick="openPosModal('${t.symbol}')">
                <div class="li-left">
                    <div class="li-sym">${sym}</div>
                    <div class="li-meta">
                        <span>${dir}</span>
                        <span>${lev}x</span>
                        <span>${fmtNum(vol)} $</span>
                        ${dca > 0 ? `<span class="dca-badge">D:${dca}</span>` : ''}
                    </div>
                </div>
                <div class="li-right">
                    <div class="li-pnl ${pnlClass}">${pnlTxt}</div>
                    <div class="li-sub">${pnlPct >= 0 ? '+' : ''}${fmtNum(pnlPct, 2)}%</div>
                </div>
            </div>
        `;
    }).join('');
}

// ---------- RENDER: KAPANAN ISLEMLER ----------
function renderClosed(trades) {
    const list = document.getElementById('closed-list');
    const countEl = document.getElementById('closed-count');
    if (!list) return;

    // Sayac
    if (countEl) countEl.textContent = trades.length;

    if (!trades || trades.length === 0) {
        list.innerHTML = '<div class="empty">Kapanan işlem yok</div>';
        return;
    }

    // exit_time DESC (yeni -> eski)
    trades = trades.slice().sort((a, b) => (b.exit_time || 0) - (a.exit_time || 0));

    list.innerHTML = trades.map(t => {
        const sym = (t.symbol || '').replace('.P', '');
        const isLong = t.trade_type === 'BUY';
        const dir = isLong ? 'LONG' : 'SHORT';
        const dirClass = isLong ? 'long' : 'short';
        const pnl = parseFloat(t.pnl_amount) || 0;
        const pnlPct = parseFloat(t.pnl_pct) || 0;
        const isProfit = pnl >= 0;

        const pnlClass = isProfit ? 'green' : 'red';
        const pnlTxt = (pnl >= 0 ? '+' : '') + fmtNum(pnl, 2) + ' $';
        const pctTxt = (pnlPct >= 0 ? '+' : '') + fmtNum(pnlPct, 2) + '%';

        // Sebep kısalt
        let reason = (t.close_reason || '').toUpperCase();
        let shortReason = '—';
        if (reason.includes('AI-TTP') || reason.includes('AI TTP') || reason.includes('TRAILING')) shortReason = 'TTP';
        else if (reason.includes('PARTIAL')) shortReason = 'PT';
        else if (reason.includes('STOP')) shortReason = 'SL';
        else if (reason.includes('TAKE')) shortReason = 'TP';
        else if (reason.includes('DELIST')) shortReason = 'DEL';

        const durationStr = _fmtDuration(t.entry_time, t.exit_time);

        return `
            <div class="list-item ${dirClass}" onclick="openClosedModal('${t.id}')">
                <div class="li-left">
                    <div class="li-sym">${sym}</div>
                    <div class="li-meta">
                        <span>${dir}</span>
                        <span>${shortReason}</span>
                        <span>${durationStr}</span>
                    </div>
                </div>
                <div class="li-right">
                    <div class="li-pnl ${pnlClass}">${pnlTxt}</div>
                    <div class="li-sub">${pctTxt}</div>
                </div>
            </div>
        `;
    }).join('');
}

// Sure formatlama (g/s/dk)
function _fmtDuration(entryTs, exitTs) {
    if (!entryTs || !exitTs) return '—';
    const sec = Math.max(0, exitTs - entryTs);
    const d = Math.floor(sec / 86400);
    const h = Math.floor((sec % 86400) / 3600);
    const m = Math.floor((sec % 3600) / 60);
    if (d > 0) return d + 'g ' + h + 's';
    if (h > 0) return h + 's ' + m + 'dk';
    return m + 'dk';
}

// ---------- RENDER: SİNYALLER ----------
function renderSignals(signals) {
    const list = document.getElementById('sig-list');
    if (!signals || signals.length === 0) {
        list.innerHTML = '<div class="empty">Sinyal yok</div>';
        return;
    }
    list.innerHTML = signals.slice(0, 10).map(s => {
        const sym = (s.symbol || '').replace('.P','');
        const isLong = s.signal === 'LONG';
        const isClose = s.signal === 'CLOSE' || s.close_reason;
        const cls = isClose ? 'sig-close' : (isLong ? 'sig-long' : 'sig-short');
        const icon = isClose ? '🔗' : (isLong ? '▲' : '▼');
        const label = isClose ? (s.close_reason || 'KAPANIŞ') : s.signal;
        const reason = s.reason ? s.reason.substring(0, 30) : '';
        return `
            <div class="list-item ${cls}">
                <div class="li-left">
                    <div class="li-sym">${icon} ${sym}</div>
                    <div class="li-meta">
                        <span>${label}</span>
                        ${reason ? `<span>${reason}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ---------- POZİSYON MODAL ----------
window.openPosModal = function(symbol) {
    const t = _activeTrades.find(x => x.symbol === symbol);
    if (!t) return;
    _selectedSymbol = symbol;

    const sym = symbol.replace('.P','');
    const isLong = t.trade_type === 'BUY';
    const pnl = parseFloat(t.unrealized_pnl || 0);
    const pnlPct = parseFloat(t.unrealized_pnl_pct || 0);
    const pnlClass = pnl >= 0 ? 'green' : 'red';

    document.getElementById('pos-modal-title').textContent = sym + ' ' + (isLong ? 'LONG' : 'SHORT');

    const details = [
        ['Yön', isLong ? 'LONG ▲' : 'SHORT ▼'],
        ['Kaldıraç', (t.leverage || 1) + 'x'],
        ['Toplam Hacim', fmtNum(t.total_vol) + ' $'],
        ['İlk Fiyat', fmtPrice(t.initial_price)],
        ['Ort. Fiyat', fmtPrice(t.avg_price)],
        ['DCA Sayısı', t.dca_count || 0],
        ['Açık K/Z', `<span class="li-pnl ${pnlClass}">${pnl >= 0 ? '+' : ''}${fmtNum(pnl)} $ (${pnlPct >= 0 ? '+' : ''}${fmtNum(pnlPct, 2)}%)</span>`],
        ['Strateji', t.strategy_name || '-'],
    ];

    document.getElementById('pos-modal-body').innerHTML = details.map(
        ([k, v]) => `<div class="detail-row"><span>${k}</span><span>${v}</span></div>`
    ).join('');

    document.getElementById('pos-modal').style.display = 'flex';
};

window.closePosModal = function() {
    document.getElementById('pos-modal').style.display = 'none';
    _selectedSymbol = null;
};

window.closePosition = async function() {
    if (!_selectedSymbol) return;
    if (!confirm(_selectedSymbol + ' pozisyonu kapatılsın mı?')) return;

    const btn = document.getElementById('btn-close-pos');
    btn.textContent = 'Kapatılıyor...';
    btn.disabled = true;

    try {
        const r = await fetch('/api/trade/close?symbol=' + encodeURIComponent(_selectedSymbol), {
            method: 'POST'
        });
        if (r.ok) {
            closePosModal();
            setTimeout(() => { fetchTrades(); fetchWallet(); fetchDaily(); }, 500);
        } else {
            alert('Hata: ' + r.status);
        }
    } catch(e) {
        alert('Bağlantı hatası');
    } finally {
        btn.textContent = 'Pozisyonu Kapat';
        btn.disabled = false;
    }
};

// ---------- BOT TOGGLE ----------
window.toggleBot = async function() {
    const btn = document.getElementById('bot-toggle');
    btn.disabled = true;

    try {
        // ⚡ 1) Mevcut durumu al
        const statusRes = await fetch('/api/engine/status');
        const status = await statusRes.json();
        const isRunning = status.running && status.config && status.config.active;

        // ⚡ 2) Ters yone cevir
        const targetActive = !isRunning;

        // ⚡ 3) Kapatiliyorsa acik pozisyon var mi kontrol et
        if (!targetActive) {
            const posRes = await fetch('/api/trade/active');
            const positions = await posRes.json();
            const count = Array.isArray(positions) ? positions.length : 0;

            if (count > 0) {
                const preview = positions.slice(0, 5).map(p => '  • ' + p.symbol + ' (' + p.trade_type + ')').join('\n');
                const more = count > 5 ? '\n  ... ve ' + (count - 5) + ' tane daha' : '';
                const msg =
                    'Şu an ' + count + ' açık pozisyon var:\n\n' + preview + more +
                    '\n\nBotu durdurunca:\n' +
                    '  ✓ Yeni sinyal üretilmez\n' +
                    '  ✓ Açık pozisyonlar KAPATILACAK\n' +
                    '  ✓ TP/SL izlemesi durur\n\n' +
                    'Devam edilsin mi?';

                if (!confirm(msg)) {
                    btn.disabled = false;
                    return;
                }
            }
        }

        // ⚡ 4) Doğru parametrelerle istek at
        let url = '/api/engine/toggle?active=' + targetActive;
        if (!targetActive) {
            // Kapatirken pozisyonlari da kapat
            url += '&force=true';

            // ⚡ FORCE close-all: klasik + grid HER SEYI kapat
            try {
                const posRes2 = await fetch('/api/trade/active');
                const pos2 = await posRes2.json();
                if (Array.isArray(pos2) && pos2.length > 0) {
                    const closeRes = await fetch('/api/trade/close-all-force', { method: 'POST' });
                    const closeData = await closeRes.json();
                    console.log('[CLOSE-ALL-FORCE]', closeData);
                }
            } catch(e) {
                console.warn('Pozisyon kapatma hatasi:', e);
            }
        }

        const r = await fetch(url, { method: 'POST' });
        const data = await r.json();

        // ⚡ 5) Backend "warning" dondurse (force olmadan)
        if (data.status === 'warning') {
            if (confirm(data.message + '\n\nZorla kapatılsın mı?')) {
                await fetch('/api/engine/toggle?active=false&force=true', { method: 'POST' });
            } else {
                btn.disabled = false;
                return;
            }
        }

        // ⚡ 6) Durumu yenile
        await fetchBotStatus();

    } catch(e) {
        alert('Bağlantı hatası: ' + e.message);
    } finally {
        btn.disabled = false;
    }
};

// ---------- COLLAPSE ----------
// ⚡ Default olarak collapsed olan listeleri senkronize et
document.querySelectorAll('.collapse-btn').forEach(btn => {
    const target = document.getElementById(btn.dataset.target);

    // Baslangic durumunu butona yansit
    if (target && target.classList.contains('collapsed')) {
        btn.textContent = '▶';
    } else if (target) {
        btn.textContent = '▼';
    }

    btn.addEventListener('click', () => {
        if (target) {
            target.classList.toggle('collapsed');
            btn.textContent = target.classList.contains('collapsed') ? '▶' : '▼';
        }
    });
});

// ---------- GÜNCELLE ----------
async function refreshAll() {
    await Promise.all([
        fetchWallet(),
        fetchTrades(),
        fetchDaily(),
        fetchClosed(),
        fetchSignals(),
        fetchBotStatus(),
    ]);
    document.getElementById('last-update').textContent =
        'Son: ' + new Date().toLocaleTimeString('tr-TR');
}

// ---------- BAŞLAT ----------
document.addEventListener('DOMContentLoaded', () => {
    // Buton event'leri
    document.getElementById('btn-refresh').addEventListener('click', refreshAll);
    document.getElementById('bot-toggle').addEventListener('click', toggleBot);
    document.getElementById('btn-close-pos').addEventListener('click', closePosition);

    // İlk yükleme
    refreshAll();

    // 15 saniyede bir otomatik güncelle (F19: rate limit icin yavaslatildi)
    setInterval(refreshAll, 15000);
});

// ============================================================
// PIN LOCK
// ============================================================
const PIN_STORAGE_KEY = 'brokerMobilePin';
const PIN_REMEMBER_KEY = 'brokerMobilePinRememberUntil';
const PIN_FAIL_KEY = 'brokerMobilePinFails';
const PIN_LOCKED_UNTIL_KEY = 'brokerMobilePinLockedUntil';

let _pinBuffer = '';
let _pinMode = 'enter';      // 'enter' | 'set' | 'confirm'
let _pinTempFirst = '';
let _pinFails = 0;

// --- HASH (SHA-256) ---
// Basit fallback hash (crypto.subtle yoksa)
function simplePinHash(pin) {
    let h = 0;
    const s = 'broker_salt_' + pin;
    for (let i = 0; i < s.length; i++) {
        h = ((h << 5) - h) + s.charCodeAt(i);
        h |= 0;
    }
    return 'sh_' + Math.abs(h).toString(16).padStart(8, '0');
}

async function hashPin(pin) {
    if (typeof crypto !== 'undefined' &&
        crypto.subtle &&
        typeof crypto.subtle.digest === 'function') {
        try {
            const data = new TextEncoder().encode('broker_salt_' + pin);
            const hash = await crypto.subtle.digest('SHA-256', data);
            return Array.from(new Uint8Array(hash))
                .map(b => b.toString(16).padStart(2,'0'))
                .join('');
        } catch(e) {
            console.warn('[PIN] crypto.subtle hata, fallback:', e);
        }
    }
    console.log('[PIN] crypto.subtle yok, basit hash kullaniliyor');
    return simplePinHash(pin);
}

// --- STORAGE ---
function getPinHash() { return localStorage.getItem(PIN_STORAGE_KEY); }
function setPinHash(h) { localStorage.setItem(PIN_STORAGE_KEY, h); }
function clearPin() {
    localStorage.removeItem(PIN_STORAGE_KEY);
    localStorage.removeItem(PIN_REMEMBER_KEY);
    localStorage.removeItem(PIN_FAIL_KEY);
    localStorage.removeItem(PIN_LOCKED_UNTIL_KEY);
}

// --- UI ---
function showPinOverlay(mode) {
    _pinMode = mode || _pinMode;
    _pinBuffer = '';
    _pinTempFirst = '';
    updatePinDots();

    const overlay = document.getElementById('pin-overlay');
    const title = document.getElementById('pin-title');
    const sub = document.getElementById('pin-subtitle');
    const err = document.getElementById('pin-error');
    const forgot = document.getElementById('pin-forgot');

    err.textContent = '';
    document.getElementById('pin-dots').classList.remove('error', 'pin-success');

    if (_pinMode === 'set') {
        title.textContent = 'PIN Belirle';
        sub.textContent = '4 haneli bir PIN olusturun';
        forgot.style.display = 'none';
    } else if (_pinMode === 'confirm') {
        title.textContent = 'PIN Onayla';
        sub.textContent = 'PIN tekrar girin';
        forgot.style.display = 'none';
    } else {
        title.textContent = 'PIN Girin';
        sub.textContent = 'Mobil dashboard kilidi';
        forgot.style.display = '';
    }

    overlay.style.display = 'flex';
}

function hidePinOverlay() {
    const overlay = document.getElementById('pin-overlay');
    overlay.style.display = 'none';
    _pinBuffer = '';
    _pinTempFirst = '';
}

function updatePinDots() {
    const dots = document.querySelectorAll('#pin-dots .pin-dot');
    dots.forEach((d, i) => {
        d.classList.toggle('filled', i < _pinBuffer.length);
    });
}

function pinError(msg) {
    const err = document.getElementById('pin-error');
    const dots = document.getElementById('pin-dots');
    err.textContent = msg;
    dots.classList.add('error');
    setTimeout(() => {
        dots.classList.remove('error');
        _pinBuffer = '';
        updatePinDots();
    }, 500);
}

function pinSuccess() {
    const dots = document.getElementById('pin-dots');
    dots.classList.add('pin-success');
    setTimeout(() => hidePinOverlay(), 400);
}

// --- INPUT ---
function pinInput(digit) {
    if (_pinBuffer.length >= 4) return;
    _pinBuffer += digit;
    updatePinDots();
    if (_pinBuffer.length === 4) {
        setTimeout(handlePinComplete, 200);
    }
}

function pinBackspace() {
    _pinBuffer = _pinBuffer.slice(0, -1);
    updatePinDots();
}

// --- AKISLAR ---
async function handlePinComplete() {
    const pin = _pinBuffer;

    // 1. PIN BELIRLEME
    if (_pinMode === 'set') {
        _pinTempFirst = pin;
        _pinMode = 'confirm';
        _pinBuffer = '';
        updatePinDots();
        document.getElementById('pin-title').textContent = 'PIN Onayla';
        document.getElementById('pin-subtitle').textContent = 'PIN tekrar girin';
        return;
    }

    // 2. PIN ONAY
    if (_pinMode === 'confirm') {
        if (pin !== _pinTempFirst) {
            pinError('PIN eslesmedi, tekrar deneyin');
            _pinMode = 'set';
            _pinTempFirst = '';
            setTimeout(() => {
                document.getElementById('pin-title').textContent = 'PIN Belirle';
                document.getElementById('pin-subtitle').textContent = '4 haneli bir PIN olusturun';
            }, 600);
            return;
        }
        const h = await hashPin(pin);
        setPinHash(h);
        localStorage.removeItem(PIN_REMEMBER_KEY);
        pinSuccess();
        window.showToast && window.showToast('PIN aktif', 'success');
        return;
    }

    // 3. PIN GIRIS
    const stored = getPinHash();
    if (!stored) {
        // Guvenlik: PIN yoksa set'e don
        _pinMode = 'set';
        showPinOverlay('set');
        return;
    }

    const h = await hashPin(pin);
    if (h === stored) {
        _pinFails = 0;
        localStorage.removeItem(PIN_FAIL_KEY);
        // 7 gun hatirla
        const rememberUntil = Date.now() + 7 * 24 * 60 * 60 * 1000;
        localStorage.setItem(PIN_REMEMBER_KEY, String(rememberUntil));
        pinSuccess();
    } else {
        _pinFails++;
        localStorage.setItem(PIN_FAIL_KEY, String(_pinFails));

        if (_pinFails >= 5) {
            const lockedUntil = Date.now() + 60 * 1000;
            localStorage.setItem(PIN_LOCKED_UNTIL_KEY, String(lockedUntil));
            pinError('5 yanlis giris! 1 dakika bekleyin');
            setTimeout(checkPinLocked, 1000);
            return;
        }
        pinError('Yanlis PIN (' + _pinFails + '/5)');
    }
}

// --- KILITLI MI KONTROL ---
function checkPinLocked() {
    const lockedUntil = parseInt(localStorage.getItem(PIN_LOCKED_UNTIL_KEY) || '0');
    if (Date.now() < lockedUntil) {
        const kalan = Math.ceil((lockedUntil - Date.now()) / 1000);
        const err = document.getElementById('pin-error');
        err.textContent = 'Kilitli: ' + kalan + ' sn';
        setTimeout(checkPinLocked, 1000);
        return true;
    }
    return false;
}

// --- BASLANGIC KONTROL ---
async function initPin() {
    // Kilitliyse bekleme baslat
    if (checkPinLocked()) {
        showPinOverlay('enter');
        return;
    }

    const stored = getPinHash();
    if (!stored) {
        // Ilk kullanim -> PIN belirle
        showPinOverlay('set');
        return;
    }

    // Hatirla suresi dolmus mu?
    const rememberUntil = parseInt(localStorage.getItem(PIN_REMEMBER_KEY) || '0');
    if (Date.now() < rememberUntil) {
        // Hatirla aktif -> gec
        hidePinOverlay();
        return;
    }

    // PIN gir
    showPinOverlay('enter');
}

// --- EVENT BINDINGS ---
document.addEventListener('DOMContentLoaded', () => {
    // Rakam tuslari
    document.querySelectorAll('.pin-btn[data-key]').forEach(btn => {
        btn.addEventListener('click', () => pinInput(btn.dataset.key));
    });

    // Silme
    document.getElementById('pin-back').addEventListener('click', pinBackspace);

    // Klavye destegi (masaustu test icin)
    document.addEventListener('keydown', (e) => {
        if (document.getElementById('pin-overlay').style.display !== 'flex') return;
        if (e.key >= '0' && e.key <= '9') pinInput(e.key);
        else if (e.key === 'Backspace') pinBackspace();
    });

    // PIN sifirla
    document.getElementById('pin-forgot').addEventListener('click', (e) => {
        e.preventDefault();
        if (!confirm('PIN sifirlansin mi? Sonraki acilista yeni PIN belirleyeceksiniz.')) return;
        clearPin();
        _pinMode = 'set';
        _pinBuffer = '';
        _pinTempFirst = '';
        showPinOverlay('set');
    });

    // Baslangic
    initPin();
});

// Global (test icin)
window.resetMobilePin = function() {
    clearPin();
    console.log('[PIN] Sifirlandi - sayfayi yenile');
};



/* MO-MANUAL-ORDER v1 */
// =============================================================
// Manuel Emir - Mobile
// =============================================================
(function() {
    'use strict';

    var _moState = {
        side: 'BUY',
        order_mode: 'market'
    };

    window.showMobileToast = function(message, type) {
        type = type || 'info';
        var container = document.getElementById('mobile-toast-container');
        if (!container) return;

        var toast = document.createElement('div');
        toast.className = 'mobile-toast ' + type;
        toast.textContent = message;
        container.appendChild(toast);

        requestAnimationFrame(function() {
            toast.classList.add('show');
        });

        setTimeout(function() {
            toast.classList.remove('show');
            setTimeout(function() { toast.remove(); }, 300);
        }, 4000);
    };

    // ⚡ Sembol listesi cache
    window._moSymbolsCache = null;
    window._moFilteredSymbols = [];
    window._moSelectedSymbol = '';

    window._loadManualSymbols = async function() {
        var input = document.getElementById('mo-symbol');
        if (!input) return;

        // Cache kontrolu (5 dk)
        var now = Date.now();
        if (window._moSymbolsCache && (now - window._moSymbolsCache.ts) < 300000) {
            window._renderSymbolList(window._moSymbolsCache.symbols);
            return;
        }

        try {
            // ⚡ Bot'un taranan TUM sembolleri
            var res = await fetch('/api/symbols/list');
            var data = await res.json();
            var symbols = (data && data.symbols) ? data.symbols : [];

            // Bos ise engine/status fallback
            if (!symbols || symbols.length === 0) {
                try {
                    var res2 = await fetch('/api/engine/status');
                    var st = await res2.json();
                    symbols = (st && st.symbols) ? st.symbols : [];
                } catch(e2) {}
            }

            // Hala bos ise hardcoded
            if (!symbols || symbols.length === 0) {
                symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
                           'DOGEUSDT', 'ADAUSDT', 'AVAXUSDT', 'LINKUSDT', 'MATICUSDT'];
            }

            symbols = symbols.filter(function(s) {
                return s && typeof s === 'string' && s.endsWith('USDT');
            });
            symbols = Array.from(new Set(symbols)).sort();

            window._moSymbolsCache = { ts: now, symbols: symbols };
            window._renderSymbolList(symbols);

            console.log('[MO-SEARCH] ' + symbols.length + ' sembol yuklendi');
        } catch(e) {
            console.error('[MO-SEARCH] Hata:', e);
            document.getElementById('mo-symbol-list').innerHTML =
                '<div class="mo-symbol-empty">Yukleme hatasi</div>';
        }
    };

    // ⚡ Filter + render
    window._filterSymbols = function(query) {
        var all = (window._moSymbolsCache && window._moSymbolsCache.symbols) || [];
        var q = String(query || '').trim().toUpperCase();

        var filtered = all;
        if (q.length > 0) {
            filtered = all.filter(function(s) {
                return s.indexOf(q) >= 0;
            });
        }

        // Max 30 goster
        filtered = filtered.slice(0, 30);
        window._moFilteredSymbols = filtered;
        return filtered;
    };

    window._renderSymbolList = function(symbols) {
        var list = document.getElementById('mo-symbol-list');
        if (!list) return;

        var q = (document.getElementById('mo-symbol') || {}).value || '';
        q = q.trim().toUpperCase();

        var items = window._filterSymbols(q);

        if (items.length === 0) {
            list.innerHTML = '<div class="mo-symbol-empty">Sonuc yok: ' + q + '</div>';
            list.style.display = 'block';
            return;
        }

        var html = '';
        items.forEach(function(s) {
            // Query'yi vurgula
            var display = s;
            if (q.length > 0 && s.indexOf(q) >= 0) {
                var idx = s.indexOf(q);
                display = s.substring(0, idx) +
                          '<span class="match">' + s.substring(idx, idx + q.length) + '</span>' +
                          s.substring(idx + q.length);
            }
            html += '<div class="mo-symbol-item" data-sym="' + s + '">' + display + '</div>';
        });
        list.innerHTML = html;
        list.style.display = 'block';

        // Tiklama event
        list.querySelectorAll('.mo-symbol-item').forEach(function(el) {
            el.addEventListener('click', function(e) {
                e.stopPropagation();
                window._selectSymbol(el.dataset.sym);
            });
        });
    };

    window._selectSymbol = function(sym) {
        var input = document.getElementById('mo-symbol');
        var hidden = document.getElementById('mo-symbol-value');
        var list = document.getElementById('mo-symbol-list');
        if (input) input.value = sym;
        if (hidden) hidden.value = sym;
        window._moSelectedSymbol = sym;
        if (list) list.style.display = 'none';
        window.showMobileToast(sym + ' secildi', 'info');
    };

    window._getSelectedSymbol = function() {
        // Once hidden value
        var hidden = document.getElementById('mo-symbol-value');
        if (hidden && hidden.value) return hidden.value;

        // Input'a yazilmissa ve eslesme varsa
        var input = document.getElementById('mo-symbol');
        var raw = (input || {}).value || '';
        raw = raw.trim().toUpperCase();
        if (!raw) return '';

        var all = (window._moSymbolsCache && window._moSymbolsCache.symbols) || [];
        // Tam eslesme
        if (all.indexOf(raw) >= 0) return raw;
        // "BTC" -> "BTCUSDT" varsa
        if (all.indexOf(raw + 'USDT') >= 0) return raw + 'USDT';

        return raw;
    };

    // ⚡ Input event (arama)
    document.addEventListener('input', function(e) {
        if (e.target && e.target.id === 'mo-symbol') {
            var list = document.getElementById('mo-symbol-list');
            if (list) {
                // Hidden value sifirla
                var hidden = document.getElementById('mo-symbol-value');
                if (hidden) hidden.value = '';
                window._renderSymbolList();
            }
        }
    });

    // ⚡ Focus event (liste ac)
    document.addEventListener('focusin', function(e) {
        if (e.target && e.target.id === 'mo-symbol') {
            if (!window._moSymbolsCache) {
                window._loadManualSymbols();
            } else {
                window._renderSymbolList();
            }
        }
    });

    // ⚡ Blur event (biraz gecikmeli kapat, tiklama kacmasin)
    document.addEventListener('focusout', function(e) {
        if (e.target && e.target.id === 'mo-symbol') {
            setTimeout(function() {
                var list = document.getElementById('mo-symbol-list');
                if (list) list.style.display = 'none';
            }, 200);
        }
    });



    window.openManualOrderModal = function() {
        var modal = document.getElementById('mo-modal');
        if (!modal) return;

        _moState.side = 'BUY';
        _moState.order_mode = 'market';
        window.setManualSide('BUY');
        window.setManualOrderMode('market');

        var lpEl = document.getElementById('mo-limit-price');
        if (lpEl) { lpEl.disabled = true; lpEl.value = ''; }

        // Sembol input temizle
        var symInput = document.getElementById('mo-symbol');
        var symHidden = document.getElementById('mo-symbol-value');
        if (symInput) symInput.value = '';
        if (symHidden) symHidden.value = '';

        window.updateManualPreview();
        window._loadManualSymbols();

        modal.style.display = 'flex';
    };

    window.closeManualOrderModal = function() {
        var modal = document.getElementById('mo-modal');
        if (modal) modal.style.display = 'none';
    };

    window.setManualSide = function(side) {
        _moState.side = side;
        document.querySelectorAll('#mo-modal .mo-toggle-btn[data-side]').forEach(function(b) {
            if (b.dataset.side === side) b.classList.add('active');
            else b.classList.remove('active');
        });
    };

    window.setManualOrderMode = function(mode) {
        _moState.order_mode = mode;
        document.querySelectorAll('#mo-modal .mo-toggle-btn[data-mode]').forEach(function(b) {
            if (b.dataset.mode === mode) b.classList.add('active');
            else b.classList.remove('active');
        });

        var lpEl = document.getElementById('mo-limit-price');
        if (lpEl) {
            if (mode === 'limit') {
                lpEl.disabled = false;
                lpEl.placeholder = 'Fiyat girin';
            } else {
                lpEl.disabled = true;
                lpEl.value = '';
                lpEl.placeholder = '—';
            }
        }
    };

    window.updateManualPreview = function() {
        var baseOrder = parseFloat((document.getElementById('mo-base-order') || {}).value) || 0;
        var leverage = parseInt((document.getElementById('mo-leverage') || {}).value) || 1;

        var margin = leverage > 0 ? baseOrder / leverage : baseOrder;
        var commission = baseOrder * 0.0004;

        var fmt = function(v) { return v.toFixed(2) + ' USDT'; };

        var elM = document.getElementById('mo-preview-margin');
        var elC = document.getElementById('mo-preview-commission');
        var elS = document.getElementById('mo-preview-size');

        if (elM) elM.textContent = fmt(margin);
        if (elC) elC.textContent = fmt(commission);
        if (elS) elS.textContent = fmt(baseOrder);
    };

    window.submitManualOrder = async function() {
        var btn = document.getElementById('mo-submit-btn');
        if (btn) { btn.disabled = true; btn.textContent = 'GONDERILIYOR...'; }

        try {
            var symbol = window._getSelectedSymbol();
            symbol = String(symbol || '').trim().toUpperCase().replace('.P', '');

            if (!symbol) {
                window.showMobileToast('Sembol sec', 'error');
                return;
            }

            var payload = {
                symbol: symbol,
                side: _moState.side,
                order_mode: _moState.order_mode,
                base_order: parseFloat((document.getElementById('mo-base-order') || {}).value) || 0,
                leverage: parseInt((document.getElementById('mo-leverage') || {}).value) || 1,
                limit_price: parseFloat((document.getElementById('mo-limit-price') || {}).value) || 0,
                take_profit: parseFloat((document.getElementById('mo-tp') || {}).value) || 0,
                trailingSteps: (document.getElementById('mo-ttp') || {}).value || '',
                stop_loss: parseFloat((document.getElementById('mo-sl') || {}).value) || 0,
                partial_tp_enabled: (document.getElementById('mo-pt-enabled') || {}).checked || false,
                partial_tp_percent: parseFloat((document.getElementById('mo-pt-percent') || {}).value) || 50,
            };

            if (payload.base_order <= 0) {
                window.showMobileToast('Miktar > 0 olmali', 'error');
                return;
            }

            var _sideLabel = payload.side === 'BUY' ? 'LONG' : 'SHORT';
            var _msg = 'Sembol: ' + payload.symbol + '\n' +
                       'Yon: ' + _sideLabel + '\n' +
                       'Tip: ' + payload.order_mode.toUpperCase() + '\n' +
                       'Miktar: ' + payload.base_order + ' USDT\n' +
                       'Kaldırac: ' + payload.leverage + 'x\n\n' +
                       'Onaylıyor musun?';
            if (!confirm(_msg)) return;

            var res = await fetch('/api/trade/manual', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            var data = await res.json();

            if (data.status === 'duplicate_warning') {
                var _dupMsg = data.message + '\n\n' +
                    'Ayni sembolde AYRI pozisyon olarak acilsin mi?';
                if (!confirm(_dupMsg)) return;

                payload.confirm_overwrite = true;
                var res2 = await fetch('/api/trade/manual', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                data = await res2.json();
            }

            if (data.status === 'success') {
                window.showMobileToast(
                    'Emir acildi: ' + data.symbol + ' ' + data.side + ' @ ' + (data.entry_price || '-'),
                    'success'
                );
                window.closeManualOrderModal();
                setTimeout(function() {
                    if (window.refreshAll) window.refreshAll();
                }, 500);
            } else if (res.status === 403) {
                window.showMobileToast('Bu ortam read-only (cloud). Manuel emir gonderilemez.', 'warning');
            } else {
                window.showMobileToast(data.message || 'Bilinmeyen hata', 'error');
            }

        } catch(e) {
            console.error('[MO-MANUAL] Hata:', e);
            window.showMobileToast('Baglanti hatasi: ' + e.message, 'error');
        } finally {
            if (btn) { btn.disabled = false; btn.textContent = 'GONDER'; }
        }
    };

    console.log('[MO-MANUAL] Hazir');
})();


/* ============================================================
   F50 - MOBILE TAKVIM
   ============================================================ */
(function() {
    'use strict';

    var _calData = {};
    var _calMonth = null;

    function trNow() {
        var d = new Date();
        return new Date(d.getTime() + 3 * 60 * 60 * 1000);
    }

    function pad(n) { return String(n).padStart(2, '0'); }

    function loadCalData() {
        return fetch('/api/stats/daily?days=365')
            .then(function(r) { return r.json(); })
            .then(function(arr) {
                _calData = {};
                if (Array.isArray(arr)) {
                    arr.forEach(function(row) {
                        _calData[row.date] = {
                            trades: row.trades || 0,
                            net_pnl: row.net_pnl || 0,
                            wins: row.wins || 0,
                            losses: row.losses || 0,
                        };
                    });
                }
            })
            .catch(function(e) {
                console.warn('[CAL] Veri hatasi:', e);
            });
    }

    function renderCal() {
        if (!_calMonth) _calMonth = trNow();

        var y = _calMonth.getUTCFullYear();
        var m = _calMonth.getUTCMonth();

        var months = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran',
                      'Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];

        var titleEl = document.getElementById('cal-title');
        if (titleEl) titleEl.textContent = months[m] + ' ' + y;

        var firstDay = new Date(Date.UTC(y, m, 1));
        var lastDay = new Date(Date.UTC(y, m + 1, 0));
        var totalDays = lastDay.getUTCDate();

        // Pzt = 0
        var startOffset = firstDay.getUTCDay() - 1;
        if (startOffset < 0) startOffset = 6;

        var tr = trNow();
        var todayKey = tr.getUTCFullYear() + '-' + pad(tr.getUTCMonth() + 1) + '-' + pad(tr.getUTCDate());

        var grid = document.getElementById('cal-grid');
        if (!grid) return;
        grid.innerHTML = '';

        // Bos gunler
        for (var i = 0; i < startOffset; i++) {
            var e = document.createElement('div');
            e.className = 'cal-day cal-empty';
            grid.appendChild(e);
        }

        var monthTotal = 0, monthTrades = 0, monthWins = 0, monthLosses = 0;

        for (var d = 1; d <= totalDays; d++) {
            var dateKey = y + '-' + pad(m + 1) + '-' + pad(d);
            var dayData = _calData[dateKey] || null;
            var el = document.createElement('div');
            el.className = 'cal-day';

            if (dateKey === todayKey) el.classList.add('cal-today');

            var pnlClass = 'empty';
            var pnlText = '—';
            var countText = '';

            if (dayData && dayData.trades > 0) {
                var pnl = dayData.net_pnl;
                if (pnl >= 0) {
                    el.classList.add('cal-profit');
                    pnlClass = 'profit';
                } else {
                    el.classList.add('cal-loss');
                    pnlClass = 'loss';
                }
                var s = pnl >= 0 ? '+' : '';
                pnlText = s + pnl.toFixed(1);
                countText = dayData.trades + ' işl.';

                monthTotal += pnl;
                monthTrades += dayData.trades;
                if (pnl >= 0) monthWins++; else monthLosses++;
            }

            el.innerHTML =
                '<div class="cal-num">' + d + '</div>' +
                '<div class="cal-pnl ' + pnlClass + '">' + pnlText + '</div>' +
                '<div class="cal-count">' + countText + '</div>';

            grid.appendChild(el);
        }

        // Ay toplami
        var totEl = document.getElementById('cal-month-total');
        if (totEl) {
            var st = monthTotal >= 0 ? '+' : '';
            totEl.textContent = st + monthTotal.toFixed(2) + ' USDT';
            totEl.style.color = monthTotal >= 0 ? '#0ECB81' : '#F6465D';
        }

        var trEl = document.getElementById('cal-sum-trades');
        var wEl = document.getElementById('cal-sum-wins');
        var lEl = document.getElementById('cal-sum-losses');
        if (trEl) trEl.textContent = monthTrades;
        if (wEl) wEl.textContent = monthWins;
        if (lEl) lEl.textContent = monthLosses;
    }

    window.openMobileCalendar = function() {
        _calMonth = trNow();
        var modal = document.getElementById('cal-modal');
        if (modal) modal.style.display = 'flex';
        loadCalData().then(renderCal);
    };

    window.closeMobileCalendar = function() {
        var modal = document.getElementById('cal-modal');
        if (modal) modal.style.display = 'none';
    };

    window.calPrevMonth = function() {
        if (!_calMonth) _calMonth = trNow();
        _calMonth.setUTCMonth(_calMonth.getUTCMonth() - 1);
        renderCal();
    };

    window.calNextMonth = function() {
        if (!_calMonth) _calMonth = trNow();
        _calMonth.setUTCMonth(_calMonth.getUTCMonth() + 1);
        renderCal();
    };

    window.calGoToday = function() {
        _calMonth = trNow();
        renderCal();
    };

    // Modal disina tiklayinca kapat
    document.addEventListener('click', function(e) {
        var modal = document.getElementById('cal-modal');
        if (modal && e.target === modal) {
            window.closeMobileCalendar();
        }
    });

    console.log('[F50] Mobile takvim hazir');
})();


/* F61 - Risk Siren (Mobile) */
(function() {
    'use strict';
    var OVERLAY_ID = 'mobile-siren-overlay';
    var DISMISS_KEY = 'mobileRiskSirenDismissUntil';
    var CHECK_INTERVAL = 15000;
    var DISMISS_MS = 3 * 60 * 1000;
    var _last = null;
    var _vibrateInterval = null;
    var _audioCtx = null;

    function shouldDismiss() {
        try { return Date.now() < parseInt(localStorage.getItem(DISMISS_KEY) || '0'); }
        catch (e) { return false; }
    }
    function dismiss() {
        try { localStorage.setItem(DISMISS_KEY, String(Date.now() + DISMISS_MS)); } catch (e) {}
    }

    function playSirenTone() {
        try {
            if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            if (_audioCtx.state === 'suspended') _audioCtx.resume();
            var now = _audioCtx.currentTime;
            var osc = _audioCtx.createOscillator();
            var gain = _audioCtx.createGain();
            osc.connect(gain); gain.connect(_audioCtx.destination);
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(800, now);
            osc.frequency.linearRampToValueAtTime(400, now + 0.25);
            osc.frequency.linearRampToValueAtTime(800, now + 0.5);
            osc.frequency.linearRampToValueAtTime(400, now + 0.75);
            gain.gain.setValueAtTime(0.1, now);
            gain.gain.linearRampToValueAtTime(0.001, now + 0.85);
            osc.start(now); osc.stop(now + 0.9);
        } catch (e) {}
    }

    function startVibrate() {
        if (!navigator.vibrate) return;
        var pattern = [200, 100, 200, 100, 400];
        try {
            navigator.vibrate(pattern);
            _vibrateInterval = setInterval(function() {
                try { navigator.vibrate(pattern); } catch (e) {}
            }, 1500);
        } catch (e) {}
    }

    function stopVibrate() {
        if (_vibrateInterval) { clearInterval(_vibrateInterval); _vibrateInterval = null; }
        if (navigator.vibrate) try { navigator.vibrate(0); } catch (e) {}
    }

    function showOverlay(s) {
        var existing = document.getElementById(OVERLAY_ID);
        if (existing) { updateStats(existing, s); return; }
        var o = document.createElement('div');
        o.id = OVERLAY_ID;
        o.className = 'risk-siren-overlay ambulance';
        o.innerHTML = '<div class="siren-box">' +
            '<div class="siren-emoji">🚨</div>' +
            '<div class="siren-h1">RİSK LİMİTİ AŞILDI</div>' +
            '<div class="siren-h2">Yeni pozisyon açılmıyor.<br>Pozisyon azaltın veya limiti yükseltin.</div>' +
            '<div class="siren-metrics">' +
                '<div class="siren-metric"><div class="siren-metric-lbl">RİSK</div><div class="siren-metric-val danger" id="ms-risk">--%</div></div>' +
                '<div class="siren-metric"><div class="siren-metric-lbl">LİMİT</div><div class="siren-metric-val" id="ms-limit">60%</div></div>' +
                '<div class="siren-metric"><div class="siren-metric-lbl">KULLANILAN</div><div class="siren-metric-val" id="ms-used">--</div></div>' +
                '<div class="siren-metric"><div class="siren-metric-lbl">BAKİYE</div><div class="siren-metric-val" id="ms-equity">--</div></div>' +
            '</div>' +
            '<button class="siren-btn" onclick="window._dismissMobileSiren()">3 DAKİKA SUSTUR</button>' +
            '<div class="siren-note">Susturulsa bile bot yeni poz AÇMAZ</div>' +
        '</div>';
        document.body.appendChild(o);
        updateStats(o, s);
        startVibrate();
        playSirenTone();
    }

    function updateStats(o, s) {
        var r = o.querySelector('#ms-risk'), l = o.querySelector('#ms-limit'),
            u = o.querySelector('#ms-used'), e = o.querySelector('#ms-equity');
        if (r) r.textContent = s.risk_pct.toFixed(1) + '%';
        if (l) l.textContent = s.max_ratio.toFixed(0) + '%';
        if (u) u.textContent = s.used_margin.toFixed(0) + ' $';
        if (e) e.textContent = s.equity.toFixed(0) + ' $';
    }

    function hideOverlay() {
        var o = document.getElementById(OVERLAY_ID);
        if (o) o.remove();
        stopVibrate();
    }

    document.addEventListener('touchstart', function initAudio() {
        if (!_audioCtx) {
            try {
                _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                if (_audioCtx.state === 'suspended') _audioCtx.resume();
            } catch (e) {}
        }
        document.removeEventListener('touchstart', initAudio);
    }, { once: true });

    window._dismissMobileSiren = function() {
        dismiss();
        hideOverlay();
        window.showMobileToast && window.showMobileToast('🚨 Siren 3 dk susturuldu', 'warning');
    };

    function checkRisk() {
        fetch('/api/risk/status')
            .then(function(r) { return r.json(); })
            .then(function(s) {
                _last = s;
                if (s.is_over_limit) {
                    if (shouldDismiss()) return;
                    showOverlay(s);
                } else {
                    hideOverlay();
                }
            })
            .catch(function(e) { console.warn('[F61] hata:', e.message); });
    }

    setTimeout(checkRisk, 4000);
    setInterval(checkRisk, CHECK_INTERVAL);
    window._mobileRiskCheck = checkRisk;
    window._mobileRiskStatus = function() { return _last; };
    console.log('[F61] Mobile siren aktif');
})();
