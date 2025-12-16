# =============================================================================
# TEST 1: BASIT HESAP MAKİNESİ
# Zorluk: KOLAY | Graf: Zengin cagri zinciri
# =============================================================================
# Beklenen: LLM bu yapiyi dogru analiz etmeli
# Potansiyel Halusinasyon: Olmayan fonksiyonlar ekleme

def add(a, b):
    """Iki sayiyi toplar."""
    result = a + b
    log_operation("add", result)
    return result

def subtract(a, b):
    """Iki sayiyi cikarir."""
    result = a - b
    log_operation("subtract", result)
    return result

def multiply(a, b):
    """Iki sayiyi carpar."""
    result = a * b
    log_operation("multiply", result)
    return result

def divide(a, b):
    """Iki sayiyi boler."""
    validate_divisor(b)
    result = a / b
    log_operation("divide", result)
    return result

def validate_divisor(value):
    """Bolenin sifir olmadigini kontrol eder."""
    if value == 0:
        handle_error("Division by zero!")

def handle_error(message):
    """Hata mesajini isler."""
    log_operation("error", message)

def log_operation(operation, value):
    """Islemi loglar."""
    pass

def calculate(operation, x, y):
    """Ana hesaplama fonksiyonu."""
    if operation == "add":
        return add(x, y)
    elif operation == "subtract":
        return subtract(x, y)
    elif operation == "multiply":
        return multiply(x, y)
    elif operation == "divide":
        return divide(x, y)

def main():
    """Program giris noktasi."""
    result1 = calculate("add", 10, 5)
    result2 = calculate("multiply", result1, 2)
    result3 = calculate("divide", result2, 3)
    return result3


# =============================================================================
# BEKLENEN CALL GRAPH:
# =============================================================================
# main --> calculate --> add --> log_operation
#                    --> subtract --> log_operation
#                    --> multiply --> log_operation
#                    --> divide --> validate_divisor --> handle_error --> log_operation
#                                --> log_operation
#
# Toplam Fonksiyon: 9
# Toplam Cagri Iliskisi: 12
# =============================================================================
