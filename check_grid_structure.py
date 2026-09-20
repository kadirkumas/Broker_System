import os

print("=" * 70)
print("GRID STRATEGY - YAPI KONTROLU")
print("=" * 70)
print()

# ============ 1. strategies/ klasoru ============
print("[1] strategies/ klasoru")
print("-" * 70)
if os.path.exists('backend/strategies'):
    for f in sorted(os.listdir('backend/strategies')):
        full = os.path.join('backend/strategies', f)
        size = os.path.getsize(full) if os.path.isfile(full) else 0
        print(f"  {f:<30} {size} bytes")
else:
    print("  KLASOR YOK!")

# ============ 2. strategies/__init__.py ============
print()
print("[2] strategies/__init__.py icerigi")
print("-" * 70)
try:
    with open('backend/strategies/__init__.py', 'r', encoding='utf-8') as f:
        content = f.read()
    for i, line in enumerate(content.split('\n'), 1):
        if line.strip():
            print(f"  {i:3}: {line}")
except Exception as e:
    print(f"  HATA: {e}")

# ============ 3. Mevcut GRIDBOT strateji dosyasi ============
print()
print("[3] Mevcut GRIDBOT stratejisi (varsa)")
print("-" * 70)
grid_files = ['gridbot.py', 'grid_strategy.py', 'grid.py', 'gridbot_scalper.py']
found_grid = None
for gf in grid_files:
    p = f'backend/strategies/{gf}'
    if os.path.exists(p):
        found_grid = p
        print(f"  BULUNDU: {p}")
        with open(p, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')
        # Sinif adi ve metotlari goster
        for i, line in enumerate(lines, 1):
            if 'class ' in line or 'def ' in line:
                print(f"    {i:4}: {line.strip()[:100]}")
        break

if not found_grid:
    print("  GRIDBOT dosyasi bulunamadi!")

# ============ 4. strategy_engine.py - _create_strategy ============
print()
print("[4] strategy_engine.py: _create_strategy metodu")
print("-" * 70)
try:
    with open('backend/strategy_engine.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    idx = content.find('def _create_strategy')
    if idx > 0:
        end = content.find('\n\n', idx + 200)
        block = content[idx:end]
        for i, line in enumerate(block.split('\n'), 1):
            print(f"  {i:3}: {line}")
except Exception as e:
    print(f"  HATA: {e}")

# ============ 5. strategy_engine.py - import satirlari ============
print()
print("[5] strategy_engine.py: import satirlari")
print("-" * 70)
try:
    with open('backend/strategy_engine.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    for line in content.split('\n')[:30]:
        if 'import' in line and 'strateg' in line.lower():
            print(f"  {line}")
except Exception as e:
    print(f"  HATA: {e}")

# ============ 6. bot_config.json GRIDBOT ============
print()
print("[6] bot_config.json: GRIDBOT ayarlari")
print("-" * 70)
try:
    import json
    with open('backend/bot_config.json', 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    grid = cfg.get('strategies', {}).get('GRIDBOT', {})
    for k, v in grid.items():
        print(f"  {k:<20} = {v}")
except Exception as e:
    print(f"  HATA: {e}")

# ============ 7. index.html GRIDBOT panel ============
print()
print("[7] index.html: GRIDBOT strateji paneli")
print("-" * 70)
try:
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    idx = content.find('data-strategy="GRIDBOT"')
    if idx > 0:
        # 60 satir goster
        end = content.find('</div>\n                    </div>', idx)
        block = content[idx:idx + 3000]
        lines = block.split('\n')[:60]
        for i, line in enumerate(lines):
            if 'cfg-row' in line or 'strat-param' in line or 'cfg-subtitle' in line or 'cfg-label' in line or 'strategy-body' in line:
                print(f"    {line.strip()[:110]}")
    else:
        print("  GRIDBOT paneli bulunamadi!")
except Exception as e:
    print(f"  HATA: {e}")

print()
print("=" * 70)
print("Bu ciktiyi kopyala, asistan'a gonder")
print("=" * 70)