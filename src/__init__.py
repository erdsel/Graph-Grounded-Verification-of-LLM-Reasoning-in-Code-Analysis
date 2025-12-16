# =============================================================================
# Graph-Grounded LLM Verification System
# Ana Paket Başlatma Dosyası
# =============================================================================
#
# Bu proje, Büyük Dil Modellerinin (LLM) kod analizi hakkındaki
# muhakemelerini doğrulamak için graf tabanlı bir sistem sunar.
#
# Modüller:
# - ast_parser: Python kodunu AST'ye dönüştürür
# - graph_builder: AST'den Call Graph ve Data Flow Graph oluşturur
# - llm_client: LLM API ile iletişim kurar
# - claim_extractor: LLM çıktısından iddiaları çıkarır
# - entity_mapper: Metin varlıklarını graf düğümlerine eşler
# - verifier: Graf traversal ile iddiaları doğrular
# - metrics: Performans metriklerini hesaplar
# - reporter: HTML rapor oluşturur
# =============================================================================

from .ast_parser import ASTParser
from .graph_builder import GraphBuilder
from .llm_client import LLMClient
from .claim_extractor import ClaimExtractor
from .entity_mapper import EntityMapper
from .verifier import Verifier
from .metrics import MetricsCalculator
from .reporter import HTMLReporter

__version__ = "1.0.0"
__author__ = "Selen Erdoğan"

# Tüm modülleri dışa aktar
__all__ = [
    "ASTParser",
    "GraphBuilder",
    "LLMClient",
    "ClaimExtractor",
    "EntityMapper",
    "Verifier",
    "MetricsCalculator",
    "HTMLReporter"
]
