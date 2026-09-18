from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """Tüm stratejilerin kalıtacağı temel sınıf."""

    name = "BASE"

    def __init__(self, params: dict):
        self.params = params or {}

    @abstractmethod
    def evaluate(self, candles: list, current_position: dict = None) -> dict:
        """
        Mumları ve mevcut pozisyonu alır, sinyal döner.

        Args:
            candles: [{time, open, high, low, close, volume}, ...]
            current_position: Açık pozisyon varsa dict, yoksa None

        Returns:
            {
                "signal": "LONG" | "SHORT" | "CLOSE" | None,
                "reason": "açıklama metni",
                "entry_price": float (signal varsa),
                "meta": {...} (opsiyonel ek bilgi)
            }
        """
        pass