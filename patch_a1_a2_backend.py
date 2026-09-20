import shutil
import os

SE_SRC = 'backend/strategy_engine.py'

if not os.path.exists(SE_SRC):
    print(f"[HATA] {SE_SRC} bulunamadi")
    exit(1)

shutil.copy2(SE_SRC, SE_SRC + '.bak_a1_a2')
print(f"[1/4] Yedek: {SE_SRC}.bak_a1_a2")

changes = 0

with open(SE_SRC, 'r', encoding='utf-8', newline='') as f:
    se = f.read().replace('\r\n', '\n')

# ============================================================
# 1. DEFAULT_CONFIG: 2 yeni alan
# ============================================================
old1 = '''    "max_symbols": 30,
    "useLimitOrder": True,'''

new1 = '''    "max_symbols": 30,
    "daily_max_loss": 0,
    "max_open_positions": 0,
    "useLimitOrder": True,'''

if 'daily_max_loss' in se:
    print("[2/4] DEFAULT_CONFIG: alanlar zaten var (atlandi)")
elif old1 in se:
    se = se.replace(old1, new1, 1)
    changes += 1
    print("[2/4] DEFAULT_CONFIG: daily_max_loss + max_open_positions eklendi")
else:
    # Alternatif cipa
    old1b = '''    "max_symbols": 30,
    "strategies": {'''
    new1b = '''    "max_symbols": 30,
    "daily_max_loss": 0,
    "max_open_positions": 0,
    "strategies": {'''
    if old1b in se:
        se = se.replace(old1b, new1b, 1)
        changes += 1
        print("[2/4] DEFAULT_CONFIG: 2 alan eklendi (fallback cipa)")
    else:
        print("[2/4] HATA: DEFAULT_CONFIG cipa bulunamadi!")

# ============================================================
# 2. _check_risk_limits metodu
# ============================================================
old2 = '''    def get_all_open_positions(self) -> list:
        """Tum acik pozisyonlari dondurur."""
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM active_trades").fetchall()
        conn.close()
        return [dict(r) for r in rows]'''

new2 = old2 + '''

    # ------------------------------------------------------------------
    # A1/A2: RISK LIMIT KONTROLU
    # ------------------------------------------------------------------
    def _check_risk_limits(self) -> str:
        """
        A1: Gunluk max zarar limiti (TR saatine gore)
        A2: Max acik pozisyon sayisi
        Ihlal varsa sebep string'i, yoksa bos string doner.
        """
        cfg = self.config or {}

        # --- A2: Max acik pozisyon ---
        try:
            max_open = int(cfg.get("max_open_positions", 0) or 0)
        except Exception:
            max_open = 0

        if max_open > 0:
            try:
                conn = get_db_connection()
                row = conn.execute("SELECT COUNT(*) as c FROM active_trades").fetchone()
                conn.close()
                cnt = row["c"] if row else 0
                if cnt >= max_open:
                    return f"Max acik pozisyon limiti ({cnt}/{max_open})"
            except Exception as e:
                print(f"[RISK] A2 kontrol hatasi: {e}")

        # --- A1: Gunluk max zarar (TR saati = UTC+3) ---
        try:
            max_loss = float(cfg.get("daily_max_loss", 0) or 0)
        except Exception:
            max_loss = 0.0

        if max_loss > 0:
            try:
                conn = get_db_connection()
                row = conn.execute("""
                    SELECT COALESCE(SUM(pnl_amount), 0) as total
                    FROM trade_history
                    WHERE DATE(exit_time + 10800, 'unixepoch') = DATE('now', '+3 hours')
                """).fetchone()
                conn.close()
                today_pnl = float(row["total"]) if row else 0.0
                if today_pnl <= -max_loss:
                    return f"Gunluk max zarar limiti ({today_pnl:.2f}/{max_loss:.2f} USDT)"
            except Exception as e:
                print(f"[RISK] A1 kontrol hatasi: {e}")

        return ""'''

if '_check_risk_limits' in se:
    print("[3/4] _check_risk_limits zaten var (atlandi)")
elif old2 in se:
    se = se.replace(old2, new2, 1)
    changes += 1
    print("[3/4] _check_risk_limits metodu eklendi")
else:
    print("[3/4] HATA: get_all_open_positions cipa bulunamadi!")

# ============================================================
# 3. _process_symbol_locked: sinyal acmadan once risk kontrolu
# ============================================================
old3 = '''                # ⚡ Emir aç
                if self.order_manager:
                    side = "BUY" if result["signal"] == "LONG" else "SELL"'''

new3 = '''                # ⚡ A1/A2: Risk limit kontrolu
                risk_reason = self._check_risk_limits()
                if risk_reason:
                    print(f"[RISK] {symbol} sinyal atlandi: {risk_reason}")
                    self._save_signal_to_db(
                        signal_id, symbol, strategy_name, result["signal"],
                        current_price, qty, base_order, candle_time, created_ms,
                        opened=0, skip_reason=risk_reason
                    )
                    self.last_signal_candle[signal_key] = candle_time
                    return

                # ⚡ Emir aç
                if self.order_manager:
                    side = "BUY" if result["signal"] == "LONG" else "SELL"'''

if 'risk_reason = self._check_risk_limits()' in se:
    print("[4/4] Risk kontrolu zaten var (atlandi)")
elif old3 in se:
    se = se.replace(old3, new3, 1)
    changes += 1
    print("[4/4] Risk kontrolu _process_symbol_locked'a eklendi")
else:
    print("[4/4] HATA: Emir acma blogu bulunamadi!")

with open(SE_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(se.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("SIMDI YAPILACAKLAR:")
print("  1. Backend --reload otomatik yukler")
print()
print("Geri donmek icin:")
print(f"  Copy-Item {SE_SRC}.bak_a1_a2 {SE_SRC} -Force")