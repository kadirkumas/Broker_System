import os
import time
import asyncio
import contextlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from starlette.staticfiles import StaticFiles as StarletteStaticFiles
from binance.client import Client
from dotenv import load_dotenv

# ----------------------------------------------------------------------
# .ENV DOSYASI
# ----------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

print(f"[*] .env dosyası aranıyor: {ENV_PATH}")
print(f"[*] .env var mı: {ENV_PATH.exists()}")

if not ENV_PATH.exists():
    raise RuntimeError(
        f"HATA: .env dosyası bulunamadı!\n"
        f"Beklenen konum: {ENV_PATH}\n"
        f"Lütfen proje kök klasöründe .env dosyası oluşturun."
    )

load_dotenv(dotenv_path=ENV_PATH, override=True)

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
USE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"

print(f"[*] API_KEY yüklendi mi: {'EVET' if API_KEY else 'HAYIR'}")
print(f"[*] API_SECRET yüklendi mi: {'EVET' if API_SECRET else 'HAYIR'}")
print(f"[*] Testnet modu: {USE_TESTNET}")

if not API_KEY or not API_SECRET:
    raise RuntimeError("HATA: .env dosyasında BINANCE_API_KEY veya BINANCE_API_SECRET eksik!")

# ----------------------------------------------------------------------
# BACKEND MODÜLLERİ
# ----------------------------------------------------------------------
from backend.strategy_engine import StrategyEngine, load_config, save_config
from backend.order_manager import OrderManager
from backend.position_manager import PositionManager
from backend.database import init_db, get_db_connection

# ----------------------------------------------------------------------
# BINANCE CLIENT + MOTORLAR
# ----------------------------------------------------------------------
client = Client(API_KEY, API_SECRET, testnet=USE_TESTNET)
order_manager = OrderManager(client, symbol="BTCUSDT", test_mode=True)
position_manager = PositionManager(client, order_manager=order_manager)
bot = StrategyEngine(client, order_manager=order_manager, position_manager=position_manager)


# ----------------------------------------------------------------------
# SUNUCU YAŞAM DÖNGÜSÜ
# ----------------------------------------------------------------------
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(bot.start())
    try:
        yield
    finally:
        bot.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


# ----------------------------------------------------------------------
# FASTAPI
# ----------------------------------------------------------------------
app = FastAPI(title="Broker System API", lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


class NoCacheStaticFiles(StarletteStaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app.mount("/static", NoCacheStaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ----------------------------------------------------------------------
# TEMEL
# ----------------------------------------------------------------------
@app.get("/")
async def read_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/favicon.ico")
async def favicon():
    """Tarayıcının otomatik istediği favicon.ico'yu SVG'ye yönlendirir."""
    return RedirectResponse(url="/static/favicon.svg")


# ----------------------------------------------------------------------
# CÜZDAN
# ----------------------------------------------------------------------
@app.get("/api/wallet")
async def get_wallet():
    try:
        assets = []
        total_usdt = 0.0
        available_usdt = 0.0

        try:
            futures_balances = client.futures_account_balance()
            for b in futures_balances:
                bal = float(b.get('balance', 0))
                avail = float(b.get('withdrawAvailable', b.get('availableBalance', 0)))
                asset = b.get('asset', '')
                if asset == 'USDT':
                    total_usdt += bal
                    available_usdt += avail
                if bal > 0 or avail > 0:
                    assets.append({
                        "coin": asset,
                        "wallet_type": "Vadeli",
                        "balance": f"{bal:.4f}" if bal < 1 else f"{bal:.2f}",
                        "available": f"{avail:.4f}" if avail < 1 else f"{avail:.2f}"
                    })
        except Exception as e:
            print(f"[!] Futures bakiye okuma hatası: {e}")

        try:
            spot_account = client.get_account()
            for b in spot_account.get('balances', []):
                free = float(b.get('free', 0))
                locked = float(b.get('locked', 0))
                total = free + locked
                if total > 0.0001:
                    assets.append({
                        "coin": b.get('asset', ''),
                        "wallet_type": "Spot",
                        "balance": f"{total:.4f}" if total < 1 else f"{total:.2f}",
                        "available": f"{free:.4f}" if free < 1 else f"{free:.2f}"
                    })
        except Exception as e:
            print(f"[!] Spot bakiye okuma hatası: {e}")

        return {
            "status": "success",
            "balance": round(total_usdt, 2),
            "available": round(available_usdt, 2),
            "assets": assets
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ----------------------------------------------------------------------
# BOT STATUS
# ----------------------------------------------------------------------
@app.get("/api/bot/status")
async def get_bot_status():
    return bot.get_status()


# ----------------------------------------------------------------------
# STRATEJİ MOTORU ENDPOINT'LERİ
# ----------------------------------------------------------------------
@app.get("/api/engine/status")
async def engine_status():
    return bot.get_status()


@app.get("/api/engine/signals")
async def engine_signals():
    return bot.latest_signals


@app.get("/api/engine/config")
async def get_engine_config():
    return bot.config


@app.post("/api/engine/config")
async def update_engine_config(new_cfg: dict):
    save_config(new_cfg)
    bot.config = new_cfg
    return {"status": "success", "config": new_cfg}


@app.post("/api/engine/toggle")
async def toggle_engine(active: bool = True, force: bool = False):
    """Motoru açar/kapatır. Kapatırken açık pozisyon uyarısı verir."""
    cfg = load_config()

    if not active and not force:
        conn = get_db_connection()
        count = conn.execute("SELECT COUNT(*) as c FROM active_trades").fetchone()["c"]
        conn.close()
        if count > 0:
            return {
                "status": "warning",
                "active_positions": count,
                "message": f"{count} açık pozisyon var. force=true ile zorla kapatabilirsiniz."
            }

    cfg["active"] = active
    save_config(cfg)
    bot.config = cfg
    print(f"[*] Strateji motoru {'AKTİF' if active else 'PASİF'} edildi.")
    return {"status": "success", "active": active}


@app.post("/api/engine/symbols/refresh")
async def refresh_symbols():
    await bot.refresh_symbol_list()
    return {"status": "success", "symbols_count": len(bot.symbols)}


# ----------------------------------------------------------------------
# SON SİNYALLER (DB'den — kalıcı)
# ----------------------------------------------------------------------
@app.get("/api/engine/recent-signals")
async def get_recent_signals(limit: int = 100):
    """
    Sinyaller + kapanan işlemleri birleşik döner.
    Her kayıt event_type: "signal" | "close"
    Timestamp DESC sıralı.
    """
    conn = get_db_connection()
    
    # Açılan sinyaller
    signals_rows = conn.execute(
        """SELECT signal_id as id, symbol, strategy_name as strategy, signal, 
                  price, qty, total_usdt, candle_time, created_at, 
                  opened_position, skip_reason
           FROM signals 
           ORDER BY created_at DESC 
           LIMIT ?""",
        (limit,)
    ).fetchall()
    
    # Kapanan işlemler
    closes_rows = conn.execute(
        """SELECT id, symbol, trade_type, total_vol, entry_price, exit_price,
                  pnl_amount, pnl_pct, entry_time, exit_time, strategy_name,
                  dca_count, close_reason, leverage
           FROM trade_history 
           ORDER BY exit_time DESC 
           LIMIT ?""",
        (limit,)
    ).fetchall()
    
    conn.close()
    
    result = []
    
    # Sinyalleri işle
    for r in signals_rows:
        d = dict(r)
        d["event_type"] = "signal"
        d["display_symbol"] = d["symbol"] + ".P"
        d["timestamp"] = d.get("created_at", 0)
        result.append(d)
    
    # Kapanışları işle
    for r in closes_rows:
        d = dict(r)
        d["event_type"] = "close"
        d["display_symbol"] = d["symbol"] + ".P"
        d["timestamp"] = (d.get("exit_time") or 0) * 1000  # saniye → ms
        d["signal"] = "LONG" if d.get("trade_type") == "BUY" else "SHORT"
        result.append(d)
    
    # Timestamp DESC sırala
    result.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    
    return result[:limit]


# ----------------------------------------------------------------------
# MANUEL EMİR
# ----------------------------------------------------------------------
@app.post("/api/trade/open")
async def trigger_trade(symbol: str = "BTCUSDT", side: str = "BUY"):
    clean_symbol = symbol.replace(".P", "")
    order_manager.symbol = clean_symbol
    result = order_manager.open_dca_position(side=side, base_amount_usdt=10.0,
                                              strategy_name="MANUAL")
    return result


@app.post("/api/trade/close")
async def trigger_close(symbol: str = "BTCUSDT"):
    clean_symbol = symbol.replace(".P", "")
    result = order_manager.close_position(symbol=clean_symbol)
    return result


@app.post("/api/trade/close-all")
async def close_all_trades():
    conn = get_db_connection()
    trades = conn.execute("SELECT symbol FROM active_trades").fetchall()
    conn.close()
    results = []
    for t in trades:
        r = order_manager.close_position(symbol=t["symbol"])
        results.append({"symbol": t["symbol"], "result": r.get("status")})
    return {"status": "success", "closed": len(results), "details": results}


@app.get("/api/trade/active")
async def get_active_trades():
    conn = get_db_connection()
    trades = conn.execute("SELECT * FROM active_trades").fetchall()
    conn.close()
    return [dict(t) for t in trades]


@app.get("/api/trade/history")
async def get_trade_history(limit: int = 100):
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM trade_history ORDER BY exit_time DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ----------------------------------------------------------------------
# STRATEJİ İSTATİSTİKLERİ
# ----------------------------------------------------------------------
@app.get("/api/stats/strategies")
async def get_strategy_stats():
    """
    Her stratejinin performansı:
    - Toplam işlem
    - Kazanç/kayıp sayısı
    - Win rate
    - Toplam net PNL
    - Ort. PNL %
    - En iyi / en kötü işlem
    """
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT 
            COALESCE(strategy_name, 'UNKNOWN') as strategy_name,
            COUNT(*) as total_trades,
            SUM(CASE WHEN pnl_amount > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl_amount <= 0 THEN 1 ELSE 0 END) as losses,
            ROUND(SUM(pnl_amount), 4) as total_pnl,
            ROUND(AVG(pnl_pct), 4) as avg_pnl_pct,
            ROUND(MAX(pnl_amount), 4) as best_trade,
            ROUND(MIN(pnl_amount), 4) as worst_trade,
            ROUND(AVG(dca_count), 2) as avg_dca
        FROM trade_history
        GROUP BY strategy_name
        ORDER BY total_pnl DESC
    """).fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        total = d["total_trades"] or 0
        wins = d["wins"] or 0
        d["win_rate"] = round((wins / total) * 100, 2) if total > 0 else 0
        result.append(d)
    return result


@app.get("/api/stats/daily")
async def get_daily_stats(days: int = 7):
    """
    Son N günün günlük PNL özeti.
    TÜRKİYE SAATİ (UTC+3) kullanır - frontend ile uyumlu.
    """
    conn = get_db_connection()
    # ⚡ +3 saat ekleyip TR saat dilimine göre grupluyoruz
    rows = conn.execute("""
        SELECT 
            DATE(exit_time + 10800, 'unixepoch') as date,
            COUNT(*) as trades,
            ROUND(SUM(pnl_amount), 4) as net_pnl,
            SUM(CASE WHEN pnl_amount > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl_amount <= 0 THEN 1 ELSE 0 END) as losses
        FROM trade_history
        WHERE exit_time >= ?
        GROUP BY DATE(exit_time + 10800, 'unixepoch')
        ORDER BY date DESC
    """, (int(time.time()) - (days * 86400),)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/stats/signals")
async def get_signal_stats():
    """Sinyal istatistikleri + tutarlılık kontrolü."""
    conn = get_db_connection()
    total = conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
    opened = conn.execute("SELECT COUNT(*) FROM signals WHERE opened_position = 1").fetchone()[0]
    skipped = conn.execute("SELECT COUNT(*) FROM signals WHERE opened_position = 0").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM active_trades").fetchone()[0]
    closed = conn.execute("SELECT COUNT(*) FROM trade_history").fetchone()[0]
    conn.close()
    
    consistent = (opened == active + closed)
    
    return {
        "total_signals": total,
        "opened_signals": opened,
        "skipped_signals": skipped,
        "active_positions": active,
        "closed_positions": closed,
        "sum_check": active + closed,
        "consistent": consistent,
        "difference": opened - (active + closed)
    }


@app.post("/api/stats/reset")
async def reset_stats():
    """Tüm istatistik verilerini sıfırlar (test için)."""
    conn = get_db_connection()
    conn.execute("DELETE FROM trade_history")
    conn.execute("DELETE FROM signals")
    conn.commit()
    conn.close()
    return {"status": "success", "message": "İstatistik verileri sıfırlandı"}

# ----------------------------------------------------------------------
# ADMIN - TÜM VERİYİ SIFIRLA (test için)
# ----------------------------------------------------------------------
@app.post("/api/admin/reset-all")
async def admin_reset_all():
    """
    Test amaçlı: tüm sinyalleri, açık pozisyonları ve işlem geçmişini siler.
    DB'yi tertemiz başlatır.
    """
    conn = get_db_connection()
    
    # Sayıları al
    counts = {
        "signals": conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0],
        "active_trades": conn.execute("SELECT COUNT(*) FROM active_trades").fetchone()[0],
        "trade_history": conn.execute("SELECT COUNT(*) FROM trade_history").fetchone()[0],
    }
    
    # Sil
    conn.execute("DELETE FROM signals")
    conn.execute("DELETE FROM active_trades")
    conn.execute("DELETE FROM trade_history")
    conn.commit()
    conn.close()
    
    print(f"[ADMIN] Sıfırlama: {counts['signals']} sinyal, {counts['active_trades']} pozisyon, {counts['trade_history']} geçmiş silindi")
    
    return {"status": "success", "cleared": counts}

# ----------------------------------------------------------------------
# ADMIN - ANORMAL ISLEMLERI TEMIZLE
# Testnet fiyat hatalarindan kaynaklanan bozuk kayitlari siler
# ----------------------------------------------------------------------
@app.post("/api/admin/clean-anomalies")
async def admin_clean_anomalies(min_pnl_pct: float = 30.0, min_ratio: float = 1.5):
    """
    Testnet fiyat hatasi kaynakli anormal islemleri siler.
    
    Args:
        min_pnl_pct: Bu yuzdeden fazla (mutlak deger) kâr/zarar = anormal
        min_ratio: exit/entry orani bu degerin disindaysa = anormal
    """
    conn = get_db_connection()
    
    # Once anormal kayitlari bul (rapor icin)
    rows = conn.execute("""
        SELECT id, symbol, entry_price, exit_price, pnl_pct
        FROM trade_history
        WHERE ABS(pnl_pct) > ?
           OR (entry_price > 0 AND (
                (exit_price / entry_price) > ?
                OR (exit_price / entry_price) < ?
           ))
    """, (min_pnl_pct, min_ratio, 1.0 / min_ratio)).fetchall()
    
    anomalies = [dict(r) for r in rows]
    
    # Sil
    conn.execute("""
        DELETE FROM trade_history
        WHERE ABS(pnl_pct) > ?
           OR (entry_price > 0 AND (
                (exit_price / entry_price) > ?
                OR (exit_price / entry_price) < ?
           ))
    """, (min_pnl_pct, min_ratio, 1.0 / min_ratio))
    
    conn.commit()
    conn.close()
    
    print(f"[ADMIN] {len(anomalies)} anormal islem silindi")
    for a in anomalies[:10]:
        print(f"      - {a['symbol']}: giris={a['entry_price']}, cikis={a['exit_price']}, pnl={a['pnl_pct']:.2f}%")
    
    return {
        "status": "success",
        "deleted_count": len(anomalies),
        "deleted": anomalies[:50]
    }

# ----------------------------------------------------------------------
# FUNDING RATE - Anlık funding oranı ve sonraki zaman
# ----------------------------------------------------------------------
@app.get("/api/funding/{symbol}")
async def get_funding(symbol: str):
    """Sembol icin anlik funding oranini ve sonraki funding zamanini doner."""
    try:
        premium = client.futures_mark_price(symbol=symbol)
        funding_rate = float(premium.get("lastFundingRate", 0))
        next_funding_time = int(premium.get("nextFundingTime", 0))
        mark_price = float(premium.get("markPrice", 0))
        
        # 8 saatlik funding maliyeti (pozisyon basina)
        daily_funding_pct = funding_rate * 3 * 100  # gunde 3 kez
        
        return {
            "status": "success",
            "symbol": symbol,
            "funding_rate": funding_rate,
            "funding_rate_pct": round(funding_rate * 100, 4),
            "daily_funding_pct": round(daily_funding_pct, 4),
            "next_funding_time": next_funding_time,
            "mark_price": mark_price,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/funding-batch")
async def get_funding_batch(symbols: str = ""):
    """Birden fazla sembol icin funding oranlarini toplu doner."""
    try:
        premiums = client.futures_mark_price()
        symbol_set = set(s.strip().upper() for s in symbols.split(",") if s.strip())
        
        result = {}
        for p in premiums:
            sym = p.get("symbol", "")
            if not symbol_set or sym in symbol_set:
                result[sym] = {
                    "funding_rate": float(p.get("lastFundingRate", 0)),
                    "next_funding_time": int(p.get("nextFundingTime", 0)),
                    "mark_price": float(p.get("markPrice", 0)),
                }
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ----------------------------------------------------------------------
# KOMISYON ORANI - Sembol icin gercek taker/maker orani
# ----------------------------------------------------------------------
@app.get("/api/commission/{symbol}")
async def get_commission(symbol: str):
    """Sembol icin gercek komisyon oranini doner (VIP + BNB dahil)."""
    try:
        rates = order_manager.get_commission_rate(symbol)
        return {
            "status": "success",
            "symbol": symbol,
            "taker": rates.get("taker", 0.0004),
            "maker": rates.get("maker", 0.0002),
            "taker_pct": round(rates.get("taker", 0.0004) * 100, 4),
            "maker_pct": round(rates.get("maker", 0.0002) * 100, 4),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ----------------------------------------------------------------------
# İŞLEM GEÇMİŞİ - KALICI SİLME (frontend + DB)
# ----------------------------------------------------------------------
@app.delete("/api/trade/history/{trade_id}")
async def delete_trade_history(trade_id: int):
    """
    Belirtilen işlem kaydını DB'den kalıcı olarak siler.
    Frontend'deki kullanıcı 'X' butonuyla tetikler.
    """
    conn = get_db_connection()
    row = conn.execute("SELECT id, symbol FROM trade_history WHERE id = ?", (trade_id,)).fetchone()
    
    if not row:
        conn.close()
        return {"status": "error", "message": "İşlem bulunamadı"}
    
    symbol = row["symbol"]
    conn.execute("DELETE FROM trade_history WHERE id = ?", (trade_id,))
    conn.commit()
    conn.close()
    
    print(f"[DELETE] İşlem #{trade_id} ({symbol}) kalıcı olarak silindi")
    
    return {"status": "success", "deleted_id": trade_id, "symbol": symbol}
