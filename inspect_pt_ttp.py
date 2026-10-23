p = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\position_manager.py'
lines = open(p, 'r', encoding='utf-8').readlines()

print("=== 1. PT (PARTIAL TP) KONTROL BLOGU (1600 - 1690) ===")
for j in range(1600, min(1690, len(lines))):
    print(f"[{j+1}] {lines[j].rstrip()}")

print("\n=== 2. TTP (TRAILING) TETIKLEME BLOGU (1690 - 1750) ===")
for j in range(1690, min(1750, len(lines))):
    print(f"[{j+1}] {lines[j].rstrip()}")
