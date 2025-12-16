# =============================================================================
# VERIFIER (DOĞRULAMA MOTORU) MODÜLÜ
# =============================================================================
# Bu modül, LLM'den çıkarılan claim'leri kod grafları üzerinde doğrular.
#
# Doğrulama Süreci:
# ----------------
# 1. Claim'deki varlıkları (subject, object) kod varlıklarına eşle
# 2. Claim tipine göre uygun doğrulama stratejisini seç
# 3. Graf üzerinde sorgu çalıştır (kenar varlığı, yol varlığı vb.)
# 4. Sonucu sınıflandır: VALID, HALLUCINATION, UNVERIFIABLE
#
# Doğrulama Stratejileri:
# ----------------------
# - CALL_CLAIM: Call graph'ta A→B kenarı var mı?
# - DATA_FLOW_CLAIM: Data flow graph'ta yol var mı?
# - EXISTENCE_CLAIM: Düğüm grafte mevcut mu?
# - ATTRIBUTE_CLAIM: Sınıfın ilgili metodu/özelliği var mı?
#
# Sonuç Sınıfları:
# ---------------
# - VALID: İddia doğru, graf ile tutarlı
# - HALLUCINATION: İddia yanlış, graf ile tutarsız (hata!)
# - UNVERIFIABLE: İddia doğrulanamıyor (eksik bilgi)
# - PARTIALLY_VALID: Kısmen doğru (fuzzy eşleşme ile)
# =============================================================================

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Diğer modülleri import et
from .claim_extractor import Claim, ClaimType
from .entity_mapper import EntityMapper, EntityMatch, MatchType
from .graph_builder import GraphBuilder


class VerificationResult(Enum):
    """
    Doğrulama sonuç türlerini tanımlayan enum.

    VALID: İddia tamamen doğru
    HALLUCINATION: İddia kesinlikle yanlış (kritik hata!)
    UNVERIFIABLE: İddia doğrulanamıyor (bilgi eksik)
    PARTIALLY_VALID: Kısmen doğru (düşük güven)
    """
    VALID = "valid"
    HALLUCINATION = "hallucination"
    UNVERIFIABLE = "unverifiable"
    PARTIALLY_VALID = "partially_valid"


@dataclass
class VerificationDetail:
    """
    Tek bir claim'in doğrulama detaylarını tutan sınıf.

    Attributes:
        claim: Doğrulanan claim
        result: Doğrulama sonucu
        confidence: Sonuç güven skoru (0-1)
        reason: Sonucun nedeni (açıklama)
        subject_match: Subject için entity eşleşmesi
        object_match: Object için entity eşleşmesi
        graph_evidence: Graf'tan elde edilen kanıt (yol, kenar vb.)
    """
    claim: Claim
    result: VerificationResult
    confidence: float
    reason: str
    subject_match: Optional[EntityMatch] = None
    object_match: Optional[EntityMatch] = None
    graph_evidence: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Sözlük formatına dönüştürür."""
        return {
            "claim": self.claim.to_dict(),
            "result": self.result.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "subject_match": self.subject_match.to_dict() if self.subject_match else None,
            "object_match": self.object_match.to_dict() if self.object_match else None,
            "graph_evidence": self.graph_evidence
        }

    def is_valid(self) -> bool:
        """Claim geçerli mi?"""
        return self.result in (VerificationResult.VALID, VerificationResult.PARTIALLY_VALID)

    def is_hallucination(self) -> bool:
        """Claim bir halüsinasyon mu?"""
        return self.result == VerificationResult.HALLUCINATION


@dataclass
class VerificationReport:
    """
    Tüm doğrulama sürecinin raporunu tutan sınıf.

    Attributes:
        details: Her claim için doğrulama detayları
        summary: Özet istatistikler
        hallucinations: Tespit edilen halüsinasyonlar listesi
    """
    details: List[VerificationDetail] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    hallucinations: List[VerificationDetail] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Sözlük formatına dönüştürür."""
        return {
            "details": [d.to_dict() for d in self.details],
            "summary": self.summary,
            "hallucinations": [h.to_dict() for h in self.hallucinations]
        }


class Verifier:
    """
    Claim'leri kod grafları üzerinde doğrulayan sınıf.

    Bu sınıf, tüm doğrulama pipeline'ını koordine eder:
    1. Entity mapping
    2. Graf sorgulaması
    3. Sonuç sınıflandırması

    Kullanım:
        verifier = Verifier(graph_builder, entity_mapper)
        report = verifier.verify_claims(claims)

        for detail in report.hallucinations:
            print(f"HALÜSİNASYON: {detail.claim.text}")
    """

    def __init__(self, graph_builder: GraphBuilder, entity_mapper: EntityMapper):
        """
        Verifier'ı başlatır.

        Args:
            graph_builder: Kod graflarını içeren GraphBuilder nesnesi
            entity_mapper: Varlık eşleştirici EntityMapper nesnesi
        """
        self.graph_builder = graph_builder
        self.entity_mapper = entity_mapper

        # Doğrulama sonuçları
        self.verification_details: List[VerificationDetail] = []

        # İstatistikler
        self.stats = {
            "total_claims": 0,
            "valid": 0,
            "hallucination": 0,
            "unverifiable": 0,
            "partially_valid": 0
        }

    def verify_claims(self, claims: List[Claim]) -> VerificationReport:
        """
        Bir claim listesini doğrular.

        Her claim için:
        1. Claim tipine göre doğrulama stratejisi seç
        2. Varlıkları eşle
        3. Graf sorgula
        4. Sonucu kaydet

        Args:
            claims: Doğrulanacak Claim listesi

        Returns:
            VerificationReport nesnesi
        """
        # Önceki sonuçları temizle
        self.verification_details = []
        self.stats = {
            "total_claims": 0,
            "valid": 0,
            "hallucination": 0,
            "unverifiable": 0,
            "partially_valid": 0
        }

        # Her claim'i doğrula
        for claim in claims:
            detail = self._verify_single_claim(claim)
            self.verification_details.append(detail)

            # İstatistikleri güncelle
            self.stats["total_claims"] += 1
            self.stats[detail.result.value] += 1

        # Rapor oluştur
        report = self._create_report()
        return report

    def _verify_single_claim(self, claim: Claim) -> VerificationDetail:
        """
        Tek bir claim'i doğrular.

        Claim tipine göre uygun doğrulama metodunu çağırır.

        Args:
            claim: Doğrulanacak claim

        Returns:
            VerificationDetail nesnesi
        """
        # Claim tipine göre doğrulama stratejisi seç
        if claim.claim_type == ClaimType.CALL:
            return self._verify_call_claim(claim)
        elif claim.claim_type == ClaimType.DATA_FLOW:
            return self._verify_data_flow_claim(claim)
        elif claim.claim_type == ClaimType.EXISTENCE:
            return self._verify_existence_claim(claim)
        elif claim.claim_type == ClaimType.ATTRIBUTE:
            return self._verify_attribute_claim(claim)
        else:
            # Bilinmeyen tip - doğrulanamaz
            return VerificationDetail(
                claim=claim,
                result=VerificationResult.UNVERIFIABLE,
                confidence=0.0,
                reason="Bilinmeyen claim tipi, doğrulanamıyor"
            )

    def _verify_call_claim(self, claim: Claim) -> VerificationDetail:
        """
        Bir çağrı claim'ini doğrular.

        "A fonksiyonu B'yi çağırır" iddiasını Call Graph üzerinde kontrol eder.

        Doğrulama mantığı:
        1. A (subject) ve B (object) varlıklarını eşle
        2. Call graph'ta A→B kenarı var mı kontrol et
        3. Doğrudan kenar yoksa, dolaylı yol var mı bak

        Args:
            claim: CALL tipinde claim

        Returns:
            VerificationDetail
        """
        subject = claim.subject
        obj = claim.object

        # Varlıkları eşle
        subject_match = self.entity_mapper.map_entity(subject, expected_type="function")
        object_match = self.entity_mapper.map_entity(obj, expected_type="function")

        # Her iki varlık da eşleşti mi?
        if not subject_match.is_matched():
            return VerificationDetail(
                claim=claim,
                result=VerificationResult.UNVERIFIABLE,
                confidence=0.3,
                reason=f"'{subject}' varlığı kodda bulunamadı",
                subject_match=subject_match,
                object_match=object_match
            )

        if not object_match.is_matched():
            # Object bulunamadı - bu bir halüsinasyon olabilir
            # Ama harici fonksiyon (print, len vb.) olabilir
            if self._is_builtin_function(obj):
                # Built-in fonksiyon - call graph'ta kontrol et
                if self.graph_builder.has_call(subject_match.code_entity, obj):
                    return VerificationDetail(
                        claim=claim,
                        result=VerificationResult.VALID,
                        confidence=0.9,
                        reason=f"'{subject}' built-in '{obj}' fonksiyonunu çağırıyor",
                        subject_match=subject_match,
                        object_match=object_match,
                        graph_evidence={"edge_exists": True, "is_builtin": True}
                    )

            return VerificationDetail(
                claim=claim,
                result=VerificationResult.HALLUCINATION,
                confidence=0.8,
                reason=f"'{obj}' fonksiyonu kodda tanımlı değil - olası halüsinasyon",
                subject_match=subject_match,
                object_match=object_match
            )

        # Her iki varlık da eşleşti - graf üzerinde kontrol et
        caller = subject_match.code_entity
        callee = object_match.code_entity

        # Doğrudan çağrı var mı?
        if self.graph_builder.has_call(caller, callee):
            confidence = min(subject_match.confidence, object_match.confidence)
            return VerificationDetail(
                claim=claim,
                result=VerificationResult.VALID,
                confidence=confidence,
                reason=f"DOĞRULANDI: '{caller}' fonksiyonu '{callee}' fonksiyonunu çağırıyor",
                subject_match=subject_match,
                object_match=object_match,
                graph_evidence={"edge_exists": True, "direct_call": True}
            )

        # Dolaylı yol var mı?
        path = self.graph_builder.find_path(caller, callee, graph_type="call")
        if path:
            return VerificationDetail(
                claim=claim,
                result=VerificationResult.PARTIALLY_VALID,
                confidence=0.6,
                reason=f"Dolaylı çağrı zinciri mevcut: {' → '.join(path)}",
                subject_match=subject_match,
                object_match=object_match,
                graph_evidence={"edge_exists": False, "path_exists": True, "path": path}
            )

        # Hiçbir bağlantı yok - halüsinasyon
        return VerificationDetail(
            claim=claim,
            result=VerificationResult.HALLUCINATION,
            confidence=0.9,
            reason=f"HALÜSİNASYON: '{caller}' fonksiyonu '{callee}' fonksiyonunu ÇAĞIRMIYOR",
            subject_match=subject_match,
            object_match=object_match,
            graph_evidence={"edge_exists": False, "path_exists": False}
        )

    def _verify_data_flow_claim(self, claim: Claim) -> VerificationDetail:
        """
        Bir veri akışı claim'ini doğrular.

        "X verisi Y'den gelir" iddiasını Data Flow Graph üzerinde kontrol eder.

        Args:
            claim: DATA_FLOW tipinde claim

        Returns:
            VerificationDetail
        """
        subject = claim.subject
        obj = claim.object

        # Varlıkları eşle
        subject_match = self.entity_mapper.map_entity(subject)
        object_match = self.entity_mapper.map_entity(obj)

        # Eşleşme kontrolü
        if not subject_match.is_matched() or not object_match.is_matched():
            unmatched = subject if not subject_match.is_matched() else obj
            return VerificationDetail(
                claim=claim,
                result=VerificationResult.UNVERIFIABLE,
                confidence=0.3,
                reason=f"'{unmatched}' varlığı kodda bulunamadı",
                subject_match=subject_match,
                object_match=object_match
            )

        source = subject_match.code_entity
        target = object_match.code_entity

        # Data flow graph'ta yol var mı?
        if self.graph_builder.has_path(source, target, graph_type="data_flow"):
            path = self.graph_builder.find_path(source, target, graph_type="data_flow")
            return VerificationDetail(
                claim=claim,
                result=VerificationResult.VALID,
                confidence=0.85,
                reason=f"Veri akışı doğrulandı: {' → '.join(path) if path else 'mevcut'}",
                subject_match=subject_match,
                object_match=object_match,
                graph_evidence={"path_exists": True, "path": path}
            )

        # Ters yönde kontrol et
        if self.graph_builder.has_path(target, source, graph_type="data_flow"):
            path = self.graph_builder.find_path(target, source, graph_type="data_flow")
            return VerificationDetail(
                claim=claim,
                result=VerificationResult.PARTIALLY_VALID,
                confidence=0.6,
                reason=f"Ters yönlü veri akışı mevcut: {' → '.join(path) if path else ''}",
                subject_match=subject_match,
                object_match=object_match,
                graph_evidence={"path_exists": True, "reversed": True, "path": path}
            )

        return VerificationDetail(
            claim=claim,
            result=VerificationResult.HALLUCINATION,
            confidence=0.7,
            reason=f"'{source}' ile '{target}' arasında veri akışı YOK",
            subject_match=subject_match,
            object_match=object_match,
            graph_evidence={"path_exists": False}
        )

    def _verify_existence_claim(self, claim: Claim) -> VerificationDetail:
        """
        Bir varlık claim'ini doğrular.

        "X fonksiyonu/sınıfı mevcuttur" iddiasını kontrol eder.

        Args:
            claim: EXISTENCE tipinde claim

        Returns:
            VerificationDetail
        """
        entity_name = claim.subject

        # Varlığı eşle
        entity_match = self.entity_mapper.map_entity(entity_name)

        if entity_match.is_matched():
            return VerificationDetail(
                claim=claim,
                result=VerificationResult.VALID,
                confidence=entity_match.confidence,
                reason=f"'{entity_match.code_entity}' varlığı kodda mevcut "
                       f"(tip: {entity_match.entity_type})",
                subject_match=entity_match,
                graph_evidence={"exists": True, "entity_type": entity_match.entity_type}
            )

        return VerificationDetail(
            claim=claim,
            result=VerificationResult.HALLUCINATION,
            confidence=0.9,
            reason=f"HALÜSİNASYON: '{entity_name}' varlığı kodda MEVCUT DEĞİL",
            subject_match=entity_match,
            graph_evidence={"exists": False}
        )

    def _verify_attribute_claim(self, claim: Claim) -> VerificationDetail:
        """
        Bir özellik claim'ini doğrular.

        "X sınıfının Y metodu vardır" iddiasını kontrol eder.

        Args:
            claim: ATTRIBUTE tipinde claim

        Returns:
            VerificationDetail
        """
        owner = claim.subject  # Sınıf adı
        attribute = claim.object  # Metod/özellik adı

        # Sınıfı eşle
        owner_match = self.entity_mapper.map_entity(owner, expected_type="class")

        if not owner_match.is_matched():
            return VerificationDetail(
                claim=claim,
                result=VerificationResult.UNVERIFIABLE,
                confidence=0.3,
                reason=f"'{owner}' sınıfı kodda bulunamadı",
                subject_match=owner_match
            )

        # Metodu eşle
        attribute_match = self.entity_mapper.map_entity(attribute, expected_type="method")

        if attribute_match.is_matched():
            # Metod var - ama bu sınıfa mı ait?
            # Basit kontrol: metod adı sınıfın metodları arasında mı?
            # (Daha detaylı kontrol için AST result'a bakmak gerekir)
            return VerificationDetail(
                claim=claim,
                result=VerificationResult.VALID,
                confidence=min(owner_match.confidence, attribute_match.confidence),
                reason=f"'{owner_match.code_entity}' sınıfının "
                       f"'{attribute_match.code_entity}' metodu mevcut",
                subject_match=owner_match,
                object_match=attribute_match,
                graph_evidence={"has_attribute": True}
            )

        return VerificationDetail(
            claim=claim,
            result=VerificationResult.HALLUCINATION,
            confidence=0.8,
            reason=f"'{owner}' sınıfında '{attribute}' metodu/özelliği YOK",
            subject_match=owner_match,
            object_match=attribute_match,
            graph_evidence={"has_attribute": False}
        )

    def _is_builtin_function(self, name: str) -> bool:
        """
        Bir fonksiyonun Python built-in fonksiyonu olup olmadığını kontrol eder.

        Args:
            name: Fonksiyon adı

        Returns:
            True eğer built-in ise
        """
        builtins = {
            "print", "len", "range", "str", "int", "float", "list", "dict",
            "set", "tuple", "bool", "type", "isinstance", "hasattr", "getattr",
            "setattr", "open", "input", "sum", "min", "max", "abs", "round",
            "sorted", "reversed", "enumerate", "zip", "map", "filter", "any",
            "all", "format", "repr", "id", "hash", "callable", "dir", "vars",
            "globals", "locals", "exec", "eval", "compile", "help"
        }
        return name.lower() in builtins

    def _create_report(self) -> VerificationReport:
        """
        Doğrulama raporunu oluşturur.

        Returns:
            VerificationReport nesnesi
        """
        # Halüsinasyonları ayır
        hallucinations = [
            d for d in self.verification_details
            if d.result == VerificationResult.HALLUCINATION
        ]

        # Özet oluştur
        total = self.stats["total_claims"]
        summary = {
            "total_claims": total,
            "valid_count": self.stats["valid"],
            "hallucination_count": self.stats["hallucination"],
            "unverifiable_count": self.stats["unverifiable"],
            "partially_valid_count": self.stats["partially_valid"],
            "validity_rate": (self.stats["valid"] + self.stats["partially_valid"]) / total if total > 0 else 0,
            "hallucination_rate": self.stats["hallucination"] / total if total > 0 else 0
        }

        return VerificationReport(
            details=self.verification_details,
            summary=summary,
            hallucinations=hallucinations
        )

    def get_hallucinations(self) -> List[VerificationDetail]:
        """Tespit edilen halüsinasyonları döndürür."""
        return [
            d for d in self.verification_details
            if d.result == VerificationResult.HALLUCINATION
        ]

    def get_valid_claims(self) -> List[VerificationDetail]:
        """Doğrulanan claim'leri döndürür."""
        return [
            d for d in self.verification_details
            if d.result in (VerificationResult.VALID, VerificationResult.PARTIALLY_VALID)
        ]

    def print_report(self):
        """Doğrulama raporunu konsola yazdırır."""
        print("=" * 70)
        print("DOĞRULAMA RAPORU")
        print("=" * 70)

        total = self.stats["total_claims"]
        if total == 0:
            print("\n⚠️  Doğrulanacak claim bulunamadı.")
            return

        print(f"\n📊 ÖZET:")
        print(f"   Toplam Claim: {total}")
        print(f"   ✅ Geçerli: {self.stats['valid']} ({self.stats['valid']/total*100:.1f}%)")
        print(f"   ⚠️  Kısmen Geçerli: {self.stats['partially_valid']} ({self.stats['partially_valid']/total*100:.1f}%)")
        print(f"   ❌ Halüsinasyon: {self.stats['hallucination']} ({self.stats['hallucination']/total*100:.1f}%)")
        print(f"   ❓ Doğrulanamayan: {self.stats['unverifiable']} ({self.stats['unverifiable']/total*100:.1f}%)")

        # Halüsinasyonları listele
        hallucinations = self.get_hallucinations()
        if hallucinations:
            print(f"\n🚨 TESPİT EDİLEN HALÜSİNASYONLAR ({len(hallucinations)} adet):")
            print("-" * 70)
            for i, detail in enumerate(hallucinations, 1):
                print(f"\n{i}. {detail.claim.text[:60]}...")
                print(f"   Sebep: {detail.reason}")
                if detail.subject_match:
                    print(f"   Subject: {detail.claim.subject} → {detail.subject_match.code_entity or 'EŞLEŞMEDİ'}")
                if detail.object_match:
                    print(f"   Object: {detail.claim.object} → {detail.object_match.code_entity or 'EŞLEŞMEDİ'}")

        # Geçerli claim'leri listele
        valid_claims = self.get_valid_claims()
        if valid_claims:
            print(f"\n✅ DOĞRULANAN CLAIM'LER ({len(valid_claims)} adet):")
            print("-" * 70)
            for i, detail in enumerate(valid_claims[:5], 1):  # İlk 5'i göster
                print(f"\n{i}. {detail.claim.text[:60]}...")
                print(f"   Sonuç: {detail.reason[:70]}")

            if len(valid_claims) > 5:
                print(f"\n   ... ve {len(valid_claims) - 5} claim daha")

        print("\n" + "=" * 70)


# =============================================================================
# TEST KODU
# =============================================================================
if __name__ == "__main__":
    # Test için diğer modülleri import et
    from .ast_parser import ASTParser
    from .graph_builder import GraphBuilder
    from .entity_mapper import EntityMapper
    from .claim_extractor import ClaimExtractor, Claim, ClaimType

    # Test kodu
    test_code = '''
class Calculator:
    def __init__(self):
        self.result = 0

    def add(self, a, b):
        self.result = a + b
        self._validate()
        return self.result

    def _validate(self):
        if self.result > 100:
            print("Warning!")

def process_data(items):
    calc = Calculator()
    total = 0
    for item in items:
        total = calc.add(total, item)
    return total

def main():
    data = [1, 2, 3]
    result = process_data(data)
    print(result)
'''

    # Pipeline
    print("=" * 70)
    print("VERIFIER TEST")
    print("=" * 70)

    # 1. Parse
    parser = ASTParser()
    ast_result = parser.parse_code(test_code)

    # 2. Graf oluştur
    graph_builder = GraphBuilder()
    graph_builder.build_from_ast_result(ast_result)

    # 3. Entity mapper
    entity_mapper = EntityMapper()
    entity_mapper.load_code_entities(ast_result)

    # 4. Test claim'leri oluştur
    test_claims = [
        # Geçerli claim'ler
        Claim(
            text="main fonksiyonu process_data'yı çağırır",
            claim_type=ClaimType.CALL,
            subject="main",
            object="process_data",
            predicate="calls"
        ),
        Claim(
            text="process_data add metodunu çağırır",
            claim_type=ClaimType.CALL,
            subject="process_data",
            object="add",
            predicate="calls"
        ),
        Claim(
            text="Calculator sınıfı mevcuttur",
            claim_type=ClaimType.EXISTENCE,
            subject="Calculator",
            predicate="exists"
        ),

        # Halüsinasyon claim'leri
        Claim(
            text="main fonksiyonu save_result'ı çağırır",
            claim_type=ClaimType.CALL,
            subject="main",
            object="save_result",  # Bu fonksiyon yok!
            predicate="calls"
        ),
        Claim(
            text="DataProcessor sınıfı mevcuttur",
            claim_type=ClaimType.EXISTENCE,
            subject="DataProcessor",  # Bu sınıf yok!
            predicate="exists"
        ),
    ]

    # 5. Doğrula
    verifier = Verifier(graph_builder, entity_mapper)
    report = verifier.verify_claims(test_claims)

    # 6. Raporu yazdır
    verifier.print_report()
