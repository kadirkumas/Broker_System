"""
Backtest Engine - Gecmis veri uzerinde strateji simulasyonu.
Async task olarak calisir, progress raporlanir.
"""
import time
import traceback
from datetime import datetime
from backend.strategies import RSIScalperStrategy, DynamicGridStrategy, DynamicGridReelStrategy, DeepHunterStrategy


# ==========================================================
# AI TTP - Kademeli Trailing Helpers (backtest)
# ==========================================================
def _parse_trailing_steps(steps_str):
    if not steps_str:
        return []
    result = []
    for pair in str(steps_str).split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        try:
            k, v = pair.split(":", 1)
            kf = float(k.strip())
            vf = float(v.strip())
            if kf >= 0 and vf > 0:
                result.append((kf, vf))
        except Exception:
            pass
    result.sort(key=lambda x: x[0])
    return result


def _get_ai_ttp_pct(steps, profit_pct, pos):
    """Ratchet - geri donmez."""
    if not steps:
        return pos.get("_trail_pct") or 0.003
    best = pos.get("_trail_pct")
    for k_pct, t_pct in steps:
        if profit_pct >= k_pct / 100.0:
            cand = t_pct / 100.0
            if best is None or cand < best:
                best = cand
        else:
            break
    if best is None:
        best = steps[0][1] / 100.0
    pos["_trail_pct"] = best
    return best

# ==========================================================
# INTERVAL RANGE LIMITER (TradingView Essential uyumlu)
# 1m: 2 hafta, 5m: 6 hafta, 15m: 3 ay, 1h: 1 yil, 4h: 2 yil, 1d: 10 yil
# ==========================================================
MAX_DAYS_BY_INTERVAL = {
    "1m":  14,
    "3m":  21,
    "5m":  45,
    "15m": 90,
    "30m": 180,
    "1h":  365,
    "2h":  365,
    "4h":  730,
    "6h":  730,
    "8h":  730,
    "12h": 1095,
    "1d":  3650,
    "3d":  3650,
    "1w":  3650,
}

_INTERVAL_MINUTES = {
    "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
    "1h": 60, "2h": 120, "4h": 240, "6h": 360, "8h": 480,
    "12h": 720, "1d": 1440, "3d": 4320, "1w": 10080,
}


def _interval_to_minutes(interval):
    iv = str(interval or "1m").lower().strip()
    if iv in _INTERVAL_MINUTES:
        return _INTERVAL_MINUTES[iv]
    try:
        if iv.endswith("m"):
            return int(iv[:-1])
        if iv.endswith("h"):
            return int(iv[:-1]) * 60
        if iv.endswith("d"):
            return int(iv[:-1]) * 1440
        if iv.endswith("w"):
            return int(iv[:-1]) * 10080
    except Exception:
        pass
    return 1


def get_max_days_for_interval(interval):
    iv = str(interval or "1m").lower().strip()
    return MAX_DAYS_BY_INTERVAL.get(iv, 14)


def clamp_date_range(start_ms, end_ms, interval):
    """start_ms cok eskiyse interval'e gore kirp."""
    if end_ms is None:
        end_ms = int(time.time() * 1000)
    if start_ms is None:
        return start_ms, end_ms
    max_days = get_max_days_for_interval(interval)
    max_ms = max_days * 24 * 3600 * 1000
    if (end_ms - start_ms) > max_ms:
        new_start = end_ms - max_ms
        print(f"[BT-LIMIT] Aralik kirpildi -> {max_days} gun ({interval})")
        return new_start, end_ms
    return start_ms, end_ms




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
    elif name == "DYNAMIC_GRID":
        return DynamicGridStrategy(params)
    elif name == "DYNAMIC_GRID_REEL":
        return DynamicGridReelStrategy(params)
    elif name == "DEEP_HUNTER":
        return DeepHunterStrategy(params)
    return None


def _fetch_all_klines(client, symbol, interval, start_ms, end_ms, mode="futures"):
    """Binance'ten paginated klines ceker. mode: futures | spot"""
    all_klines = []
    current = start_ms
    iters = 0
    max_iters = 50   # 50 * 1500 = 75,000 bar (guvenli sinir)

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


def run_grid_reel_backtest(task_id, client, symbol, params, initial_balance,
                            interval="1m", start_date=None, end_date=None, mode="futures"):
    """
    DYNAMIC_GRID_REEL icin gercek grid simulasyonu.
    Her seviye bagimsiz pozisyon. TP = komsu seviye.
    Recenter olunca eski pozisyonlar piyasa fiyatindan kapatilir.
    """
    task = _BACKTEST_TASKS.get(task_id)
    if not task:
        return

    try:
        base_order = float(params.get("baseOrder", 5))
        leverage = max(1, int(params.get("leverage", 5)))

        balance = float(initial_balance)
        equity_curve = []
        closed_trades = []

        # Aktif pozisyonlar: {(group_id, level): pos_dict}
        open_positions = {}

        task["status"] = "running"
        task["progress"] = 5
        task["message"] = "Grid REEL baslatiliyor..."

        end_ms = int(time.time() * 1000) if end_date is None else int(end_date)
        if start_date is None:
            task["message"] = "Listing tarihi bulunuyor..."
            start_ms = _get_listing_date(client, symbol, mode)
            if start_ms is None:
                start_ms = end_ms - (365 * 24 * 3600 * 1000)
            # ⚡ Interval'e gore kirp
            _md = get_max_days_for_interval(interval)
            _mm = _md * 24 * 3600 * 1000
            if (end_ms - start_ms) > _mm:
                start_ms = end_ms - _mm
                print(f"[BT-LIMIT] {symbol} {interval} -> max {_md} gun")
        else:
            start_ms = int(start_date)
            start_ms, end_ms = clamp_date_range(start_ms, end_ms, interval)

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

        strategy = DynamicGridReelStrategy(params)

        warmup = max(
            int(params.get("smaPeriod", 100)),
            int(params.get("pivotLookback", 100)),
            100
        ) + 10

        if warmup >= total:
            task["status"] = "error"
            task["message"] = "Yetersiz veri"
            return

        step_size = max(1, (total - warmup) // 50)
        recenter_count = 0
        tp_count = 0

        for i in range(warmup, total):
            candle = candles[i]
            current_price = candle["close"]
            current_high = candle["high"]
            current_low = candle["low"]

            # --- 1) Mevcut pozisyonlarin TP kontrolu ---
            to_close = []
            for key, pos in open_positions.items():
                tp_price = pos.get("tp_price")
                if not tp_price or tp_price <= 0:
                    continue
                is_long = pos["side"] == "BUY"
                if is_long and current_high >= tp_price:
                    to_close.append((key, tp_price))
                elif not is_long and current_low <= tp_price:
                    to_close.append((key, tp_price))

            for key, exit_price in to_close:
                pos = open_positions.pop(key)
                is_long = pos["side"] == "BUY"
                if is_long:
                    pct = (exit_price - pos["avg_price"]) / pos["avg_price"]
                else:
                    pct = (pos["avg_price"] - exit_price) / pos["avg_price"]

                gross = pos["total_vol"] * pct
                exit_comm = pos["total_vol"] * 0.0004
                entry_comm = pos["total_vol"] * 0.0004
                net = gross - exit_comm - entry_comm

                balance += pos["_margin"] + net
                tp_count += 1

                closed_trades.append({
                    "entry_time": pos["entry_time"],
                    "exit_time": candle["time"],
                    "side": pos["side"],
                    "entry_price": round(pos["avg_price"], 8),
                    "exit_price": round(exit_price, 8),
                    "total_vol": round(pos["total_vol"], 4),
                    "pnl_amount": round(net, 4),
                    "pnl_pct": round(pct * 100, 4),
                    "reason": f"GRID TP L{pos.get('grid_level', 0)}",
                    "dca_count": 0,
                })

            # --- 2) Strateji evaluate ---
            window = candles[:i + 1]
            try:
                result = strategy.evaluate(window, None, symbol=symbol)
            except Exception:
                result = {"signal": None}

            sig = result.get("signal")
            meta = result.get("meta", {}) or {}

            # --- Recenter: eski grubu kapat ---
            if meta.get("recenter_happened") and meta.get("prev_group_id"):
                prev_gid = meta.get("prev_group_id")
                recenter_count += 1
                keys_to_close = [
                    k for k, p in open_positions.items()
                    if p.get("group_id") == prev_gid
                ]
                for key in keys_to_close:
                    pos = open_positions.pop(key)
                    is_long = pos["side"] == "BUY"
                    if is_long:
                        pct = (current_price - pos["avg_price"]) / pos["avg_price"]
                    else:
                        pct = (pos["avg_price"] - current_price) / pos["avg_price"]

                    gross = pos["total_vol"] * pct
                    exit_comm = pos["total_vol"] * 0.0004
                    entry_comm = pos["total_vol"] * 0.0004
                    net = gross - exit_comm - entry_comm

                    balance += pos["_margin"] + net

                    closed_trades.append({
                        "entry_time": pos["entry_time"],
                        "exit_time": candle["time"],
                        "side": pos["side"],
                        "entry_price": round(pos["avg_price"], 8),
                        "exit_price": round(current_price, 8),
                        "total_vol": round(pos["total_vol"], 4),
                        "pnl_amount": round(net, 4),
                        "pnl_pct": round(pct * 100, 4),
                        "reason": "GRID RECENTER",
                        "dca_count": 0,
                    })

            # --- Yeni sinyal ---
            if sig in ("LONG", "SHORT") and meta.get("is_grid_reel"):
                group_id = meta.get("grid_group_id")
                grid_level = meta.get("grid_level")
                grid_tp_price = meta.get("grid_tp_price")
                grid_entry_price = meta.get("grid_entry_price") or current_price

                key = (group_id, grid_level)
                if key not in open_positions:
                    margin = base_order / leverage
                    entry_comm = base_order * 0.0004
                    if balance >= margin + entry_comm:
                        balance -= margin + entry_comm
                        open_positions[key] = {
                            "side": "BUY" if sig == "LONG" else "SELL",
                            "avg_price": grid_entry_price,
                            "total_vol": base_order,
                            "entry_time": candle["time"],
                            "tp_price": grid_tp_price,
                            "group_id": group_id,
                            "grid_level": grid_level,
                            "_margin": margin,
                        }

            # --- Equity ---
            unreal = 0
            for pos in open_positions.values():
                is_long = pos["side"] == "BUY"
                if is_long:
                    up = (current_price - pos["avg_price"]) / pos["avg_price"]
                else:
                    up = (pos["avg_price"] - current_price) / pos["avg_price"]
                unreal += pos["total_vol"] * up

            total_margin = sum(p["_margin"] for p in open_positions.values())
            equity = balance + unreal + total_margin
            equity_curve.append({"time": candle["time"], "value": equity})

            if (i - warmup) % step_size == 0:
                pct = 20 + int(70 * (i - warmup) / max(1, total - warmup))
                task["progress"] = min(pct, 95)
                task["message"] = (
                    f"Grid test  ·  Mum: {i}/{total}  ·  "
                    f"Acik: {len(open_positions)}  ·  "
                    f"TP: {tp_count}  ·  Recenter: {recenter_count}"
                )

        # ⚡ Acik pozisyonlari SAYMA (kullanici tercihi)
        # Test sonunda acik kalan grid seviyeleri listede gosterilmez.

        # --- Metrikler ---
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

        # ⚡ Acik pozisyonlari sayma
        final = initial_balance + total_pnl

        step = max(1, len(equity_curve) // 500)
        equity_sampled = equity_curve[::step]

        # ⚡ Son noktayi final ile esitle (downsample SONRASI)
        if equity_sampled and len(equity_sampled) > 0:
            equity_sampled[-1] = {"time": equity_sampled[-1]["time"], "value": final}

        task["result"] = {
            "symbol": symbol,
            "strategy": "DYNAMIC_GRID_REEL",
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
            "grid_stats": {
                "tp_count": tp_count,
                "recenter_count": recenter_count,
            },
        }
        task["progress"] = 100
        task["status"] = "done"
        task["message"] = "Tamamlandi"
        task["completed_at"] = time.time()

    except Exception as e:
        print(f"[BT-GRID] Task {task_id} hata: {e}")
        traceback.print_exc()
        task["status"] = "error"
        task["message"] = f"Hata: {str(e)}"


def run_backtest_sync(task_id, client, symbol, strategy_name, params, initial_balance,
                      interval="4h", start_date=None, end_date=None, mode="futures"):
    task = _BACKTEST_TASKS.get(task_id)
    if not task:
        return

    # ⚡ GRID REEL icin ayri simulasyon motoru
    if strategy_name == "DYNAMIC_GRID_REEL":
        return run_grid_reel_backtest(
            task_id, client, symbol, params, initial_balance,
            interval, start_date, end_date, mode
        )

    try:
        base_order = float(params.get("baseOrder", 10))
        leverage = max(1, int(params.get("leverage", 1)))
        take_profit = float(params.get("takeProfit", 1.5)) / 100
        stop_loss = float(params.get("stopLoss", 3.0)) / 100

        # ⚡ AI TTP - kademeli trailing
        _steps_str = params.get("trailingSteps") or ""
        trail_steps = _parse_trailing_steps(_steps_str)
        if not trail_steps and params.get("trailing"):
            trail_steps = [(0.0, float(params["trailing"]))]
        if not trail_steps:
            trail_steps = [(1.5, 0.3), (2.5, 0.2), (4.0, 0.12), (6.0, 0.07), (10.0, 0.03)]
        trailing = trail_steps[0][1] / 100.0  # fallback
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
            # ⚡ Interval'e gore kirp
            _md = get_max_days_for_interval(interval)
            _mm = _md * 24 * 3600 * 1000
            if (end_ms - start_ms) > _mm:
                start_ms = end_ms - _mm
                print(f"[BT-LIMIT] {symbol} {interval} -> max {_md} gun")
        else:
            start_ms = int(start_date)
            start_ms, end_ms = clamp_date_range(start_ms, end_ms, interval)

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

                # ⚡ AI TTP - Kademeli Trailing
                if pos["ttp_active"]:
                    # Her tick'te kademeyi hesapla (ratchet)
                    _cur_trail = _get_ai_ttp_pct(trail_steps, pnl_pct, pos)
                    if is_long:
                        if price > pos["hwm"]:
                            pos["hwm"] = price
                        trigger = pos["hwm"] * (1 - _cur_trail)
                        if price <= trigger:
                            _close_position(pos, price, "AI-TTP", balance, closed_trades, candle["time"])
                            balance = pos["_new_balance"]
                            open_position = None
                            continue
                    else:
                        if price < pos["hwm"]:
                            pos["hwm"] = price
                        trigger = pos["hwm"] * (1 + _cur_trail)
                        if price >= trigger:
                            _close_position(pos, price, "AI-TTP", balance, closed_trades, candle["time"])
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
                            pos["_trail_pct"] = None  # ilk kademe hesaplanacak

                # ⚡ DCA ONCE (canli botta oldugu gibi)
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
                                    # ⚡ DCA history (SL base icin)
                                    if "_dca_history" not in pos:
                                        pos["_dca_history"] = []
                                    pos["_dca_history"].append({"price": price, "step": new_count})
                                    # ⚡ Hibrit koruma icin son DCA bilgisi
                                    pos["_last_dca_price"] = price
                                    pos["_last_dca_time"] = candle["time"]
                                    # DCA olduktan sonra pnl_pct guncelle
                                    if is_long:
                                        pnl_pct = (price - pos["avg_price"]) / pos["avg_price"]
                                    else:
                                        pnl_pct = (pos["avg_price"] - price) / pos["avg_price"]

                # ⚡ SL SONRA (canli botta oldugu gibi - son DCA fiyatindan)
                sl_base_price = pos["avg_price"]
                # Son DCA varsa ondan
                try:
                    _dh = pos.get("_dca_history", [])
                    if _dh:
                        _last_dca = _dh[-1].get("price", 0)
                        if _last_dca > 0:
                            sl_base_price = _last_dca
                except Exception:
                    pass

                if not pos["ttp_active"]:
                    if is_long:
                        sl_trigger = sl_base_price * (1 - stop_loss)
                        sl_hit = price <= sl_trigger
                    else:
                        sl_trigger = sl_base_price * (1 + stop_loss)
                        sl_hit = price >= sl_trigger

                    if sl_hit:
                        _close_position(pos, price, "STOP LOSS", balance, closed_trades, candle["time"])
                        balance = pos["_new_balance"]
                        open_position = None
                        continue

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
                            "_trail_pct": None,
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

        # ⚡ Acik pozisyonlari SAYMA (kullanici tercihi)
        # Test sonunda hala acik olan pozisyonlar listede gosterilmez.
        # Sadece kapanmis trade'ler PnL'e dahil edilir.
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

        # ⚡ Acik pozisyonu sayma - sadece kapanmis trade'lerin toplami
        final = initial_balance + total_pnl

        # Downsample equity curve (max 500 nokta)
        step = max(1, len(equity_curve) // 500)
        equity_sampled = equity_curve[::step]

        # ⚡ Son noktayi final ile esitle (downsample SONRASI)
        if equity_sampled and len(equity_sampled) > 0:
            equity_sampled[-1] = {"time": equity_sampled[-1]["time"], "value": final}

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


# ==========================================================
# FUNDING ARBITRAGE BACKTEST
# ==========================================================
def run_funding_backtest(task_id, client, symbol, params, initial_balance,
                          interval="1m", start_date=None, end_date=None, mode="futures"):
    """
    Funding Arbitrage backtest.
    Veri: Binance funding history (8 saatte 1 kayit).
    Ek: TP/SL icin mumlar (funding event anindaki fiyat).

    Basitlestirilmis mantik:
    - Her funding event'inde pozisyon ac (eger firsat varsa)
    - Sonraki funding event'ine kadar fiyat hareketi izle (TP/SL)
    - Funding gelirini ekle
    """
    task = _BACKTEST_TASKS.get(task_id)
    if not task:
        return

    try:
        # --- Parametreler ---
        min_funding = float(params.get("minFundingRate", 0.05)) / 100.0
        base_order = float(params.get("baseOrder", 20))
        leverage = max(1, int(params.get("leverage", 3)))
        tp_pct = float(params.get("takeProfit", 0.3)) / 100.0
        sl_pct = float(params.get("stopLoss", 1.5)) / 100.0
        long_enabled = bool(params.get("longEnabled", True))
        short_enabled = bool(params.get("shortEnabled", True))
        mode_val = str(params.get("mode", "both")).lower()

        if mode_val == "long":
            short_enabled = False
        elif mode_val == "short":
            long_enabled = False

        task["status"] = "running"
        task["progress"] = 5
        task["message"] = "Funding gecmisi cekiliyor..."

        # --- Tarih araligi ---
        end_ms = int(time.time() * 1000) if end_date is None else int(end_date)
        if start_date is None:
            # Varsayilan: 30 gun
            start_ms = end_ms - (30 * 24 * 3600 * 1000)
        else:
            start_ms = int(start_date)

        # --- Funding history cek (paginated) ---
        fetch_fn = client.futures_funding_rate if mode == "futures" else None
        if fetch_fn is None:
            task["status"] = "error"
            task["message"] = "Funding verisi sadece vadeli icin"
            return

        task["progress"] = 15
        task["message"] = "Funding verileri yukleniyor..."

        all_fundings = []
        cur = start_ms
        iters = 0
        while cur < end_ms and iters < 10:
            iters += 1
            try:
                chunk = fetch_fn(
                    symbol=symbol,
                    startTime=cur,
                    endTime=end_ms,
                    limit=1000
                )
            except Exception as e:
                print(f"[BT-FUNDING] Fetch hata: {e}")
                break

            if not chunk:
                break

            all_fundings.extend(chunk)

            if len(chunk) < 1000:
                break

            last_ts = int(chunk[-1].get("fundingTime", 0))
            if last_ts <= cur:
                break
            cur = last_ts + 1
            time.sleep(0.1)

        if not all_fundings:
            task["status"] = "error"
            task["message"] = "Funding verisi bulunamadi (bu aralikta)"
            return

        # Sort by time
        all_fundings.sort(key=lambda x: int(x.get("fundingTime", 0)))
        total_events = len(all_fundings)

        task["progress"] = 30
        task["message"] = f"{total_events} funding event yuklendi"

        # --- Mumlari cek (TP/SL icin) ---
        task["progress"] = 40
        task["message"] = "Fiyat verileri yukleniyor..."

        # 1m veya 5m mum (funding event anlarini yakalamak icin)
        bt_interval = "5m" if interval in ("1m", "3m") else interval
        try:
            klines = _fetch_all_klines(client, symbol, bt_interval, start_ms, end_ms, mode)
        except Exception as e:
            print(f"[BT-FUNDING] Klines hata: {e}")
            klines = []

        candles = _klines_to_candles(klines) if klines else []
        candle_map = {int(c["time"]): c for c in candles}
        candle_times = sorted(candle_map.keys())

        # --- Simulasyon ---
        task["progress"] = 55
        task["message"] = "Simulasyon calisiyor..."

        balance = float(initial_balance)
        equity_curve = []
        closed_trades = []

        position = None  # {side, entry_price, entry_time, total_vol, margin, funding_income}

        def _find_price_at(t_sec):
            """Verilen saniyeye en yakin mum kapanis."""
            if not candle_times:
                return None
            # binary-ish find
            lo, hi = 0, len(candle_times) - 1
            target = t_sec
            while lo < hi:
                mid = (lo + hi) // 2
                if candle_times[mid] < target:
                    lo = mid + 1
                else:
                    hi = mid
            # En yakin
            best = candle_times[lo]
            if lo > 0 and abs(candle_times[lo - 1] - target) < abs(best - target):
                best = candle_times[lo - 1]
            c = candle_map.get(best)
            return c["close"] if c else None

        def _check_tp_sl(pos, current_price, current_time):
            """True -> kapatildi."""
            if pos["side"] == "BUY":
                pnl_pct = (current_price - pos["entry_price"]) / pos["entry_price"]
            else:
                pnl_pct = (pos["entry_price"] - current_price) / pos["entry_price"]

            is_tp = pnl_pct >= tp_pct
            is_sl = pnl_pct <= -sl_pct

            if not (is_tp or is_sl):
                return None

            # Kapat
            reason = "FUNDING_TP" if is_tp else "FUNDING_SL"
            gross = pos["total_vol"] * pnl_pct
            # Komisyon: giris (taker) + cikis (taker)
            comm = pos["total_vol"] * 0.0004 * 2
            net = gross - comm + pos["funding_income"]

            nonlocal_balance = pos["margin"] + net

            closed_trades.append({
                "entry_time": pos["entry_time"],
                "exit_time": current_time,
                "side": pos["side"],
                "entry_price": round(pos["entry_price"], 8),
                "exit_price": round(current_price, 8),
                "total_vol": round(pos["total_vol"], 4),
                "pnl_amount": round(net, 4),
                "pnl_pct": round(pnl_pct * 100, 4),
                "reason": reason,
                "dca_count": 0,
            })

            return nonlocal_balance

        # Funding event dongusu
        step_size = max(1, total_events // 50)
        last_price = None

        for evt_idx, evt in enumerate(all_fundings):
            evt_time_sec = int(evt.get("fundingTime", 0)) // 1000
            try:
                fr = float(evt.get("fundingRate", 0))
            except Exception:
                fr = 0.0

            # Fiyat
            price = _find_price_at(evt_time_sec)
            if price is None:
                price = last_price
            if price is None:
                continue
            last_price = price

            # --- Acik pozisyon: TP/SL + funding geliri ---
            if position:
                # Funding geliri hesapla
                # SHORT + pozitif funding -> para ALIR (pozitif)
                # LONG + negatif funding -> para ALIR
                # LONG + pozitif funding -> para ODETIR (negatif)
                if position["side"] == "SELL":
                    funding_income = position["total_vol"] * fr
                else:  # BUY
                    funding_income = -position["total_vol"] * fr

                position["funding_income"] += funding_income

                # TP/SL kontrol
                close_balance = _check_tp_sl(position, price, evt_time_sec)
                if close_balance is not None:
                    balance = close_balance
                    position = None
                    continue

            # --- Yeni pozisyon ac (eger yoksa ve firsat varsa) ---
            if not position and abs(fr) >= min_funding:
                side = None
                if fr > 0 and short_enabled:
                    side = "SELL"
                elif fr < 0 and long_enabled:
                    side = "BUY"

                if side:
                    margin = base_order / leverage
                    entry_comm = base_order * 0.0004

                    if balance >= margin + entry_comm:
                        balance -= (margin + entry_comm)
                        position = {
                            "side": side,
                            "entry_price": price,
                            "entry_time": evt_time_sec,
                            "total_vol": base_order,
                            "margin": margin,
                            "funding_income": 0.0,
                        }

            # --- Equity ---
            if position:
                if position["side"] == "BUY":
                    upnl_pct = (price - position["entry_price"]) / position["entry_price"]
                else:
                    upnl_pct = (position["entry_price"] - price) / position["entry_price"]
                upnl = position["total_vol"] * upnl_pct
                eq = balance + position["margin"] + upnl + position["funding_income"]
            else:
                eq = balance

            equity_curve.append({"time": evt_time_sec, "value": eq})

            if evt_idx % step_size == 0:
                pct = 55 + int(40 * evt_idx / max(1, total_events))
                task["progress"] = min(pct, 95)
                task["message"] = f"Simulasyon  ·  Event: {evt_idx}/{total_events}"

        # --- Bitis: acik pozisyonu kapatma (sayma) ---

        # --- Metrikler ---
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

        final = initial_balance + total_pnl

        # Downsample
        step = max(1, len(equity_curve) // 500)
        eq_sampled = equity_curve[::step] if equity_curve else []
        if eq_sampled:
            eq_sampled[-1] = {"time": eq_sampled[-1]["time"], "value": final}

        task["result"] = {
            "symbol": symbol,
            "strategy": "UNKNOWN",
            "interval": bt_interval,
            "start_time": all_fundings[0].get("fundingTime", 0) // 1000 if all_fundings else 0,
            "end_time": all_fundings[-1].get("fundingTime", 0) // 1000 if all_fundings else 0,
            "total_candles": total_events,
            "initial_balance": initial_balance,
            "final_balance": round(final, 4),
            "total_pnl": round(total_pnl, 4),
            "total_pnl_pct": round((final - initial_balance) / initial_balance * 100, 2),
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wr, 2),
            "max_drawdown": round(max_dd, 2),
            "equity_curve": eq_sampled,
            "trades": closed_trades[:500],
            "trades_total": total_trades,
            "funding_stats": {
                "total_events": total_events,
                "min_funding_pct": round(min_funding * 100, 4),
                "avg_funding_pct": round(
                    sum(abs(float(f.get("fundingRate", 0))) for f in all_fundings) / total_events * 100, 4
                ) if total_events else 0,
            },
        }
        task["progress"] = 100
        task["status"] = "done"
        task["message"] = "Tamamlandi"
        task["completed_at"] = time.time()

        print(f"[BT-FUNDING] Tamamlandi: {total_trades} trade, {total_pnl:+.4f} USDT")

    except Exception as e:
        print(f"[BT-FUNDING] Task {task_id} hata: {e}")
        traceback.print_exc()
        task["status"] = "error"
        task["message"] = f"Hata: {str(e)}"
