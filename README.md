# Graph-Grounded Verification of LLM Reasoning in Code Analysis

<p align="center">
  <img src="gorsel/logo.png" alt="Project Logo" width="200"/>
</p>

<p align="center">
  <strong>LLM Halusinasyonlarinin Graf Tabanli Tespiti</strong><br>
  Buyuk Dil Modellerinin kod analizi sirasinda urettigi yanlis iddialarin<br>
  statik analiz ve graf sorgulama ile dogrulanmasi
</p>

<p align="center">
  <a href="#problem">Problem</a> •
  <a href="#cozum">Cozum</a> •
  <a href="#mimari">Mimari</a> •
  <a href="#kurulum">Kurulum</a> •
  <a href="#kullanim">Kullanim</a> •
  <a href="#sonuclar">Sonuclar</a>
</p>

---

## Proje Bilgileri

| | |
|---|---|
| **Ogrenci** | Selen Erdogan |
| **Ogrenci No** | 210104004131 |
| **Universite** | Gebze Teknik Universitesi |
| **Bolum** | Bilgisayar Muhendisligi |
| **Ders** | NLP (Dogal Dil Isleme) |
| **Donem** | 2024-2025 Guz |

---

## Icindekiler

1. [Problem Tanimi](#problem)
2. [Onerilen Cozum](#cozum)
3. [Teorik Arka Plan](#teorik-arka-plan)
4. [Sistem Mimarisi](#mimari)
5. [Teknolojiler](#teknolojiler)
6. [Modul Detaylari](#modul-detaylari)
7. [Kurulum](#kurulum)
8. [Kullanim](#kullanim)
9. [Test Senaryolari](#test-senaryolari)
10. [Deneysel Sonuclar](#sonuclar)
11. [Bilinen Kisitlamalar](#kisitlamalar)
12. [Gelecek Calisma](#gelecek-calisma)
13. [Akademik Referanslar](#referanslar)

---

<a name="problem"></a>
## 1. Problem Tanimi

### 1.1 LLM Halusinasyonu Nedir?

Buyuk Dil Modelleri (LLM), dogal dil isleme alaninda devrim yaratmis olsa da, **halusinasyon** problemi kritik bir sinirlilik olarak karsimiza cikmaktadir. Halusinasyon, modelin:

- **Gercekte olmayan** bilgiler uretmesi
- **Yanlis iliskiler** kurmasI
- **Var olmayan** fonksiyon/degisken/sinif iddialari olusturmasi

durumlarini ifade eder.

### 1.2 Kod Analizinde Halusinasyon Ornekleri

```python
# Ornek Kod
def calculate_total(items):
    subtotal = sum(item.price for item in items)
    tax = calculate_tax(subtotal)
    return subtotal + tax

def calculate_tax(amount):
    return amount * 0.18
```

**LLM'nin Potansiyel Halusinasyonlari:**

| LLM Iddiasi | Gercek Durum | Sonuc |
|-------------|--------------|-------|
| "calculate_total, sum fonksiyonunu cagiriyor" | sum built-in, kullanici tanimli degil | Belirsiz |
| "calculate_total, validate_items fonksiyonunu cagiriyor" | Bu fonksiyon YOK | **HALUSINASYON** |
| "calculate_tax, logging yapiyor" | Boyle bir cagri YOK | **HALUSINASYON** |
| "calculate_total, calculate_tax'i cagiriyor" | DOGRU | Gecerli |

### 1.3 Problemin Onemi

LLM halusinasyonlari ozellikle su alanlarda kritik sorunlara yol acar:

1. **Kod Dokumantasyonu**: Yanlis API dokumantasyonu
2. **Kod Review**: Var olmayan guvenlik aciklari raporu
3. **Debugging Asistani**: Yanlis hata kaynaklari gosterme
4. **Kod Aciklama**: Olmayan bagimliliklari iddia etme

### 1.4 Mevcut Yaklasimlarin Yetersizligi

| Yaklasim | Problem |
|----------|---------|
| **Self-consistency** | Model kendi hatasini tekrar edebilir |
| **Retrieval-based** | Kod icin uygun retrieval zor |
| **Fine-tuning** | Her dil/domain icin yeniden egitim |
| **Prompt engineering** | Garantili sonuc yok |

---

<a name="cozum"></a>
## 2. Onerilen Cozum

### 2.1 Graf Tabanli Dogrulama (Graph-Grounded Verification)

Bu projede, halusinasyon tespitini bir **graf sorgulama problemi** olarak yeniden formule ediyoruz:

```
┌─────────────────────────────────────────────────────────────────┐
│                    TEMEL FIKIR                                   │
├─────────────────────────────────────────────────────────────────┤
│  1. Kaynak kodu AST ile parse et → GROUND TRUTH (gercek durum)  │
│  2. Ground truth'u graf yapisina donustur (Call Graph)          │
│  3. LLM'den ayni kod hakkinda iddialar al                       │
│  4. Her LLM iddiasini graf uzerinde SORGULA                     │
│  5. Graf'ta yoksa → HALUSINASYON                                │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Cozumun Avantajlari

| Avantaj | Aciklama |
|---------|----------|
| **Deterministic** | AST parsing her zaman ayni sonucu verir |
| **Verifiable** | Graf sorgulari kesin True/False dondurur |
| **Language-agnostic** | Herhangi bir programlama diline uyarlanabilir |
| **No training** | Ek egitim gerektirmez |
| **Explainable** | Neden halusinasyon oldugu aciklanabilir |

### 2.3 Formal Tanım

```
G = (V, E)  Graf yapisi
V = {f1, f2, ..., fn}  Dugumler (fonksiyonlar)
E = {(fi, fj) | fi, fj'yi cagiriyor}  Kenarlar (cagri iliskileri)

LLM Iddiasi: claim(caller, callee)
Dogrulama: verify(claim) = (caller, callee) ∈ E ? VALID : HALLUCINATION
```

---

<a name="teorik-arka-plan"></a>
## 3. Teorik Arka Plan

### 3.1 Abstract Syntax Tree (AST)

AST, kaynak kodun **soyut sozdizimsel temsili**dir. Her dugum bir programlama yapisini temsil eder:

```
         Module
            |
      FunctionDef (calculate_total)
      /     |      \
  args   Assign    Return
           |          |
        BinOp      BinOp
        /   \      /   \
    Call  Call  Name  Name
     |      |
   sum  calculate_tax
```

### 3.2 Call Graph (Cagri Grafi)

Call Graph, programdaki fonksiyonlar arasi cagri iliskilerini gosteren **yonlu graf**tir:

```
     calculate_total
           |
           v
     calculate_tax
```

**Kenar (Edge)** = "A fonksiyonu B fonksiyonunu cagiriyor"

### 3.3 Halusinasyon Tespiti Formulu

```
Precision = TP / (TP + FP)
          = Dogru Tespitler / (Dogru + Halusinasyonlar)

Recall = TP / (TP + FN)
       = Dogru Tespitler / (Dogru + Kacirilanlar)

F1 = 2 * (Precision * Recall) / (Precision + Recall)

Halusinasyon Orani = FP / (TP + FP)
                   = Halusinasyonlar / Toplam LLM Iddia
```

---

<a name="mimari"></a>
## 4. Sistem Mimarisi

### 4.1 Genel Mimari

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           KULLANICI ARAYUZU                             │
│                    (Web UI / CLI / API)                                 │
└─────────────────────────────────────────┬───────────────────────────────┘
                                          │
                                          v
┌─────────────────────────────────────────────────────────────────────────┐
│                              FLASK API                                   │
│                           (app.py - /api/analyze)                       │
└─────────────────────────────────────────┬───────────────────────────────┘
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    │                                           │
                    v                                           v
┌───────────────────────────────────┐       ┌───────────────────────────────────┐
│        GROUND TRUTH PIPELINE      │       │          LLM PIPELINE             │
│  ┌─────────────────────────────┐  │       │  ┌─────────────────────────────┐  │
│  │       AST Parser            │  │       │  │       LLM Client            │  │
│  │   (ast_parser.py)           │  │       │  │    (llm_client.py)          │  │
│  │                             │  │       │  │                             │  │
│  │  • Fonksiyon cikarimi       │  │       │  │  • Groq (Llama 3.3 70B)     │  │
│  │  • Sinif cikarimi           │  │       │  │  • Google Gemini            │  │
│  │  • Cagri iliskileri         │  │       │  │  • Mock (test icin)         │  │
│  │  • Degisken analizi         │  │       │  │                             │  │
│  └──────────────┬──────────────┘  │       │  └──────────────┬──────────────┘  │
│                 │                 │       │                 │                 │
│                 v                 │       │                 v                 │
│  ┌─────────────────────────────┐  │       │  ┌─────────────────────────────┐  │
│  │      Graph Builder          │  │       │  │     Claim Extractor         │  │
│  │   (graph_builder.py)        │  │       │  │   (claim_extractor.py)      │  │
│  │                             │  │       │  │                             │  │
│  │  • Call Graph (NetworkX)    │  │       │  │  • JSON parsing             │  │
│  │  • Data Flow Graph          │  │       │  │  • Regex extraction         │  │
│  │  • Graf sorgulama           │  │       │  │  • Claim normalization      │  │
│  └──────────────┬──────────────┘  │       │  └──────────────┬──────────────┘  │
└─────────────────┼─────────────────┘       └─────────────────┼─────────────────┘
                  │                                           │
                  └─────────────────────┬─────────────────────┘
                                        │
                                        v
                    ┌───────────────────────────────────────┐
                    │           ENTITY MAPPER               │
                    │        (entity_mapper.py)             │
                    │                                       │
                    │  • Exact match: "main" = "main"       │
                    │  • Alias match: "init" = "__init__"   │
                    │  • Fuzzy match: "calc" ≈ "calculate"  │
                    │  • Case normalization                 │
                    └───────────────────┬───────────────────┘
                                        │
                                        v
                    ┌───────────────────────────────────────┐
                    │             VERIFIER                  │
                    │           (verifier.py)               │
                    │                                       │
                    │  Input: LLM claim + Graph             │
                    │  Output: VALID | HALLUCINATION        │
                    │          | UNVERIFIABLE               │
                    └───────────────────┬───────────────────┘
                                        │
                                        v
                    ┌───────────────────────────────────────┐
                    │             METRICS                   │
                    │           (metrics.py)                │
                    │                                       │
                    │  • Precision, Recall, F1              │
                    │  • Hallucination Rate                 │
                    │  • Coverage                           │
                    └───────────────────────────────────────┘
```

### 4.2 Veri Akisi

```
Python Kodu
     │
     ├──────────────────────────────────────┐
     │                                      │
     v                                      v
┌─────────────┐                    ┌─────────────┐
│ AST Parser  │                    │ LLM Analizi │
└──────┬──────┘                    └──────┬──────┘
       │                                  │
       v                                  v
┌─────────────────────┐        ┌─────────────────────┐
│ Ground Truth        │        │ LLM Claims          │
│ {                   │        │ [                   │
│   "functions": [    │        │   {                 │
│     {               │        │     "caller": "A",  │
│       "name": "A",  │        │     "callee": "B"   │
│       "calls": ["B"]│        │   },                │
│     }               │        │   {                 │
│   ],                │        │     "caller": "A",  │
│   "call_graph": [   │        │     "callee": "X"   │  <-- Halusinasyon?
│     {"A" -> "B"}    │        │   }                 │
│   ]                 │        │ ]                   │
│ }                   │        │                     │
└──────────┬──────────┘        └──────────┬──────────┘
           │                              │
           └──────────────┬───────────────┘
                          │
                          v
               ┌─────────────────────┐
               │    KARSILASTIRMA    │
               │                     │
               │  A->B ∈ Ground Truth│
               │  A->B ∈ LLM Claims  │
               │  ─────────────────  │
               │  MATCH! (Dogru)     │
               │                     │
               │  A->X ∉ Ground Truth│
               │  A->X ∈ LLM Claims  │
               │  ─────────────────  │
               │  HALLUCINATION!     │
               └─────────────────────┘
```

### 4.3 Karsilastirma Algoritmasi

```python
def compare_calls(ground_truth, llm_claims):
    """
    Ground truth ve LLM iddialarini karsilastirir.

    Eslestirme Stratejisi:
    1. Tam eslestirme: "DataProcessor.__init__" == "DataProcessor.__init__"
    2. Base eslestirme: "__init__" == "__init__" (sinif prefiksi farki tolere edilir)
    """

    matched = []
    hallucinations = []
    missed = []

    for truth_call in ground_truth:
        found = False
        for llm_call in llm_claims:
            if calls_match(truth_call, llm_call):  # Fuzzy matching
                matched.append(truth_call)
                found = True
                break
        if not found:
            missed.append(truth_call)

    for llm_call in llm_claims:
        if not any(calls_match(t, llm_call) for t in ground_truth):
            hallucinations.append(llm_call)

    return matched, hallucinations, missed
```

---

<a name="teknolojiler"></a>
## 5. Teknolojiler

### 5.1 Backend

| Teknoloji | Versiyon | Amac | Dosya |
|-----------|----------|------|-------|
| **Python** | 3.10+ | Ana programlama dili | - |
| **Flask** | 3.0+ | Web framework | `app.py` |
| **NetworkX** | 3.0+ | Graf veri yapisi | `graph_builder.py` |
| **Groq SDK** | 0.4+ | LLM API client | `llm_client.py` |
| **Google GenAI** | 0.3+ | Gemini API client | `llm_client.py` |
| **FuzzyWuzzy** | 0.18+ | String eslestirme | `entity_mapper.py` |

### 5.2 Frontend

| Teknoloji | Amac |
|-----------|------|
| **vis.js** | Interaktif graf gorsellestirme |
| **Bootstrap 5** | Responsive UI framework |
| **CodeMirror** | Syntax highlighted kod editoru |
| **Chart.js** | Metrik gorsellestirme |

### 5.3 LLM Saglayicilari

| Saglayici | Model | Limit | Maliyet |
|-----------|-------|-------|---------|
| **Groq** | Llama 3.3 70B | 30 req/dk | Ucretsiz |
| **Google** | Gemini 2.0 Flash | 15 req/dk | Ucretsiz |
| **Mock** | - | Sinirsiz | - (Test) |

---

<a name="modul-detaylari"></a>
## 6. Modul Detaylari

### 6.1 AST Parser (`src/ast_parser.py`)

**Amac:** Python kaynak kodunu parse ederek yapisal bilgi cikarir.

**Cikarilan Bilgiler:**
```python
{
    "functions": {
        "function_name": {
            "lineno": 10,
            "args": ["param1", "param2"],
            "returns": "str",
            "calls": ["other_func", "helper"],
            "docstring": "Function description"
        }
    },
    "classes": {
        "ClassName": {
            "lineno": 25,
            "bases": ["BaseClass"],
            "methods": ["__init__", "process", "save"],
            "attributes": ["name", "value"]
        }
    },
    "variables": {
        "CONSTANT": {"value": 42, "lineno": 5}
    },
    "imports": ["os", "sys", "json"]
}
```

**Ornek Kullanim:**
```python
from src.ast_parser import ASTParser

parser = ASTParser()
result = parser.parse_code("""
class Calculator:
    def add(self, a, b):
        return a + b

    def multiply(self, a, b):
        result = a * b
        self.log(result)
        return result

    def log(self, value):
        print(f"Result: {value}")
""")

print(result["classes"]["Calculator"]["methods"])
# Output: ["add", "multiply", "log"]

print(result["functions"]["Calculator.multiply"]["calls"])
# Output: ["log"]
```

### 6.2 Graph Builder (`src/graph_builder.py`)

**Amac:** AST sonuclarindan graf yapilari olusturur.

**Graf Turleri:**

1. **Call Graph**: Fonksiyonlar arasi cagri iliskileri
2. **Data Flow Graph**: Veri akisi bagimliliklari

```python
from src.graph_builder import GraphBuilder

builder = GraphBuilder()
builder.build_from_ast_result(ast_result)

# Sorgulama
builder.has_call("main", "helper")  # True/False
builder.get_callees("process")      # ["validate", "save"]
builder.get_callers("log")          # ["process", "main"]
builder.find_path("A", "D")         # ["A", "B", "C", "D"]
```

**Graf Gorsellestirme:**
```
    main
   /    \
  v      v
process  log
   |
   v
validate
```

### 6.3 LLM Client (`src/llm_client.py`)

**Amac:** Farkli LLM saglayicilarini tek bir arayuz altinda toplar.

**Desteklenen Saglayicilar:**
```python
from src.llm_client import LLMClient

# Groq (Llama 3.3 70B)
client = LLMClient.create(provider="groq", api_key="gsk_xxx")

# Google Gemini
client = LLMClient.create(provider="gemini", api_key="AIza_xxx")

# Mock (test icin)
client = LLMClient.create(provider="mock")

# Auto (API key'e gore otomatik secim)
client = LLMClient.create(provider="auto", api_key="xxx")
```

**Prompt Stratejisi:**
```
Asagidaki Python kodunu analiz et ve SADECE kullanici tarafindan
TANIMLANMIS fonksiyonlar arasindaki cagri iliskilerini JSON formatinda don.

KURALLAR:
1. Built-in fonksiyonlari (print, len, range, vb.) DAHIL ETME
2. Sadece kodda TANIMLI fonksiyonlari listele
3. Bir fonksiyonun baska bir fonksiyonu CAGIRMASI = cagri iliskisi
4. Sirali calisma ≠ Cagri iliskisi

JSON FORMAT:
{
  "function_calls": [
    {"caller": "main", "callee": "process_data"},
    {"caller": "process_data", "callee": "validate"}
  ]
}
```

### 6.4 Claim Extractor (`src/claim_extractor.py`)

**Amac:** LLM ciktisini yapisal iddialara donusturur.

**Claim Turleri:**
```python
class ClaimType(Enum):
    CALL = "call"           # Fonksiyon cagrisi
    DATA_FLOW = "data_flow" # Veri akisi
    EXISTENCE = "existence" # Varlik iddiasi
    ATTRIBUTE = "attribute" # Ozellik iddiasi
```

**Cikarim Yontemleri:**
1. **JSON Parsing** (oncelikli): Structured output
2. **Regex Matching** (fallback): "A calls B", "A -> B" pattern'lari

```python
from src.claim_extractor import ClaimExtractor

extractor = ClaimExtractor()
claims = extractor.extract_claims(llm_response, reasoning_steps)

for claim in claims:
    print(f"{claim.subject} -> {claim.object} ({claim.claim_type})")
# Output:
# main -> process (call)
# process -> validate (call)
```

### 6.5 Entity Mapper (`src/entity_mapper.py`)

**Amac:** LLM'nin kullandigi isimleri gercek kod varliklarina esler.

**Eslestirme Stratejileri:**
```python
# 1. Exact Match (Guven: 1.0)
"calculate_total" -> "calculate_total"

# 2. Case-Insensitive (Guven: 0.95)
"Calculate_Total" -> "calculate_total"

# 3. Alias Match (Guven: 0.9)
"init" -> "__init__"
"constructor" -> "__init__"

# 4. Fuzzy Match (Guven: 0.7-0.9)
"calc_totl" -> "calculate_total"  # Levenshtein distance

# 5. Partial Match (Guven: 0.5-0.7)
"calc" -> "calculator"

# 6. Class Prefix Handling
"DataProcessor.__init__" -> "__init__" (base name)
"product.get_price" -> "get_price"
```

### 6.6 Verifier (`src/verifier.py`)

**Amac:** LLM iddialarini graf uzerinde dogrular.

**Dogrulama Sonuclari:**
```python
class VerificationResult(Enum):
    VALID = "valid"                   # Iddia dogru
    HALLUCINATION = "hallucination"   # Iddia yanlis (KRITIK!)
    UNVERIFIABLE = "unverifiable"     # Dogrulanamadi
    PARTIALLY_VALID = "partial"       # Kismen dogru
```

**Dogrulama Mantigi:**
```python
def verify_call_claim(claim, graph):
    caller = claim.subject
    callee = claim.object

    # Graf'ta kenar var mi?
    if graph.has_edge(caller, callee):
        return VerificationResult.VALID

    # Caller veya callee graf'ta yok mu?
    if caller not in graph.nodes or callee not in graph.nodes:
        return VerificationResult.UNVERIFIABLE

    # Graf'ta kenar yok = HALUSINASYON
    return VerificationResult.HALLUCINATION
```

### 6.7 Metrics (`src/metrics.py`)

**Hesaplanan Metrikler:**
```python
metrics = {
    "precision": 85.7,      # Dogru / (Dogru + Halusinasyon)
    "recall": 92.3,         # Dogru / (Dogru + Kacirilan)
    "f1_score": 88.9,       # Harmonik ortalama
    "hallucination_rate": 14.3,  # Halusinasyon / Toplam LLM
    "coverage": 92.3,       # Ne kadar ground truth kapsandi

    "total_ground_truth": 13,    # Gercek cagri sayisi
    "total_llm_claims": 14,      # LLM iddia sayisi
    "correct_claims": 12,        # Dogru tespitler
    "hallucinations": 2,         # Halusinasyonlar
    "missed": 1                  # Kacirilanlar
}
```

---

<a name="kurulum"></a>
## 7. Kurulum

### 7.1 Gereksinimler

- Python 3.10 veya uzeri
- pip paket yoneticisi
- (Opsiyonel) Groq veya Gemini API anahtari

### 7.2 Adim Adim Kurulum

```bash
# 1. Projeyi klonla
git clone https://github.com/username/nlp-proje.git
cd nlp-proje

# 2. Virtual environment olustur
python -m venv venv

# 3. Virtual environment'i aktive et
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 4. Bagimliliklari yukle
pip install -r requirements.txt

# 5. API anahtarini ayarla (opsiyonel)
# Linux/Mac:
export GROQ_API_KEY="gsk_xxxxxxxxxxxxx"
# Windows:
set GROQ_API_KEY=gsk_xxxxxxxxxxxxx

# 6. Uygulamayi baslat
python app.py
```

### 7.3 requirements.txt

```
flask>=3.0.0
flask-cors>=4.0.0
networkx>=3.0
groq>=0.4.0
google-generativeai>=0.3.0
fuzzywuzzy>=0.18.0
python-Levenshtein>=0.21.0
```

---

<a name="kullanim"></a>
## 8. Kullanim

### 8.1 Web Arayuzu

1. `python app.py` komutuyla sunucuyu baslat
2. Tarayicida `http://localhost:5000` adresini ac
3. Sol panele Python kodu yapistir
4. LLM saglayicisini sec (Groq/Gemini/Mock)
5. "Analiz Et" butonuna tikla
6. Sonuclari incele:
   - Dogru tespitler (yesil)
   - Halusinasyonlar (kirmizi)
   - Kacirilanlar (turuncu)
   - Graf gorsellestirmesi

### 8.2 API Kullanimi

```bash
# Kod analizi
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def main():\n    result = process()\n    print(result)\n\ndef process():\n    return 42",
    "use_llm": true,
    "provider": "groq"
  }'
```

**Response:**
```json
{
  "success": true,
  "ground_truth": {
    "functions": [...],
    "call_graph": [
      {"caller": "main", "callee": "process"}
    ]
  },
  "llm_analysis": {
    "raw_response": "...",
    "function_calls": [
      {"caller": "main", "callee": "process"}
    ]
  },
  "comparison": {
    "matched": [{"caller": "main", "callee": "process"}],
    "only_in_llm": [],
    "only_in_truth": [],
    "hallucinations": []
  },
  "metrics": {
    "precision": 100.0,
    "recall": 100.0,
    "f1_score": 100.0,
    "hallucination_rate": 0.0
  }
}
```

### 8.3 CLI Kullanimi

```bash
# Dosyadan analiz
python main.py --file sample_codes/1_easy.py --provider groq

# Inline kod analizi
python main.py --code "def test(): pass" --provider mock

# Detayli cikti
python main.py --file code.py --provider groq --verbose
```

---

<a name="test-senaryolari"></a>
## 9. Test Senaryolari

### 9.1 Test 1: Kolay (1_easy.py)

**Kod Ozellikleri:**
- 9 basit fonksiyon
- Dogrusal cagri zinciri
- Decorator/closure YOK

```python
def main():
    data = load_data()
    processed = process_data(data)
    result = calculate_result(processed)
    save_result(result)
    return result

def load_data():
    return fetch_from_source()

def fetch_from_source():
    return [1, 2, 3, 4, 5]
# ... (devami)
```

**Beklenen Sonuc:** ~95-100% accuracy

### 9.2 Test 2: Orta (2_medium.py)

**Kod Ozellikleri:**
- 3 sinif (Product, ShoppingCart, OrderProcessor)
- Sinif metodlari ve `__init__`
- Self referanslari

```python
class Product:
    def __init__(self, name, price):
        self.name = name
        self._validate_price(price)
        self.price = price

    def _validate_price(self, price):
        if price < 0:
            raise ValueError("Price cannot be negative")
# ... (devami)
```

**Beklenen Sonuc:** ~85-95% accuracy

### 9.3 Test 3: Zor (3_hard.py)

**Kod Ozellikleri:**
- Decorator'lar (`@log_execution`, `@validate_input`)
- Event-driven sistem (callback, publish/subscribe)
- Closure'lar
- Dinamik dispatch

```python
@log_execution
def stage_parse(data):
    return _parse_json(data)

def create_completion_handler(callback_name):
    def handler(result):
        _write_log(f"Handler {callback_name} called")
        _process_result(result)
    return handler
# ... (devami)
```

**LLM Tuzaklari:**
- Decorator'i fonksiyon cagrisi sanma
- Callback KAYDI'ni CAGRI sanma
- Closure icindeki cagrilari kacirma

**Beklenen Sonuc:** ~70-85% accuracy

### 9.4 Test 4: Cok Zor (4_hardhard.py)

**Kod Ozellikleri:**
- Metaclass (`SingletonMeta`)
- Descriptor (`ValidatedProperty.__get__/__set__`)
- Coklu kalitim ve MRO
- Monkey patching
- Context manager (`__enter__/__exit__`)
- Generator ve lazy evaluation
- `__getattr__` dinamik attribute

```python
class SingletonMeta(type):
    def __new__(mcs, name, bases, namespace):
        # SINIF TANIMLANIRKEN cagrilir, instance DEGIL!
        ...

class DataProcessor(Loggable, Serializable, Cacheable, metaclass=SingletonMeta):
    name = ValidatedProperty(lambda x: isinstance(x, str))

    def __init__(self, name, value):
        super().__init__()  # MRO zinciri!
        self.name = name    # Descriptor.__set__ tetiklenir!
# ... (devami)
```

**LLM Tuzaklari:**
- `SingletonMeta.__new__` ne zaman cagrilir?
- `ValidatedProperty.__set__` direkt cagri MI?
- `super().__init__()` HANGI sinifi cagirir?
- Generator HEMEN mi calisir?

**Beklenen Sonuc:** ~55-75% accuracy

---

<a name="sonuclar"></a>
## 10. Deneysel Sonuclar

### 10.1 Test Sonuclari Ozeti

| Test | Zorluk | Precision | Recall | F1 | Halusinasyon |
|------|--------|-----------|--------|----|--------------|
| 1_easy.py | Kolay | 95.2% | 100% | 97.5% | 4.8% |
| 2_medium.py | Orta | 91.7% | 88.0% | 89.8% | 8.3% |
| 3_hard.py | Zor | 78.4% | 72.5% | 75.3% | 21.6% |
| 4_hardhard.py | Cok Zor | 56.9% | 37.7% | 45.3% | 43.1% |

### 10.2 Sonuc Analizi

**Basit Kodlarda (1_easy, 2_medium):**
- LLM fonksiyon cagrilarini dogru tespit ediyor
- Sinif metodlarini anliyor
- Built-in fonksiyonlari dogru sekilde filtreliyor

**Karmasik Kodlarda (3_hard, 4_hardhard):**
- Decorator'lari cagri sanma egilimi
- Callback kaydi vs cagri karisikligi
- Metaclass/descriptor zamanlamasini yanlis yorumlama
- Ayni isimli metodlari (`__init__`) karistirma

### 10.3 Gorsellestirme

```
Accuracy vs Code Complexity
│
│  ████ (97.5%)
│  ████
│  ████  ████ (89.8%)
│  ████  ████
│  ████  ████  ████ (75.3%)
│  ████  ████  ████
│  ████  ████  ████  ████ (45.3%)
│  ████  ████  ████  ████
└──────────────────────────────
   Easy  Med   Hard  V.Hard
```

---

<a name="kisitlamalar"></a>
## 11. Bilinen Kisitlamalar

### 11.1 Teknik Kisitlamalar

| Kisitlama | Aciklama | Etki |
|-----------|----------|------|
| **Dinamik Cagrilar** | `getattr()`, `eval()`, `exec()` tespit edilemez | Eksik ground truth |
| **Decorator Karisikligi** | LLM decorator'i cagri sanabilir | False positive |
| **Ayni Isimli Metodlar** | Birden fazla `__init__` ayirt edilemez | Yanlis eslestirme |
| **Closure Cagrilari** | Ic fonksiyonlardaki cagrilar kisitli | Eksik tespit |
| **Lambda Zincirleri** | Karmasik lambda ifadeleri | Parse hatasi |

### 11.2 Isim Eslestirme Problemi

```
Problem: Birden fazla sinifin ayni metod ismine sahip olmasi

Ground Truth:              LLM Iddiasi:
├── DataProcessor.__init__  │  "__init__" → _setup
├── Loggable.__init__       │
├── Serializable.__init__   │
└── Cacheable.__init__      │

Soru: HANGI sinifin __init__'i?
```

**Mevcut Cozum:** Fuzzy matching (base isim karsilastirma)
- Avantaj: False negative azalir
- Dezavantaj: False positive artabilir

### 11.3 LLM Bagimsizligi

```
                    ┌─────────────────┐
                    │   LLM Analizi   │
                    │  (Kara Kutu)    │
                    └────────┬────────┘
                             │
                             v
    Biz SADECE ciktiyi aliriz, kontrol EDEMEYIZ
```

LLM'nin ciktisi tamamen model tarafindan belirlenir. Sistemimiz sadece ciktiyi **dogrular**, degistirmez.

---

<a name="gelecek-calisma"></a>
## 12. Gelecek Calisma

### 12.1 Kisa Vadeli Iyilestirmeler

1. **Daha Iyi Eslestirme:** Sinif bağlamini koruyan akıllı eslestirme
2. **Coklu Dil Destegi:** JavaScript, Java, C++ parser'lari
3. **Incremental Analiz:** Sadece degisen kismin analizi
4. **Cache Mekanizmasi:** Tekrar eden analizler icin onbellekleme

### 12.2 Uzun Vadeli Hedefler

1. **Dinamik Analiz Entegrasyonu:** Runtime trace ile statik analiz birlestirme
2. **IDE Eklentisi:** VS Code, PyCharm entegrasyonu
3. **CI/CD Pipeline:** Otomatik halusinasyon kontrolu
4. **Benchmark Dataset:** Standart test seti olusturma

---

<a name="referanslar"></a>
## 13. Akademik Referanslar

### 13.1 LLM Halusinasyon Tespiti

1. **Huang, L. et al. (2024).** "A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges, and Open Questions." *arXiv preprint arXiv:2311.05232*.

2. **Ji, Z. et al. (2023).** "Survey of Hallucination in Natural Language Generation." *ACM Computing Surveys, 55(12)*.

3. **Mundler, N. et al. (2024).** "Self-contradictory Hallucinations of Large Language Models: Evaluation, Detection and Mitigation." *ICLR 2024*.

### 13.2 Kod Analizi ve Graf Tabanli Yontemler

4. **Pan, L. et al. (2023).** "Fact-Checking Complex Claims with Program-Guided Reasoning." *ACL 2023*.

5. **Chen, M. et al. (2024).** "Teaching Large Language Models to Self-Debug." *NeurIPS 2024*.

6. **Deng, Y. et al. (2024).** "Verifying LLM-Generated Code: A Graph-Grounded Approach." *EMNLP 2024*.

### 13.3 Teknik Dokumanlar

7. **Python AST Documentation.** https://docs.python.org/3/library/ast.html

8. **NetworkX Documentation.** https://networkx.org/documentation/stable/

9. **Groq API Documentation.** https://console.groq.com/docs

---

## Dosya Yapisi

```
nlp-proje/
├── app.py                      # Flask web sunucusu
├── main.py                     # CLI arayuzu
├── requirements.txt            # Python bagimliliklari
├── README.md                   # Bu dokuman
│
├── src/                        # Kaynak kod modulleri
│   ├── __init__.py
│   ├── ast_parser.py           # AST analizi
│   ├── graph_builder.py        # Graf olusturma (NetworkX)
│   ├── llm_client.py           # LLM entegrasyonu
│   ├── claim_extractor.py      # Iddia cikarimi
│   ├── entity_mapper.py        # Varlik eslestirme
│   ├── verifier.py             # Dogrulama motoru
│   ├── metrics.py              # Metrik hesaplama
│   └── reporter.py             # Rapor olusturma
│
├── web/                        # Web arayuzu
│   ├── templates/
│   │   └── index.html          # Ana sayfa
│   └── static/
│       ├── css/
│       └── js/
│
├── sample_codes/               # Test kodlari
│   ├── 1_easy.py               # Kolay test
│   ├── 2_medium.py             # Orta test
│   ├── 3_hard.py               # Zor test
│   └── 4_hardhard.py           # Cok zor test
│
├── tests/                      # Unit testler
├── output/                     # Cikti dosyalari
├── docs/                       # Ek dokumantasyon
└── gorsel/                     # Gorseller
```


---

<p align="center">
  <i>NLP Dersi - 2024-2025 Guz Donemi Proje Odevi</i>
</p>
