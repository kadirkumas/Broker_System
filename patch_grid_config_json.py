import shutil
import json
import os

CFG_SRC = 'backend/bot_config.json'

if not os.path.exists(CFG_SRC):
    print(f"[HATA] {CFG_SRC} bulunamadi")
    exit(1)

shutil.copy2(CFG_SRC, CFG_SRC + '.bak_grid_json')
print(f"[1/3] Yedek: {CFG_SRC}.bak_grid_json")

with open(CFG_SRC, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

# Yeni GRIDBOT yapisi
new_grid = {
    "enabled": False,
    "interval": "15m",
    "gridType": "geometric",
    "gridCount": 20,
    "smaPeriod": 100,
    "atrPeriod": 14,
    "atrMultiplier": 5,
    "baseOrder": 10,
    "leverage": 5,
    "takeProfit": 0.6,
    "trailing": 0.15,
    "stopLoss": 8.0,
    "useDCA": True,
    "volMultiplier": 1.5,
    "steps": "1, 2, 3, 5",
    "partialTPEnabled": True,
    "partialTPPercent": 50,
    "partialTPKeepDCA": True
}

cfg.setdefault("strategies", {})["GRIDBOT"] = new_grid

with open(CFG_SRC, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)

print("[2/3] bot_config.json: GRIDBOT yeni yapiyla degistirildi")
print("[3/3] Kaydedildi")

print()
print("=" * 60)
print("BASARILI")
print("=" * 60)
print()
print("YENI GRIDBOT:")
for k, v in new_grid.items():
    print(f"  {k:<20} = {v}")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend --reload otomatik yukler")
print("  2. /api/engine/config ile dogrula")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {CFG_SRC}.bak_grid_json {CFG_SRC} -Force")