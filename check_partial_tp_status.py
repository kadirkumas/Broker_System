import os

print("=" * 65)
print("KISMI TP (PARTIAL TP) KURULU MU? - DURUM KONTROLU")
print("=" * 65)
print()

results = []

# 1. Yedek dosyalari var mi?
files_with_bak = [
    'backend/database.py.bak_partial_tp',
    'backend/strategy_engine.py.bak_partial_tp',
    'backend/order_manager.py.bak_partial_tp',
    'backend/position_manager.py.bak_partial_tp',
    'frontend/index.html.bak_partial_tp',
    'frontend/chart.js.bak_partial_tp',
    'frontend/style.css.bak_partial_tp',
]
bak_count = sum(1 for f in files_with_bak if os.path.exists(f))
results.append(("Yedek dosyalar (.bak_partial_tp)", f"{bak_count}/7", bak_count >= 5))

# 2. database.py: pt_enabled sutunu
try:
    with open('backend/database.py', 'r', encoding='utf-8') as f:
        db = f.read()
    ok = 'pt_enabled' in db and 'pt_done' in db and 'pt_volume' in db
    results.append(("database.py: pt_enabled/pt_done/pt_volume", "VAR" if ok else "YOK", ok))
except Exception as e:
    results.append(("database.py okuma", f"HATA: {e}", False))

# 3. strategy_engine.py: partialTPEnabled
try:
    with open('backend/strategy_engine.py', 'r', encoding='utf-8') as f:
        se = f.read()
    ok = 'partialTPEnabled' in se and 'pt_enabled' in se
    results.append(("strategy_engine.py: partialTPEnabled", "VAR" if ok else "YOK", ok))
except Exception as e:
    results.append(("strategy_engine.py okuma", f"HATA: {e}", False))

# 4. order_manager.py: partial_close_position
try:
    with open('backend/order_manager.py', 'r', encoding='utf-8') as f:
        om = f.read()
    ok = 'def partial_close_position' in om
    results.append(("order_manager.py: partial_close_position()", "VAR" if ok else "YOK", ok))
except Exception as e:
    results.append(("order_manager.py okuma", f"HATA: {e}", False))

# 5. position_manager.py: _execute_partial_close
try:
    with open('backend/position_manager.py', 'r', encoding='utf-8') as f:
        pm = f.read()
    ok = 'async def _execute_partial_close' in pm
    results.append(("position_manager.py: _execute_partial_close()", "VAR" if ok else "YOK", ok))
except Exception as e:
    results.append(("position_manager.py okuma", f"HATA: {e}", False))

# 6. index.html: Kismi TP bolumu
try:
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    ok = 'Kısmi TP' in html and 'partialTPEnabled' in html
    results.append(("index.html: Kismi TP UI bolumu", "VAR" if ok else "YOK", ok))
except Exception as e:
    results.append(("index.html okuma", f"HATA: {e}", False))

# 7. chart.js: PT rozet + tooltip v2
try:
    with open('frontend/chart.js', 'r', encoding='utf-8') as f:
        js = f.read()
    ok1 = 'ptDone' in js or 'pt_done' in js
    ok2 = 'setupCfgTooltipsV2' in js
    results.append(("chart.js: PT rozet (ptDone)", "VAR" if ok1 else "YOK", ok1))
    results.append(("chart.js: Tooltip v2", "VAR" if ok2 else "YOK", ok2))
except Exception as e:
    results.append(("chart.js okuma", f"HATA: {e}", False))

# 8. bot_config.json
try:
    import json
    with open('backend/bot_config.json', 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    rsi = cfg.get('strategies', {}).get('RSI_SCALPER', {})
    ok = 'partialTPEnabled' in rsi
    results.append(("bot_config.json: partialTPEnabled", "VAR" if ok else "YOK", ok))
except Exception as e:
    results.append(("bot_config.json okuma", f"HATA: {e}", False))

# Sonuc tablosu
print(f"{'KONTROL':<50} {'DURUM':<10} {'OK?'}")
print("-" * 65)
for name, val, ok in results:
    icon = "✅" if ok else "❌"
    print(f"{name:<50} {val:<10} {icon}")

print()
print("=" * 65)

passed = sum(1 for _, _, ok in results if ok)
total = len(results)

if passed == total:
    print(f"✅ TAM KURULU: {passed}/{total} - Kismi TP aktif!")
    print("   Test etmeye hazirsin.")
elif passed >= total * 0.7:
    print(f"⚠️  KISMEN KURULU: {passed}/{total}")
    print("   Bazi patch'ler eksik olabilir.")
else:
    print(f"❌ KURULU DEGIL: {passed}/{total}")
    print("   Kismi TP patch'lerini sirayla calistir:")
    print("     1. py patch_partial_tp_backend.py")
    print("     2. py patch_partial_tp_position_manager.py")
    print("     3. py patch_partial_tp_frontend.py")

print("=" * 65)