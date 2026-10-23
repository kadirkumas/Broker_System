import json
import os

cfg_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\bot_config.json'
pm_path = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\position_manager.py'

print("--- BOT_CONFIG.JSON ICINDE AI TTP AYARLARI ---")
try:
    with open(cfg_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    
    # Tum config icinde TTP, TRAILING veya AI ile ilgili anahtarlari bul
    def find_keys(d, parent=""):
        for k, v in d.items():
            if isinstance(v, dict):
                find_keys(v, parent + k + ".")
            elif any(x in k.lower() for x in ['ttp', 'trail', 'ai', 'activation', 'hwm']):
                print(f"{parent}{k}: {v}")
                
    find_keys(cfg)
except Exception as e:
    print("Config okuma hatasi:", e)

print("\n--- POSITION_MANAGER.PY ICINDE AI TTP KODU ---")
try:
    lines = open(pm_path, 'r', encoding='utf-8').readlines()
    found = 0
    for i, l in enumerate(lines):
        # AI TTP tetikleme veya hesaplama bloklarini ariyoruz
        if "ai_ttp" in l.lower() or "aiTTP" in l or "TTP" in l and "execute_close" in lines[i:i+15].__str__():
            start = max(0, i - 5)
            end = min(len(lines), i + 20)
            print(f"\n--- Satir {i+1} Civari ---")
            for j in range(start, end):
                prefix = ">> " if j == i else "   "
                print(f"{prefix}{j+1}: {lines[j].rstrip()}")
            found += 1
            if found >= 3: break
    if found == 0:
        # Daha genel bir arama yapalim
        for i, l in enumerate(lines):
            if "TTP" in l.upper():
                print(f"[{i+1}] {l.strip()[:250]}")
except Exception as e:
    print("PM okuma hatasi:", e)
