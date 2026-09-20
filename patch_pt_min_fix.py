import shutil
import os

PM_SRC = 'backend/position_manager.py'

if not os.path.exists(PM_SRC):
    print(f"[HATA] {PM_SRC} bulunamadi")
    exit(1)

shutil.copy2(PM_SRC, PM_SRC + '.bak_pt_min_fix')
print(f"[1/3] Yedek: {PM_SRC}.bak_pt_min_fix")

changes = 0

with open(PM_SRC, 'r', encoding='utf-8', newline='') as f:
    pm = f.read().replace('\r\n', '\n')

# Eski statik deger
old = '''                pt_close_vol = pos["total_vol"] * (pt_percent_val / 100.0)
                MIN_ORDER_USDT = 5.0'''

new = '''                pt_close_vol = pos["total_vol"] * (pt_percent_val / 100.0)
                # ⚡ Test modunda min notional uygulanmaz (gercek emir yok)
                _is_test = bool(getattr(self.order_manager, 'test_mode', False)) if self.order_manager else False
                MIN_ORDER_USDT = 0.5 if _is_test else 5.0'''

if old in pm:
    pm = pm.replace(old, new, 1)
    changes += 1
    print("[2/3] MIN_ORDER_USDT dinamik yapildi")
else:
    print("[2/3] HATA: MIN_ORDER_USDT blogu bulunamadi!")
    exit(1)

# pt_done=1 olmus ve pt_volume=0 olanlari da sifirla (tekrar denenebilsin)
# Bunu runtime'da yapacak mini hook ekle
anchor = '    async def _execute_partial_close(self, symbol: str, exit_price: float, close_vol_usdt: float,'

helper = '''    def _reset_stuck_pt_flags(self):
        """
        Test modunda yanlislikla pt_done=1 yapilmis ama pt_volume=0 olan
        kayitlari geri al (atlanmis kismi TP'ler tekrar denenebilsin).
        """
        try:
            _is_test = bool(getattr(self.order_manager, 'test_mode', False)) if self.order_manager else False
            if not _is_test:
                return
            conn = get_db_connection()
            cur = conn.execute(
                "UPDATE active_trades SET pt_done = 0 WHERE pt_done = 1 AND (pt_volume IS NULL OR pt_volume = 0)"
            )
            cnt = cur.rowcount
            conn.commit()
            conn.close()
            if cnt > 0:
                print(f"[PARTIAL-TP] {cnt} stuck pt_done=0 olarak sifirlandi (test modu)")
        except Exception as e:
            print(f"[PARTIAL-TP] Reset hatasi: {e}")

    async def _execute_partial_close(self, symbol: str, exit_price: float, close_vol_usdt: float,'''

if anchor in pm and '_reset_stuck_pt_flags' not in pm:
    pm = pm.replace(anchor, helper, 1)
    changes += 1
    print("[2/3] _reset_stuck_pt_flags metodu eklendi")

with open(PM_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(pm.replace('\n', '\r\n'))

# strategy_engine.py'ye startup hook ekle
SE_SRC = 'backend/strategy_engine.py'
shutil.copy2(SE_SRC, SE_SRC + '.bak_pt_min_fix')

with open(SE_SRC, 'r', encoding='utf-8', newline='') as f:
    se = f.read().replace('\r\n', '\n')

old_start = '''        await self.refresh_symbol_list()

        self._scan_task = asyncio.create_task(self._scan_loop())'''

new_start = '''        await self.refresh_symbol_list()

        # ⚡ Test modunda yanlislikla kilitlenmis PT flag'lerini temizle
        if self.position_manager and hasattr(self.position_manager, '_reset_stuck_pt_flags'):
            self.position_manager._reset_stuck_pt_flags()

        self._scan_task = asyncio.create_task(self._scan_loop())'''

if old_start in se:
    se = se.replace(old_start, new_start, 1)
    changes += 1
    print("[3/3] strategy_engine.py: startup PT reset hook")
else:
    print("[3/3] UYARI: startup blogu bulunamadi (atlandi)")

with open(SE_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(se.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("YENI OZELLIK:")
print("  - Test modunda MIN_ORDER_USDT = 0.5 (mainnet'te 5.0)")
print("  - Backend baslarken 'stuck' pt_done=1 kayitlar sifirlanir")
print("  - Mevcut FLOCKUSDT pozisyonu icin PT tekrar denenebilir hale gelir")
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend --reload otomatik yukler (veya Ctrl+C + tekrar)")
print("  2. Backend log'unda: '[PARTIAL-TP] N stuck pt_done=0 olarak sifirlandi'")
print("  3. Sonraki tick'te FLOCKUSDT icin PT tetiklenmeli")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {PM_SRC}.bak_pt_min_fix {PM_SRC} -Force")
print(f"  Copy-Item {SE_SRC}.bak_pt_min_fix {SE_SRC} -Force")