import shutil
import os

MAIN_SRC = 'backend/main.py'

if not os.path.exists(MAIN_SRC):
    print(f"[HATA] {MAIN_SRC} bulunamadi")
    exit(1)

shutil.copy2(MAIN_SRC, MAIN_SRC + '.bak_recent_signals_fields')
print(f"[1/3] Yedek: {MAIN_SRC}.bak_recent_signals_fields")

with open(MAIN_SRC, 'r', encoding='utf-8', newline='') as f:
    main = f.read().replace('\r\n', '\n')

old = """        """ + '"""SELECT id, symbol, trade_type, total_vol, entry_price, exit_price,\n                  pnl_amount, pnl_pct, entry_time, exit_time, strategy_name,\n                  dca_count, close_reason, leverage\n           FROM trade_history ' + '"""'

new = """        """ + '"""SELECT id, symbol, trade_type, total_vol, entry_price, exit_price,\n                  pnl_amount, pnl_pct, entry_time, exit_time, strategy_name,\n                  dca_count, close_reason, leverage, is_partial, commission\n           FROM trade_history ' + '"""'

if 'is_partial, commission' in main and 'FROM trade_history' in main:
    print("[2/3] main.py: recent-signals zaten guncel (atlandi)")
elif old in main:
    main = main.replace(old, new, 1)
    print("[2/3] main.py: is_partial + commission eklendi")
else:
    # Daha esnek: sadece 'dca_count, close_reason, leverage\n           FROM trade_history' bul
    old2 = "dca_count, close_reason, leverage\n           FROM trade_history"
    new2 = "dca_count, close_reason, leverage, is_partial, commission\n           FROM trade_history"
    if old2 in main:
        main = main.replace(old2, new2, 1)
        print("[2/3] main.py: is_partial + commission eklendi (fallback)")
    else:
        print("[2/3] HATA: SQL blogu bulunamadi!")
        exit(1)

with open(MAIN_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(main.replace('\n', '\r\n'))

print("[3/3] Kaydedildi")
print()
print("=" * 60)
print("BASARILI")
print("=" * 60)
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend --reload otomatik yukler")
print("  2. Ctrl+Shift+R")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {MAIN_SRC}.bak_recent_signals_fields {MAIN_SRC} -Force")