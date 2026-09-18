import shutil
import os
import re

# ============================================================
# DOSYALAR
# ============================================================
NEW_FILE = 'backend/telegram_notifier.py'
MAIN_SRC = 'backend/main.py'
MAIN_BAK = 'backend/main.py.bak_telegram'
SE_SRC = 'backend/strategy_engine.py'
SE_BAK = 'backend/strategy_engine.py.bak_telegram'
PM_SRC = 'backend/position_manager.py'
PM_BAK = 'backend/position_manager.py.bak_telegram'
ENV_SRC = '.env'
ENV_BAK = '.env.bak_telegram'

for src, bak in [(MAIN_SRC, MAIN_BAK), (SE_SRC, SE_BAK), (PM_SRC, PM_BAK), (ENV_SRC, ENV_BAK)]:
    if os.path.exists(src):
        shutil.copy2(src, bak)

print(f"[1/6] Yedekler alindi")

# ============================================================
# 1. YENİ DOSYA: backend/telegram_notifier.py
# ============================================================
telegram_code = '''import os
import asyncio
import requests
from dotenv import load_dotenv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)


def _get_credentials():
    """Telegram token ve chat_id'yi .env'den okur."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    return token, chat_id


def is_configured() -> bool:
    """Telegram ayarları yapılmış mı?"""
    token, chat_id = _get_credentials()
    return bool(token and chat_id)


async def send_telegram_message(text: str, parse_mode: str = "HTML") -> dict:
    """Telegram'a mesaj gönderir (async)."""
    token, chat_id = _get_credentials()
    
    if not token or not chat_id:
        return {"status": "skip", "message": "Telegram ayarları eksik (.env)"}
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    
    try:
        r = await asyncio.to_thread(requests.post, url, json=payload, timeout=10)
        data = r.json()
        if not data.get("ok"):
            print(f"[TG] Gönderim hatası: {data.get('description', 'bilinmeyen')}")
        return data
    except Exception as e:
        print(f"[TG] Bağlantı hatası: {e}")
        return {"status": "error", "message": str(e)}


def _fmt_price(p) -> str:
    """Fiyatı okunabilir formatta döner."""
    try:
        p = float(p)
        if p == 0: return "0"
        if p >= 1000: return f"{p:,.2f}"
        if p >= 1: return f"{p:.4f}"
        if p >= 0.01: return f"{p:.6f}"
        return f"{p:.8f}"
    except:
        return str(p)


async def notify_signal(symbol: str, strategy: str, signal_type: str, price: float, total_usdt: float):
    """Yeni sinyal bildirimi."""
    emoji = "🟢" if signal_type == "LONG" else "🔴"
    text = (
        f"{emoji} <b>YENİ SİNYAL</b>\\n"
        f"\\n"
        f"<b>Sembol:</b> {symbol}\\n"
        f"<b>Strateji:</b> {strategy}\\n"
        f"<b>Yön:</b> {signal_type}\\n"
        f"<b>Fiyat:</b> {_fmt_price(price)} USDT\\n"
        f"<b>Tutar:</b> {total_usdt:.2f} USDT"
    )
    return await send_telegram_message(text)


async def notify_close(
    symbol: str, trade_type: str, entry_price: float, exit_price: float,
    pnl_pct: float, net_pnl: float, reason: str, dca_count: int = 0
):
    """Pozisyon kapanış bildirimi."""
    is_profit = net_pnl >= 0
    emoji = "✅" if is_profit else "❌"
    sign = "+" if is_profit else ""
    side = "LONG" if trade_type == "BUY" else "SHORT"
    dca_info = f" (DCA:{dca_count})" if dca_count > 0 else ""
    
    text = (
        f"{emoji} <b>POZİSYON KAPANDI</b>\\n"
        f"\\n"
        f"<b>Sembol:</b> {symbol}{dca_info}\\n"
        f"<b>Yön:</b> {side}\\n"
        f"<b>Giriş:</b> {_fmt_price(entry_price)}\\n"
        f"<b>Çıkış:</b> {_fmt_price(exit_price)}\\n"
        f"<b>Sebep:</b> {reason}\\n"
        f"<b>Kâr:</b> {sign}{pnl_pct:.2f}%\\n"
        f"<b>Net:</b> {sign}{net_pnl:.4f} USDT"
    )
    return await send_telegram_message(text)


async def notify_error(message: str):
    """Hata bildirimi."""
    text = f"⚠️ <b>BOT HATASI</b>\\n\\n<code>{message[:500]}</code>"
    return await send_telegram_message(text)


async def notify_delisting(symbol: str):
    """Delist uyarısı."""
    text = f"🚫 <b>DELIST</b>\\n\\n<b>{symbol}</b> delist edildi. Pozisyon kapatılıyor."
    return await send_telegram_message(text)


async def notify_startup():
    """Bot başlatıldığında."""
    text = "🚀 <b>Broker System</b>\\n\\nStrateji motoru <b>AKTİF</b> edildi."
    return await send_telegram_message(text)


async def notify_shutdown(reason: str = ""):
    """Bot durdurulduğunda."""
    text = f"⏹ <b>Broker System</b>\\n\\nStrateji motoru <b>PASİF</b> edildi.\\n{reason}"
    return await send_telegram_message(text)
'''

with open(NEW_FILE, 'w', encoding='utf-8', newline='') as f:
    f.write(telegram_code)

print(f"[2/6] YENI: backend/telegram_notifier.py olusturuldu")

# ============================================================
# 2. main.py - /api/telegram/* endpoint'leri
# ============================================================
with open(MAIN_SRC, 'r', encoding='utf-8', newline='') as f:
    main = f.read().replace('\r\n', '\n')

# Import ekle
old_import = "from backend.database import init_db, get_db_connection"
new_import = "from backend.database import init_db, get_db_connection\nfrom backend import telegram_notifier"
if old_import in main and 'telegram_notifier' not in main:
    main = main.replace(old_import, new_import, 1)
    print("[3/6] main.py: telegram_notifier import")

# Endpoints ekle (dosya sonuna)
new_endpoints = '''

# ----------------------------------------------------------------------
# TELEGRAM BİLDİRİM ENDPOINT'LERİ
# ----------------------------------------------------------------------
@app.get("/api/telegram/status")
async def telegram_status():
    """Telegram ayarları yapılmış mı?"""
    return {
        "status": "success",
        "configured": telegram_notifier.is_configured(),
    }


@app.post("/api/telegram/test")
async def telegram_test():
    """Test mesajı gönderir."""
    if not telegram_notifier.is_configured():
        return {
            "status": "error",
            "message": "Telegram ayarları eksik. .env dosyasında TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID olmalı."
        }
    
    result = await telegram_notifier.send_telegram_message(
        "🔔 <b>Broker System</b>\\n\\n"
        "✅ Telegram bildirimleri başarıyla bağlandı!\\n"
        "Artık sinyal ve kapanış bildirimleri buraya gelecek."
    )
    
    if result.get("ok"):
        return {"status": "success", "message": "Test mesajı gönderildi"}
    else:
        return {"status": "error", "message": result.get("description") or result.get("message") or "Bilinmeyen hata"}
'''

if '/api/telegram/' not in main:
    main = main.rstrip() + new_endpoints
    print("[3/6] main.py: Telegram endpoint'leri eklendi")

with open(MAIN_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(main.replace('\n', '\r\n'))

# ============================================================
# 3. strategy_engine.py - sinyal bildirimi
# ============================================================
with open(SE_SRC, 'r', encoding='utf-8', newline='') as f:
    se = f.read().replace('\r\n', '\n')

# Import
old = "from backend.database import get_db_connection"
new = "from backend.database import get_db_connection\nfrom backend import telegram_notifier"
if old in se and 'telegram_notifier' not in se:
    se = se.replace(old, new, 1)
    print("[4/6] strategy_engine: import eklendi")

# Sinyal bildirimi - "print(f\"\\n[>> SİNYAL] ..." satırından sonra
old = '''                side = "BUY" if result["signal"] == "LONG" else "SELL"
                base_order = float(strat_cfg.get("baseOrder", 10))
                print(f"\\n[>> SİNYAL] {symbol} [{strategy_name}] {result['signal']} | {result['reason']}")'''

new = '''                side = "BUY" if result["signal"] == "LONG" else "SELL"
                base_order = float(strat_cfg.get("baseOrder", 10))
                print(f"\\n[>> SİNYAL] {symbol} [{strategy_name}] {result['signal']} | {result['reason']}")
                
                # ⚡ Telegram bildirimi
                try:
                    if self.config.get("telegram", {}).get("notify_signals", True):
                        asyncio.create_task(telegram_notifier.notify_signal(
                            symbol=symbol,
                            strategy=strategy_name,
                            signal_type=result["signal"],
                            price=current_price,
                            total_usdt=base_order,
                        ))
                except Exception as _e:
                    print(f"[TG] Sinyal bildirim hatası: {_e}")'''

if old in se:
    se = se.replace(old, new, 1)
    print("[4/6] strategy_engine: sinyal bildirimi eklendi")
else:
    print("[4/6] UYARI: sinyal print pattern bulunamadi")

# Delist bildirimi
old = '''                if newly and getattr(self, '_delisted_cache_time', 0) > 0:
                    for sym in newly:
                        print(f"[DELIST] YENI DELIST: {sym}")'''
new = '''                if newly and getattr(self, '_delisted_cache_time', 0) > 0:
                    for sym in newly:
                        print(f"[DELIST] YENI DELIST: {sym}")
                        try:
                            if self.config.get("telegram", {}).get("notify_signals", True):
                                asyncio.create_task(telegram_notifier.notify_delisting(sym))
                        except Exception:
                            pass'''

if old in se:
    se = se.replace(old, new, 1)
    print("[4/6] strategy_engine: delist bildirimi eklendi")

# Telegram defaults ekle
old = '''    "auto_close_delisted": True,'''
new = '''    "auto_close_delisted": True,
    "telegram": {
        "notify_signals": True,
        "notify_closes": True,
    },'''

if old in se and 'notify_signals' not in se:
    se = se.replace(old, new, 1)
    print("[4/6] strategy_engine: telegram defaults eklendi")

with open(SE_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(se.replace('\n', '\r\n'))

# ============================================================
# 4. position_manager.py - kapanış bildirimi
# ============================================================
with open(PM_SRC, 'r', encoding='utf-8', newline='') as f:
    pm = f.read().replace('\r\n', '\n')

# Import
old = "from backend.database import get_db_connection"
new = "from backend.database import get_db_connection\nfrom backend import telegram_notifier"
if old in pm and 'telegram_notifier' not in pm:
    pm = pm.replace(old, new, 1)
    print("[5/6] position_manager: import eklendi")

# Kapanış bildirimi - print satırından sonra
old = '''        print(f"[✓ KAPANIŞ] {symbol}{dca_info}{lev_info} | {reason} | Çıkış: {exit_price:.6f} | "
              f"Kâr: {sign}{pnl_pct*100:.2f}% | Kom: -{commission:.4f} | Net: {sign}{net_pnl:.4f} USDT")'''

new = '''        print(f"[✓ KAPANIŞ] {symbol}{dca_info}{lev_info} | {reason} | Çıkış: {exit_price:.6f} | "
              f"Kâr: {sign}{pnl_pct*100:.2f}% | Kom: -{commission:.4f} | Net: {sign}{net_pnl:.4f} USDT")
        
        # ⚡ Telegram bildirimi
        try:
            asyncio.create_task(telegram_notifier.notify_close(
                symbol=symbol,
                trade_type=trade["trade_type"],
                entry_price=avg_price,
                exit_price=exit_price,
                pnl_pct=pnl_pct * 100,
                net_pnl=net_pnl,
                reason=reason,
                dca_count=dca_count,
            ))
        except Exception as _e:
            print(f"[TG] Kapanış bildirim hatası: {_e}")'''

if old in pm:
    pm = pm.replace(old, new, 1)
    print("[5/6] position_manager: kapanış bildirimi eklendi")
else:
    print("[5/6] UYARI: kapanış print pattern bulunamadi")

with open(PM_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(pm.replace('\n', '\r\n'))

# ============================================================
# 5. .env - şablon satırlar ekle
# ============================================================
with open(ENV_SRC, 'r', encoding='utf-8', newline='') as f:
    env = f.read().replace('\r\n', '\n')

if 'TELEGRAM_BOT_TOKEN' not in env:
    env = env.rstrip() + '\n\n# Telegram Bildirim\nTELEGRAM_BOT_TOKEN=\nTELEGRAM_CHAT_ID=\n'
    print("[6/6] .env: Telegram şablon satırları eklendi")
else:
    print("[6/6] .env: Telegram satırları zaten var")

with open(ENV_SRC, 'w', encoding='utf-8', newline='') as f:
    f.write(env.replace('\n', '\r\n'))

print()
print("=" * 60)
print("BASARILI!")
print("=" * 60)
print()
print("SIMDI YAPILACAKLAR:")
print()
print("1. .env dosyasini ac ve SU 2 SATIRI DOLDUR:")
print("   TELEGRAM_BOT_TOKEN=123456:ABC-DEF...")
print("   TELEGRAM_CHAT_ID=123456789")
print()
print("   Token almak icin: Telegram'da @BotFather -> /newbot")
print("   Chat ID almak icin: @userinfobot'a /start yaz")
print()
print("2. Backend'i Ctrl+C ile durdur")
print("3. py -m uvicorn backend.main:app --reload")
print("4. Test: curl.exe -X POST http://127.0.0.1:8000/api/telegram/test")
print()
print("Geri donmek icin:")
for src, bak in [(MAIN_SRC, MAIN_BAK), (SE_SRC, SE_BAK), (PM_SRC, PM_BAK), (ENV_SRC, ENV_BAK)]:
    if os.path.exists(bak):
        print(f"  copy /Y {bak} {src}")