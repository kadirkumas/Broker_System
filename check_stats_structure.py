print("=" * 70)
print("STATS MODAL YAPISI KONTROLU")
print("=" * 70)
print()

# 1. HTML: stats-tabs
print("[1] frontend/index.html - stats-tabs")
print("-" * 70)
try:
    with open('frontend/index.html', 'r', encoding='utf-8', newline='') as f:
        lines = f.read().replace('\r\n', '\n').split('\n')
    
    for i, line in enumerate(lines):
        if 'stats-tab' in line and 'data-tab' in line:
            print(f"  {i+1:4}: {line.strip()[:100]}")
except Exception as e:
    print(f"  HATA: {e}")

# 2. JS: switchStatsTab
print()
print("[2] frontend/chart.js - switchStatsTab")
print("-" * 70)
try:
    with open('frontend/chart.js', 'r', encoding='utf-8', newline='') as f:
        js = f.read().replace('\r\n', '\n')
    
    # switchStatsTab fonksiyonunu bul
    idx = js.find('window.switchStatsTab = function')
    if idx < 0:
        print("  switchStatsTab bulunamadi!")
    else:
        # 15 satir goster
        end = js.find('};', idx)
        block = js[idx:end + 2]
        for i, line in enumerate(block.split('\n')):
            print(f"  {i+1:4}: {line}")
except Exception as e:
    print(f"  HATA: {e}")

# 3. JS: loadStatsContent (sadece tab case'leri)
print()
print("[3] frontend/chart.js - loadStatsContent tab case'leri")
print("-" * 70)
try:
    with open('frontend/chart.js', 'r', encoding='utf-8', newline='') as f:
        js = f.read().replace('\r\n', '\n')
    
    idx = js.find('window.loadStatsContent = async function')
    if idx < 0:
        print("  loadStatsContent bulunamadi!")
    else:
        # 60 satir goster - tab case'lerini gorelim
        end = js.find('};', idx + 3000)
        block = js[idx:end + 2]
        for i, line in enumerate(block.split('\n')):
            if 'tab ===' in line or 'renderStrategy' in line or 'renderSymbol' in line or 'renderReason' in line or 'content.innerHTML' in line:
                print(f"  {i+1:4}: {line.strip()[:110]}")
except Exception as e:
    print(f"  HATA: {e}")

# 4. JS: Mevcut render fonksiyonlari
print()
print("[4] frontend/chart.js - render fonksiyonlari")
print("-" * 70)
try:
    with open('frontend/chart.js', 'r', encoding='utf-8', newline='') as f:
        js = f.read().replace('\r\n', '\n')
    
    for name in ['renderStrategyStats', 'renderSymbolStats', 'renderReasonStats']:
        print(f"  {name}: {'VAR' if f'window.{name}' in js else 'YOK'}")
except Exception as e:
    print(f"  HATA: {e}")

# 5. main.py: Mevcut stats endpoint'leri
print()
print("[5] backend/main.py - stats endpoint'leri")
print("-" * 70)
try:
    with open('backend/main.py', 'r', encoding='utf-8', newline='') as f:
        main = f.read().replace('\r\n', '\n')
    
    for ep in ['/api/stats/strategies', '/api/stats/symbols', '/api/stats/close-reasons', '/api/stats/symbols-by-count']:
        print(f"  {ep:<35} {'VAR' if ep in main else 'YOK'}")
except Exception as e:
    print(f"  HATA: {e}")

print()
print("=" * 70)