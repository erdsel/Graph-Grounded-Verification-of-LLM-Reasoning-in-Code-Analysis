
import os
from typing import List, Optional

# Global sabitler
MAX_ITEMS = 100
DEBUG = True

class DataProcessor:
    """
    Veri işleme sınıfı.
    Verileri okur, işler ve kaydeder.
    """

    def __init__(self, name: str):
        """DataProcessor'ı başlatır."""
        self.name = name
        self.data = []
        self.processed = False

    def load_data(self, items: List[int]) -> None:
        """Veriyi yükler."""
        self.data = items
        self._validate_data()
        print(f"[{self.name}] {len(items)} öğe yüklendi")

    def _validate_data(self) -> bool:
        """Veriyi doğrular."""
        if len(self.data) > MAX_ITEMS:
            print("Uyarı: Maksimum öğe sayısı aşıldı!")
            return False
        return True

    def process(self) -> List[int]:
        """Veriyi işler ve sonucu döndürür."""
        if not self.data:
            return []

        result = []
        for item in self.data:
            processed_item = self._transform(item)
            result.append(processed_item)

        self.processed = True
        self._log_result(result)
        return result

    def _transform(self, value: int) -> int:
        """Tek bir değeri dönüştürür."""
        return value * 2

    def _log_result(self, result: List[int]) -> None:
        """Sonucu loglar."""
        if DEBUG:
            print(f"[{self.name}] İşlenen öğe sayısı: {len(result)}")


class Calculator:
    """Basit hesap makinesi."""

    def __init__(self):
        self.result = 0

    def add(self, a: int, b: int) -> int:
        """İki sayıyı toplar."""
        self.result = a + b
        return self.result

    def subtract(self, a: int, b: int) -> int:
        """İki sayıyı çıkarır."""
        self.result = a - b
        return self.result


def initialize_system() -> DataProcessor:
    """Sistemi başlatır."""
    processor = DataProcessor("MainProcessor")
    return processor


def run_processing(processor: DataProcessor, data: List[int]) -> List[int]:
    """İşleme sürecini çalıştırır."""
    processor.load_data(data)
    result = processor.process()
    return result


def calculate_statistics(data: List[int]) -> dict:
    """İstatistikleri hesaplar."""
    if not data:
        return {"sum": 0, "avg": 0, "count": 0}

    total = sum(data)
    count = len(data)
    average = total / count

    return {
        "sum": total,
        "avg": average,
        "count": count
    }


def generate_report(stats: dict) -> str:
    """Rapor oluşturur."""
    report = f"""
    === RAPOR ===
    Toplam: {stats['sum']}
    Ortalama: {stats['avg']:.2f}
    Sayı Adedi: {stats['count']}
    =============
    """
    return report


def save_report(report: str, filename: str) -> None:
    """Raporu dosyaya kaydeder."""
    with open(filename, 'w') as f:
        f.write(report)
    print(f"Rapor kaydedildi: {filename}")


def main():
    """Ana fonksiyon."""
    # Sistemi başlat
    processor = initialize_system()

    # Veriyi hazırla
    sample_data = [10, 20, 30, 40, 50]

    # İşle
    processed_data = run_processing(processor, sample_data)

    # İstatistikleri hesapla
    stats = calculate_statistics(processed_data)

    # Rapor oluştur
    report = generate_report(stats)
    print(report)

    # Kaydet
    save_report(report, "output.txt")

