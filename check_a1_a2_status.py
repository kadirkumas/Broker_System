print("=" * 70)
print("A1 + A2 KURULU MU? - KONTROL")
print("=" * 70)
print()

# strategy_engine.py
print("[1] backend/strategy_engine.py")
print("-" * 70)
try:
    with open('backend/strategy_engine.py', 'r', encoding='utf-8') as f:
        se = f.read()
    print(f"  daily_max_loss       : {'VAR' if 'daily_max_loss' in se else 'YOK'}")
    print(f"  max_open_positions   : {'VAR' if 'max_open_positions' in se else 'YOK'}")
    print(f"  _check_risk_limits   : {'VAR' if '_check_risk_limits' in se else 'YOK'}")
    print(f"  risk_reason cagrisi  : {'VAR' if 'risk_reason' in se else 'YOK'}")
except Exception as e:
    print(f"  HATA: {e}")

# index.html
print()
print("[2] frontend/index.html")
print("-" * 70)
try:
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    print(f"  cfg-daily-max-loss   : {'VAR' if 'cfg-daily-max-loss' in html else 'YOK'}")
    print(f"  cfg-max-open-positions: {'VAR' if 'cfg-max-open-positions' in html else 'YOK'}")
except Exception as e:
    print(f"  HATA: {e}")

# chart.js
print()
print("[3] frontend/chart.js")
print("-" * 70)
try:
    with open('frontend/chart.js', 'r', encoding='utf-8') as f:
        js = f.read()
    print(f"  daily_max_loss yukle  : {'VAR' if 'cfg-daily-max-loss' in js else 'YOK'}")
    print(f"  daily_max_loss kaydet : {'VAR' if 'daily_max_loss:' in js else 'YOK'}")
    print(f"  max_open_positions    : {'VAR' if 'max_open_positions:' in js else 'YOK'}")
except Exception as e:
    print(f"  HATA: {e}")

# bot_config.json
print()
print("[4] backend/bot_config.json")
print("-" * 70)
try:
    import json
    with open('backend/bot_config.json', 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    print(f"  daily_max_loss      = {cfg.get('daily_max_loss', 'YOK')}")
    print(f"  max_open_positions  = {cfg.get('max_open_positions', 'YOK')}")
except Exception as e:
    print(f"  HATA: {e}")

print()
print("=" * 70)