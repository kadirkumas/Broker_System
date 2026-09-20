import shutil
import os

JS_SRC = 'frontend/chart.js'

if not os.path.exists(JS_SRC):
    print(f"[HATA] {JS_SRC} bulunamadi")
    exit(1)

shutil.copy2(JS_SRC, JS_SRC + '.bak_a1_a2')
print(f"[1/4] Yedek: {JS_SRC}.bak_a1_a2")

changes = 0

with open(JS_SRC, 'r', encoding='utf-8', newline='') as f:
    js = f.read().replace('\r\n', '\n')

# 1. YUKLEME (openBotConfigModal icinde)
old1 = """        document.getElementById('cfg-auto-close-delisted').checked = cfg.auto_close_delisted !== false;"""

new1 = """        document.getElementById('cfg-auto-close-delisted').checked = cfg.auto_close_delisted !== false;
        document.getElementById('cfg-daily-max-loss').value = cfg.daily_max_loss || 0;
        document.getElementById('cfg-max-open-positions').value = cfg.max_open_positions || 0;"""

if 'cfg-daily-max-loss\').value = cfg.daily_max_loss' in js:
    print("[2/4] YUKLEME: zaten var (atlandi)")
elif old1 in js:
    js = js.replace(old1, new1, 1)
    changes += 1
    print("[2/4] openBotConfigModal: 2 input yukleniyor")
else:
    print("[2/4] UYARI: cfg-auto-close-delisted satiri bulunamadi!")

# 2. KAYDETME (saveBotConfig icinde) — auto_close_delisted satirindan sonra
old2 = """            auto_close_delisted: document.getElementById('cfg-auto-close-delisted').checked,"""

new2 = """            auto_close_delisted: document.getElementById('cfg-auto-close-delisted').checked,
            daily_max_loss: parseFloat(document.getElementById('cfg-daily-max-loss').value) || 0,
            max_open_positions: parseInt(document.getElementById('cfg-max-open-positions').value) || 0,"""

if 'daily_max_loss: parseFloat' in js:
    print("[3/4] KAYDETME: zaten var (atlandi)")
elif old2 in js:
    js = js.replace(old2, new2, 1)
    changes += 1
    print("[3/4] saveBotConfig: 2 alan kaydediliyor")
else:
    print("[3/4] UYARI: auto_close_delisted kaydetme satiri bulunamadi!")

# 3. TOOLTIP sozlugu
old3 = """        "PT Sonrası DCA": "Kismi TP sonrasi kalan pozisyon icin DCA kademeleri aktif kalsin mi?",
    };"""

new3 = """        "PT Sonrası DCA": "Kismi TP sonrasi kalan pozisyon icin DCA kademeleri aktif kalsin mi?",
        "Günlük Max Zarar": "Bugunun toplam net zarari bu degeri asarsa yeni sinyaller acilmaz. 0 = devre disi.",
        "Max Açık Pozisyon": "Ayni anda acik olabilecek maksimum pozisyon sayisi. 0 = sinirsiz.",
    };"""

if 'Günlük Max Zarar' in js and 'CFG_TIPS' in js:
    print("[4/4] Tooltip: zaten var (atlandi)")
elif old3 in js:
    js = js.replace(old3, new3, 1)
    changes += 1
    print("[4/4] Tooltip sozlugune 2 giris eklendi")
else:
    print("[4/4] UYARI: tooltip sozlugu sonu bulunamadi (atlandi)")

with open(JS_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(js.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend --reload otomatik yukler")
print("  2. Ctrl+Shift+R")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {JS_SRC}.bak_a1_a2 {JS_SRC} -Force")