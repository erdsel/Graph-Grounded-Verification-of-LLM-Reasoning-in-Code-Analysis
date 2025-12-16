"""
=============================================================================
LLM DOĞRULAMA SİSTEMİ - ÖRNEK PYTHON KODLARI
=============================================================================
Bu dosya, web arayüzünde test edebileceğiniz örnek kodları içerir.
Her örneği kopyalayıp http://localhost:5000 adresindeki editöre yapıştırın.

Kodlar basit -> karmaşık sıralamasıyla düzenlenmiştir.
=============================================================================
"""

# =============================================================================
# ÖRNEK 1: TEK FONKSİYON (Basit)
# =============================================================================
# Beklenen: factorial -> range çağrısı
"""
def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

print(factorial(5))
"""

# =============================================================================
# ÖRNEK 2: İKİ FONKSİYON - BİRBİRİNİ ÇAĞIRAN
# =============================================================================
# Beklenen:
#   - is_even -> (hiçbir şey çağırmıyor, sadece modulo)
#   - check_number -> is_even çağrısı
#   - <module> -> check_number çağrısı
"""
def is_even(num):
    return num % 2 == 0

def check_number(x):
    if is_even(x):
        return "Çift"
    return "Tek"

result = check_number(10)
print(result)
"""

# =============================================================================
# ÖRNEK 3: ASAL SAYI KONTROLÜ
# =============================================================================
# Beklenen:
#   - is_prime -> range çağrısı
#   - <module> -> is_prime çağrısı
"""
def is_prime(num):
    if num < 2:
        return False
    for i in range(2, int(num ** 0.5) + 1):
        if num % i == 0:
            return False
    return True

number = 17
if is_prime(number):
    print(f"{number} asal sayıdır")
else:
    print(f"{number} asal sayı değildir")
"""

# =============================================================================
# ÖRNEK 4: ÜÇ FONKSİYON ZİNCİRİ
# =============================================================================
# Beklenen:
#   - add -> (hiçbir şey)
#   - multiply -> (hiçbir şey)
#   - calculate -> add, multiply çağrıları
#   - <module> -> calculate çağrısı
"""
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

def calculate(x, y):
    sum_result = add(x, y)
    product = multiply(x, y)
    return sum_result, product

result = calculate(5, 3)
print(result)
"""

# =============================================================================
# ÖRNEK 5: REKÜRSİF FONKSİYON
# =============================================================================
# Beklenen:
#   - fibonacci -> fibonacci (kendi kendini çağırıyor)
#   - <module> -> fibonacci çağrısı
"""
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

for i in range(10):
    print(fibonacci(i), end=" ")
"""

# =============================================================================
# ÖRNEK 6: YARDIMCI FONKSİYONLU HESAPLAMA
# =============================================================================
# Beklenen:
#   - square -> (hiçbir şey)
#   - cube -> (hiçbir şey)
#   - sum_of_powers -> square, cube, range çağrıları
#   - <module> -> sum_of_powers çağrısı
"""
def square(x):
    return x * x

def cube(x):
    return x * x * x

def sum_of_powers(n):
    total = 0
    for i in range(1, n + 1):
        total += square(i) + cube(i)
    return total

result = sum_of_powers(5)
print(f"Toplam: {result}")
"""

# =============================================================================
# ÖRNEK 7: LİSTE İŞLEMLERİ
# =============================================================================
# Beklenen:
#   - filter_positive -> (hiçbir şey, list comprehension)
#   - calculate_average -> len, sum çağrıları
#   - process_numbers -> filter_positive, calculate_average çağrıları
#   - <module> -> process_numbers çağrısı
"""
def filter_positive(numbers):
    return [n for n in numbers if n > 0]

def calculate_average(numbers):
    if len(numbers) == 0:
        return 0
    return sum(numbers) / len(numbers)

def process_numbers(data):
    positive = filter_positive(data)
    avg = calculate_average(positive)
    return positive, avg

numbers = [-5, 10, -3, 8, 15, -2, 7]
result = process_numbers(numbers)
print(result)
"""

# =============================================================================
# ÖRNEK 8: SINIF TABANLI (Class)
# =============================================================================
# Beklenen:
#   - Calculator sınıfı, add/subtract/multiply/divide metodları
#   - <module> -> Calculator çağrısı (instance oluşturma)
"""
class Calculator:
    def __init__(self):
        self.result = 0

    def add(self, x):
        self.result += x
        return self.result

    def subtract(self, x):
        self.result -= x
        return self.result

    def multiply(self, x):
        self.result *= x
        return self.result

    def divide(self, x):
        if x != 0:
            self.result /= x
        return self.result

calc = Calculator()
calc.add(10)
calc.multiply(2)
print(calc.result)
"""

# =============================================================================
# ÖRNEK 9: İÇ İÇE FONKSİYON ÇAĞRILARI
# =============================================================================
# Beklenen:
#   - validate -> len çağrısı
#   - transform -> upper çağrısı (string metodu)
#   - process -> validate, transform çağrıları
#   - main -> process çağrısı
#   - <module> -> main çağrısı
"""
def validate(text):
    return len(text) > 0

def transform(text):
    return text.upper()

def process(data):
    if validate(data):
        return transform(data)
    return None

def main():
    result = process("hello world")
    print(result)

main()
"""

# =============================================================================
# ÖRNEK 10: KARMAŞIK SENARYO
# =============================================================================
# Beklenen:
#   - get_divisors -> range çağrısı
#   - is_perfect -> get_divisors, sum çağrıları
#   - find_perfect_numbers -> range, is_perfect çağrıları
#   - <module> -> find_perfect_numbers çağrısı
"""
def get_divisors(n):
    divisors = []
    for i in range(1, n):
        if n % i == 0:
            divisors.append(i)
    return divisors

def is_perfect(n):
    divisors = get_divisors(n)
    return sum(divisors) == n

def find_perfect_numbers(limit):
    perfect = []
    for num in range(2, limit):
        if is_perfect(num):
            perfect.append(num)
    return perfect

result = find_perfect_numbers(100)
print(f"Mükemmel sayılar: {result}")
"""

# =============================================================================
# KULLANIM TALİMATI
# =============================================================================
"""
1. Web arayüzünü açın: http://localhost:5000
2. Yukarıdaki örneklerden birini seçin
3. Üç tırnak (''') içindeki kodu kopyalayın
4. Editöre yapıştırın
5. "Analiz Et" butonuna tıklayın
6. Sonuçları inceleyin:
   - Yeşil: LLM doğru tespit etti
   - Kırmızı: LLM halüsinasyon üretti (yanlış iddia)
   - Sarı: LLM kaçırdı (gerçekte var ama LLM bulamadı)
"""
