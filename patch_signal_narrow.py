import shutil
import os

CSS_SRC = 'frontend/style.css'
CSS_BAK = 'frontend/style.css.bak_signal_narrow'

shutil.copy2(CSS_SRC, CSS_BAK)
print(f"[1/2] Yedek: {CSS_BAK}")

with open(CSS_SRC, 'r', encoding='utf-8', newline='') as f:
    css = f.read().replace('\r\n', '\n')

new_css = '''

/* ============================================================
   SON AYAR - Sinyaller paneli daralt + sağ boşluk kapat
   ============================================================ */
.sidebar {
    width: 340px !important;   /* Sidebar genişliği - İSTEDİĞİN GİBİ DEĞİŞTİR */
    flex-shrink: 0 !important;
}

.sidebar-panels-row {
    display: flex !important;
    width: 100% !important;
    gap: 4px !important;
}

.sidebar-panels-row > .watchlist-module {
    flex: 0 0 165px !important;   /* İzleme listesi - SABİT */
    min-width: 140px !important;
}

.sidebar-panels-row > .signal-panel-module {
    flex: 1 1 auto !important;    /* Kalan alanı doldur */
    max-width: none !important;
    min-width: 0 !important;
}

.panel-v-resizer {
    display: none !important;     /* Sürükleme kolunu gizle (artık gerekmez) */
}
'''

# Aynı bloğu tekrar eklemeyi önle
if 'SON AYAR - Sinyaller paneli daralt' not in css:
    css = css.rstrip() + new_css
    print("[2/2] Sinyaller paneli daraltıldı")
else:
    print("[2/2] Zaten ekli")

with open(CSS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(css.replace('\n', '\r\n'))

print()
print("BASARILI!")
print("Ctrl+Shift+R yapin.")