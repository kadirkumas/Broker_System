import shutil
import os
import re

JS_SRC = 'frontend/chart.js'
JS_BAK = 'frontend/chart.js.bak_toast_v2'
CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_toast_v2'

for src in [JS_SRC, CSS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_toast_v2')
    print(f"[1/3] Yedek: {src}.bak_toast_v2")

# ============================================================
# 1. JS: showToast fonksiyonunu komple degistir
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# Eski showToast'u bul
pattern = r'window\.showToast\s*=\s*function\s*\([^)]*\)\s*\{.*?\n\};'
match = re.search(pattern, js, re.DOTALL)

if not match:
    print("[HATA] Eski showToast bulunamadi")
    exit(1)

print(f"[2/3] Eski showToast bulundu ({len(match.group(0))} karakter)")

new_func = '''window.showToast = function(message, type = 'info', duration = 4000, customTitle = null) {
    // ⚡ Deduplication: ayni mesaj 4 saniye icinde tekrar gelirse yoksay
    const msgStr = String(message || '');
    const dedupeKey = type + '|' + msgStr;
    const now = Date.now();
    
    if (!window._toastDedupeCache) window._toastDedupeCache = {};
    
    if (window._toastDedupeCache[dedupeKey]) {
        const elapsed = now - window._toastDedupeCache[dedupeKey];
        if (elapsed < 4000) return;
    }
    window._toastDedupeCache[dedupeKey] = now;
    
    // 30 sn'den eski kayitlari temizle
    Object.keys(window._toastDedupeCache).forEach(function(k) {
        if (now - window._toastDedupeCache[k] > 30000) delete window._toastDedupeCache[k];
    });
    
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }
    
    // Maks 5 toast
    while (container.children.length >= 5) {
        container.removeChild(container.firstChild);
    }
    
    const icons = {
        success: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>',
        error: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
        warning: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path></svg>',
        info: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line><circle cx="12" cy="12" r="10"></circle></svg>'
    };
    
    const titles = { success: 'Başarılı', error: 'Hata', warning: 'Uyarı', info: 'Bilgi' };
    
    // Bastaki emojiyi temizle
    let cleanMessage = msgStr.replace(/^[\\u2705\\u274C\\u26A0\\uFE0F\\u2139\\uFE0F\\uD83D\\uDCB0\\uD83D\\uDCCA\\u25B6\\u23F9\\uD83D\\uDDD1\\uFE0F\\uD83E\\uDDF9\\uD83D\\uDD04\\u26A1\\uD83D\\uDCBE\\u2713\\u2717\\uD83D\\uDEAB\\uD83C\\uDFAF\\uD83D\\uDD35\\uD83D\\uDFE2\\uD83D\\uDD34\\uD83D\\uDFE1]\\s*/u, '').trim();
    if (!cleanMessage) cleanMessage = msgStr;
    
    const title = customTitle || titles[type] || 'Bilgi';
    const icon = icons[type] || icons.info;
    
    const toast = document.createElement('div');
    toast.className = 'toast toast-v2 toast-v2-' + type;
    
    toast.innerHTML = '<div class="toast-v2-icon">' + icon + '</div>'
        + '<div class="toast-v2-content">'
        + '<div class="toast-v2-title">' + title + '</div>'
        + '<div class="toast-v2-message">' + cleanMessage + '</div>'
        + '</div>'
        + '<button class="toast-v2-close" type="button">×</button>'
        + '<div class="toast-v2-progress" style="animation-duration: ' + duration + 'ms;"></div>';
    
    container.appendChild(toast);
    requestAnimationFrame(function() { toast.classList.add('show'); });
    
    const closeBtn = toast.querySelector('.toast-v2-close');
    const timer = setTimeout(function() {
        toast.classList.remove('show');
        setTimeout(function() { toast.remove(); }, 350);
    }, duration);
    
    closeBtn.addEventListener('click', function() {
        clearTimeout(timer);
        toast.classList.remove('show');
        setTimeout(function() { toast.remove(); }, 350);
    });
};'''

js = js[:match.start()] + new_func + js[match.end():]

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print("[2/3] Yeni showToast eklendi")

# ============================================================
# 2. CSS: Yeni toast stilleri
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

new_css = '''

/* ============================================================
   TOAST V2 - İKONLU, BAŞLIKLI, MODERN BİLDİRİM
   ============================================================ */
#toast-container {
    position: fixed !important;
    top: 20px !important;
    right: 20px !important;
    bottom: auto !important;
    left: auto !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 10px !important;
    z-index: 99999 !important;
    pointer-events: none !important;
    max-width: 400px !important;
    width: calc(100% - 40px) !important;
}

#toast-container .toast-v2 {
    position: relative !important;
    display: flex !important;
    align-items: flex-start !important;
    gap: 12px !important;
    padding: 14px 40px 14px 16px !important;
    border-radius: 10px !important;
    color: #fff !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5) !important;
    pointer-events: auto !important;
    opacity: 0 !important;
    transform: translateX(420px) !important;
    transition: opacity 0.35s ease, transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    overflow: hidden !important;
    font-family: inherit !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    min-height: 60px !important;
    box-sizing: border-box !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    margin: 0 !important;
}

#toast-container .toast-v2.show {
    opacity: 1 !important;
    transform: translateX(0) !important;
}

.toast-v2-icon {
    flex-shrink: 0 !important;
    width: 26px !important;
    height: 26px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: rgba(255,255,255,0.22) !important;
    border-radius: 50% !important;
    margin-top: 1px !important;
}

.toast-v2-icon svg {
    color: #fff !important;
    display: block !important;
}

.toast-v2-content {
    flex: 1 !important;
    min-width: 0 !important;
    padding-right: 4px !important;
}

.toast-v2-title {
    font-size: 13px !important;
    font-weight: 700 !important;
    margin-bottom: 2px !important;
    letter-spacing: 0.2px !important;
    color: #fff !important;
    line-height: 1.3 !important;
}

.toast-v2-message {
    font-size: 12px !important;
    font-weight: 500 !important;
    line-height: 1.4 !important;
    word-wrap: break-word !important;
    opacity: 0.95 !important;
    color: #fff !important;
}

.toast-v2-close {
    position: absolute !important;
    top: 6px !important;
    right: 8px !important;
    background: transparent !important;
    border: none !important;
    color: rgba(255,255,255,0.7) !important;
    font-size: 22px !important;
    line-height: 1 !important;
    cursor: pointer !important;
    padding: 0 !important;
    width: 22px !important;
    height: 22px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: color 0.15s, background 0.15s !important;
    border-radius: 4px !important;
    font-family: inherit !important;
}

.toast-v2-close:hover {
    color: #fff !important;
    background: rgba(255,255,255,0.15) !important;
}

.toast-v2-progress {
    position: absolute !important;
    bottom: 0 !important;
    left: 0 !important;
    height: 3px !important;
    background: rgba(255,255,255,0.45) !important;
    animation: toastProgressBar linear forwards !important;
    width: 100% !important;
}

@keyframes toastProgressBar {
    from { width: 100%; }
    to { width: 0%; }
}

#toast-container .toast-v2-success {
    background: linear-gradient(135deg, #0ECB81 0%, #079c62 100%) !important;
}
#toast-container .toast-v2-error {
    background: linear-gradient(135deg, #F6465D 0%, #c53045 100%) !important;
}
#toast-container .toast-v2-warning {
    background: linear-gradient(135deg, #f5a623 0%, #d68910 100%) !important;
}
#toast-container .toast-v2-info {
    background: linear-gradient(135deg, #2962ff 0%, #1e4fd6 100%) !important;
}

/* Eski toast stillerini etkisiz kil */
#toast-container .toast:not(.toast-v2) {
    display: none !important;
}
'''

css = css.rstrip() + new_css

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

print("[3/3] Yeni CSS stilleri eklendi")

print()
print("=" * 60)
print("BASARILI!")
print("=" * 60)
print()
print("YENI OZELLIKLER:")
print("  ✓ Ikon + Baslik + Mesaj yapisi")
print("  ✓ 4 renk temasi (success/error/warning/info)")
print("  ✓ Kapatma butonu (X)")
print("  ✓ Ilerleme cubugu (progress bar)")
print("  ✓ Ust sag kose (eskiden sag alttan)")
print("  ✓ DEDUPLICATION: ayni mesaj 4 saniyede 1 kez gorunur")
print("  ✓ Yukaridan asagi kayan animasyon")
print()
print("Ctrl+Shift+R yapin.")
print()
print("Geri donmek icin:")
print(f"  copy /Y {JS_BAK} {JS_SRC}")
print(f"  copy /Y {CSS_BAK} {CSS_SRC}")