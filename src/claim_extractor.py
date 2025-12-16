# =============================================================================
# CLAIM EXTRACTOR MODÜLÜ
# =============================================================================
# Bu modül, LLM çıktısından doğrulanabilir "claim" (iddia) cümlelerini çıkarır.
#
# Claim Nedir?
# ------------
# Claim, LLM'nin kod hakkında yaptığı ve doğrulanabilir bir ifadedir.
# Örnekler:
# - "main fonksiyonu process_data fonksiyonunu çağırır" (ÇAĞRI İDDİASI)
# - "result değişkeni calculate fonksiyonundan gelir" (VERİ AKIŞI İDDİASI)
# - "Calculator sınıfının add metodu vardır" (YAPI İDDİASI)
#
# Claim Türleri:
# -------------
# 1. CALL_CLAIM: Fonksiyon çağrı ilişkisi (A, B'yi çağırır)
# 2. DATA_FLOW_CLAIM: Veri akışı ilişkisi (X verisi Y'den gelir)
# 3. EXISTENCE_CLAIM: Varlık iddiası (X fonksiyonu/sınıfı mevcuttur)
# 4. ATTRIBUTE_CLAIM: Özellik iddiası (X sınıfının Y özelliği vardır)
# 5. RELATIONSHIP_CLAIM: Genel ilişki (X ve Y arasında ilişki var)
#
# Çıkarma Yöntemleri:
# ------------------
# 1. Kural tabanlı (regex pattern matching)
# 2. Anahtar kelime tespiti
# 3. Cümle yapısı analizi
# =============================================================================

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ClaimType(Enum):
    """
    Claim türlerini tanımlayan enum.

    Her claim türü, farklı bir doğrulama stratejisi gerektirir:
    - CALL: Graf'ta kenar varlığı kontrolü
    - DATA_FLOW: Veri akış grafında yol kontrolü
    - EXISTENCE: Düğüm varlığı kontrolü
    - ATTRIBUTE: Sınıf/fonksiyon özellik kontrolü
    - RELATIONSHIP: Genel ilişki kontrolü
    """
    CALL = "call"                    # Fonksiyon çağrısı
    DATA_FLOW = "data_flow"          # Veri akışı
    EXISTENCE = "existence"          # Varlık
    ATTRIBUTE = "attribute"          # Özellik
    RELATIONSHIP = "relationship"    # Genel ilişki
    UNKNOWN = "unknown"              # Belirlenemeyen


@dataclass
class Claim:
    """
    Tek bir iddiayı temsil eden veri sınıfı.

    Attributes:
        text: Orijinal iddia metni
        claim_type: İddia türü (ClaimType enum)
        subject: İddianın öznesi (örn: çağıran fonksiyon)
        object: İddianın nesnesi (örn: çağrılan fonksiyon)
        predicate: İlişki türü (örn: "calls", "uses", "inherits")
        confidence: Çıkarım güven skoru (0-1 arası)
        source_step: İddianın çıkarıldığı adım numarası
        metadata: Ek bilgiler
    """
    text: str
    claim_type: ClaimType
    subject: Optional[str] = None
    object: Optional[str] = None
    predicate: Optional[str] = None
    confidence: float = 1.0
    source_step: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Claim'i sözlük formatına dönüştürür."""
        return {
            "text": self.text,
            "claim_type": self.claim_type.value,
            "subject": self.subject,
            "object": self.object,
            "predicate": self.predicate,
            "confidence": self.confidence,
            "source_step": self.source_step,
            "metadata": self.metadata
        }


class ClaimExtractor:
    """
    LLM çıktısından claim'leri çıkaran sınıf.

    Bu sınıf, doğal dil metnini analiz ederek doğrulanabilir
    iddiaları tespit eder ve yapılandırılmış formata dönüştürür.

    Kullanım:
        extractor = ClaimExtractor()
        claims = extractor.extract_claims(llm_output)

        for claim in claims:
            print(f"{claim.subject} -> {claim.object}: {claim.predicate}")
    """

    # =========================================================================
    # ÇAĞRI İLİŞKİSİ TESPİT KALIPLARI
    # Bu regex pattern'ları "X, Y'yi çağırır" tarzı ifadeleri yakalar
    # =========================================================================
    CALL_PATTERNS = [
        # Türkçe kalıplar
        r"(\w+)\s+(?:fonksiyonu|metodu)?\s*[,]?\s*(\w+)\s*(?:'[yiıuü]|'[yiıuü]|[yiıuü])?\s*çağır",
        r"(\w+)\s+(?:fonksiyonu|metodu)?\s+(\w+)\s+(?:fonksiyonunu|metodunu)\s+çağır",
        r"(\w+)\s+içinde\s+(\w+)\s+çağr[ıi]l",
        r"(\w+)\s+(?:tarafından)?\s*(\w+)\s+(?:çağrılıyor|çağırılır)",

        # İngilizce kalıplar
        r"(\w+)\s+(?:function|method)?\s*calls?\s+(\w+)",
        r"(\w+)\s+invokes?\s+(\w+)",
        r"(\w+)\s+executes?\s+(\w+)",
        r"in\s+(\w+)[,]?\s+(\w+)\s+is\s+called",

        # Genel kalıplar
        r"(\w+)\s*->\s*(\w+)",  # ok işareti ile gösterim
        r"(\w+)\s*→\s*(\w+)",   # unicode ok
        r"ÇAĞIRIYOR:\s*(\w+).*?(\w+)",  # Mock format

        # LLM formatı (FONKSIYON: X \n ÇAĞIRIYOR: Y)
        r"FONKSIYON:\s*(\w+)\s*\n\s*ÇAĞIRIYOR:\s*(\w+)",  # Yeni satır ile
        r"FONKSIYON:\s*(\w+).*?ÇAĞIRIYOR:\s*(\w+)",  # Genel
    ]

    # =========================================================================
    # VERİ AKIŞI TESPİT KALIPLARI
    # "X verisi Y'den gelir" tarzı ifadeleri yakalar
    # =========================================================================
    DATA_FLOW_PATTERNS = [
        # Türkçe kalıplar
        r"(\w+)\s+(?:değişkeni|verisi)?\s*(\w+)\s*'?(?:den|dan|ten|tan)\s+(?:gelir|alınır|elde edilir)",
        r"(\w+)\s+(\w+)\s*'?(?:ye|ya|e|a)\s+(?:atanır|aktarılır|geçirilir)",
        r"(\w+)\s+(?:değeri)?\s*(\w+)\s+(?:tarafından|ile)\s+(?:hesaplanır|belirlenir)",

        # İngilizce kalıplar
        r"(\w+)\s+(?:is\s+)?(?:derived|obtained|calculated)\s+from\s+(\w+)",
        r"(\w+)\s+(?:uses?|depends?\s+on)\s+(\w+)",
        r"(\w+)\s+(?:is\s+)?passed\s+to\s+(\w+)",
        r"data\s+flows?\s+from\s+(\w+)\s+to\s+(\w+)",
    ]

    # =========================================================================
    # VARLIK TESPİT KALIPLARI
    # "X fonksiyonu/sınıfı mevcuttur" tarzı ifadeleri yakalar
    # =========================================================================
    EXISTENCE_PATTERNS = [
        # Türkçe kalıplar
        r"(\w+)\s+(?:adında|isminde)?\s*(?:bir)?\s*(?:fonksiyon|metod|sınıf|değişken)\s+(?:var|mevcut|tanımlı|bulunuyor)",
        r"(\w+)\s+(?:fonksiyonu|metodu|sınıfı|değişkeni)\s+(?:tanımlanmış|mevcut)",
        r"(?:fonksiyon|metod|sınıf):\s*(\w+)",

        # İngilizce kalıplar
        r"(?:function|method|class|variable)\s+(?:named\s+)?(\w+)\s+(?:exists?|is\s+defined)",
        r"there\s+is\s+(?:a\s+)?(?:function|method|class)\s+(?:called\s+)?(\w+)",
        r"(\w+)\s+(?:function|method|class)\s+is\s+(?:defined|declared)",

        # Genel
        r"FONKSIYON:\s*(\w+)",  # Mock format
    ]

    # =========================================================================
    # ÖZELLİK TESPİT KALIPLARI
    # "X sınıfının Y özelliği/metodu vardır" tarzı ifadeleri yakalar
    # =========================================================================
    ATTRIBUTE_PATTERNS = [
        # Türkçe kalıplar
        r"(\w+)\s+sınıfının\s+(\w+)\s+(?:metodu|özelliği|niteliği)\s+(?:var|mevcut)",
        r"(\w+)\s+sınıfı\s+(\w+)\s+(?:metodunu|özelliğini)\s+(?:içerir|barındırır)",
        r"(\w+)\s+içinde\s+(\w+)\s+(?:metodu|özelliği)\s+(?:tanımlı|mevcut)",

        # İngilizce kalıplar
        r"(\w+)\s+(?:class\s+)?has\s+(?:a\s+)?(?:method|attribute|property)\s+(?:called\s+)?(\w+)",
        r"(\w+)\s+contains?\s+(\w+)\s+(?:method|attribute)",
        r"method\s+(\w+)\s+(?:of|in)\s+(?:class\s+)?(\w+)",
    ]

    # =========================================================================
    # ÇAĞRI ANAHTAR KELİMELERİ
    # Bu kelimeler bir çağrı ilişkisini işaret eder
    # =========================================================================
    CALL_KEYWORDS = [
        "çağır", "çağrı", "invoke", "call", "execute", "run",
        "kullan", "use", "trigger", "tetikle"
    ]

    # =========================================================================
    # VERİ AKIŞI ANAHTAR KELİMELERİ
    # =========================================================================
    DATA_FLOW_KEYWORDS = [
        "veri", "data", "değer", "value", "parametre", "parameter",
        "girdi", "input", "çıktı", "output", "sonuç", "result",
        "akış", "flow", "geçir", "pass", "aktarır", "transfer"
    ]

    def __init__(self):
        """ClaimExtractor'ı başlatır."""
        # Çıkarılan claim'leri saklayan liste
        self.claims: List[Claim] = []

        # İstatistikler
        self.stats = {
            "total_claims": 0,
            "by_type": {ct.value: 0 for ct in ClaimType}
        }

    def extract_claims(self, llm_output: str, reasoning_steps: Optional[List[str]] = None) -> List[Claim]:
        """
        LLM çıktısından tüm claim'leri çıkarır.

        Bu ana metod, farklı çıkarma stratejilerini sırayla uygular:
        1. Önce JSON formatını dene (yeni strict format)
        2. JSON başarısız olursa regex tabanlı çıkarma yap

        Args:
            llm_output: LLM'den gelen ham metin
            reasoning_steps: Ayrıştırılmış adımlar (opsiyonel)

        Returns:
            Çıkarılan Claim nesnelerinin listesi
        """
        # Önceki sonuçları temizle
        self.claims = []
        self.stats = {
            "total_claims": 0,
            "by_type": {ct.value: 0 for ct in ClaimType}
        }

        # 1. Önce JSON formatını dene
        json_success = self._extract_from_json(llm_output)

        if json_success:
            print("✅ JSON formatı başarıyla parse edildi")
        else:
            print("⚠️ JSON parse başarısız, regex yöntemine geçiliyor...")
            # 2. JSON başarısız olursa mevcut regex yöntemini kullan
            self._extract_from_text(llm_output, 0)

            # Adımlar verilmişse onları da işle (ek claim'ler için)
            if reasoning_steps:
                for step_num, step in enumerate(reasoning_steps, 1):
                    self._extract_from_text(step, step_num)

        # Tekrar eden claim'leri kaldır
        self._remove_duplicates()

        # İstatistikleri güncelle
        self._update_stats()

        return self.claims

    def _extract_from_json(self, text: str) -> bool:
        """
        JSON formatındaki LLM çıktısından claim'leri çıkarır.

        Beklenen format:
        {
            "functions": [
                {"name": "func_name", "calls": ["called_func1", "called_func2"]}
            ]
        }

        Args:
            text: LLM çıktısı (JSON olması beklenir)

        Returns:
            True eğer JSON başarıyla parse edildiyse
        """
        try:
            # JSON'u metinden çıkar (bazen markdown code block içinde olabilir)
            json_text = text.strip()

            # Markdown code block'ları temizle
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0]

            json_text = json_text.strip()

            # JSON parse et
            data = json.loads(json_text)

            # "functions" anahtarı var mı kontrol et
            if "functions" not in data:
                return False

            functions = data["functions"]

            if not isinstance(functions, list):
                return False

            # Her fonksiyon için claim'ler oluştur
            for func_data in functions:
                if not isinstance(func_data, dict):
                    continue

                func_name = func_data.get("name", "").strip()
                calls = func_data.get("calls", [])

                if not func_name:
                    continue

                # Fonksiyon varlık claim'i
                existence_claim = Claim(
                    text=f"Function {func_name} exists",
                    claim_type=ClaimType.EXISTENCE,
                    subject=func_name.lower(),
                    predicate="exists",
                    confidence=1.0,
                    source_step=0,
                    metadata={"entity_type": "function", "source": "json"}
                )
                self.claims.append(existence_claim)

                # Çağrı claim'leri
                if isinstance(calls, list):
                    for callee in calls:
                        callee = str(callee).strip()
                        if callee and self._is_valid_identifier(callee):
                            call_claim = Claim(
                                text=f"{func_name} calls {callee}",
                                claim_type=ClaimType.CALL,
                                subject=func_name.lower(),
                                object=callee.lower(),
                                predicate="calls",
                                confidence=1.0,  # JSON formatında yüksek güven
                                source_step=0,
                                metadata={"source": "json"}
                            )
                            self.claims.append(call_claim)

            # En az bir claim çıkarıldı mı?
            return len(self.claims) > 0

        except (json.JSONDecodeError, KeyError, TypeError, IndexError) as e:
            # JSON parse hatası - False dön, regex yöntemine geçilecek
            print(f"   JSON parse hatası: {e}")
            return False

    def _extract_from_text(self, text: str, step_num: int):
        """
        Tek bir metin bloğundan claim'leri çıkarır.

        Args:
            text: Analiz edilecek metin
            step_num: Bu metnin adım numarası
        """
        # 1. Çağrı claim'lerini çıkar
        self._extract_call_claims(text, step_num)

        # 2. Veri akışı claim'lerini çıkar
        self._extract_data_flow_claims(text, step_num)

        # 3. Varlık claim'lerini çıkar
        self._extract_existence_claims(text, step_num)

        # 4. Özellik claim'lerini çıkar
        self._extract_attribute_claims(text, step_num)

    def _extract_call_claims(self, text: str, step_num: int):
        """
        Metinden çağrı ilişkisi claim'lerini çıkarır.

        Hem regex pattern'ları hem de anahtar kelime tespiti kullanır.

        Args:
            text: Analiz edilecek metin
            step_num: Adım numarası
        """
        # Her pattern'ı dene
        for pattern in self.CALL_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    caller, callee = groups[0], groups[1]

                    # Geçersiz eşleşmeleri filtrele
                    if self._is_valid_identifier(caller) and self._is_valid_identifier(callee):
                        claim = Claim(
                            text=match.group(0),
                            claim_type=ClaimType.CALL,
                            subject=caller.lower(),
                            object=callee.lower(),
                            predicate="calls",
                            confidence=0.9,
                            source_step=step_num
                        )
                        self.claims.append(claim)

        # Özel format: "FONKSIYON: X\nÇAĞIRIYOR: Y, Z" blokları
        # Tüm FONKSIYON-ÇAĞIRIYOR bloklarını bul
        # Backtick'leri (`) de kabul et çünkü LLM'ler bazen `fonksiyon_adı` şeklinde yazıyor
        # Parantez içindeki ek açıklamaları da kabul et: `main` (dolaylı olarak)
        block_pattern = r"FONKSIYON:\s*`?(\w+(?:\.\w+)?)`?\s*(?:\([^)]*\))?\s*\n\s*ÇAĞIRIYOR:\s*([^\n]+)"
        blocks = re.findall(block_pattern, text, re.IGNORECASE)

        for caller, callees_text in blocks:
            # "YOK" değilse işle
            if callees_text.strip().upper() != "YOK":
                # Virgülle ayrılmış fonksiyonları ayır
                callees = [c.strip() for c in callees_text.split(",")]
                for callee in callees:
                    # Backtick'leri temizle
                    callee = callee.strip("`").strip()
                    # Noktalı isimleri de kabul et (örn: DataProcessor.load_data)
                    callee_clean = callee.split(".")[-1] if "." in callee else callee
                    if self._is_valid_identifier(callee_clean):
                        claim = Claim(
                            text=f"{caller} -> {callee}",
                            claim_type=ClaimType.CALL,
                            subject=caller.lower().split(".")[-1],
                            object=callee_clean.lower(),
                            predicate="calls",
                            confidence=0.95,
                            source_step=step_num
                        )
                        self.claims.append(claim)

    def _extract_data_flow_claims(self, text: str, step_num: int):
        """
        Metinden veri akışı claim'lerini çıkarır.

        Args:
            text: Analiz edilecek metin
            step_num: Adım numarası
        """
        for pattern in self.DATA_FLOW_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    source, target = groups[0], groups[1]

                    if self._is_valid_identifier(source) and self._is_valid_identifier(target):
                        claim = Claim(
                            text=match.group(0),
                            claim_type=ClaimType.DATA_FLOW,
                            subject=source.lower(),
                            object=target.lower(),
                            predicate="data_flows_to",
                            confidence=0.8,
                            source_step=step_num
                        )
                        self.claims.append(claim)

    def _extract_existence_claims(self, text: str, step_num: int):
        """
        Metinden varlık claim'lerini çıkarır.

        Args:
            text: Analiz edilecek metin
            step_num: Adım numarası
        """
        for pattern in self.EXISTENCE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                groups = match.groups()
                if groups:
                    entity = groups[0]

                    if self._is_valid_identifier(entity):
                        # Varlık tipini belirle
                        entity_type = self._detect_entity_type(match.group(0))

                        claim = Claim(
                            text=match.group(0),
                            claim_type=ClaimType.EXISTENCE,
                            subject=entity.lower(),
                            predicate="exists",
                            confidence=0.85,
                            source_step=step_num,
                            metadata={"entity_type": entity_type}
                        )
                        self.claims.append(claim)

    def _extract_attribute_claims(self, text: str, step_num: int):
        """
        Metinden özellik claim'lerini çıkarır.

        Args:
            text: Analiz edilecek metin
            step_num: Adım numarası
        """
        for pattern in self.ATTRIBUTE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    owner, attribute = groups[0], groups[1]

                    if self._is_valid_identifier(owner) and self._is_valid_identifier(attribute):
                        claim = Claim(
                            text=match.group(0),
                            claim_type=ClaimType.ATTRIBUTE,
                            subject=owner.lower(),
                            object=attribute.lower(),
                            predicate="has_attribute",
                            confidence=0.8,
                            source_step=step_num
                        )
                        self.claims.append(claim)

        # "Metodları: x, y, z" formatı
        methods_pattern = r"Metodlar[ıi]?:\s*([^\n]+)"
        class_pattern = r"(\w+)\s+(?:SINIFI|sınıfı|class)"

        class_match = re.search(class_pattern, text, re.IGNORECASE)
        methods_match = re.search(methods_pattern, text, re.IGNORECASE)

        if class_match and methods_match:
            class_name = class_match.group(1)
            methods_text = methods_match.group(1)
            methods = [m.strip() for m in methods_text.split(",")]

            for method in methods:
                if self._is_valid_identifier(method):
                    claim = Claim(
                        text=f"{class_name} has method {method}",
                        claim_type=ClaimType.ATTRIBUTE,
                        subject=class_name.lower(),
                        object=method.lower(),
                        predicate="has_method",
                        confidence=0.9,
                        source_step=step_num
                    )
                    self.claims.append(claim)

    def _is_valid_identifier(self, name: str) -> bool:
        """
        Bir ismin geçerli Python tanımlayıcısı olup olmadığını kontrol eder.

        Args:
            name: Kontrol edilecek isim

        Returns:
            True eğer geçerli bir tanımlayıcıysa
        """
        if not name:
            return False

        # Python anahtar kelimeleri ve yaygın kelimeler filtrelenir
        invalid_words = {
            "bir", "bu", "şu", "ve", "ile", "için", "the", "a", "an",
            "is", "are", "was", "were", "this", "that", "these",
            "function", "fonksiyon", "method", "metod", "class", "sınıf",
            "variable", "değişken", "yok", "none", "true", "false"
        }

        name_lower = name.lower().strip()

        # Çok kısa veya invalid kelime mi?
        if len(name_lower) < 2 or name_lower in invalid_words:
            return False

        # Geçerli Python identifier mı?
        return name_lower.isidentifier()

    def _detect_entity_type(self, text: str) -> str:
        """
        Metinden varlık tipini tespit eder.

        Args:
            text: Analiz edilecek metin

        Returns:
            Varlık tipi ("function", "class", "variable", "method", "unknown")
        """
        text_lower = text.lower()

        if "fonksiyon" in text_lower or "function" in text_lower:
            return "function"
        elif "sınıf" in text_lower or "class" in text_lower:
            return "class"
        elif "metod" in text_lower or "method" in text_lower:
            return "method"
        elif "değişken" in text_lower or "variable" in text_lower:
            return "variable"
        else:
            return "unknown"

    def _remove_duplicates(self):
        """
        Tekrar eden claim'leri kaldırır.

        İki claim, aynı subject, object ve predicate'e sahipse tekrar sayılır.
        """
        seen = set()
        unique_claims = []

        for claim in self.claims:
            # Benzersiz anahtar oluştur
            key = (claim.claim_type.value, claim.subject, claim.object, claim.predicate)

            if key not in seen:
                seen.add(key)
                unique_claims.append(claim)

        self.claims = unique_claims

    def _update_stats(self):
        """İstatistikleri günceller."""
        self.stats["total_claims"] = len(self.claims)

        for claim in self.claims:
            self.stats["by_type"][claim.claim_type.value] += 1

    def get_claims_by_type(self, claim_type: ClaimType) -> List[Claim]:
        """
        Belirli türdeki claim'leri döndürür.

        Args:
            claim_type: İstenilen claim türü

        Returns:
            Filtrelenmiş claim listesi
        """
        return [c for c in self.claims if c.claim_type == claim_type]

    def get_call_claims(self) -> List[Claim]:
        """Sadece çağrı claim'lerini döndürür."""
        return self.get_claims_by_type(ClaimType.CALL)

    def get_existence_claims(self) -> List[Claim]:
        """Sadece varlık claim'lerini döndürür."""
        return self.get_claims_by_type(ClaimType.EXISTENCE)

    def to_dict(self) -> Dict[str, Any]:
        """Tüm sonuçları sözlük formatında döndürür."""
        return {
            "claims": [c.to_dict() for c in self.claims],
            "statistics": self.stats
        }

    def print_summary(self):
        """Claim özetini konsola yazdırır."""
        print("=" * 60)
        print("CLAIM EXTRACTION ÖZETİ")
        print("=" * 60)

        print(f"\n📊 Toplam claim sayısı: {self.stats['total_claims']}")
        print("\nTüre göre dağılım:")
        for claim_type, count in self.stats["by_type"].items():
            if count > 0:
                print(f"   {claim_type}: {count}")

        print("\n📝 ÇIKARILAN CLAIM'LER:")
        for i, claim in enumerate(self.claims, 1):
            print(f"\n{i}. [{claim.claim_type.value.upper()}]")
            print(f"   Metin: {claim.text[:80]}{'...' if len(claim.text) > 80 else ''}")
            if claim.subject:
                print(f"   Özne: {claim.subject}")
            if claim.object:
                print(f"   Nesne: {claim.object}")
            print(f"   İlişki: {claim.predicate}")
            print(f"   Güven: {claim.confidence:.2f}")


# =============================================================================
# TEST KODU
# =============================================================================
if __name__ == "__main__":
    # Test metni (Mock LLM çıktısı benzeri)
    test_text = """
ADIM 1: GENEL BAKIŞ
Bu kod 4 fonksiyon ve 1 sınıf içermektedir.

ADIM 2: main FONKSİYONU ANALİZİ
- main fonksiyonu process_data fonksiyonunu çağırıyor
- main fonksiyonu save_result fonksiyonunu çağırıyor
- result değişkeni process_data'dan elde ediliyor

ADIM 3: process_data FONKSİYONU ANALİZİ
- process_data fonksiyonu Calculator sınıfını kullanıyor
- calc.add metodu çağrılıyor
- total değişkeni hesaplanıyor

ADIM 4: Calculator SINIFI ANALİZİ
- Calculator sınıfı tanımlanmış
- Metodları: __init__, add, _validate

ADIM 5: ÇAĞRI İLİŞKİLERİ ÖZETİ
FONKSIYON: main
ÇAĞIRIYOR: process_data, save_result, print

FONKSIYON: process_data
ÇAĞIRIYOR: add

FONKSIYON: save_result
ÇAĞIRIYOR: YOK
"""

    print("=" * 60)
    print("CLAIM EXTRACTOR TESTİ")
    print("=" * 60)

    # Extractor oluştur
    extractor = ClaimExtractor()

    # Claim'leri çıkar
    claims = extractor.extract_claims(test_text)

    # Sonuçları yazdır
    extractor.print_summary()

    # Sadece çağrı claim'lerini göster
    print("\n" + "=" * 60)
    print("SADECE ÇAĞRI CLAIM'LERİ")
    print("=" * 60)
    for claim in extractor.get_call_claims():
        print(f"   {claim.subject} -> {claim.object}")
