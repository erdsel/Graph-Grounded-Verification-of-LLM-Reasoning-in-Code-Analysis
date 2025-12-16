# =============================================================================
# METRICS (METRİKLER) MODÜLÜ
# =============================================================================
# Bu modül, doğrulama sürecinin performansını ölçen metrikleri hesaplar.
#
# Hesaplanan Metrikler:
# --------------------
# 1. HALLUCINATION RATE (Halüsinasyon Oranı):
#    Yanlış/desteklenmeyen iddiaların toplam iddialara oranı
#    Formül: hallucination_count / total_claims
#
# 2. VALIDITY RATE (Geçerlilik Oranı):
#    Doğru iddiaların toplam iddialara oranı
#    Formül: (valid + partially_valid) / total_claims
#
# 3. COVERAGE (Kapsam):
#    LLM'nin bahsettiği kod yapılarının gerçek yapılara oranı
#    Formül: mentioned_entities / total_code_entities
#
# 4. STEP VALIDITY (Adım Geçerliliği):
#    Her reasoning adımının doğruluk durumu
#
# 5. CHAIN COHERENCE (Zincir Tutarlılığı):
#    Ardışık adımlar arasındaki tutarlılık
#
# 6. PRECISION & RECALL:
#    - Precision: Doğru pozitif / (Doğru pozitif + Yanlış pozitif)
#    - Recall: Doğru pozitif / (Doğru pozitif + Yanlış negatif)
# =============================================================================

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

from .verifier import VerificationDetail, VerificationResult, VerificationReport
from .claim_extractor import Claim, ClaimType


@dataclass
class MetricResult:
    """
    Tek bir metrik sonucunu temsil eden sınıf.

    Attributes:
        name: Metrik adı
        value: Metrik değeri (0-1 arası oran veya sayı)
        description: Metrik açıklaması
        details: Detaylı bilgiler
    """
    name: str
    value: float
    description: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Sözlük formatına dönüştürür."""
        return {
            "name": self.name,
            "value": self.value,
            "description": self.description,
            "details": self.details
        }

    def as_percentage(self) -> str:
        """Yüzde olarak formatlar."""
        return f"{self.value * 100:.1f}%"


@dataclass
class MetricsReport:
    """
    Tüm metriklerin raporunu tutan sınıf.

    Attributes:
        metrics: Hesaplanan metrikler listesi
        summary: Özet bilgiler
        recommendations: İyileştirme önerileri
    """
    metrics: List[MetricResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Sözlük formatına dönüştürür."""
        return {
            "metrics": [m.to_dict() for m in self.metrics],
            "summary": self.summary,
            "recommendations": self.recommendations
        }

    def get_metric(self, name: str) -> Optional[MetricResult]:
        """İsme göre metrik döndürür."""
        for metric in self.metrics:
            if metric.name == name:
                return metric
        return None


class MetricsCalculator:
    """
    Doğrulama metriklerini hesaplayan sınıf.

    Bu sınıf, VerificationReport'tan metrikleri hesaplar ve
    LLM'nin güvenilirliği hakkında sayısal değerlendirmeler sunar.

    Kullanım:
        calculator = MetricsCalculator()
        report = calculator.calculate(verification_report, code_entities)

        print(f"Halüsinasyon Oranı: {report.get_metric('hallucination_rate').as_percentage()}")
    """

    def __init__(self):
        """MetricsCalculator'ı başlatır."""
        self.metrics: List[MetricResult] = []
        self.verification_report: Optional[VerificationReport] = None
        self.code_entities: Set[str] = set()

    def calculate(self, verification_report: VerificationReport,
                  code_entities: Optional[Set[str]] = None) -> MetricsReport:
        """
        Tüm metrikleri hesaplar.

        Args:
            verification_report: Doğrulama raporu
            code_entities: Koddaki tüm varlıklar (coverage için)

        Returns:
            MetricsReport nesnesi
        """
        self.verification_report = verification_report
        self.code_entities = code_entities or set()
        self.metrics = []

        # Metrikleri hesapla
        self._calculate_hallucination_rate()
        self._calculate_validity_rate()
        self._calculate_coverage()
        self._calculate_step_validity()
        self._calculate_claim_type_breakdown()
        self._calculate_confidence_distribution()
        self._calculate_chain_coherence()

        # Özet ve öneriler oluştur
        summary = self._create_summary()
        recommendations = self._generate_recommendations()

        return MetricsReport(
            metrics=self.metrics,
            summary=summary,
            recommendations=recommendations
        )

    def _calculate_hallucination_rate(self):
        """
        Halüsinasyon oranını hesaplar.

        Halüsinasyon oranı, LLM'nin ne kadar sıklıkla yanlış
        veya desteklenmeyen iddialar ürettiğini gösterir.

        Düşük oran (< 0.1): İyi, LLM güvenilir
        Orta oran (0.1-0.3): Dikkatli olunmalı
        Yüksek oran (> 0.3): Sorunlu, LLM çıktıları güvenilmez
        """
        details = self.verification_report.summary
        total = details.get("total_claims", 0)
        hallucinations = details.get("hallucination_count", 0)

        rate = hallucinations / total if total > 0 else 0

        self.metrics.append(MetricResult(
            name="hallucination_rate",
            value=rate,
            description="Halüsinasyon (yanlış iddia) oranı. "
                       "Düşük değer daha iyi (< 0.1 ideal).",
            details={
                "total_claims": total,
                "hallucination_count": hallucinations,
                "threshold_good": 0.1,
                "threshold_bad": 0.3
            }
        ))

    def _calculate_validity_rate(self):
        """
        Geçerlilik oranını hesaplar.

        Geçerlilik oranı, LLM'nin doğru iddiaların toplam
        iddialara oranıdır.

        Yüksek oran (> 0.8): İyi
        Orta oran (0.5-0.8): Kabul edilebilir
        Düşük oran (< 0.5): Sorunlu
        """
        details = self.verification_report.summary
        total = details.get("total_claims", 0)
        valid = details.get("valid_count", 0)
        partially_valid = details.get("partially_valid_count", 0)

        rate = (valid + partially_valid) / total if total > 0 else 0

        self.metrics.append(MetricResult(
            name="validity_rate",
            value=rate,
            description="Geçerli iddiaların oranı. "
                       "Yüksek değer daha iyi (> 0.8 ideal).",
            details={
                "total_claims": total,
                "valid_count": valid,
                "partially_valid_count": partially_valid,
                "threshold_good": 0.8,
                "threshold_bad": 0.5
            }
        ))

    def _calculate_coverage(self):
        """
        Kapsam metriğini hesaplar.

        Kapsam, LLM'nin bahsettiği kod varlıklarının gerçek
        kod varlıklarına oranıdır.

        Yüksek kapsam: LLM kodun büyük bölümünü analiz etti
        Düşük kapsam: LLM kodun sadece bir kısmından bahsetti
        """
        if not self.code_entities:
            self.metrics.append(MetricResult(
                name="coverage",
                value=0,
                description="Kod kapsamı hesaplanamadı (kod varlıkları sağlanmadı).",
                details={"error": "no_code_entities"}
            ))
            return

        # LLM'nin bahsettiği varlıkları topla
        mentioned_entities = set()
        for detail in self.verification_report.details:
            if detail.subject_match and detail.subject_match.code_entity:
                mentioned_entities.add(detail.subject_match.code_entity)
            if detail.object_match and detail.object_match.code_entity:
                mentioned_entities.add(detail.object_match.code_entity)

        total_entities = len(self.code_entities)
        mentioned_count = len(mentioned_entities & self.code_entities)

        coverage = mentioned_count / total_entities if total_entities > 0 else 0

        self.metrics.append(MetricResult(
            name="coverage",
            value=coverage,
            description="LLM'nin analiz ettiği kod yapılarının oranı.",
            details={
                "total_code_entities": total_entities,
                "mentioned_entities": mentioned_count,
                "mentioned_list": list(mentioned_entities & self.code_entities)
            }
        ))

    def _calculate_step_validity(self):
        """
        Her reasoning adımının geçerlilik durumunu hesaplar.

        Bu metrik, hangi adımlarda hata yapıldığını gösterir.
        """
        # Adımlara göre grupla
        steps: Dict[int, List[VerificationDetail]] = defaultdict(list)
        for detail in self.verification_report.details:
            step = detail.claim.source_step
            steps[step].append(detail)

        # Her adım için geçerlilik hesapla
        step_validity = {}
        for step_num, details in sorted(steps.items()):
            valid_count = sum(1 for d in details if d.is_valid())
            total_count = len(details)
            validity = valid_count / total_count if total_count > 0 else 0
            step_validity[step_num] = {
                "validity_rate": validity,
                "valid_count": valid_count,
                "total_count": total_count
            }

        # Ortalama adım geçerliliği
        avg_validity = sum(s["validity_rate"] for s in step_validity.values()) / len(step_validity) if step_validity else 0

        self.metrics.append(MetricResult(
            name="step_validity",
            value=avg_validity,
            description="Reasoning adımlarının ortalama geçerlilik oranı.",
            details={
                "per_step": step_validity,
                "total_steps": len(step_validity)
            }
        ))

    def _calculate_claim_type_breakdown(self):
        """
        Claim türlerine göre başarı oranlarını hesaplar.

        Her claim türü (CALL, DATA_FLOW, EXISTENCE vb.) için
        ayrı ayrı başarı oranları gösterilir.
        """
        # Türlere göre grupla
        by_type: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            "total": 0, "valid": 0, "hallucination": 0, "other": 0
        })

        for detail in self.verification_report.details:
            claim_type = detail.claim.claim_type.value
            by_type[claim_type]["total"] += 1

            if detail.is_valid():
                by_type[claim_type]["valid"] += 1
            elif detail.is_hallucination():
                by_type[claim_type]["hallucination"] += 1
            else:
                by_type[claim_type]["other"] += 1

        # Her tür için oran hesapla
        type_breakdown = {}
        for claim_type, counts in by_type.items():
            total = counts["total"]
            type_breakdown[claim_type] = {
                "total": total,
                "validity_rate": counts["valid"] / total if total > 0 else 0,
                "hallucination_rate": counts["hallucination"] / total if total > 0 else 0
            }

        self.metrics.append(MetricResult(
            name="claim_type_breakdown",
            value=len(type_breakdown),  # Tür sayısı
            description="Claim türlerine göre başarı oranları.",
            details=type_breakdown
        ))

    def _calculate_confidence_distribution(self):
        """
        Güven skoru dağılımını hesaplar.

        Doğrulama sonuçlarının güven skorlarının dağılımını gösterir.
        """
        confidences = [d.confidence for d in self.verification_report.details]

        if not confidences:
            self.metrics.append(MetricResult(
                name="confidence_distribution",
                value=0,
                description="Güven skoru dağılımı hesaplanamadı.",
                details={"error": "no_data"}
            ))
            return

        # İstatistikler
        avg_confidence = sum(confidences) / len(confidences)
        min_confidence = min(confidences)
        max_confidence = max(confidences)

        # Dağılım grupları
        distribution = {
            "low (0-0.3)": sum(1 for c in confidences if c < 0.3),
            "medium (0.3-0.7)": sum(1 for c in confidences if 0.3 <= c < 0.7),
            "high (0.7-1.0)": sum(1 for c in confidences if c >= 0.7)
        }

        self.metrics.append(MetricResult(
            name="confidence_distribution",
            value=avg_confidence,
            description="Doğrulama sonuçlarının ortalama güven skoru.",
            details={
                "average": avg_confidence,
                "min": min_confidence,
                "max": max_confidence,
                "distribution": distribution,
                "total_claims": len(confidences)
            }
        ))

    def _calculate_chain_coherence(self):
        """
        Zincir tutarlılığını hesaplar.

        Ardışık reasoning adımları arasındaki tutarlılığı ölçer.
        Eğer bir adımda halüsinasyon varsa ve sonraki adım ona
        dayalıysa, tutarlılık düşer.
        """
        details = self.verification_report.details
        if len(details) < 2:
            self.metrics.append(MetricResult(
                name="chain_coherence",
                value=1.0,
                description="Zincir tutarlılığı (yeterli veri yok).",
                details={"insufficient_data": True}
            ))
            return

        # Adımlara göre sırala
        sorted_details = sorted(details, key=lambda d: d.claim.source_step)

        # Ardışık adımlar arasında tutarlılık kontrolü
        coherent_transitions = 0
        total_transitions = 0

        for i in range(len(sorted_details) - 1):
            current = sorted_details[i]
            next_detail = sorted_details[i + 1]

            total_transitions += 1

            # Her ikisi de valid veya her ikisi de invalid ise tutarlı
            if current.is_valid() == next_detail.is_valid():
                coherent_transitions += 1
            # Önceki halüsinasyon, sonraki de halüsinasyon ise (hata yayılımı)
            elif current.is_hallucination() and next_detail.is_hallucination():
                coherent_transitions += 0.5  # Kısmen tutarlı (kötü şekilde)

        coherence = coherent_transitions / total_transitions if total_transitions > 0 else 1.0

        self.metrics.append(MetricResult(
            name="chain_coherence",
            value=coherence,
            description="Ardışık reasoning adımları arasındaki tutarlılık.",
            details={
                "total_transitions": total_transitions,
                "coherent_transitions": coherent_transitions
            }
        ))

    def _create_summary(self) -> Dict[str, Any]:
        """
        Özet bilgileri oluşturur.

        Returns:
            Özet sözlüğü
        """
        hallucination_rate = self._get_metric_value("hallucination_rate")
        validity_rate = self._get_metric_value("validity_rate")

        # Genel değerlendirme
        if hallucination_rate < 0.1 and validity_rate > 0.8:
            overall_assessment = "MÜKEMMEL"
            assessment_color = "green"
        elif hallucination_rate < 0.2 and validity_rate > 0.6:
            overall_assessment = "İYİ"
            assessment_color = "yellow"
        elif hallucination_rate < 0.3:
            overall_assessment = "ORTA"
            assessment_color = "orange"
        else:
            overall_assessment = "ZAYIF"
            assessment_color = "red"

        return {
            "overall_assessment": overall_assessment,
            "assessment_color": assessment_color,
            "hallucination_rate": hallucination_rate,
            "validity_rate": validity_rate,
            "total_claims": self.verification_report.summary.get("total_claims", 0),
            "hallucination_count": self.verification_report.summary.get("hallucination_count", 0)
        }

    def _generate_recommendations(self) -> List[str]:
        """
        İyileştirme önerileri oluşturur.

        Metriklere göre spesifik öneriler sunar.

        Returns:
            Öneri listesi
        """
        recommendations = []

        hallucination_rate = self._get_metric_value("hallucination_rate")
        validity_rate = self._get_metric_value("validity_rate")
        coverage = self._get_metric_value("coverage")

        # Halüsinasyon oranına göre öneriler
        if hallucination_rate > 0.3:
            recommendations.append(
                "⚠️  Yüksek halüsinasyon oranı! LLM çıktılarına güvenmeyin. "
                "Daha spesifik promptlar kullanmayı deneyin."
            )
        elif hallucination_rate > 0.1:
            recommendations.append(
                "📝 Orta düzeyde halüsinasyon oranı. "
                "Kritik kararlar için LLM çıktılarını manuel doğrulayın."
            )

        # Geçerlilik oranına göre öneriler
        if validity_rate < 0.5:
            recommendations.append(
                "❌ Düşük geçerlilik oranı. LLM'nin kod anlayışı yetersiz. "
                "Daha basit kod yapıları veya daha güçlü model deneyin."
            )

        # Kapsama göre öneriler
        if coverage < 0.5:
            recommendations.append(
                "📊 Düşük kapsam. LLM kodun sadece bir kısmını analiz etti. "
                "Tüm yapıları sorgulamak için ek promptlar kullanın."
            )

        # Claim türü başarı oranlarına göre öneriler
        type_metric = self._get_metric("claim_type_breakdown")
        if type_metric and type_metric.details:
            for claim_type, stats in type_metric.details.items():
                if isinstance(stats, dict) and stats.get("hallucination_rate", 0) > 0.4:
                    recommendations.append(
                        f"🔍 '{claim_type}' türündeki iddialar için yüksek hata oranı. "
                        f"Bu tür iddiaları özellikle doğrulayın."
                    )

        # Hiç öneri yoksa pozitif mesaj
        if not recommendations:
            recommendations.append(
                "✅ LLM çıktıları genel olarak güvenilir görünüyor. "
                "Yine de kritik kararlar için manuel doğrulama önerilir."
            )

        return recommendations

    def _get_metric_value(self, name: str) -> float:
        """İsme göre metrik değeri döndürür."""
        for metric in self.metrics:
            if metric.name == name:
                return metric.value
        return 0.0

    def _get_metric(self, name: str) -> Optional[MetricResult]:
        """İsme göre metrik döndürür."""
        for metric in self.metrics:
            if metric.name == name:
                return metric
        return None

    def print_report(self, metrics_report: MetricsReport):
        """
        Metrik raporunu konsola yazdırır.

        Args:
            metrics_report: MetricsReport nesnesi
        """
        print("=" * 70)
        print("METRİK RAPORU")
        print("=" * 70)

        # Genel değerlendirme
        summary = metrics_report.summary
        print(f"\n🎯 GENEL DEĞERLENDİRME: {summary['overall_assessment']}")

        # Ana metrikler
        print("\n📊 ANA METRİKLER:")
        print("-" * 50)

        for metric in metrics_report.metrics:
            if metric.name in ["hallucination_rate", "validity_rate", "coverage",
                              "step_validity", "chain_coherence", "confidence_distribution"]:
                print(f"\n   {metric.name}:")
                print(f"      Değer: {metric.as_percentage()}")
                print(f"      Açıklama: {metric.description}")

        # Claim türü analizi
        type_metric = metrics_report.get_metric("claim_type_breakdown")
        if type_metric and isinstance(type_metric.details, dict):
            print("\n📈 CLAIM TÜRÜ ANALİZİ:")
            print("-" * 50)
            for claim_type, stats in type_metric.details.items():
                if isinstance(stats, dict):
                    print(f"\n   {claim_type}:")
                    print(f"      Toplam: {stats.get('total', 0)}")
                    print(f"      Geçerlilik: {stats.get('validity_rate', 0)*100:.1f}%")
                    print(f"      Halüsinasyon: {stats.get('hallucination_rate', 0)*100:.1f}%")

        # Öneriler
        print("\n💡 ÖNERİLER:")
        print("-" * 50)
        for rec in metrics_report.recommendations:
            print(f"   {rec}")

        print("\n" + "=" * 70)


# =============================================================================
# TEST KODU
# =============================================================================
if __name__ == "__main__":
    from .verifier import VerificationReport, VerificationDetail, VerificationResult
    from .claim_extractor import Claim, ClaimType
    from .entity_mapper import EntityMatch, MatchType

    # Test verisi oluştur
    test_details = [
        VerificationDetail(
            claim=Claim("main calls process", ClaimType.CALL, "main", "process", "calls", source_step=1),
            result=VerificationResult.VALID,
            confidence=0.95,
            reason="Doğrulandı"
        ),
        VerificationDetail(
            claim=Claim("calc add", ClaimType.CALL, "calc", "add", "calls", source_step=1),
            result=VerificationResult.VALID,
            confidence=0.85,
            reason="Doğrulandı"
        ),
        VerificationDetail(
            claim=Claim("main save_result", ClaimType.CALL, "main", "save_result", "calls", source_step=2),
            result=VerificationResult.HALLUCINATION,
            confidence=0.9,
            reason="save_result yok"
        ),
        VerificationDetail(
            claim=Claim("DataProcessor exists", ClaimType.EXISTENCE, "DataProcessor", None, "exists", source_step=3),
            result=VerificationResult.HALLUCINATION,
            confidence=0.85,
            reason="Sınıf yok"
        ),
        VerificationDetail(
            claim=Claim("Calculator exists", ClaimType.EXISTENCE, "Calculator", None, "exists", source_step=3),
            result=VerificationResult.VALID,
            confidence=1.0,
            reason="Mevcut"
        ),
    ]

    test_report = VerificationReport(
        details=test_details,
        summary={
            "total_claims": 5,
            "valid_count": 3,
            "hallucination_count": 2,
            "unverifiable_count": 0,
            "partially_valid_count": 0
        },
        hallucinations=[d for d in test_details if d.is_hallucination()]
    )

    # Metrikleri hesapla
    calculator = MetricsCalculator()
    code_entities = {"main", "process_data", "Calculator", "add", "_validate"}
    metrics_report = calculator.calculate(test_report, code_entities)

    # Raporu yazdır
    calculator.print_report(metrics_report)
