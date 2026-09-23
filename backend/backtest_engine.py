"""
Backtest Engine - Gecmis veri uzerinde strateji simulasyonu.
Async task olarak calisir, progress raporlanir.
"""
import time
import traceback
from datetime import datetime
from backend.strategies import RSIScalperStrategy, HullSRPStrategy


# In-memory task store
_BACKTEST_TASKS = {}


def create_task(task_id, symbol, strategy, params, initial_balance, interval):
    _BACKTEST_TASKS[task_id] = {
        "task_id": task_id,
        "symbol": symbol,
        "strategy": strategy,
        "params": params,
        "initial_balance": initial_balance,
        "interval": interval,
        "status": "pending",
        "progress": 0,
        "message": "Kuyruga alindi",
        "created_at": time.time(),
        "result": None,
    }


def get_task(task_id):
    return _BACKTEST_TASKS.get(task_id)


def get_strategy(name, params):
    if name == "RSI_SCALPER":
        return RSIScalperStrategy(params)
    elif name == "HULL_SRP":
        return HullSRPStrategy(params)
    return None


def _fetch_all_klines(client, symbol, interval, start_ms, end_ms, mode="futures"):
    """Binance'ten paginated klines ceker. mode: futures | spot"""
    all_klines = []
    current = start_ms
    iters = 0
    max_iters = 300

    fetch_fn = client.futures_klines if mode == "futures" else client.klines

    while current < end_ms and iters < max_iters:
        iters += 1
        try:
            klines = fetch_fn(
                symbol=symbol,
                interval=interval,
                startTime=current,
                endTime=end_ms,
                limit=1500
            )
        except Exception as e:
            print(f"[BT] klines hatasi ({mode}): {e}")
            break

        if not klines:
            break

        all_klines.extend(klines)

        if len(klines) < 1500:
            break

        current = klines[-1][0] + 1
        time.sleep(0.05)

    return all_klines


def _klines_to_candles(klines):
    return [
        {
            "time": int(k[0] / 1000),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        }
        for k in klines
    ]


def _get_listing_date(client, symbol, mode="futures"):
    """Sembolun ilk kline zamanini bulur (ms). mode: futures | spot"""
    try:
        fetch_fn = client.futures_klines if mode == "futures" else client.klines
        klines = fetch_fn(symbol=symbol, interval="1d", startTime=0, limit=1)
        if klines:
            return klines[0][0]
    except Exception as e:
        print(f"[BT] Listing date hatasi ({mode}): {e}")
    return None


def _close_position(pos, exit_price, reason, balance, closed_trades, exit_time):
    is_long = pos["side"] == "BUY"
    if is_long:
        pct = (exit_price - pos["avg_price"]) / pos["avg_price"]
    else:
        pct = (pos["avg_price"] - exit_price) / pos["avg_price"]

    gross = pos["total_vol"] * pct
    exit_comm = pos["total_vol"] * 0.0004
    net = gross - exit_comm

    new_balance = balance + pos["_margin_total"] + net

    closed_trades.append({
        "entry_time": pos["entry_time"],
        "exit_time": exit_time,
        "side": pos["side"],
        "entry_price": round(pos["avg_price"], 8),
        "exit_price": round(exit_price, 8),
        "total_vol": round(pos["total_vol"], 4),
        "pnl_amount": round(net, 4),
        "pnl_pct": round(pct * 100, 4),
        "reason": reason,
        "dca_count": pos["dca_count"],
    })

    pos["_new_balance"] = new_balance


def _partial_close(pos, exit_price, close_vol, balance, closed_trades, exit_time):
    is_long = pos["side"] == "BUY"
    if is_long:
        pct = (exit_price - pos["avg_price"]) / pos["avg_price"]
    else:
        pct = (pos["avg_price"] - exit_price) / pos["avg_price"]

    gross = close_vol * pct
    exit_comm = close_vol * 0.0004
    net = gross - exit_comm

    ratio = close_vol / pos["total_vol"] if pos["total_vol"] > 0 else 0
    partial_margin = pos["_margin_total"] * ratio

    new_balance = balance + partial_margin + net

    closed_trades.append({
        "entry_time": pos["entry_time"],
        "exit_time": exit_time,
        "side": pos["side"],
        "entry_price": round(pos["avg_price"], 8),
        "exit_price": round(exit_price, 8),
        "total_vol": round(close_vol, 4),
        "pnl_amount": round(net, 4),
        "pnl_pct": round(pct * 100, 4),
        "reason": "PARTIAL TP",
        "dca_count": pos["dca_count"],
    })

    pos["total_vol"] -= close_vol
    pos["_margin_total"] -= partial_margin
    pos["_new_balance"] = new_balance


def run_backtest_sync(task_id, client, symbol, strategy_name, params, initial_balance,
                      interval="4h", start_date=None, end_date=None, mode="futures"):
    task = _BACKTEST_TASKS.get(task_id)
    if not task:
        return

    try:
        base_order = float(params.get("baseOrder", 10))
        leverage = max(1, int(params.get("leverage", 1)))
        take_profit = float(params.get("takeProfit", 1.5)) / 100
        trailing = float(params.get("trailing", 0.3)) / 100
        stop_loss = float(params.get("stopLoss", 3.0)) / 100
        use_dca = bool(params.get("useDCA", False))
        vol_mult = float(params.get("volMultiplier", 1.2))
        steps_str = str(params.get("steps", "1.5, 3, 5"))
        steps = [float(s.strip()) for s in steps_str.split(",") if s.strip()]
        pt_enabled = bool(params.get("partialTPEnabled", False))
        pt_percent = float(params.get("partialTPPercent", 50))
        pt_keep_dca = bool(params.get("partialTPKeepDCA", True))
        trade_direction = str(params.get("tradeDirection", "both")).lower()  # long | short | both

        balance = float(initial_balance)
        equity_curve = []
        closed_trades = []
        open_position = None

        task["status"] = "running"
        task["progress"] = 5
        task["message"] = "Baslatiliyor..."

        end_ms = int(time.time() * 1000) if end_date is None else int(end_date)
        if start_date is None:
            task["message"] = "Listing tarihi bulunuyor..."
            start_ms = _get_listing_date(client, symbol, mode)
            if start_ms is None:
                start_ms = end_ms - (365 * 24 * 3600 * 1000)
        else:
            start_ms = int(start_date)

        task["progress"] = 10
        task["message"] = "Klines cekiliyor..."
        klines = _fetch_all_klines(client, symbol, interval, start_ms, end_ms, mode)
        if not klines:
            task["status"] = "error"
            task["message"] = "Veri cekilemedi"
            return

        candles = _klines_to_candles(klines)
        total = len(candles)

        task["progress"] = 20
        task["message"] = f"{total} mum yuklendi"

        strategy = get_strategy(strategy_name, params)
        if strategy is None:
            task["status"] = "error"
            task["message"] = f"Bilinmeyen strateji: {strategy_name}"
            return

        warmup = max(100, int(params.get("smaPeriod", 100)), int(params.get("period", 10)) * 3)
        if warmup >= total:
            task["status"] = "error"
            task["message"] = "Yetersiz veri"
            return

        step_size = max(1, (total - warmup) // 50)

        for i in range(warmup, total):
            candle = candles[i]
            price = candle["close"]

            # --- Acik pozisyon kontrolu ---
            if open_position:
                pos = open_position
                is_long = pos["side"] == "BUY"

                if is_long:
                    pnl_pct = (price - pos["avg_price"]) / pos["avg_price"]
                else:
                    pnl_pct = (pos["avg_price"] - price) / pos["avg_price"]

                # Trailing
                if pos["ttp_active"]:
                    if is_long:
                        if price > pos["hwm"]:
                            pos["hwm"] = price
                        trigger = pos["hwm"] * (1 - trailing)
                        if price <= trigger:
                            _close_position(pos, price, "TRAILING", balance, closed_trades, candle["time"])
                            balance = pos["_new_balance"]
                            open_position = None
                            continue
                    else:
                        if price < pos["hwm"]:
                            pos["hwm"] = price
                        trigger = pos["hwm"] * (1 + trailing)
                        if price >= trigger:
                            _close_position(pos, price, "TRAILING", balance, closed_trades, candle["time"])
                            balance = pos["_new_balance"]
                            open_position = None
                            continue
                else:
                    if pnl_pct >= take_profit:
                        if pt_enabled and not pos["pt_done"]:
                            close_vol = pos["total_vol"] * (pt_percent / 100)
                            _partial_close(pos, price, close_vol, balance, closed_trades, candle["time"])
                            balance = pos["_new_balance"]
                            pos["pt_done"] = 1
                        else:
                            pos["ttp_active"] = True
                            pos["hwm"] = price

                # SL
                if not pos["ttp_active"] and pnl_pct <= -stop_loss:
                    _close_position(pos, price, "STOP LOSS", balance, closed_trades, candle["time"])
                    balance = pos["_new_balance"]
                    open_position = None
                    continue

                # DCA
                if use_dca and not pos["ttp_active"]:
                    if pos["dca_count"] < len(steps):
                        if pt_keep_dca or not pos["pt_done"]:
                            step_pct = steps[pos["dca_count"]] / 100
                            if is_long:
                                trig = pos["initial_price"] * (1 - step_pct)
                                hit = price <= trig
                            else:
                                trig = pos["initial_price"] * (1 + step_pct)
                                hit = price >= trig

                            if hit:
                                new_count = pos["dca_count"] + 1
                                step_vol = base_order * (vol_mult ** new_count)
                                step_margin = step_vol / leverage
                                step_comm = step_vol * 0.0004

                                if balance >= step_margin + step_comm:
                                    balance -= (step_margin + step_comm)
                                    old_total = pos["total_vol"]
                                    old_avg = pos["avg_price"]
                                    new_total = old_total + step_vol
                                    new_avg = ((old_avg * old_total) + (price * step_vol)) / new_total
                                    pos["total_vol"] = new_total
                                    pos["avg_price"] = new_avg
                                    pos["dca_count"] = new_count
                                    pos["_margin_total"] += step_margin

            # --- Yeni sinyal ---
            if open_position is None:
                margin = base_order / leverage
                entry_comm = base_order * 0.0002

                if balance >= margin + entry_comm:
                    window = candles[:i+1]
                    try:
                        result = strategy.evaluate(window, None)
                    except Exception:
                        result = {"signal": None}

                    sig = result.get("signal")

                    # ⚡ Direction filtresi
                    if sig == "LONG" and trade_direction == "short":
                        sig = None
                    elif sig == "SHORT" and trade_direction == "long":
                        sig = None

                    if sig in ("LONG", "SHORT"):
                        balance -= (margin + entry_comm)
                        open_position = {
                            "side": "BUY" if sig == "LONG" else "SELL",
                            "entry_price": price,
                            "initial_price": price,
                            "avg_price": price,
                            "total_vol": base_order,
                            "entry_time": candle["time"],
                            "dca_count": 0,
                            "ttp_active": False,
                            "hwm": None,
                            "pt_done": 0,
                            "_margin_total": margin,
                        }

            # --- Equity ---
            unreal = 0
            if open_position:
                pos = open_position
                is_long = pos["side"] == "BUY"
                if is_long:
                    up = (price - pos["avg_price"]) / pos["avg_price"]
                else:
                    up = (pos["avg_price"] - price) / pos["avg_price"]
                unreal = pos["total_vol"] * up

            equity = balance + unreal + (open_position["_margin_total"] if open_position else 0)
            equity_curve.append({"time": candle["time"], "value": equity})

            if (i - warmup) % step_size == 0:
                pct = 20 + int(70 * (i - warmup) / max(1, total - warmup))
                task["progress"] = min(pct, 95)
                task["message"] = f"Test devam ediyor  ·  Mum: {i}/{total}"

        if open_position:
            last_price = candles[-1]["close"]
            _close_position(open_position, last_price, "END", balance, closed_trades, candles[-1]["time"])
            balance = open_position["_new_balance"]
            open_position = None

        task["progress"] = 96
        task["message"] = "Metrikler hesaplaniyor..."

        total_trades = len(closed_trades)
        wins = sum(1 for t in closed_trades if t["pnl_amount"] > 0)
        losses = total_trades - wins
        total_pnl = sum(t["pnl_amount"] for t in closed_trades)
        wr = (wins / total_trades * 100) if total_trades > 0 else 0

        max_dd = 0
        peak = initial_balance
        for p in equity_curve:
            if p["value"] > peak:
                peak = p["value"]
            dd = (peak - p["value"]) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        final = equity_curve[-1]["value"] if equity_curve else initial_balance

        # Downsample equity curve (max 500 nokta)
        step = max(1, len(equity_curve) // 500)
        equity_sampled = equity_curve[::step]

        task["result"] = {
            "symbol": symbol,
            "strategy": strategy_name,
            "interval": interval,
            "start_time": candles[warmup]["time"],
            "end_time": candles[-1]["time"],
            "total_candles": total,
            "initial_balance": initial_balance,
            "final_balance": round(final, 4),
            "total_pnl": round(total_pnl, 4),
            "total_pnl_pct": round((final - initial_balance) / initial_balance * 100, 2),
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wr, 2),
            "max_drawdown": round(max_dd, 2),
            "equity_curve": equity_sampled,
            "trades": closed_trades[:500],
            "trades_total": total_trades,
        }
        task["progress"] = 100
        task["status"] = "done"
        task["message"] = "Tamamlandi"
        task["completed_at"] = time.time()

    except Exception as e:
        print(f"[BT] Task {task_id} hata: {e}")
        traceback.print_exc()
        task["status"] = "error"
        task["message"] = f"Hata: {str(e)}"
