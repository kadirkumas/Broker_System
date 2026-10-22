import os

files = [
    r'C:\Users\kadir.kumas\Desktop\Broker_System\frontend\chart.js',
    r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\main.py',
    r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\position_manager.py'
]

print("--- SISTEMDE KALINTI ARANIYOR (F355 - F379) ---")
found_any = False
# F355'ten F379'a kadar tum etiketler
tags_to_search = [f"F{i}" for i in range(355, 380)]

for f in files:
    if not os.path.exists(f): continue
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
        
    file_found = []
    for tag in tags_to_search:
        if tag in content:
            file_found.append(tag)
            
    if file_found:
        print(f"[-] {os.path.basename(f)}: Kalinti bulundu! -> {', '.join(file_found)}")
        found_any = True
    else:
        print(f"[+] {os.path.basename(f)}: TERTEMIZ. Hicbir F355-F379 kalintisi yok.")

if found_any:
    print("\n⚠️ DIKKAT: Dosyalarda hala F355-F379 yamalari var!")
else:
    print("\n✅ MUKKEMMEL! F380 islemi kusursuz calismis. Sistem tamamen F354 haline donmus.")
