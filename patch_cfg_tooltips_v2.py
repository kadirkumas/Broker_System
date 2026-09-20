import shutil
import os

JS_SRC = 'frontend/chart.js'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_SRC + '.bak_cfg_tooltips_v2')
print(f"[1/3] Yedek: {JS_SRC}.bak_cfg_tooltips_v2")

changes = 0

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# ============================================================
# 1. Eski CFG LABEL TOOLTIP blogunu sil (varsa)
# ============================================================
old_marker = '// CFG LABEL TOOLTIP'
idx = js.find(old_marker)

if idx > 0:
    # Geriye dogru git, en son // === blogunun basini bul
    start = js.rfind('\n\n// ====', 0, idx)
    if start < 0:
        start = idx - 60
    # Sona kadar sil (blok dosya sonunda)
    js = js[:start].rstrip() + '\n'
    changes += 1
    print("[2/3] Eski tooltip blogu silindi")
else:
    print("[2/3] Eski tooltip blogu yok (atlandi)")

# ============================================================
# 2. Yeni event-delegation tabanli tooltip sistemi ekle
# ============================================================
new_js = '''

// =============================================================
// CFG LABEL TOOLTIP v2 (Event Delegation + JS Sozluk)
// =============================================================
(function setupCfgTooltipsV2() {
    const CFG_TIPS = {
        "Tarama Süresi": "Sembollerin kac saniyede bir taranacagi. Kucuk deger = daha sik tarama, daha fazla API kullanimi.",
        "Pozisyon Kontrol": "Acik pozisyonlarin TP/SL/Trailing icin kac saniyede bir kontrol edilecegi.",
        "Maks Sembol": "Taranacak maksimum sembol sayisi. Likiditeye gore en aktif USDT pariteleri secilir.",
        "Delist Kapat": "Bir sembol borsadan cikarilirsa otomatik olarak pozisyonu kapatir.",
        "Zaman Dilimi": "Stratejinin hangi mum periyodunda calisacagi (1m, 5m, 15m, 1h, 4h).",
        "RSI Period": "RSI hesaplama periyodu. Kucuk = daha hassas, buyuk = daha guvenilir.",
        "HMA Length": "Hull Hareketli Ortalama periyodu. Trend yonunu belirler.",
        "Kaynak": "HMA hesaplamasinda kullanilacak fiyat kaynagi (hl2, close, open).",
        "Long Trade": "Yukari yonlu (alis) sinyalleri acilsin mi?",
        "Short Trade": "Asagi yonlu (satis) sinyalleri acilsin mi?",
        "Geriye Dönük Tarama": "Pivot noktalarini bulmak icin geriye bakilacak mum sayisi.",
        "İlk İşlem": "Pozisyon acilisinda kullanilacak USDT miktari (kaldiracli degil, saf teminat).",
        "Kaldıraç": "1 = kaldiracli degil. 5x = 5 kat. Kar/zarar kaldiracli oraninda buyur, tasfiye riski artar.",
        "Marjin": "Bu pozisyon icin hesabinizda kilitlenen gercek teminat = Ilk Islem / Kaldiracli.",
        "Hedef Kâr": "Pozisyon bu kar yuzdesine ulastiginda Izleyen Stop aktif olur. Ornek: 1.5 = %1.5 kar.",
        "İzleyen Stop": "Fiyat tepe noktasindan bu yuzde kadar geri cekilirse pozisyon kapatilir. Kari korur.",
        "Stop Loss": "Fiyat girise gore bu yuzde ters giderse pozisyon otomatik kapanir. Zarari sinirlar.",
        "DCA Aktif": "Kademeli alim. Fiyat ters giderse ek alim yapar ve ortalama maliyeti dusurur.",
        "Hacim Çarpanı": "Her DCA kademesinde eklenecek hacim carpani. 1.2 = her kademe 1.2x onceki hacim.",
        "Düşüş Adımları": "Her DCA kademesinin hangi yuzde dususte tetiklenecegi. Ornek: 5,10,15,20.",
        "Kısmi TP Aktif": "Pozisyon kara gectiginde tamamini kapatmak yerine bir kismini kapatir, kalani trendde tutar.",
        "Kapatma Oranı": "Kismi TP'de kapatilacak pozisyon yuzdesi. 50 = pozisyonun yarisi kapatilir.",
        "PT Sonrası DCA": "Kismi TP sonrasi kalan pozisyon icin DCA kademeleri aktif kalsin mi?",
    };

    function getTooltip() {
        let tip = document.getElementById('cfg-tooltip');
        if (!tip) {
            tip = document.createElement('div');
            tip.id = 'cfg-tooltip';
            document.body.appendChild(tip);
        }
        return tip;
    }

    function findTipText(el) {
        // 1) data-tip varsa onu kullan
        const dt = el.getAttribute('data-tip');
        if (dt) return dt;
        // 2) Yoksa metinden sozluge bak
        const txt = (el.textContent || '').replace(/\\s+/g, ' ').trim();
        if (CFG_TIPS[txt]) return CFG_TIPS[txt];
        for (const key in CFG_TIPS) {
            if (txt.startsWith(key)) return CFG_TIPS[key];
        }
        return null;
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

    let currentEl = null;

    function showTip(el, text) {
        const tip = getTooltip();
        tip.textContent = text;
        tip.style.display = 'block';
        tip.style.opacity = '0';
        positionTooltip(el, tip);
        requestAnimationFrame(function() {
            tip.classList.add('show');
            tip.style.opacity = '';
        });
        currentEl = el;
    }

    function hideTip() {
        const tip = document.getElementById('cfg-tooltip');
        if (tip) {
            tip.classList.remove('show');
            setTimeout(function() { tip.style.display = 'none'; }, 150);
        }
        currentEl = null;
    }

    // ⚡ EVENT DELEGATION - document seviyesinde dinle
    document.addEventListener('mouseover', function(e) {
        const el = e.target.closest ? e.target.closest('.cfg-label') : null;
        if (!el) return;
        if (el === currentEl) return;
        const txt = findTipText(el);
        if (!txt) return;
        if (currentEl) hideTip();
        showTip(el, txt);
    }, true);

    document.addEventListener('mouseout', function(e) {
        const el = e.target.closest ? e.target.closest('.cfg-label') : null;
        if (!el) return;
        // Ilgili baska bir cfg-label'a gecmediyse kapat
        const related = e.relatedTarget && e.relatedTarget.closest ? e.relatedTarget.closest('.cfg-label') : null;
        if (related === el) return;
        if (currentEl === el) hideTip();
    }, true);

    console.log('[TOOLTIP v2] Event delegation kuruldu. Sozluk:', Object.keys(CFG_TIPS).length, 'alan');
})();
'''

js = js.rstrip() + new_js
changes += 1
print("[3/3] Yeni tooltip sistemi eklendi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("DEGISIKLIKLER:")
print("  - Eski tooltip kodu silindi")
print("  - Yeni event-delegation tabanli sistem eklendi")
print("  - HTML'de data-tip olsa da olmasa da metinden eslesme yapar")
print("  - Konsola '[TOOLTIP v2] Event delegation kuruldu' yazacak")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Ctrl+Shift+R")
print("  2. F12 ile konsolu ac")
print("  3. Konsolda '[TOOLTIP v2] Event delegation kuruldu' gormelisin")
print("  4. Bot Ayarlari'ni ac, herhangi bir label'a hover yap")
print("     -> Tooltip acilmali")
print()
print("Hala calismazsa konsolda su komutu calistir ve ciktisini gonder:")
print("  document.querySelectorAll('.cfg-label').length")
print("  document.getElementById('cfg-tooltip')")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {JS_SRC}.bak_cfg_tooltips_v2 {JS_SRC} -Force")