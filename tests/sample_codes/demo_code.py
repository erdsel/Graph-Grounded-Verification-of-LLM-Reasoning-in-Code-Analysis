
# =============================================================================
# ÖRNEK KOD: Hesap Makinesi Uygulaması
# =============================================================================

MAX_VALUE = 1000
DEBUG_MODE = True

class Calculator:
    """Basit bir hesap makinesi sınıfı."""

    def __init__(self, name: str = "Calculator"):
        self.name = name
        self.result = 0
        self.history = []

    def add(self, a: int, b: int) -> int:
        """İki sayıyı toplar."""
        self.result = a + b
        self._log_operation("add", self.result)
        self._validate()
        return self.result

    def multiply(self, a: int, b: int) -> int:
        """İki sayıyı çarpar."""
        self.result = a * b
        self._log_operation("multiply", self.result)
        self._validate()
        return self.result

    def _validate(self):
        """Sonucu doğrular."""
        if self.result > MAX_VALUE:
            print(f"Uyarı: Sonuç {MAX_VALUE} değerini aştı!")

    def _log_operation(self, operation: str, result: int):
        """İşlemi geçmişe kaydeder."""
        self.history.append(f"{operation}: {result}")
        if DEBUG_MODE:
            print(f"[LOG] {operation} = {result}")


def process_numbers(numbers: list) -> int:
    """Bir sayı listesini işler ve toplamı döndürür."""
    calc = Calculator("Main Calculator")
    total = 0

    for num in numbers:
        total = calc.add(total, num)

    return total


def generate_report(value: int) -> str:
    """Sonuç raporu oluşturur."""
    return f"Hesaplanan değer: {value}"


def main():
    """Ana fonksiyon."""
    # Veriyi hazırla
    data = [10, 20, 30, 40, 50]

    # İşle
    result = process_numbers(data)

    # Raporla
    report = generate_report(result)
    print(report)

    # Kaydet
    save_to_file(result)


def save_to_file(value: int):
    """Sonucu dosyaya kaydeder."""
    with open("result.txt", "w") as f:
        f.write(str(value))
    print("Sonuç kaydedildi!")


if __name__ == "__main__":
    main()
