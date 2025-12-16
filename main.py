#!/usr/bin/env python3
# =============================================================================
# GRAPH-GROUNDED LLM VERIFICATION SYSTEM
# Ana Uygulama Dosyası
# =============================================================================
# Bu dosya, tüm modülleri bir araya getirerek LLM doğrulama pipeline'ını
# çalıştırır.
#
# Kullanım:
#   python main.py --code example.py --output report.html
#   python main.py --code example.py --no-llm  # LLM olmadan test
#
# Pipeline Akışı:
# 1. Python kodunu oku ve AST'ye dönüştür
# 2. Kod graflarını oluştur (Call Graph, Data Flow Graph)
# 3. LLM'den kod analizi al (veya mock kullan)
# 4. LLM çıktısından claim'leri çıkar
# 5. Claim'leri graf üzerinde doğrula
# 6. Metrikleri hesapla
# 7. HTML rapor oluştur
# =============================================================================

import argparse
import sys
import os
from pathlib import Path

# Modül yolunu ekle
sys.path.insert(0, str(Path(__file__).parent))

from src.ast_parser import ASTParser
from src.graph_builder import GraphBuilder
from src.llm_client import LLMClient
from src.claim_extractor import ClaimExtractor
from src.entity_mapper import EntityMapper
from src.verifier import Verifier
from src.metrics import MetricsCalculator
from src.reporter import HTMLReporter


def print_banner():
    """Program başlık banner'ını yazdırır."""
    banner = """
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   ██╗     ██╗     ███╗   ███╗    ██╗   ██╗███████╗██████╗ ██╗███████╗   ║
║   ██║     ██║     ████╗ ████║    ██║   ██║██╔════╝██╔══██╗██║██╔════╝   ║
║   ██║     ██║     ██╔████╔██║    ██║   ██║█████╗  ██████╔╝██║█████╗     ║
║   ██║     ██║     ██║╚██╔╝██║    ╚██╗ ██╔╝██╔══╝  ██╔══██╗██║██╔══╝     ║
║   ███████╗███████╗██║ ╚═╝ ██║     ╚████╔╝ ███████╗██║  ██║██║██║        ║
║   ╚══════╝╚══════╝╚═╝     ╚═╝      ╚═══╝  ╚══════╝╚═╝  ╚═╝╚═╝╚═╝        ║
║                                                                           ║
║        Graph-Grounded Verification of LLM Reasoning in Code Analysis     ║
║                                                                           ║
║                         Selen Erdoğan - GTU                               ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def run_pipeline(code_path: str, output_path: str, use_llm: bool = True,
                 api_key: str = None, provider: str = "auto", verbose: bool = True):
    """
    Ana doğrulama pipeline'ını çalıştırır.

    Args:
        code_path: Analiz edilecek Python dosyasının yolu
        output_path: HTML rapor çıktı yolu
        use_llm: Gerçek LLM kullanılsın mı? (False ise mock)
        api_key: OpenAI API anahtarı (opsiyonel)
        verbose: Detaylı çıktı gösterilsin mi?

    Returns:
        VerificationReport nesnesi
    """
    if verbose:
        print_banner()

    # =========================================================================
    # ADIM 1: Kodu Oku ve Parse Et
    # =========================================================================
    if verbose:
        print("\n" + "=" * 70)
        print("ADIM 1: KOD ANALİZİ")
        print("=" * 70)

    # Dosyayı oku
    if verbose:
        print(f"\n📂 Dosya okunuyor: {code_path}")

    with open(code_path, 'r', encoding='utf-8') as f:
        source_code = f.read()

    # AST Parser ile analiz et
    parser = ASTParser()
    ast_result = parser.parse_code(source_code)

    if verbose:
        parser.print_summary()

    # =========================================================================
    # ADIM 2: Graf Oluştur
    # =========================================================================
    if verbose:
        print("\n" + "=" * 70)
        print("ADIM 2: GRAF OLUŞTURMA")
        print("=" * 70)

    graph_builder = GraphBuilder()
    graph_builder.build_from_ast_result(ast_result)

    if verbose:
        graph_builder.print_summary()

    # =========================================================================
    # ADIM 3: Entity Mapper Hazırla
    # =========================================================================
    if verbose:
        print("\n" + "=" * 70)
        print("ADIM 3: ENTITY MAPPER")
        print("=" * 70)

    entity_mapper = EntityMapper()
    entity_mapper.load_code_entities(ast_result)

    if verbose:
        print(f"\n📊 Yüklenen varlıklar:")
        for category, entities in entity_mapper.get_all_code_entities().items():
            if category != "all" and entities:
                print(f"   {category}: {entities}")

    # =========================================================================
    # ADIM 4: LLM'den Analiz Al
    # =========================================================================
    if verbose:
        print("\n" + "=" * 70)
        print("ADIM 4: LLM ANALİZİ")
        print("=" * 70)

    # LLM client oluştur
    if use_llm:
        llm_client = LLMClient.create(provider=provider, api_key=api_key)
    else:
        llm_client = LLMClient.create(provider="mock")

    if verbose:
        print(f"\n🤖 Kullanılan LLM: {type(llm_client).__name__}")

    # LLM'den analiz al
    if verbose:
        print("📝 Kod analizi yapılıyor...")

    llm_response = llm_client.generate_reasoning(source_code, prompt_type="analysis")

    if verbose:
        print(f"\n📊 Token kullanımı: {llm_response.usage}")
        print(f"📄 Reasoning adım sayısı: {len(llm_response.reasoning_steps)}")

    # =========================================================================
    # ADIM 5: Claim Extraction
    # =========================================================================
    if verbose:
        print("\n" + "=" * 70)
        print("ADIM 5: CLAIM ÇIKARMA")
        print("=" * 70)

    claim_extractor = ClaimExtractor()
    claims = claim_extractor.extract_claims(
        llm_response.content,
        llm_response.reasoning_steps
    )

    if verbose:
        claim_extractor.print_summary()

    # =========================================================================
    # ADIM 6: Doğrulama
    # =========================================================================
    if verbose:
        print("\n" + "=" * 70)
        print("ADIM 6: DOĞRULAMA")
        print("=" * 70)

    verifier = Verifier(graph_builder, entity_mapper)
    verification_report = verifier.verify_claims(claims)

    if verbose:
        verifier.print_report()

    # =========================================================================
    # ADIM 7: Metrik Hesaplama
    # =========================================================================
    if verbose:
        print("\n" + "=" * 70)
        print("ADIM 7: METRİK HESAPLAMA")
        print("=" * 70)

    metrics_calculator = MetricsCalculator()
    code_entities = set(entity_mapper.get_all_code_entities()["all"])
    metrics_report = metrics_calculator.calculate(verification_report, code_entities)

    if verbose:
        metrics_calculator.print_report(metrics_report)

    # =========================================================================
    # ADIM 8: Rapor Oluşturma
    # =========================================================================
    if verbose:
        print("\n" + "=" * 70)
        print("ADIM 8: RAPOR OLUŞTURMA")
        print("=" * 70)

    reporter = HTMLReporter()
    reporter.generate_and_save(
        verification_report,
        metrics_report,
        output_path,
        code_info={
            "filename": os.path.basename(code_path),
            "filepath": code_path,
            "lines": len(source_code.split('\n'))
        }
    )

    # =========================================================================
    # SONUÇ
    # =========================================================================
    if verbose:
        print("\n" + "=" * 70)
        print("TAMAMLANDI")
        print("=" * 70)
        print(f"\n✅ Analiz tamamlandı!")
        print(f"📊 Toplam claim: {len(claims)}")
        print(f"❌ Halüsinasyon: {len(verification_report.hallucinations)}")
        print(f"📄 Rapor: {output_path}")
        print("\n" + "=" * 70)

    return verification_report


def run_demo():
    """
    Demo modunu çalıştırır.

    Örnek bir kod üzerinde tüm pipeline'ı gösterir.
    """
    print_banner()
    print("\n🎯 DEMO MODU")
    print("=" * 70)

    # Örnek kod
    demo_code = '''
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
'''

    # Geçici dosya oluştur
    demo_file = Path(__file__).parent / "tests" / "sample_codes" / "demo_code.py"
    demo_file.parent.mkdir(parents=True, exist_ok=True)

    with open(demo_file, 'w', encoding='utf-8') as f:
        f.write(demo_code)

    print(f"📝 Demo kod oluşturuldu: {demo_file}")

    # Output dosyası
    output_file = Path(__file__).parent / "output" / "demo_report.html"

    # Pipeline'ı çalıştır
    run_pipeline(
        code_path=str(demo_file),
        output_path=str(output_file),
        use_llm=False,  # Mock kullan
        verbose=True
    )


def main():
    """
    Komut satırı arayüzü.
    """
    arg_parser = argparse.ArgumentParser(
        description="Graph-Grounded LLM Verification System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python main.py --demo                    # Demo modunu çalıştır
  python main.py --code example.py         # Kodu analiz et
  python main.py --code example.py --no-llm  # LLM olmadan (mock) test
  python main.py --code example.py --output report.html --api-key sk-...
        """
    )

    arg_parser.add_argument(
        "--demo",
        action="store_true",
        help="Demo modunu çalıştır (örnek kod ile)"
    )

    arg_parser.add_argument(
        "--code", "-c",
        type=str,
        help="Analiz edilecek Python dosyası"
    )

    arg_parser.add_argument(
        "--output", "-o",
        type=str,
        default="output/report.html",
        help="HTML rapor çıktı yolu (varsayılan: output/report.html)"
    )

    arg_parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Gerçek LLM yerine mock kullan"
    )

    arg_parser.add_argument(
        "--api-key",
        type=str,
        help="API anahtarı (Gemini veya OpenAI)"
    )

    arg_parser.add_argument(
        "--provider",
        type=str,
        choices=["groq", "gemini", "openai", "mock", "auto"],
        default="auto",
        help="LLM sağlayıcı (varsayılan: auto). Groq önerilir - ücretsiz ve hızlı!"
    )

    arg_parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Sessiz mod (sadece sonuç göster)"
    )

    args = arg_parser.parse_args()

    # Demo modu
    if args.demo:
        run_demo()
        return

    # Kod dosyası belirtilmeli
    if not args.code:
        arg_parser.print_help()
        print("\n❌ Hata: --code veya --demo parametresi gerekli!")
        sys.exit(1)

    # Dosya var mı kontrol et
    if not os.path.exists(args.code):
        print(f"❌ Hata: Dosya bulunamadı: {args.code}")
        sys.exit(1)

    # Pipeline'ı çalıştır
    run_pipeline(
        code_path=args.code,
        output_path=args.output,
        use_llm=not args.no_llm,
        api_key=args.api_key,
        provider=args.provider,
        verbose=not args.quiet
    )


if __name__ == "__main__":
    main()
