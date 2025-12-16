# =============================================================================
# LLM CLIENT MODÜLÜ
# =============================================================================
# Bu modül, Büyük Dil Modelleri (LLM) ile iletişim kurar ve kod analizi
# için reasoning (muhakeme) çıktıları üretir.
#
# Desteklenen LLM'ler:
# - OpenAI GPT modelleri (GPT-4, GPT-3.5-turbo)
# - Yerel/Alternatif API'ler (opsiyonel)
#
# Chain-of-Thought (CoT) Prompting:
# ---------------------------------
# CoT, LLM'lerin adım adım düşünmesini sağlayan bir prompting tekniğidir.
# Model, doğrudan cevap vermek yerine düşünce sürecini açıklar:
#
# Normal prompt: "Bu fonksiyon ne yapar?"
# CoT prompt: "Bu fonksiyonu adım adım analiz et. Her adımda ne olduğunu açıkla."
#
# Bu sayede modelin muhakeme sürecini görebilir ve doğrulayabiliriz.
# =============================================================================

import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

# OpenAI kütüphanesi opsiyonel - kurulu değilse mock kullanılır
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Google Gemini kütüphanesi
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Groq kütüphanesi (OpenAI uyumlu)
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


@dataclass
class LLMResponse:
    """
    LLM'den gelen yanıtı temsil eden veri sınıfı.

    Attributes:
        content: Ana yanıt metni
        reasoning_steps: Ayrıştırılmış muhakeme adımları (varsa)
        model: Kullanılan model adı
        usage: Token kullanım bilgileri
        raw_response: Ham API yanıtı (debug için)
    """
    content: str
    reasoning_steps: List[str]
    model: str
    usage: Dict[str, int]
    raw_response: Optional[Dict] = None


class BaseLLMClient(ABC):
    """
    LLM client'ları için soyut temel sınıf.

    Farklı LLM sağlayıcıları için ortak arayüz tanımlar.
    Yeni bir LLM eklemek için bu sınıftan türetilir.
    """

    @abstractmethod
    def generate_reasoning(self, code: str, prompt_type: str = "analysis") -> LLMResponse:
        """
        Verilen kod için LLM'den reasoning çıktısı üretir.

        Args:
            code: Analiz edilecek Python kodu
            prompt_type: Prompt tipi ("analysis", "explanation", "review")

        Returns:
            LLMResponse nesnesi
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        LLM servisinin kullanılabilir olup olmadığını kontrol eder.
        """
        pass


class OpenAIClient(BaseLLMClient):
    """
    OpenAI API ile iletişim kuran client sınıfı.

    Kullanım:
        client = OpenAIClient(api_key="sk-...")
        response = client.generate_reasoning(kod, "analysis")
    """

    # Farklı analiz türleri için prompt şablonları
    PROMPT_TEMPLATES = {
        "analysis": """
Sen bir kod analiz uzmanısın. Aşağıdaki Python kodunu detaylı olarak analiz et.

KURALLAR:
1. Her adımı numaralandırarak açıkla
2. Fonksiyonlar arası çağrı ilişkilerini belirt
3. Veri akışını takip et
4. Değişkenlerin nasıl kullanıldığını açıkla

FORMAT:
Her analiz adımını şu formatta yaz:
ADIM X: [Açıklama]
- Detay 1
- Detay 2

KOD:
```python
{code}
```

Analizi başlat:
""",

        "explanation": """
Aşağıdaki Python kodunu bir yazılım geliştiriciye açıklar gibi anlat.

KOD:
```python
{code}
```

Açıklamanı şu başlıklar altında yap:
1. GENEL BAKIŞ: Kodun amacı nedir?
2. YAPISAL ANALİZ: Hangi fonksiyonlar/sınıflar var?
3. ÇAĞRI İLİŞKİLERİ: Hangi fonksiyon hangisini çağırıyor?
4. VERİ AKIŞI: Veriler nasıl işleniyor?
""",

        "review": """
Aşağıdaki Python kodunu kod review perspektifinden değerlendir.

KOD:
```python
{code}
```

Her fonksiyon için şunları belirt:
- Ne iş yapıyor
- Hangi fonksiyonları çağırıyor
- Hangi değişkenleri kullanıyor
- Potansiyel sorunlar (varsa)
""",

        "function_calls": """
Aşağıdaki Python kodundaki fonksiyon çağrı ilişkilerini analiz et.

KOD:
```python
{code}
```

Her fonksiyon için şu formatta yanıt ver:
FONKSIYON: [fonksiyon_adı]
ÇAĞIRIYOR: [çağırdığı fonksiyonların listesi]
ÇAĞRILIYOR_TARAFINDAN: [bu fonksiyonu çağıran fonksiyonlar]

Eğer bir fonksiyon başka fonksiyon çağırmıyorsa "YOK" yaz.
"""
    }

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        OpenAI client'ı başlatır.

        Args:
            api_key: OpenAI API anahtarı. None ise çevre değişkeninden alınır.
            model: Kullanılacak model (varsayılan: gpt-3.5-turbo)
        """
        # API anahtarını al (parametre > çevre değişkeni > .env dosyası)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

        # OpenAI client'ı oluştur (kütüphane mevcutsa)
        self.client = None
        if OPENAI_AVAILABLE and self.api_key:
            self.client = OpenAI(api_key=self.api_key)

    def is_available(self) -> bool:
        """
        OpenAI API'nin kullanılabilir olup olmadığını kontrol eder.

        Returns:
            True eğer API anahtarı ve kütüphane mevcutsa
        """
        return OPENAI_AVAILABLE and self.api_key is not None and self.client is not None

    def generate_reasoning(self, code: str, prompt_type: str = "analysis") -> LLMResponse:
        """
        OpenAI API'sini kullanarak kod analizi yapar.

        Args:
            code: Analiz edilecek Python kodu
            prompt_type: Prompt tipi

        Returns:
            LLMResponse nesnesi

        Raises:
            RuntimeError: API kullanılamıyorsa
        """
        if not self.is_available():
            raise RuntimeError("OpenAI API kullanılamıyor. API anahtarını kontrol edin.")

        # Prompt şablonunu seç ve kodu yerleştir
        template = self.PROMPT_TEMPLATES.get(prompt_type, self.PROMPT_TEMPLATES["analysis"])
        prompt = template.format(code=code)

        # API çağrısı yap
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Sen deneyimli bir yazılım mühendisisin. Kod analizi yaparken "
                               "her adımı detaylı açıklarsın ve fonksiyonlar arası ilişkileri "
                               "net bir şekilde belirtirsin."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,  # Düşük sıcaklık = daha tutarlı çıktı
            max_tokens=2000
        )

        # Yanıtı parse et
        content = response.choices[0].message.content
        reasoning_steps = self._extract_reasoning_steps(content)

        return LLMResponse(
            content=content,
            reasoning_steps=reasoning_steps,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            raw_response=response.model_dump()
        )

    def _extract_reasoning_steps(self, content: str) -> List[str]:
        """
        LLM yanıtından muhakeme adımlarını çıkarır.

        "ADIM X:" veya numaralı maddeleri arar.

        Args:
            content: LLM yanıt metni

        Returns:
            Muhakeme adımları listesi
        """
        steps = []
        lines = content.split('\n')

        current_step = []
        for line in lines:
            line = line.strip()

            # Yeni adım başlangıcı mı?
            if (line.startswith("ADIM") or
                line.startswith("1.") or line.startswith("2.") or
                line.startswith("3.") or line.startswith("4.") or
                line.startswith("FONKSIYON:") or
                line.startswith("GENEL BAKIŞ") or
                line.startswith("YAPISAL ANALİZ")):

                # Önceki adımı kaydet
                if current_step:
                    steps.append('\n'.join(current_step))
                current_step = [line]
            elif current_step:
                current_step.append(line)

        # Son adımı ekle
        if current_step:
            steps.append('\n'.join(current_step))

        return steps


class GeminiClient(BaseLLMClient):
    """
    Google Gemini API ile iletişim kuran client sınıfı.

    Kullanım:
        client = GeminiClient(api_key="AIza...")
        response = client.generate_reasoning(kod, "analysis")
    """

    # Prompt şablonları - JSON formatında strict analiz
    PROMPT_TEMPLATES = {
        "analysis": """
Sen kıdemli bir statik kod analiz motorusun. Görevin, Python kodunun "Call Graph" (Çağrı Grafiği) yapısını çıkarmaktır.

HEDEF:
Sadece sözdizimsel (syntactic) olarak bir fonksiyonun GÖVDESİ İÇİNDE çağrılan diğer fonksiyonları tespit et.

KURALLAR (Çok Önemli):
1. SIRALI ÇALIŞMA != ÇAĞRI: Eğer A fonksiyonu çalışıp bittikten sonra B fonksiyonu çalışıyorsa, bu A'nın B'yi çağırdığı anlamına GELMEZ. Sadece A'nın gövdesi içinde B() yazıyorsa çağırıyor demektir.
2. RECURSION YOKSA KENDİNİ EKLEME: Fonksiyon içinde kendi ismi açıkça geçmiyorsa, kendini çağırıyor olarak işaretleme.
3. BUILT-IN DAHİL ETME: print, len, range, open, str, int, float gibi gömülü fonksiyonları DAHİL ETME. Sadece kodda tanımlı fonksiyonları/metotları dikkate al.
4. METOT ÇAĞRILARI: self.method() şeklindeki çağrıları "method" olarak yaz (self. olmadan).
5. SINIF İÇİ METOTLAR: Sınıf metotlarını da fonksiyon olarak listele (örn: Calculator.add -> "add").
6. ÇIKTI FORMATI: Sadece saf bir JSON nesnesi döndür. Açıklama, yorum veya markdown (```) EKLEME.

JSON ŞEMASI (Bu formatı AYNEN kullan):
{{
  "functions": [
    {{
      "name": "fonksiyon_adi",
      "calls": ["cagirdigi_fonksiyon_1", "cagirdigi_fonksiyon_2"]
    }}
  ]
}}

Eğer bir fonksiyon hiçbir şey çağırmıyorsa: "calls": []

KOD:
```python
{code}
```

SADECE JSON DÖNDÜR:
""",

        "explanation": """
Aşağıdaki Python kodunu bir yazılım geliştiriciye açıklar gibi anlat.

KOD:
```python
{code}
```

Açıklamanı şu başlıklar altında yap:
1. GENEL BAKIŞ: Kodun amacı nedir?
2. YAPISAL ANALİZ: Hangi fonksiyonlar/sınıflar var?
3. ÇAĞRI İLİŞKİLERİ: Hangi fonksiyon hangisini çağırıyor?
4. VERİ AKIŞI: Veriler nasıl işleniyor?
""",

        "function_calls": """
Aşağıdaki Python kodundaki fonksiyon çağrı ilişkilerini analiz et.

KOD:
```python
{code}
```

Her fonksiyon için şu formatta yanıt ver:
FONKSIYON: [fonksiyon_adı]
ÇAĞIRIYOR: [çağırdığı fonksiyonların listesi]

Eğer bir fonksiyon başka fonksiyon çağırmıyorsa "YOK" yaz.
Sadece kodda tanımlı fonksiyonları listele, print, len gibi built-in fonksiyonları dahil etme.
"""
    }

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        """
        Gemini client'ı başlatır.

        Args:
            api_key: Google AI API anahtarı
            model: Kullanılacak model (varsayılan: gemini-2.0-flash)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model
        self.model = None

        if GEMINI_AVAILABLE and self.api_key:
            # Gemini API'yi yapılandır
            genai.configure(api_key=self.api_key)
            try:
                self.model = genai.GenerativeModel(self.model_name)
            except Exception as e:
                # Model bulunamazsa alternatif dene
                print(f"⚠️ {self.model_name} bulunamadı, gemini-pro deneniyor...")
                self.model_name = "gemini-pro"
                self.model = genai.GenerativeModel(self.model_name)

    def is_available(self) -> bool:
        """Gemini API'nin kullanılabilir olup olmadığını kontrol eder."""
        return GEMINI_AVAILABLE and self.api_key is not None and self.model is not None

    def generate_reasoning(self, code: str, prompt_type: str = "analysis") -> LLMResponse:
        """
        Gemini API'sini kullanarak kod analizi yapar.

        Args:
            code: Analiz edilecek Python kodu
            prompt_type: Prompt tipi

        Returns:
            LLMResponse nesnesi
        """
        if not self.is_available():
            raise RuntimeError("Gemini API kullanılamıyor. API anahtarını kontrol edin.")

        # Prompt şablonunu seç ve kodu yerleştir
        template = self.PROMPT_TEMPLATES.get(prompt_type, self.PROMPT_TEMPLATES["analysis"])
        prompt = template.format(code=code)

        # API çağrısı yap (hata durumunda alternatif model dene veya retry)
        import time
        import re as regex_module

        alternative_models = ["gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-pro", "gemini-1.0-pro"]
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                break  # Başarılı, döngüden çık
            except Exception as e:
                error_msg = str(e)

                # 429 Rate Limit hatası
                if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
                    # Bekleme süresini çıkar
                    wait_match = regex_module.search(r'retry.*?(\d+\.?\d*)\s*s', error_msg.lower())
                    wait_time = float(wait_match.group(1)) if wait_match else 10

                    print(f"⚠️ Rate limit aşıldı. {wait_time:.1f} saniye bekleniyor... (Deneme {attempt + 1}/{max_retries})")
                    time.sleep(wait_time + 1)  # +1 güvenlik payı

                    # Farklı model dene (quota model bazlı olabilir)
                    if attempt > 0 and attempt - 1 < len(alternative_models):
                        alt_model = alternative_models[attempt - 1]
                        print(f"   Alternatif model deneniyor: {alt_model}")
                        try:
                            self.model = genai.GenerativeModel(alt_model)
                            self.model_name = alt_model
                        except:
                            pass
                    continue

                # 404 Model bulunamadı hatası
                elif "404" in error_msg or "not found" in error_msg.lower():
                    print(f"⚠️ {self.model_name} modeli bulunamadı. Alternatif deneniyor...")
                    for alt_model in alternative_models:
                        try:
                            print(f"   Deneniyor: {alt_model}")
                            self.model = genai.GenerativeModel(alt_model)
                            self.model_name = alt_model
                            response = self.model.generate_content(prompt)
                            print(f"✅ {alt_model} modeli çalıştı!")
                            break
                        except Exception:
                            continue
                    else:
                        raise RuntimeError(f"Hiçbir Gemini modeli çalışmadı. Hata: {error_msg}")
                    break
                else:
                    raise
        else:
            raise RuntimeError(f"Maksimum deneme sayısına ulaşıldı. Lütfen daha sonra tekrar deneyin veya API planınızı kontrol edin.")

        # Yanıtı al
        content = response.text
        reasoning_steps = self._extract_reasoning_steps(content)

        # Token bilgisi (Gemini'de farklı şekilde alınıyor)
        usage = {
            "prompt_tokens": len(prompt.split()),  # Yaklaşık
            "completion_tokens": len(content.split()),  # Yaklaşık
            "total_tokens": len(prompt.split()) + len(content.split())
        }

        return LLMResponse(
            content=content,
            reasoning_steps=reasoning_steps,
            model=self.model_name,
            usage=usage
        )

    def _extract_reasoning_steps(self, content: str) -> List[str]:
        """LLM yanıtından muhakeme adımlarını çıkarır."""
        steps = []
        lines = content.split('\n')

        current_step = []
        for line in lines:
            line = line.strip()

            # Yeni adım başlangıcı mı?
            if (line.startswith("ADIM") or
                line.startswith("1.") or line.startswith("2.") or
                line.startswith("3.") or line.startswith("4.") or
                line.startswith("FONKSIYON:") or
                line.startswith("GENEL BAKIŞ") or
                line.startswith("YAPISAL ANALİZ")):

                if current_step:
                    steps.append('\n'.join(current_step))
                current_step = [line]
            elif current_step:
                current_step.append(line)

        if current_step:
            steps.append('\n'.join(current_step))

        return steps


class GroqClient(BaseLLMClient):
    """
    Groq API ile iletişim kuran client sınıfı.

    Groq, LPU (Language Processing Unit) teknolojisi ile çok hızlı inference sağlar.
    Ücretsiz tier: 30 req/dakika, 14400 req/gün

    Kullanım:
        client = GroqClient(api_key="gsk_...")
        response = client.generate_reasoning(kod, "analysis")
    """

    # Prompt şablonları - JSON formatında strict analiz
    PROMPT_TEMPLATES = {
        "analysis": """
Sen kıdemli bir statik kod analiz motorusun. Görevin, Python kodunun "Call Graph" (Çağrı Grafiği) yapısını çıkarmaktır.

HEDEF:
Sadece sözdizimsel (syntactic) olarak bir fonksiyonun GÖVDESİ İÇİNDE çağrılan diğer fonksiyonları tespit et.

KURALLAR (Çok Önemli):
1. SIRALI ÇALIŞMA != ÇAĞRI: Eğer A fonksiyonu çalışıp bittikten sonra B fonksiyonu çalışıyorsa, bu A'nın B'yi çağırdığı anlamına GELMEZ. Sadece A'nın gövdesi içinde B() yazıyorsa çağırıyor demektir.
2. RECURSION YOKSA KENDİNİ EKLEME: Fonksiyon içinde kendi ismi açıkça geçmiyorsa, kendini çağırıyor olarak işaretleme.
3. BUILT-IN DAHİL ETME: print, len, range, open, str, int, float gibi gömülü fonksiyonları DAHİL ETME. Sadece kodda tanımlı fonksiyonları/metotları dikkate al.
4. METOT ÇAĞRILARI: self.method() şeklindeki çağrıları "method" olarak yaz (self. olmadan).
5. SINIF İÇİ METOTLAR: Sınıf metotlarını da fonksiyon olarak listele (örn: Calculator.add -> "add").
6. ÇIKTI FORMATI: Sadece saf bir JSON nesnesi döndür. Açıklama, yorum veya markdown (```) EKLEME.

JSON ŞEMASI (Bu formatı AYNEN kullan):
{{
  "functions": [
    {{
      "name": "fonksiyon_adi",
      "calls": ["cagirdigi_fonksiyon_1", "cagirdigi_fonksiyon_2"]
    }}
  ]
}}

Eğer bir fonksiyon hiçbir şey çağırmıyorsa: "calls": []

KOD:
```python
{code}
```

SADECE JSON DÖNDÜR:
""",
        "explanation": """
Aşağıdaki Python kodunu bir yazılım geliştiriciye açıklar gibi anlat.

KOD:
```python
{code}
```

Açıklamanı şu başlıklar altında yap:
1. GENEL BAKIŞ: Kodun amacı nedir?
2. YAPISAL ANALİZ: Hangi fonksiyonlar/sınıflar var?
3. ÇAĞRI İLİŞKİLERİ: Hangi fonksiyon hangisini çağırıyor?
4. VERİ AKIŞI: Veriler nasıl işleniyor?
""",
    }

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        """
        Groq client'ı başlatır.

        Args:
            api_key: Groq API anahtarı
            model: Kullanılacak model (varsayılan: llama-3.3-70b-versatile)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.client = None

        if GROQ_AVAILABLE and self.api_key:
            self.client = Groq(api_key=self.api_key)

    def is_available(self) -> bool:
        """Groq API'nin kullanılabilir olup olmadığını kontrol eder."""
        return GROQ_AVAILABLE and self.api_key is not None and self.client is not None

    def generate_reasoning(self, code: str, prompt_type: str = "analysis") -> LLMResponse:
        """
        Groq API'sini kullanarak kod analizi yapar.

        Args:
            code: Analiz edilecek Python kodu
            prompt_type: Prompt tipi

        Returns:
            LLMResponse nesnesi
        """
        if not self.is_available():
            raise RuntimeError("Groq API kullanılamıyor. API anahtarını kontrol edin.")

        # Prompt şablonunu seç ve kodu yerleştir
        template = self.PROMPT_TEMPLATES.get(prompt_type, self.PROMPT_TEMPLATES["analysis"])
        prompt = template.format(code=code)

        # API çağrısı yap
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Sen deneyimli bir yazılım mühendisisin. Kod analizi yaparken "
                               "sadece JSON formatında yanıt verirsin. Markdown veya açıklama ekleme."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,  # Düşük sıcaklık = daha tutarlı JSON çıktısı
            max_tokens=2000
        )

        # Yanıtı parse et
        content = response.choices[0].message.content
        reasoning_steps = self._extract_reasoning_steps(content)

        return LLMResponse(
            content=content,
            reasoning_steps=reasoning_steps,
            model=self.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        )

    def _extract_reasoning_steps(self, content: str) -> List[str]:
        """LLM yanıtından muhakeme adımlarını çıkarır."""
        # JSON formatında geldiği için tek adım olarak döndür
        return [content]


class MockLLMClient(BaseLLMClient):
    """
    Test amaçlı sahte (mock) LLM client.

    API anahtarı olmadan test yapabilmek için önceden tanımlanmış
    yanıtlar döndürür. Geliştirme ve test sürecinde kullanışlıdır.
    """

    def __init__(self):
        """Mock client'ı başlatır."""
        self.call_count = 0

    def is_available(self) -> bool:
        """Mock client her zaman kullanılabilir."""
        return True

    def generate_reasoning(self, code: str, prompt_type: str = "analysis") -> LLMResponse:
        """
        Sahte bir LLM yanıtı üretir.

        Kod içeriğini analiz ederek gerçekçi görünen bir yanıt oluşturur.
        Bu, API maliyeti olmadan sistemin test edilmesini sağlar.

        Args:
            code: Analiz edilecek kod
            prompt_type: Prompt tipi

        Returns:
            Sahte LLMResponse
        """
        self.call_count += 1

        # Koddan basit bilgiler çıkar
        import re

        # Fonksiyon adlarını bul
        func_pattern = r'def\s+(\w+)\s*\('
        functions = re.findall(func_pattern, code)

        # Sınıf adlarını bul
        class_pattern = r'class\s+(\w+)'
        classes = re.findall(class_pattern, code)

        # Sahte analiz oluştur
        reasoning_content = self._generate_mock_analysis(functions, classes, code)

        return LLMResponse(
            content=reasoning_content,
            reasoning_steps=self._extract_steps_from_mock(reasoning_content),
            model="mock-model",
            usage={
                "prompt_tokens": len(code.split()),
                "completion_tokens": len(reasoning_content.split()),
                "total_tokens": len(code.split()) + len(reasoning_content.split())
            }
        )

    def _generate_mock_analysis(self, functions: List[str], classes: List[str], code: str) -> str:
        """
        Sahte analiz metni oluşturur.

        Args:
            functions: Bulunan fonksiyon adları
            classes: Bulunan sınıf adları
            code: Kaynak kod

        Returns:
            Analiz metni
        """
        import re

        analysis = []
        analysis.append("ADIM 1: GENEL BAKIŞ")
        analysis.append(f"Bu kod {len(functions)} fonksiyon ve {len(classes)} sınıf içermektedir.")
        analysis.append("")

        # Her fonksiyon için analiz
        step = 2
        for func in functions:
            analysis.append(f"ADIM {step}: {func} FONKSİYONU ANALİZİ")

            # Bu fonksiyonun çağırdığı diğer fonksiyonları bul
            # Basit regex ile fonksiyon çağrılarını ara
            func_body_match = re.search(
                rf'def\s+{func}\s*\([^)]*\):[^\n]*\n((?:\s+[^\n]+\n)*)',
                code
            )

            if func_body_match:
                func_body = func_body_match.group(1)
                # Fonksiyon çağrılarını bul
                calls = re.findall(r'(\w+)\s*\(', func_body)
                # Kendisi ve built-in'leri filtrele
                calls = [c for c in calls if c != func and c not in ('print', 'len', 'range', 'str', 'int', 'if', 'for', 'while')]
                calls = list(set(calls))

                if calls:
                    analysis.append(f"- {func} fonksiyonu şu fonksiyonları çağırıyor: {', '.join(calls)}")
                else:
                    analysis.append(f"- {func} fonksiyonu başka fonksiyon çağırmıyor")
            else:
                analysis.append(f"- {func} fonksiyonu analiz edildi")

            analysis.append("")
            step += 1

        # Sınıflar için analiz
        for cls in classes:
            analysis.append(f"ADIM {step}: {cls} SINIFI ANALİZİ")
            analysis.append(f"- {cls} sınıfı tanımlanmış")

            # Sınıf metodlarını bul
            class_body_match = re.search(
                rf'class\s+{cls}[^:]*:((?:\n(?:\s+[^\n]+))*)',
                code
            )
            if class_body_match:
                class_body = class_body_match.group(1)
                methods = re.findall(r'def\s+(\w+)\s*\(self', class_body)
                if methods:
                    analysis.append(f"- Metodları: {', '.join(methods)}")

            analysis.append("")
            step += 1

        # Çağrı ilişkileri özeti
        analysis.append(f"ADIM {step}: ÇAĞRI İLİŞKİLERİ ÖZETİ")
        for func in functions:
            analysis.append(f"FONKSIYON: {func}")
            # Basit çağrı analizi
            func_body_match = re.search(
                rf'def\s+{func}\s*\([^)]*\):[^\n]*\n((?:\s+[^\n]+\n)*)',
                code
            )
            if func_body_match:
                func_body = func_body_match.group(1)
                calls = re.findall(r'(\w+)\s*\(', func_body)
                valid_calls = [c for c in calls if c in functions and c != func]
                if valid_calls:
                    analysis.append(f"ÇAĞIRIYOR: {', '.join(valid_calls)}")
                else:
                    analysis.append("ÇAĞIRIYOR: YOK")
            analysis.append("")

        return '\n'.join(analysis)

    def _extract_steps_from_mock(self, content: str) -> List[str]:
        """Mock içerikten adımları çıkarır."""
        steps = []
        current_step = []

        for line in content.split('\n'):
            if line.startswith("ADIM") or line.startswith("FONKSIYON:"):
                if current_step:
                    steps.append('\n'.join(current_step))
                current_step = [line]
            elif current_step:
                current_step.append(line)

        if current_step:
            steps.append('\n'.join(current_step))

        return steps


class LLMClient:
    """
    LLM client'ları için fabrika sınıfı.

    Uygun client'ı otomatik olarak seçer:
    - provider="groq": Groq API (ÖNERİLEN - ücretsiz ve hızlı)
    - provider="gemini": Google Gemini API
    - provider="openai": OpenAI API
    - provider="mock": Test için sahte client
    - provider="auto": Otomatik seçim (Groq > Gemini > OpenAI > Mock)

    Kullanım:
        client = LLMClient.create()  # Otomatik seçim
        client = LLMClient.create(provider="groq", api_key="gsk_...")
        client = LLMClient.create(provider="gemini", api_key="AIza...")
        client = LLMClient.create(provider="openai", api_key="sk-...")
        client = LLMClient.create(provider="mock")  # Test için
    """

    @staticmethod
    def create(provider: str = "auto", **kwargs) -> BaseLLMClient:
        """
        Uygun LLM client'ı oluşturur.

        Args:
            provider: "groq", "gemini", "openai", "mock" veya "auto"
            **kwargs: Client'a geçirilecek ek parametreler
                - api_key: API anahtarı
                - model: Model adı

        Returns:
            BaseLLMClient türevi client
        """
        # Mock client istendi
        if provider == "mock":
            return MockLLMClient()

        # Groq client (ÖNERİLEN)
        if provider == "groq":
            api_key = kwargs.get("api_key") or os.getenv("GROQ_API_KEY")
            if api_key and GROQ_AVAILABLE:
                print("✅ Groq API kullanılıyor (Llama 3.3 70B).")
                return GroqClient(api_key=api_key, model=kwargs.get("model", "llama-3.3-70b-versatile"))
            else:
                raise RuntimeError("Groq API anahtarı bulunamadı veya kütüphane kurulu değil. "
                                   "Kurulum: pip install groq")

        # Gemini client
        if provider == "gemini":
            api_key = kwargs.get("api_key") or os.getenv("GEMINI_API_KEY")
            if api_key and GEMINI_AVAILABLE:
                print("✅ Google Gemini API kullanılıyor.")
                return GeminiClient(api_key=api_key, model=kwargs.get("model", "gemini-2.0-flash"))
            else:
                raise RuntimeError("Gemini API anahtarı bulunamadı veya kütüphane kurulu değil.")

        # OpenAI client
        if provider == "openai":
            api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
            if api_key and OPENAI_AVAILABLE:
                print("✅ OpenAI API kullanılıyor.")
                return OpenAIClient(api_key=api_key, model=kwargs.get("model", "gpt-3.5-turbo"))
            else:
                raise RuntimeError("OpenAI API anahtarı bulunamadı veya kütüphane kurulu değil.")

        # Auto mod: Sırayla dene (Groq > Gemini > OpenAI > Mock)
        if provider == "auto":
            api_key = kwargs.get("api_key")

            # Önce Groq dene (ücretsiz ve hızlı)
            groq_key = api_key or os.getenv("GROQ_API_KEY")
            if groq_key and GROQ_AVAILABLE:
                print("✅ Groq API kullanılıyor (auto) - Llama 3.3 70B.")
                return GroqClient(api_key=groq_key, model=kwargs.get("model", "llama-3.3-70b-versatile"))

            # Sonra Gemini dene
            gemini_key = api_key or os.getenv("GEMINI_API_KEY")
            if gemini_key and GEMINI_AVAILABLE:
                print("✅ Google Gemini API kullanılıyor (auto).")
                return GeminiClient(api_key=gemini_key, model=kwargs.get("model", "gemini-2.0-flash"))

            # Sonra OpenAI dene
            openai_key = api_key or os.getenv("OPENAI_API_KEY")
            if openai_key and OPENAI_AVAILABLE:
                print("✅ OpenAI API kullanılıyor (auto).")
                return OpenAIClient(api_key=openai_key, model=kwargs.get("model", "gpt-3.5-turbo"))

        # Hiçbiri yoksa Mock kullan
        print("ℹ️  API bulunamadı, Mock mod kullanılıyor.")
        return MockLLMClient()


# =============================================================================
# TEST KODU
# =============================================================================
if __name__ == "__main__":
    # Test kodu
    test_code = '''
class Calculator:
    def __init__(self):
        self.result = 0

    def add(self, a, b):
        self.result = a + b
        self._log("add")
        return self.result

    def _log(self, operation):
        print(f"İşlem: {operation}, Sonuç: {self.result}")

def process_numbers(numbers):
    calc = Calculator()
    total = 0
    for num in numbers:
        total = calc.add(total, num)
    return total

def main():
    data = [1, 2, 3, 4, 5]
    result = process_numbers(data)
    print(f"Toplam: {result}")
    save_to_file(result)

def save_to_file(value):
    with open("output.txt", "w") as f:
        f.write(str(value))
'''

    print("=" * 60)
    print("LLM CLIENT TESTİ")
    print("=" * 60)

    # Client oluştur (otomatik seçim)
    client = LLMClient.create()
    print(f"\n📡 Kullanılan client: {type(client).__name__}")
    print(f"   Kullanılabilir: {client.is_available()}")

    # Analiz yap
    print("\n🔍 Kod analizi yapılıyor...")
    response = client.generate_reasoning(test_code, "analysis")

    print(f"\n📊 Token kullanımı: {response.usage}")
    print(f"🤖 Model: {response.model}")

    print("\n" + "=" * 60)
    print("LLM YANITI")
    print("=" * 60)
    print(response.content)

    print("\n" + "=" * 60)
    print("ÇIKARILAN ADIMLAR")
    print("=" * 60)
    for i, step in enumerate(response.reasoning_steps, 1):
        print(f"\n--- Adım {i} ---")
        print(step[:200] + "..." if len(step) > 200 else step)
