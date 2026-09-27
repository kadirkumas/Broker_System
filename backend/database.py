import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'bot_data.db')


def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    # ⚡ WAL mode aktif et (tek seferlik, kalici)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
    except Exception as e:
        print(f"[DB] WAL init hatasi: {e}")
    cursor = conn.cursor()

    # 1. Açık İşlemler
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS active_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            trade_type TEXT NOT NULL,
            total_vol REAL NOT NULL,
            avg_price REAL NOT NULL,
            dca_count INTEGER DEFAULT 0,
            entry_time INTEGER NOT NULL
        )
    ''')

    # 2. İşlem Geçmişi
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            trade_type TEXT NOT NULL,
            total_vol REAL NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL NOT NULL,
            pnl_amount REAL NOT NULL,
            pnl_pct REAL NOT NULL,
            entry_time INTEGER NOT NULL,
            exit_time INTEGER NOT NULL
        )
    ''')

    # 3. Sinyaller
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT UNIQUE NOT NULL,
            symbol TEXT NOT NULL,
            strategy_name TEXT,
            signal TEXT NOT NULL,
            price REAL NOT NULL,
            qty REAL,
            total_usdt REAL,
            candle_time INTEGER,
            created_at INTEGER NOT NULL
        )
    ''')

    # 4. GRID STATE - Backend grid durumu (tek dogru kaynak)
    # Her recenter'da UPSERT edilir.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grid_state (
            symbol TEXT PRIMARY KEY,
            strategy_name TEXT NOT NULL,
            group_id TEXT,
            reference REAL,
            top REAL,
            bottom REAL,
            levels_json TEXT,
            interval TEXT,
            mode TEXT,
            recenter_ts INTEGER,
            updated_at INTEGER
        )
    ''')

    # MIGRATION: active_trades
    cols_at = [row[1] for row in cursor.execute("PRAGMA table_info(active_trades)").fetchall()]
    migrations_at = {
        "strategy_name": "ALTER TABLE active_trades ADD COLUMN strategy_name TEXT",
        "initial_price": "ALTER TABLE active_trades ADD COLUMN initial_price REAL",
        "initial_vol": "ALTER TABLE active_trades ADD COLUMN initial_vol REAL",
        "leverage": "ALTER TABLE active_trades ADD COLUMN leverage INTEGER DEFAULT 1",
        "pt_enabled": "ALTER TABLE active_trades ADD COLUMN pt_enabled INTEGER DEFAULT 0",
        "pt_percent": "ALTER TABLE active_trades ADD COLUMN pt_percent REAL DEFAULT 50",
        "pt_done": "ALTER TABLE active_trades ADD COLUMN pt_done INTEGER DEFAULT 0",
        "pt_volume": "ALTER TABLE active_trades ADD COLUMN pt_volume REAL DEFAULT 0",
        "pt_pnl": "ALTER TABLE active_trades ADD COLUMN pt_pnl REAL DEFAULT 0",
        "pt_keep_dca": "ALTER TABLE active_trades ADD COLUMN pt_keep_dca INTEGER DEFAULT 1",
        "entry_is_maker": "ALTER TABLE active_trades ADD COLUMN entry_is_maker INTEGER DEFAULT 0",
        "dca_history": "ALTER TABLE active_trades ADD COLUMN dca_history TEXT DEFAULT '[]'",
        # ============= FAZ 2 GRID REEL ALANLARI =============
        # is_grid_position : 0 = klasik DCA, 1 = grid seviye pozisyonu
        # grid_group_id    : ayni grid oturumundaki seviyeleri gruplar (uuid)
        # grid_level       : seviye indeksi (-N..-1=BUY, +1..+N=SELL)
        # grid_side        : "BUY" | "SELL"
        # grid_entry_price : seviyenin tetiklenme fiyati
        # grid_tp_price    : bu seviyenin hedef cikis fiyati (komsu seviye)
        # grid_created_at  : grid recenter zamani (unix sn)
        # grid_state       : "pending" | "open"
        "is_grid_position": "ALTER TABLE active_trades ADD COLUMN is_grid_position INTEGER DEFAULT 0",
        "grid_group_id": "ALTER TABLE active_trades ADD COLUMN grid_group_id TEXT",
        "grid_level": "ALTER TABLE active_trades ADD COLUMN grid_level INTEGER",
        "grid_side": "ALTER TABLE active_trades ADD COLUMN grid_side TEXT",
        "grid_entry_price": "ALTER TABLE active_trades ADD COLUMN grid_entry_price REAL",
        "grid_tp_price": "ALTER TABLE active_trades ADD COLUMN grid_tp_price REAL",
        "grid_created_at": "ALTER TABLE active_trades ADD COLUMN grid_created_at INTEGER",
        "grid_state": "ALTER TABLE active_trades ADD COLUMN grid_state TEXT DEFAULT 'open'",
    }
    for col, sql in migrations_at.items():
        if col not in cols_at:
            try:
                cursor.execute(sql)
                print(f"[DB] active_trades + {col}")
            except Exception as e:
                print(f"[DB] Migration hatası ({col}): {e}")

    # MIGRATION: trade_history
    cols_th = [row[1] for row in cursor.execute("PRAGMA table_info(trade_history)").fetchall()]
    migrations_th = {
        "strategy_name": "ALTER TABLE trade_history ADD COLUMN strategy_name TEXT",
        "dca_count": "ALTER TABLE trade_history ADD COLUMN dca_count INTEGER DEFAULT 0",
        "close_reason": "ALTER TABLE trade_history ADD COLUMN close_reason TEXT",
        "leverage": "ALTER TABLE trade_history ADD COLUMN leverage INTEGER DEFAULT 1",
        "funding_fee": "ALTER TABLE trade_history ADD COLUMN funding_fee REAL DEFAULT 0",
        "is_partial": "ALTER TABLE trade_history ADD COLUMN is_partial INTEGER DEFAULT 0",
        "commission": "ALTER TABLE trade_history ADD COLUMN commission REAL DEFAULT 0",
    }
    for col, sql in migrations_th.items():
        if col not in cols_th:
            try:
                cursor.execute(sql)
                print(f"[DB] trade_history + {col}")
            except Exception as e:
                print(f"[DB] Migration hatası ({col}): {e}")

    # MIGRATION: signals
    cols_sig = [row[1] for row in cursor.execute("PRAGMA table_info(signals)").fetchall()]
    migrations_sig = {
        "opened_position": "ALTER TABLE signals ADD COLUMN opened_position INTEGER DEFAULT 0",
        "skip_reason": "ALTER TABLE signals ADD COLUMN skip_reason TEXT",
    }
    for col, sql in migrations_sig.items():
        if col not in cols_sig:
            try:
                cursor.execute(sql)
                print(f"[DB] signals + {col}")
            except Exception as e:
                print(f"[DB] Migration hatası ({col}): {e}")

    # ==========================================================
    # FAZ 2: CIFT PARTIAL UNIQUE INDEX
    # ----------------------------------------------------------
    # KLASIK : symbol UNIQUE   (is_grid_position=0) -> tek pozisyon
    # GRID   : (symbol+group+level) UNIQUE (is_grid_position=1)
    #          -> ayni sembolde cok seviye ayni anda acik olabilir
    # ==========================================================

    # Eski tek index'i kaldir
    try:
        cursor.execute("DROP INDEX IF EXISTS idx_active_symbol")
        print("[DB] Eski idx_active_symbol kaldirildi")
    except Exception as e:
        print(f"[DB] Eski index drop hatasi: {e}")

    # --- Klasik duplicate temizleme ---
    try:
        cursor.execute("""
            DELETE FROM active_trades
            WHERE id NOT IN (
                SELECT MIN(id) FROM active_trades
                WHERE COALESCE(is_grid_position, 0) = 0
                GROUP BY symbol
            ) AND COALESCE(is_grid_position, 0) = 0
        """)
        d = cursor.rowcount
        if d > 0:
            print(f"[DB] {d} klasik duplicate temizlendi")
    except Exception as e:
        print(f"[DB] Klasik dup temizleme hatasi: {e}")

    # --- Grid duplicate temizleme (group+level) ---
    try:
        cursor.execute("""
            DELETE FROM active_trades
            WHERE id NOT IN (
                SELECT MIN(id) FROM active_trades
                WHERE is_grid_position = 1
                GROUP BY symbol, grid_group_id, grid_level
            ) AND is_grid_position = 1
        """)
        d = cursor.rowcount
        if d > 0:
            print(f"[DB] {d} grid duplicate temizlendi")
    except Exception as e:
        print(f"[DB] Grid dup temizleme hatasi: {e}")

    # --- Klasik UNIQUE: symbol (MANUAL hariç, partial) ---
    try:
        cursor.execute("DROP INDEX IF EXISTS idx_active_classic_symbol")
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_active_classic_symbol
            ON active_trades(symbol)
            WHERE COALESCE(is_grid_position, 0) = 0
              AND (strategy_name IS NULL OR strategy_name != 'MANUAL')
        """)
        print("[DB] UNIQUE index: klasik symbol (MANUAL haric)")
    except Exception as e:
        print(f"[DB] Klasik index hatasi: {e}")

    # --- MANUAL icin ayri UNIQUE: (symbol, id) zaten primary, ek kisit yok ---
    # MANUAL pozisyonlar is_grid_position=0 kullanir, UNIQUE index'ten muaf

    # --- Grid UNIQUE: (symbol+group+level) (partial) ---
    try:
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_active_grid_level
            ON active_trades(symbol, grid_group_id, grid_level)
            WHERE is_grid_position = 1
        """)
        print("[DB] UNIQUE index: grid (symbol+group+level)")
    except Exception as e:
        print(f"[DB] Grid index hatasi: {e}")

    # --- Sorgu performansi: group bazli ---
    try:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_active_grid_group
            ON active_trades(grid_group_id)
            WHERE is_grid_position = 1
        """)
        print("[DB] INDEX: grid_group_id")
    except Exception as e:
        print(f"[DB] Group index hatasi: {e}")
    
    conn.commit()
    conn.close()


def get_db_connection():
    # ⚡ SQLite WAL mode + busy_timeout (concurrent erisim icin)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
    except Exception as e:
        print(f"[DB] PRAGMA hatasi: {e}")
    return conn