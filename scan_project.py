import os

print("=" * 75)
print("PROJE KLASORU TARAMASI")
print("=" * 75)
print()

# Kok dizin
ROOT = '.'
skip_dirs = {'__pycache__', '.git', 'venv', 'env', '.venv', 'node_modules', '.idea', '.vscode'}

# Kategoriler
cat_backend = []
cat_frontend = []
cat_patch = []
cat_check = []
cat_backup = []
cat_config = []
cat_other = []

for root, dirs, files in os.walk(ROOT):
    # Gizli ve gereksiz klasorleri atla
    dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
    
    # Kok dizini atla, sadece icerikleri isle
    for f in files:
        full = os.path.join(root, f)
        rel = os.path.relpath(full, ROOT)
        
        # Kategorize et
        if f.endswith('.bak_') or '.bak_' in f:
            cat_backup.append(rel)
        elif f.startswith('patch_') and f.endswith('.py'):
            cat_patch.append(rel)
        elif f.startswith('check_') and f.endswith('.py'):
            cat_check.append(rel)
        elif rel.startswith('backend' + os.sep) and not f.endswith('.bak_') and '.bak_' not in f:
            cat_backend.append(rel)
        elif rel.startswith('frontend' + os.sep) and not f.endswith('.bak_') and '.bak_' not in f:
            cat_frontend.append(rel)
        elif f in ('.gitignore', '.env', '.env.example', 'README.md', 'requirements.txt'):
            cat_config.append(rel)
        elif f.endswith('.py') or f.endswith('.json') or f.endswith('.txt'):
            cat_other.append(rel)

def print_category(name, items, icon=""):
    print(f"\n{icon} {name} ({len(items)} dosya)")
    print("-" * 75)
    if not items:
        print("  (bos)")
    else:
        for item in sorted(items):
            size = os.path.getsize(item) if os.path.exists(item) else 0
            size_str = f"{size:>8} B" if size < 1024 else f"{size/1024:>7.1f} KB"
            print(f"  {size_str}  {item}")

# 1. KOK DIZIN
print("=" * 75)
print("1. KOK DIZIN DOSYALARI")
print("=" * 75)
root_files = [f for f in os.listdir(ROOT) if os.path.isfile(f)]
for f in sorted(root_files):
    size = os.path.getsize(f)
    size_str = f"{size:>8} B" if size < 1024 else f"{size/1024:>7.1f} KB"
    print(f"  {size_str}  {f}")

# 2. BACKEND
print_category("2. BACKEND DOSYALARI", cat_backend, "📁")

# 3. FRONTEND
print_category("3. FRONTEND DOSYALARI", cat_frontend, "📁")

# 4. YEDEK DOSYALAR
print_category("4. YEDEK DOSYALAR (.bak_*)", cat_backup, "💾")

# 5. PATCH SCRIPT'LERI
print_category("5. PATCH SCRIPT'LERI", cat_patch, "🔧")

# 6. CHECK SCRIPT'LERI
print_category("6. CHECK SCRIPT'LERI", cat_check, "🔍")

# 7. DIGER SCRIPT'LER
print_category("7. DIGER PY/JSON/TXT DOSYALARI", cat_other, "📄")

# 8. CONFIG
print_category("8. CONFIG DOSYALARI", cat_config, "⚙️")

# OZET
print()
print("=" * 75)
print("OZET")
print("=" * 75)
print(f"  Backend:        {len(cat_backend):>4} dosya")
print(f"  Frontend:       {len(cat_frontend):>4} dosya")
print(f"  Yedek:          {len(cat_backup):>4} dosya")
print(f"  Patch script:   {len(cat_patch):>4} dosya")
print(f"  Check script:   {len(cat_check):>4} dosya")
print(f"  Diger:          {len(cat_other):>4} dosya")
print(f"  Config:         {len(cat_config):>4} dosya")
print(f"  {'-'*40}")
print(f"  TOPLAM:         {len(cat_backend)+len(cat_frontend)+len(cat_backup)+len(cat_patch)+len(cat_check)+len(cat_other)+len(cat_config)+len(root_files):>4} dosya")
print("=" * 75)
print()
print("Bu ciktiyi kopyala, asistan'a gonder.")
print("=" * 75)