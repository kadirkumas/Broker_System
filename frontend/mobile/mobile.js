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
        const r = await fetch('/api/trade/close', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ symbol: _selectedSymbol, reason: 'MOBILE_MANUAL' })
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
        const r = await fetch('/api/engine/toggle', { method: 'POST' });
        if (r.ok) {
            await fetchBotStatus();
        }
    } catch(e) {
        alert('Bağlantı hatası');
    } finally {
        btn.disabled = false;
    }
};

// ---------- COLLAPSE ----------
document.querySelectorAll('.collapse-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const target = document.getElementById(btn.dataset.target);
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

    // 8 saniyede bir otomatik güncelle
    setInterval(refreshAll, 8000);
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
async function hashPin(pin) {
    const data = new TextEncoder().encode('broker_salt_' + pin);
    const hash = await crypto.subtle.digest('SHA-256', data);
    return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2,'0')).join('');
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

