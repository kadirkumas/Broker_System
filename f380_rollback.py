import os
import shutil

files = [
    r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js',
    r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\main.py',
    r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\position_manager.py'
]

print("--- F380: SISTEM F354 TEMIZ HALINE DONUYOR ---")

for f in files:
    backup = f + '.bak_f354'
    if os.path.exists(backup):
        shutil.copy2(backup, f)
        print(f"Basarili: {os.path.basename(f)} F354 haline dondu.")
    else:
        print(f"UYARI: {backup} bulunamadi! Bu dosya eski haline donemedi.")

print("\n✅ ISLEM TAMAMLANDI! Lutfen tarayicida Ctrl+Shift+R yapip kontrol edin.")
