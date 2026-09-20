import os
from dotenv import load_dotenv
from pathlib import Path

ENV_PATH = Path('.env')
load_dotenv(dotenv_path=ENV_PATH, override=True)

API_KEY = os.getenv("BINANCE_API_KEY", "")
API_SECRET = os.getenv("BINANCE_API_SECRET", "")
USE_TESTNET = os.getenv("BINANCE_TESTNET", "true").lower() == "true"
ORDER_TEST_MODE = os.getenv("ORDER_TEST_MODE", "(yok)")

print("=" * 70)
print("TESTNET DURUM KONTROLU")
print("=" * 70)
print()
print(f"  .env dosyasi       : {'VAR' if ENV_PATH.exists() else 'YOK'}")
print(f"  BINANCE_TESTNET    : {USE_TESTNET}")
print(f"  ORDER_TEST_MODE    : {ORDER_TEST_MODE}")
print(f"  API_KEY            : {'VAR' if API_KEY else 'YOK'} ({API_KEY[:8]}...)" if API_KEY else "  API_KEY            : YOK")
print()

if not API_KEY or not API_SECRET:
    print("!! API key eksik, kontrol edilemiyor.")
    exit(0)

# Binance baglantisi
print("[BINANCE TESTNET BAGLANTISI]")
print("-" * 70)
try:
    from binance.client import Client
    client = Client(API_KEY, API_SECRET, testnet=USE_TESTNET)
    
    # Hesap bilgisi
    account = client.futures_account()
    print(f"  Baglanti           : BASARILI")
    print(f"  Toplam Cuzdan      : {account.get('totalWalletBalance', 0)} USDT")
    print(f"  Kullanilabilir     : {account.get('availableBalance', 0)} USDT")
    print(f"  Acik PnL           : {account.get('totalUnrealizedProfit', 0)} USDT")
    print()
    
    # Mevcut pozisyonlar
    positions = client.futures_position_information()
    active = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
    print(f"[POZISYONLAR]")
    print(f"  Aktif pozisyon sayisi: {len(active)}")
    for p in active[:10]:
        sym = p.get('symbol')
        amt = p.get('positionAmt')
        entry = p.get('entryPrice')
        pnl = p.get('unRealizedProfit')
        lev = p.get('leverage')
        liq = p.get('liquidationPrice')
        print(f"    {sym:<15} | amt={amt:<10} | entry={entry:<12} | lev={lev}x | liq={liq:<12} | pnl={pnl}")
    print()
    
    # Açık emirler
    open_orders = client.futures_get_open_orders()
    print(f"[ACIK EMIRLER] Toplam: {len(open_orders)}")
    for o in open_orders[:5]:
        print(f"    {o['symbol']:<15} | {o['type']:<20} | side={o['side']}")
    print()
    
    # Rate limit
    print(f"[RATE LIMIT]")
    print(f"  Kullanilan: ~%5 (tahmin)")
    print()
    
except Exception as e:
    print(f"  HATA: {e}")
    import traceback
    traceback.print_exc()

print("=" * 70)