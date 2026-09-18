import asyncio
from binance.client import Client
from backend.indicators import calculate_rsi
from backend.database import get_db_connection


class BotEngine:
    def __init__(self, client: Client, symbol: str = "BTCUSDT", order_manager=None):
        self.client = client
        self.symbol = symbol
        self.order_manager = order_manager
        self.is_running = False
        self.latest_data = {}

    def has_active_position(self) -> bool:
        """Veritabanında açık pozisyon kontrolü"""
        conn = get_db_connection()
        row = conn.execute(
            "SELECT id FROM active_trades WHERE symbol = ?",
            (self.symbol,)
        ).fetchone()
        conn.close()
        return row is not None

    async def start(self):
        self.is_running = True
        print(f"[*] {self.symbol} için RSI(7) 5M Motoru Devrede.")

        while self.is_running:
            try:
                # ⚡ KRİTİK: Blocking Binance çağrısını ayrı thread'de çalıştır
                # Böylece FastAPI event loop'u bloke olmaz, sayfa donmaz
                klines = await asyncio.to_thread(
                    self.client.futures_klines,
                    symbol=self.symbol,
                    interval="5m",
                    limit=100
                )
                closes = [float(k[4]) for k in klines]
                current_price = closes[-1]

                # RSI(7) hesapla
                current_rsi = calculate_rsi(closes, period=7)

                # Sinyal kontrolü
                has_pos = self.has_active_position()

                if not has_pos:
                    if current_rsi < 20:
                        print(f"\n[!] RSI AŞIRI SATIM ({current_rsi} < 20) -> LONG (BUY) Emri Tetiklendi!")
                        if self.order_manager:
                            # ⚡ Order açma da blocking, ayrı thread'de çalıştır
                            await asyncio.to_thread(
                                self.order_manager.open_dca_position,
                                side="BUY",
                                base_amount_usdt=50.0
                            )

                    elif current_rsi > 80:
                        print(f"\n[!] RSI AŞIRI ALIM ({current_rsi} > 80) -> SHORT (SELL) Emri Tetiklendi!")
                        if self.order_manager:
                            await asyncio.to_thread(
                                self.order_manager.open_dca_position,
                                side="SELL",
                                base_amount_usdt=50.0
                            )

                self.latest_data = {
                    "symbol": self.symbol,
                    "price": current_price,
                    "rsi": current_rsi,
                    "status": "Running",
                    "has_position": has_pos
                }

            except Exception as e:
                self.latest_data["error"] = str(e)
                print(f"[!] Hata: {e}")

            # 5 saniyede bir döngü
            await asyncio.sleep(5)

    def stop(self):
        self.is_running = False