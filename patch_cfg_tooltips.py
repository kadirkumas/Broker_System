import shutil
import re
import os

HTML_SRC = 'frontend/index.html'
CSS_SRC = 'frontend/style.css'
JS_SRC = 'frontend/chart.js'

for src in [HTML_SRC, CSS_SRC, JS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_cfg_tooltips')
    print(f"[1/4] Yedek: {src}.bak_cfg_tooltips")

changes = 0

# ============================================================
# 1. HTML: cfg-label'lara data-tip ekle
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

tooltips = {
    "Tarama Süresi (sn)": "Sembollerin kac saniyede bir taranacagi. Kucuk deger = daha sik tarama, daha fazla API kullanimi.",
    "Pozisyon Kontrol (sn)": "Acik pozisyonlarin TP/SL/Trailing icin kac saniyede bir kontrol edilecegi.",
    "Maks Sembol": "Taranacak maksimum sembol sayisi. Likiditeye gore en aktif USDT pariteleri secilir.",
    "Delist Kapat": "Bir sembol borsadan cikarilirsa otomatik olarak pozisyonu kapatir.",
    "Zaman Dilimi": "Stratejinin hangi mum periyodunda calisacagi (1m, 5m, 15m, 1h, 4h).",
    "RSI Period": "RSI hesaplama periyodu. Kucuk = daha hassas, buyuk = daha guvenilir.",
    "HMA Length": "Hull Hareketli Ortalama periyodu. Trend yonunu belirler.",
    "Kaynak": "HMA hesaplamasinda kullanilacak fiyat kaynagi (hl2, close, open).",
    "Long Trade": "Yukari yonlu (alis) sinyalleri acilsin mi?",
    "Short Trade": "Asagi yonlu (satis) sinyalleri acilsin mi?",
    "Geriye Dönük Tarama": "Pivot noktalarini bulmak icin geriye bakilacak mum sayisi.",
    "İlk İşlem (USDT)": "Pozisyon acilisinda kullanilacak USDT miktari (kaldiracli degil, saf teminat).",
    "Marjin (Kilitlenen)": "Bu pozisyon icin hesabinizda kilitlenen gercek teminat = Ilk Islem / Kaldiracli.",
    "Hedef Kâr (%)": "Pozisyon bu kar yuzdesine ulastiginda Izleyen Stop aktif olur. Ornek: 1.5 = %1.5 kar.",
    "İzleyen Stop (%)": "Fiyat tepe noktasindan bu yuzde kadar geri cekilirse pozisyon kapatilir. Kari korur.",
    "Stop Loss (%)": "Fiyat girise gore bu yuzde ters giderse pozisyon otomatik kapanir. Zarari sinirlar.",
    "DCA Aktif": "Kademeli alim. Fiyat ters giderse ek alim yapar ve ortalama maliyeti dusurur.",
    "Hacim Çarpanı": "Her DCA kademesinde eklenecek hacim carpani. 1.2 = her kademe 1.2x onceki hacim.",
    "Düşüş Adımları (%)": "Her DCA kademesinin hangi yuzde dususte tetiklenecegi. Ornek: 5,10,15,20.",
    "Kısmi TP Aktif": "Pozisyon kara gectiginde tamamini kapatmak yerine bir kismini kapatir, kalani trendde tutar.",
    "Kapatma Oranı (%)": "Kismi TP'de kapatilacak pozisyon yuzdesi. 50 = pozisyonun yarisi kapatilir.",
    "PT Sonrası DCA": "Kismi TP sonrasi kalan pozisyon icin DCA kademeleri aktif kalsin mi?",
}

def replace_label(m):
    text = m.group(1).strip()
    clean = re.sub(r'^\W+\s*', '', text).strip()
    tip = tooltips.get(text) or tooltips.get(clean)
    if tip:
        tip_esc = tip.replace('"', '&quot;')
        return f'<span class="cfg-label" data-tip="{tip_esc}">{m.group(1)}</span>'
    return m.group(0)

new_html, cnt = re.subn(
    r'<span class="cfg-label">([^<]*)</span>',
    replace_label,
    html
)

if cnt > 0:
    html = new_html
    changes += 1
    print(f"[2/4] HTML: {cnt} label'a data-tip eklendi")

# Kaldiraç ozel (icinde lev-badge var)
kald_tip = "1 = kaldiracli degil. 5x = 5 kat. Kar/zarar kaldiracli oraninda buyur, tasfiye riski artar."
old_kald = '<span class="cfg-label">Kaldıraç <span class="lev-badge">X</span></span>'
new_kald = f'<span class="cfg-label" data-tip="{kald_tip}">Kaldıraç <span class="lev-badge">X</span></span>'

k_cnt = html.count(old_kald)
if k_cnt > 0:
    html = html.replace(old_kald, new_kald)
    changes += 1
    print(f"[2/4] HTML: {k_cnt} Kaldıraç label'ina data-tip eklendi")

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 2. CSS: tooltip stili
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

new_css = '''

/* ============================================================
   CFG LABEL TOOLTIP (Bot Ayarlari info)
   ============================================================ */
.cfg-label[data-tip] {
    cursor: help;
}

#cfg-tooltip {
    position: fixed;
    z-index: 999999;
    max-width: 320px;
    min-width: 200px;
    padding: 8px 12px;
    background: #0b0e14;
    color: #d1d4dc;
    font-size: 11px;
    font-weight: 500;
    line-height: 1.45;
    border: 1px solid #2962ff;
    border-radius: 6px;
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.7);
    pointer-events: none;
    opacity: 0;
    transform: translateY(-4px);
    transition: opacity 0.15s ease, transform 0.15s ease;
    font-family: inherit;
    letter-spacing: 0;
    text-transform: none;
    display: none;
}

#cfg-tooltip.show {
    opacity: 1;
    transform: translateY(0);
}

#cfg-tooltip::before {
    content: '';
    position: absolute;
    width: 0;
    height: 0;
    border: 5px solid transparent;
}

#cfg-tooltip.pos-bottom::before {
    top: -10px;
    left: var(--arrow-left, 15px);
    border-bottom-color: #2962ff;
}

#cfg-tooltip.pos-top::before {
    bottom: -10px;
    left: var(--arrow-left, 15px);
    border-top-color: #2962ff;
}
'''

if 'cfg-tooltip' not in css:
    css = css.rstrip() + new_css
    changes += 1
    print("[3/4] CSS: tooltip stili eklendi")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

# ============================================================
# 3. JS: tooltip hover logic
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

new_js = '''

// =============================================================
// CFG LABEL TOOLTIP (Bot Ayarlari info)
// =============================================================
(function setupCfgTooltips() {
    function getTooltip() {
        let tip = document.getElementById('cfg-tooltip');
        if (!tip) {
            tip = document.createElement('div');
            tip.id = 'cfg-tooltip';
            document.body.appendChild(tip);
        }
        return tip;
    }

    function positionTooltip(el, tip) {
        const rect = el.getBoundingClientRect();
        const tipRect = tip.getBoundingClientRect();
        const spaceAbove = rect.top;
        const spaceBelow = window.innerHeight - rect.bottom;

        let top, posClass;
        if (spaceAbove >= tipRect.height + 12 || spaceAbove >= spaceBelow) {
            top = rect.top - tipRect.height - 10;
            posClass = 'pos-top';
        } else {
            top = rect.bottom + 10;
            posClass = 'pos-bottom';
        }

        let left = rect.left;
        if (left + tipRect.width > window.innerWidth - 15) {
            left = window.innerWidth - tipRect.width - 15;
        }
        if (left < 10) left = 10;

        tip.style.top = top + 'px';
        tip.style.left = left + 'px';
        tip.className = posClass;

        const arrowLeft = Math.max(10, Math.min(tipRect.width - 20, rect.left - left + 10));
        tip.style.setProperty('--arrow-left', arrowLeft + 'px');
    }

    function showTip(el) {
        const txt = el.getAttribute('data-tip');
        if (!txt) return;
        const tip = getTooltip();
        tip.textContent = txt;
        tip.style.display = 'block';
        tip.style.opacity = '0';
        positionTooltip(el, tip);
        requestAnimationFrame(() => tip.classList.add('show'));
    }

    function hideTip() {
        const tip = document.getElementById('cfg-tooltip');
        if (tip) {
            tip.classList.remove('show');
            setTimeout(() => { tip.style.display = 'none'; }, 150);
        }
    }

    function attachTooltips() {
        document.querySelectorAll('.cfg-label[data-tip]').forEach(el => {
            if (el._tipHooked) return;
            el._tipHooked = true;
            el.addEventListener('mouseenter', () => showTip(el));
            el.addEventListener('mouseleave', hideTip);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => setTimeout(attachTooltips, 500));
    } else {
        setTimeout(attachTooltips, 500);
    }

    const origOpen = window.openBotConfigModal;
    if (origOpen && !origOpen._tipHooked) {
        window.openBotConfigModal = function() {
            origOpen.apply(this, arguments);
            setTimeout(attachTooltips, 100);
        };
        window.openBotConfigModal._tipHooked = true;
    }
})();
'''

if 'setupCfgTooltips' not in js:
    js = js.rstrip() + new_js
    changes += 1
    print("[4/4] JS: tooltip hover logic eklendi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - Bot Ayarlari'ndaki tum cfg-label'larin uzerine gelince")
print("    mavi cerceveli info tooltip acilir")
print("  - Tooltip ekran konumuna gore otomatik ust/alt yerlesir")
print("  - Modal kenarindan kesilmez (position: fixed)")
print("  - Fare imleci 'help' sekline doner")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print()
print("Geri donmek icin:")
for src in [HTML_SRC, CSS_SRC, JS_SRC]:
    print(f"  Copy-Item {src}.bak_cfg_tooltips {src} -Force")