import shutil
import os

MAIN_SRC = 'backend/main.py'
HTML_SRC = 'frontend/index.html'
CSS_SRC = 'frontend/style.css'
JS_SRC = 'frontend/chart.js'

for src in [MAIN_SRC, HTML_SRC, CSS_SRC, JS_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_dev_tools')
    print(f"[1/5] Yedek: {src}.bak_dev_tools")

changes = 0

# ============================================================
# 1. backend/main.py: 2 yeni endpoint
# ============================================================
with open(MAIN_SRC, 'r', encoding='utf-8', newline='') as f:
    main = f.read().replace('\r\n', '\n')

anchor = 'app.mount("/static", NoCacheStaticFiles(directory=str(FRONTEND_DIR)), name="static")'

if 'api/dev/stop' in main:
    print("[2/5] main.py: dev endpoints zaten var (atlandi)")
elif anchor in main:
    new_block = anchor + '''


# ----------------------------------------------------------------------
# DEV TOOLS - Backend stop / restart
# ----------------------------------------------------------------------
@app.post("/api/dev/stop")
async def dev_stop():
    """Backend process'ini kapatir (dev araci)."""
    async def _delayed_exit():
        await asyncio.sleep(0.8)
        print("[DEV] Backend kapatiliyor (os._exit)...")
        os._exit(0)
    asyncio.create_task(_delayed_exit())
    return {"status": "success", "message": "Backend kapatiliyor"}


@app.post("/api/dev/restart")
async def dev_restart():
    """main.py mtime'ini gunceller -> uvicorn --reload yeniden baslatir."""
    try:
        import time as _time
        main_file = Path(__file__)
        os.utime(main_file, (_time.time(), _time.time()))
        print("[DEV] Reload tetiklendi (main.py touch)")
        return {"status": "success", "message": "Reload tetiklendi"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
'''
    main = main.replace(anchor, new_block, 1)
    changes += 1
    print("[2/5] main.py: /api/dev/stop + /api/dev/restart eklendi")
else:
    print("[2/5] HATA: app.mount cipa bulunamadi!")
    exit(1)

with open(MAIN_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(main.replace('\n', '\r\n'))

# ============================================================
# 2. frontend/index.html: basliga 3 minik buton
# ============================================================
with open(HTML_SRC, 'r', encoding='utf-8', newline='') as f:
    html = f.read().replace('\r\n', '\n')

old_h3 = '<h3>İzleme Listesi</h3>'

new_h3 = '''<h3 style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
                            <span>İzleme Listesi</span>
                            <div class="dev-tools" style="display: flex; gap: 3px; flex-shrink: 0;">
                                <button class="dev-btn" onclick="devStopBackend()" title="⏹ Backend Durdur">⏹</button>
                                <button class="dev-btn" onclick="devRestartBackend()" title="🔄 Backend Yeniden Başlat (--reload)">🔄</button>
                                <button class="dev-btn" onclick="devHardReload()" title="⚡ Hard Refresh (Ctrl+Shift+R)">⚡</button>
                            </div>
                        </h3>'''

if 'dev-btn' in html:
    print("[3/5] index.html: dev butonlari zaten var (atlandi)")
elif old_h3 in html:
    html = html.replace(old_h3, new_h3, 1)
    changes += 1
    print("[3/5] index.html: 3 dev butonu eklendi")
else:
    print("[3/5] HATA: <h3>İzleme Listesi</h3> bulunamadi!")
    exit(1)

with open(HTML_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(html.replace('\n', '\r\n'))

# ============================================================
# 3. frontend/style.css: .dev-btn stili
# ============================================================
with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

new_css = '''

/* ============================================================
   DEV TOOLS - Minik Restart Butonlari
   ============================================================ */
.dev-tools .dev-btn {
    background: #1e222d;
    border: 1px solid #2a2e39;
    color: #848e9c;
    padding: 1px 6px;
    font-size: 11px;
    line-height: 1.2;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
    min-width: 22px;
    text-align: center;
}

.dev-tools .dev-btn:hover {
    background: #2a2e39;
    color: #EAECEF;
    border-color: #363c4e;
}

.dev-tools .dev-btn:active {
    transform: scale(0.9);
}

.dev-tools .dev-btn:nth-child(1):hover {
    color: #F6465D;
    border-color: #F6465D;
}

.dev-tools .dev-btn:nth-child(2):hover {
    color: #fcd535;
    border-color: #fcd535;
}

.dev-tools .dev-btn:nth-child(3):hover {
    color: #2962ff;
    border-color: #2962ff;
}
'''

if '.dev-tools .dev-btn' not in css:
    css = css.rstrip() + new_css
    changes += 1
    print("[4/5] style.css: dev buton stilleri eklendi")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

# ============================================================
# 4. frontend/chart.js: dev fonksiyonlari
# ============================================================
with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

new_js = '''

// =============================================================
// DEV TOOLS - Backend restart / stop / reload
// =============================================================
window.devStopBackend = async function() {
    const ok = await window.showConfirm(
        '⏹ BACKEND DURDUR',
        'Backend kapatılsın mı?\\n\\n' +
        '• Bot çalışıyorsa durur\\n' +
        '• Sayfa veri çekemez hale gelir\\n' +
        '• Yeniden başlatmak için terminalden:\\n' +
        '   py -m uvicorn backend.main:app --reload',
        'DURDUR',
        'İPTAL',
        'danger'
    );
    if (!ok) return;
    try {
        window.showToast('⏹ Backend kapatılıyor...', 'warning', 3000);
        await fetch('/api/dev/stop', { method: 'POST' });
    } catch(e) {
        // Beklenen: process öldüğü için bağlantı kesilir
        console.log('[DEV] Stop response alinamadi (beklenen)');
    }
};

window.devRestartBackend = async function() {
    try {
        const res = await fetch('/api/dev/restart', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            window.showToast('🔄 Backend yeniden başlatılıyor... (3-5 sn)', 'info', 3500);
        } else {
            window.showToast('❌ Restart hatası: ' + (data.message || 'bilinmeyen'), 'error', 4000);
        }
    } catch(e) {
        window.showToast('❌ Restart başarısız: ' + e.message, 'error', 4000);
    }
};

window.devHardReload = function() {
    window.showToast('⚡ Sayfa yenileniyor...', 'info', 1200);
    setTimeout(function() {
        try {
            location.reload(true);
        } catch(e) {
            location.reload();
        }
    }, 300);
};
'''

if 'window.devStopBackend' not in js:
    js = js.rstrip() + new_js
    changes += 1
    print("[5/5] chart.js: dev fonksiyonlari eklendi")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - Izleme Listesi basliginin sagina 3 minik buton eklendi")
print("  - ⏹  Backend Durdur  (onay sormali)")
print("  - 🔄  Backend Restart (uvicorn --reload gerekir)")
print("  - ⚡  Hard Refresh   (Ctrl+Shift+R esdegeri)")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend'i Ctrl+C ile DURDUR")
print("  2. py -m uvicorn backend.main:app --reload")
print("  3. Ctrl+Shift+R")
print()
print("Geri donmek icin:")
for src in [MAIN_SRC, HTML_SRC, CSS_SRC, JS_SRC]:
    print(f"  Copy-Item {src}.bak_dev_tools {src} -Force")