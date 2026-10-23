p = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\position_manager.py'
lines = open(p, 'r', encoding='utf-8').readlines()
print("--- TRAILING_STATE GUNCELLEME BLOGU (1680 - 1750) ---")
for j in range(1680, min(1750, len(lines))):
    print(f"[{j+1}] {lines[j].rstrip()}")
