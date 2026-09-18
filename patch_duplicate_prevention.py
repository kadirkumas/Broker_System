import shutil
import os
import re

# ============================================================
# DOSYALAR
# ============================================================
DB_SRC = 'backend/database.py'
DB_BAK = 'backend/database.py.bak_dup_prevent'

SE_SRC = 'backend/strategy_engine.py'
SE_BAK = 'backend/strategy_engine.py.bak_dup_prevent'

OM_SRC = 'backend/order_manager.py'
OM_BAK = 'backend/order_manager.py.bak_dup_prevent'

for src in [DB_SRC, SE_SRC, OM_SRC]:
    if not os.path.exists(src):
        print(f"[HATA] {src} bulunamadi")
        exit(1)
    shutil.copy2(src, src + '.bak_dup_prevent')

print(f"[1/5] 3 dosya yedeklendi")

changes = 0

# ============================================================
# 1. DATABASE.PY - UNIQUE constraint ekle + duplicate temizle
# ============================================================
with open(DB_SRC, 'r', encoding='utf-8', newline='') as f:
    db = f.read().replace('\r\n', '\n')

# init_db sonunda duplicate temizleme + UNIQUE index ekle
old = '''    conn.commit()
    conn.close()


def get_db_connection():'''

new = '''    # ⚡ DUPLICATE PREVENTION: symbol bazlı UNIQUE index
    # Önce mevcut duplicate'leri temizle (en eskisini tut)
    try:
        cursor.execute("""
            DELETE FROM active_trades
            WHERE id NOT IN (
                SELECT MIN(id) FROM active_trades GROUP BY symbol
            )
        """)
        deleted = cursor.rowcount
        if deleted > 0:
            print(f"[DB] {deleted} duplicate aktif pozisyon temizlendi")
    except Exception as e:
        print(f"[DB] Duplicate temizleme hatası: {e}")
    
    # UNIQUE index ekle (varsa atla)
    try:
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_active_symbol ON active_trades(symbol)")
        print("[DB] UNIQUE index aktif: symbol")
    except Exception as e:
        print(f"[DB] UNIQUE index hatası: {e}")
    
    conn.commit()
    conn.close()


def get_db_connection():'''

if old in db:
    db = db.replace(old, new, 1)
    changes += 1
    print("[2/5] database.py: UNIQUE index + duplicate temizleme eklendi")
else:
    print("[2/5] UYARI: database.py pattern bulunamadi")

with open(DB_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(db.replace('\n', '\r\n'))

# ============================================================
# 2. STRATEGY_ENGINE.PY - asyncio.Lock (sembol bazlı)
# ============================================================
with open(SE_SRC, 'r', encoding='utf-8', newline='') as f:
    se = f.read().replace('\r\n', '\n')

# __init__'e lock dict ekle
old = '''        self._delisted_symbols_cache = set()
        self._delisted_cache_time = 0'''

new = '''        self._delisted_symbols_cache = set()
        self._delisted_cache_time = 0
        # ⚡ Duplicate prevention: sembol bazlı kilit
        self._symbol_locks = {}'''

if old in se:
    se = se.replace(old, new, 1)
    changes += 1
    print("[3/5] strategy_engine: _symbol_locks eklendi")
else:
    print("[3/5] UYARI: __init__ pattern bulunamadi")

# _get_symbol_lock fonksiyonu ekle
old = '''    # ------------------------------------------------------------------
    # DELIST KONTROLU - acik pozisyonu olan delist sembolleri kapatir
    # ------------------------------------------------------------------'''
new = '''    def _get_symbol_lock(self, symbol: str):
        """Sembol bazlı asyncio.Lock döner (thread-safe)."""
        if symbol not in self._symbol_locks:
            self._symbol_locks[symbol] = asyncio.Lock()
        return self._symbol_locks[symbol]

    # ------------------------------------------------------------------
    # DELIST KONTROLU - acik pozisyonu olan delist sembolleri kapatir
    # ------------------------------------------------------------------'''

if old in se:
    se = se.replace(old, new, 1)
    changes += 1
    print("[3/5] strategy_engine: _get_symbol_lock fonksiyonu eklendi")

# _process_symbol icinde lock kullan
old = '''    async def _process_symbol(self, symbol, strategy_name, strategy, strat_cfg, interval, candle_cache):
        try:
            cache_key = f"{symbol}_{interval}"
            if cache_key in candle_cache:
                candles = candle_cache[cache_key]
            else:
                candles = await self.fetch_candles(symbol, interval, 500)
                candle_cache[cache_key] = candles

            if not candles:
                return

            open_pos = self.get_open_position(symbol)
            result = strategy.evaluate(candles, open_pos)'''

new = '''    async def _process_symbol(self, symbol, strategy_name, strategy, strat_cfg, interval, candle_cache):
        # ⚡ SEMBOL BAZLI KİLİT (race condition engeli)
        lock = self._get_symbol_lock(symbol)
        
        async with lock:
            await self._process_symbol_locked(symbol, strategy_name, strategy, strat_cfg, interval, candle_cache)
    
    async def _process_symbol_locked(self, symbol, strategy_name, strategy, strat_cfg, interval, candle_cache):
        try:
            cache_key = f"{symbol}_{interval}"
            if cache_key in candle_cache:
                candles = candle_cache[cache_key]
            else:
                candles = await self.fetch_candles(symbol, interval, 500)
                candle_cache[cache_key] = candles

            if not candles:
                return

            open_pos = self.get_open_position(symbol)
            result = strategy.evaluate(candles, open_pos)'''

if old in se:
    se = se.replace(old, new, 1)
    changes += 1
    print("[4/5] strategy_engine: _process_symbol lock ile sarıldı")
else:
    print("[4/5] UYARI: _process_symbol pattern bulunamadi")

with open(SE_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(se.replace('\n', '\r\n'))

# ============================================================
# 3. ORDER_MANAGER.PY - emir açmadan önce duplicate kontrol
# ============================================================
with open(OM_SRC, 'r', encoding='utf-8', newline='') as f:
    om = f.read().replace('\r\n', '\n')

# open_dca_position başında duplicate kontrol
old = '''        price_prec, qty_prec = self.get_symbol_precision(self.symbol)
        ticker = self.client.futures_symbol_ticker(symbol=self.symbol)
        current_price = float(ticker['price'])'''

new = '''        # ⚡ SON KONTROL: Aynı sembolde zaten pozisyon var mı? (race condition son savunma)
        conn = get_db_connection()
        existing = conn.execute(
            "SELECT id FROM active_trades WHERE symbol = ?", (self.symbol,)
        ).fetchone()
        conn.close()
        
        if existing:
            print(f"[DUP-PREVENT] {self.symbol} zaten açık pozisyonda! Yeni emir reddedildi.")
            return {
                "status": "duplicate",
                "symbol": self.symbol,
                "message": "Aynı sembolde açık pozisyon var"
            }
        
        price_prec, qty_prec = self.get_symbol_precision(self.symbol)
        ticker = self.client.futures_symbol_ticker(symbol=self.symbol)
        current_price = float(ticker['price'])'''

if old in om:
    om = om.replace(old, new, 1)
    changes += 1
    print("[5/5] order_manager: duplicate savunma eklendi")
else:
    print("[5/5] UYARI: order_manager pattern bulunamadi")

with open(OM_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(om.replace('\n', '\r\n'))

print()
print("=" * 60)
print(f"BASARILI: {changes} degisiklik")
print("=" * 60)
print()
print("3 KATMANLI KORUMA:")
print("  1. DB UNIQUE INDEX: symbol tekrar edemez")
print("  2. asyncio.Lock: Aynı sembole paralel erişim engellenir")
print("  3. order_manager son kontrol: Emir öncesi DB check")
print()
print("AYRICA:")
print("  - Mevcut duplicate'ler otomatik silinecek (en eski tutulur)")
print()
print("Backend'i Ctrl+C ile durdurup yeniden başlat:")
print("  py -m uvicorn backend.main:app --reload")
print()
print("Beklenen ilk açılışta:")
print("  [DB] X duplicate aktif pozisyon temizlendi")
print("  [DB] UNIQUE index aktif: symbol")
print()
print("Geri donmek icin:")
for src in [DB_SRC, SE_SRC, OM_SRC]:
    print(f"  copy /Y {src}.bak_dup_prevent {src}")