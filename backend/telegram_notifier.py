import os
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
        f"{emoji} <b>YENİ SİNYAL</b>\n"
        f"\n"
        f"<b>Sembol:</b> {symbol}\n"
        f"<b>Strateji:</b> {strategy}\n"
        f"<b>Yön:</b> {signal_type}\n"
        f"<b>Fiyat:</b> {_fmt_price(price)} USDT\n"
        f"<b>Tutar:</b> {total_usdt:.2f} USDT"
    )
    return await send_telegram_message(text)


async def notify_close(
    symbol: str, trade_type: str, entry_price: float, exit_price: float,
    pnl_pct: float, net_pnl: float, reason: str, dca_count: int = 0
):
    """Pozisyon kapanış bildirimi."""
    is_profit = net_pnl >= 0
    emoji = "🥳" if is_profit else "😮"
    sign = "+" if is_profit else ""
    side = "LONG" if trade_type == "BUY" else "SHORT"
    dca_info = f" (DCA:{dca_count})" if dca_count > 0 else ""
    
    text = (
        f"{emoji} <b>POZİSYON KAPANDI</b>\n"
        f"\n"
        f"<b>Sembol:</b> {symbol}{dca_info}\n"
        f"<b>Yön:</b> {side}\n"
        f"<b>Giriş:</b> {_fmt_price(entry_price)}\n"
        f"<b>Çıkış:</b> {_fmt_price(exit_price)}\n"
        f"<b>Sebep:</b> {reason}\n"
        f"<b>Kâr:</b> {sign}{pnl_pct:.2f}%\n"
        f"<b>Net:</b> {sign}{net_pnl:.4f} USDT"
    )
    return await send_telegram_message(text)


async def notify_error(message: str):
    """Hata bildirimi."""
    text = f"⚠️ <b>BOT HATASI</b>\n\n<code>{message[:500]}</code>"
    return await send_telegram_message(text)


async def notify_delisting(symbol: str):
    """Delist uyarısı."""
    text = f"🚫 <b>DELIST</b>\n\n<b>{symbol}</b> delist edildi. Pozisyon kapatılıyor."
    return await send_telegram_message(text)


async def notify_startup():
    """Bot başlatıldığında."""
    text = "🚀 <b>Broker System</b>\n\nStrateji motoru <b>AKTİF</b> edildi."
    return await send_telegram_message(text)


async def notify_shutdown(reason: str = ""):
    """Bot durdurulduğunda."""
    text = f"⏹ <b>Broker System</b>\n\nStrateji motoru <b>PASİF</b> edildi.\n{reason}"
    return await send_telegram_message(text)
