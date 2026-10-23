p = r'C:\Users\kadir.kumas\Desktop\Broker_System\backend\position_manager.py'
lines = open(p, 'r', encoding='utf-8').readlines()
print("=== 1. tp_pct TANIMLARI ===")
for i, l in enumerate(lines):
    if "tp_pct" in l and "=" in l and "profit_pct" not in l:
        print(f"[{i+1}] {l.strip()[:200]}")

print("\n=== 2. profit_pct TANIMLARI ===")
for i, l in enumerate(lines):
    if "profit_pct" in l and "=" in l and "<=" not in l and ">=" not in l:
        print(f"[{i+1}] {l.strip()[:200]}")

print("\n=== 3. _trail_steps TANIMLARI ===")
for i, l in enumerate(lines):
    if "trail_steps" in l and "=" in l:
        print(f"[{i+1}] {l.strip()[:200]}")

print("\n=== 4. TTP'YE ULASMADAN ONCEKI 'continue' KONTROLLERI (1450-1700) ===")
for i, l in enumerate(lines):
    if 1450 < i < 1700 and "continue" in l:
        # Baglami goster
        print(f"[{i+1}] {l.strip()[:200]}")
