# =============================================================================
# ENTITY MAPPER MODÜLÜ
# =============================================================================
# Bu modül, LLM çıktısındaki metin varlıklarını (entity) kaynak koddaki
# gerçek kod varlıklarına eşler.
#
# Problem:
# --------
# LLM, kod hakkında konuşurken farklı ifadeler kullanabilir:
# - "calculate_total fonksiyonu" → calculate_total
# - "toplam hesaplayan fonksiyon" → calculate_total (semantik eşleşme)
# - "calc_total" → calculate_total (fuzzy eşleşme)
#
# Eşleştirme Stratejileri:
# -----------------------
# 1. EXACT MATCH (Tam Eşleşme):
#    Metin varlığı ile kod varlığı birebir aynı
#
# 2. FUZZY MATCH (Bulanık Eşleşme):
#    Levenshtein mesafesi veya benzer algoritmalarla yakın eşleşmeler
#    Örnek: "calc_totl" → "calc_total" (typo tolerance)
#
# 3. SEMANTIC MATCH (Anlamsal Eşleşme):
#    Anlam benzerliği üzerinden eşleşme (opsiyonel, NLP gerektirir)
#
# 4. ALIAS MATCH (Takma Ad Eşleşmesi):
#    Bilinen takma adlar üzerinden eşleşme
#    Örnek: "init" → "__init__"
# =============================================================================

from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum

# FuzzyWuzzy opsiyonel - kurulu değilse basit algoritma kullanılır
try:
    from fuzzywuzzy import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    print("⚠️  FuzzyWuzzy bulunamadı. Basit eşleşme kullanılacak.")


class MatchType(Enum):
    """
    Eşleşme türlerini tanımlayan enum.

    EXACT: Birebir aynı isim
    FUZZY: Benzer isim (typo, kısaltma vb.)
    ALIAS: Bilinen takma ad
    PARTIAL: Kısmi eşleşme (içerme)
    NO_MATCH: Eşleşme bulunamadı
    """
    EXACT = "exact"
    FUZZY = "fuzzy"
    ALIAS = "alias"
    PARTIAL = "partial"
    NO_MATCH = "no_match"


@dataclass
class EntityMatch:
    """
    Bir varlık eşleşmesini temsil eden veri sınıfı.

    Attributes:
        text_entity: LLM metnindeki varlık adı
        code_entity: Koddaki gerçek varlık adı
        match_type: Eşleşme türü
        confidence: Eşleşme güven skoru (0-1)
        entity_type: Varlık tipi (function, class, variable)
    """
    text_entity: str
    code_entity: Optional[str]
    match_type: MatchType
    confidence: float
    entity_type: Optional[str] = None

    def is_matched(self) -> bool:
        """Eşleşme başarılı mı?"""
        return self.match_type != MatchType.NO_MATCH

    def to_dict(self) -> Dict[str, Any]:
        """Sözlük formatına dönüştürür."""
        return {
            "text_entity": self.text_entity,
            "code_entity": self.code_entity,
            "match_type": self.match_type.value,
            "confidence": self.confidence,
            "entity_type": self.entity_type
        }


class EntityMapper:
    """
    Metin varlıklarını kod varlıklarına eşleyen sınıf.

    Bu sınıf, LLM'nin bahsettiği isimleri gerçek kod yapılarıyla
    eşleştirir. Farklı eşleştirme stratejileri kullanır.

    Kullanım:
        mapper = EntityMapper()
        mapper.load_code_entities(ast_result)

        match = mapper.map_entity("calc_total")
        print(f"Eşleşme: {match.code_entity} ({match.match_type})")
    """

    # Yaygın takma adlar (alias) sözlüğü
    # Anahtar: Takma ad, Değer: Olası gerçek isimler listesi
    COMMON_ALIASES = {
        "init": ["__init__"],
        "constructor": ["__init__"],
        "yapıcı": ["__init__"],
        "str": ["__str__"],
        "repr": ["__repr__"],
        "main": ["main", "__main__"],
        "ana": ["main"],
        "self": ["self"],
    }

    # Minimum fuzzy eşleşme skoru (0-100)
    FUZZY_THRESHOLD = 75

    # Minimum partial eşleşme oranı
    PARTIAL_THRESHOLD = 0.6

    def __init__(self, fuzzy_threshold: int = 75):
        """
        EntityMapper'ı başlatır.

        Args:
            fuzzy_threshold: Fuzzy eşleşme için minimum skor (0-100)
        """
        self.fuzzy_threshold = fuzzy_threshold

        # Kod varlıklarını kategorize eden sözlük
        self.code_entities: Dict[str, Set[str]] = {
            "functions": set(),
            "classes": set(),
            "methods": set(),
            "variables": set(),
            "imports": set(),
            "all": set()  # Tüm varlıkların birleşimi
        }

        # Varlık -> tip eşlemesi (hızlı lookup için)
        self.entity_types: Dict[str, str] = {}

        # Eşleştirme önbelleği (cache)
        self._cache: Dict[str, EntityMatch] = {}

        # İstatistikler
        self.stats = {
            "total_mappings": 0,
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "alias_matches": 0,
            "partial_matches": 0,
            "no_matches": 0
        }

    def load_code_entities(self, ast_result: Dict[str, Any]):
        """
        AST analiz sonuçlarından kod varlıklarını yükler.

        Args:
            ast_result: ASTParser.parse_code() çıktısı
        """
        # Önbelleği temizle
        self._cache = {}

        # Fonksiyonları yükle
        for func_name in ast_result.get("functions", {}).keys():
            self.code_entities["functions"].add(func_name)
            self.code_entities["all"].add(func_name)
            self.entity_types[func_name] = "function"

        # Sınıfları yükle
        for class_name, class_data in ast_result.get("classes", {}).items():
            self.code_entities["classes"].add(class_name)
            self.code_entities["all"].add(class_name)
            self.entity_types[class_name] = "class"

            # Sınıf metodlarını yükle
            for method_name in class_data.get("methods", []):
                self.code_entities["methods"].add(method_name)
                self.code_entities["all"].add(method_name)
                self.entity_types[method_name] = "method"

        # Değişkenleri yükle
        for var_name in ast_result.get("variables", {}).keys():
            self.code_entities["variables"].add(var_name)
            self.code_entities["all"].add(var_name)
            self.entity_types[var_name] = "variable"

        # Import'ları yükle
        for imp_data in ast_result.get("imports", []):
            module = imp_data.get("module", "")
            if module:
                self.code_entities["imports"].add(module)
                self.code_entities["all"].add(module)
                self.entity_types[module] = "import"

            for name in imp_data.get("names", []):
                self.code_entities["imports"].add(name)
                self.code_entities["all"].add(name)
                self.entity_types[name] = "import"

    def load_from_graph_builder(self, graph_builder):
        """
        GraphBuilder'dan kod varlıklarını yükler.

        Args:
            graph_builder: GraphBuilder nesnesi
        """
        # Tüm düğümleri al
        for node_name in graph_builder.get_all_nodes("combined"):
            node_type = graph_builder.get_node_type(node_name)

            if node_type:
                # Tipe göre kategorize et
                if node_type == "function":
                    self.code_entities["functions"].add(node_name)
                elif node_type == "class":
                    self.code_entities["classes"].add(node_name)
                elif node_type == "method":
                    self.code_entities["methods"].add(node_name)
                elif node_type in ("variable", "local_variable"):
                    self.code_entities["variables"].add(node_name)

                self.code_entities["all"].add(node_name)
                self.entity_types[node_name] = node_type

    def map_entity(self, text_entity: str, expected_type: Optional[str] = None) -> EntityMatch:
        """
        Bir metin varlığını kod varlığına eşler.

        Eşleştirme sırası:
        1. Önbellek kontrolü
        2. Exact match (tam eşleşme)
        3. Alias match (takma ad)
        4. Fuzzy match (bulanık eşleşme)
        5. Partial match (kısmi eşleşme)

        Args:
            text_entity: LLM metnindeki varlık adı
            expected_type: Beklenen varlık tipi (opsiyonel filtre)

        Returns:
            EntityMatch nesnesi
        """
        # Normalize et (küçük harf, boşluk temizleme)
        normalized = text_entity.lower().strip()

        # Önbellekte var mı?
        cache_key = f"{normalized}:{expected_type or 'any'}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Hedef varlık kümesini belirle
        if expected_type:
            target_entities = self._get_entities_by_type(expected_type)
        else:
            target_entities = self.code_entities["all"]

        # 1. Exact Match (Tam Eşleşme)
        match = self._try_exact_match(normalized, target_entities)
        if match.is_matched():
            self._cache[cache_key] = match
            self._update_stats(match)
            return match

        # 2. Alias Match (Takma Ad Eşleşmesi)
        match = self._try_alias_match(normalized, target_entities)
        if match.is_matched():
            self._cache[cache_key] = match
            self._update_stats(match)
            return match

        # 3. Fuzzy Match (Bulanık Eşleşme)
        match = self._try_fuzzy_match(normalized, target_entities)
        if match.is_matched():
            self._cache[cache_key] = match
            self._update_stats(match)
            return match

        # 4. Partial Match (Kısmi Eşleşme)
        match = self._try_partial_match(normalized, target_entities)
        if match.is_matched():
            self._cache[cache_key] = match
            self._update_stats(match)
            return match

        # Eşleşme bulunamadı
        no_match = EntityMatch(
            text_entity=text_entity,
            code_entity=None,
            match_type=MatchType.NO_MATCH,
            confidence=0.0
        )
        self._cache[cache_key] = no_match
        self._update_stats(no_match)
        return no_match

    def _get_entities_by_type(self, entity_type: str) -> Set[str]:
        """Tipe göre varlık kümesi döndürür."""
        type_mapping = {
            "function": "functions",
            "class": "classes",
            "method": "methods",
            "variable": "variables",
            "import": "imports"
        }

        key = type_mapping.get(entity_type, "all")
        return self.code_entities.get(key, self.code_entities["all"])

    def _try_exact_match(self, normalized: str, target_entities: Set[str]) -> EntityMatch:
        """
        Tam eşleşme dener.

        Args:
            normalized: Normalize edilmiş metin varlığı
            target_entities: Aranacak varlık kümesi

        Returns:
            EntityMatch (eşleşme varsa EXACT tipi)
        """
        # Büyük/küçük harf duyarsız karşılaştırma için
        lower_entities = {e.lower(): e for e in target_entities}

        if normalized in lower_entities:
            original_name = lower_entities[normalized]
            return EntityMatch(
                text_entity=normalized,
                code_entity=original_name,
                match_type=MatchType.EXACT,
                confidence=1.0,
                entity_type=self.entity_types.get(original_name)
            )

        return EntityMatch(
            text_entity=normalized,
            code_entity=None,
            match_type=MatchType.NO_MATCH,
            confidence=0.0
        )

    def _try_alias_match(self, normalized: str, target_entities: Set[str]) -> EntityMatch:
        """
        Takma ad eşleşmesi dener.

        Args:
            normalized: Normalize edilmiş metin varlığı
            target_entities: Aranacak varlık kümesi

        Returns:
            EntityMatch (eşleşme varsa ALIAS tipi)
        """
        # Takma ad sözlüğünde ara
        if normalized in self.COMMON_ALIASES:
            possible_names = self.COMMON_ALIASES[normalized]
            for possible_name in possible_names:
                # Hedef varlıklarda var mı?
                lower_entities = {e.lower(): e for e in target_entities}
                if possible_name.lower() in lower_entities:
                    original_name = lower_entities[possible_name.lower()]
                    return EntityMatch(
                        text_entity=normalized,
                        code_entity=original_name,
                        match_type=MatchType.ALIAS,
                        confidence=0.95,
                        entity_type=self.entity_types.get(original_name)
                    )

        return EntityMatch(
            text_entity=normalized,
            code_entity=None,
            match_type=MatchType.NO_MATCH,
            confidence=0.0
        )

    def _try_fuzzy_match(self, normalized: str, target_entities: Set[str]) -> EntityMatch:
        """
        Bulanık eşleşme dener.

        FuzzyWuzzy kütüphanesi mevcutsa Levenshtein mesafesi kullanır,
        yoksa basit bir algoritma kullanır.

        Args:
            normalized: Normalize edilmiş metin varlığı
            target_entities: Aranacak varlık kümesi

        Returns:
            EntityMatch (eşleşme varsa FUZZY tipi)
        """
        best_match = None
        best_score = 0

        for entity in target_entities:
            entity_lower = entity.lower()

            if FUZZY_AVAILABLE:
                # FuzzyWuzzy ile skor hesapla
                score = fuzz.ratio(normalized, entity_lower)
            else:
                # Basit benzerlik hesabı
                score = self._simple_similarity(normalized, entity_lower) * 100

            if score > best_score and score >= self.fuzzy_threshold:
                best_score = score
                best_match = entity

        if best_match:
            return EntityMatch(
                text_entity=normalized,
                code_entity=best_match,
                match_type=MatchType.FUZZY,
                confidence=best_score / 100.0,
                entity_type=self.entity_types.get(best_match)
            )

        return EntityMatch(
            text_entity=normalized,
            code_entity=None,
            match_type=MatchType.NO_MATCH,
            confidence=0.0
        )

    def _try_partial_match(self, normalized: str, target_entities: Set[str]) -> EntityMatch:
        """
        Kısmi eşleşme dener.

        Bir varlık diğerini içeriyor mu kontrol eder.
        Örnek: "calc" → "calculator"

        Args:
            normalized: Normalize edilmiş metin varlığı
            target_entities: Aranacak varlık kümesi

        Returns:
            EntityMatch (eşleşme varsa PARTIAL tipi)
        """
        best_match = None
        best_ratio = 0

        for entity in target_entities:
            entity_lower = entity.lower()

            # İçerme kontrolü
            if normalized in entity_lower or entity_lower in normalized:
                # İçerme oranını hesapla
                ratio = min(len(normalized), len(entity_lower)) / max(len(normalized), len(entity_lower))

                if ratio > best_ratio and ratio >= self.PARTIAL_THRESHOLD:
                    best_ratio = ratio
                    best_match = entity

        if best_match:
            return EntityMatch(
                text_entity=normalized,
                code_entity=best_match,
                match_type=MatchType.PARTIAL,
                confidence=best_ratio,
                entity_type=self.entity_types.get(best_match)
            )

        return EntityMatch(
            text_entity=normalized,
            code_entity=None,
            match_type=MatchType.NO_MATCH,
            confidence=0.0
        )

    def _simple_similarity(self, s1: str, s2: str) -> float:
        """
        İki string arasında basit benzerlik hesaplar.

        Levenshtein mesafesi yerine kullanılan basit algoritma.

        Args:
            s1: İlk string
            s2: İkinci string

        Returns:
            Benzerlik oranı (0-1)
        """
        if s1 == s2:
            return 1.0

        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0.0

        # Ortak karakter sayısı
        common = sum(1 for c in s1 if c in s2)
        max_len = max(len1, len2)

        return common / max_len

    def _update_stats(self, match: EntityMatch):
        """İstatistikleri günceller."""
        self.stats["total_mappings"] += 1

        if match.match_type == MatchType.EXACT:
            self.stats["exact_matches"] += 1
        elif match.match_type == MatchType.FUZZY:
            self.stats["fuzzy_matches"] += 1
        elif match.match_type == MatchType.ALIAS:
            self.stats["alias_matches"] += 1
        elif match.match_type == MatchType.PARTIAL:
            self.stats["partial_matches"] += 1
        else:
            self.stats["no_matches"] += 1

    def map_multiple(self, text_entities: List[str]) -> List[EntityMatch]:
        """
        Birden fazla varlığı eşler.

        Args:
            text_entities: Metin varlıkları listesi

        Returns:
            EntityMatch listesi
        """
        return [self.map_entity(entity) for entity in text_entities]

    def get_all_code_entities(self) -> Dict[str, List[str]]:
        """Tüm kod varlıklarını kategorize ederek döndürür."""
        return {
            category: list(entities)
            for category, entities in self.code_entities.items()
        }

    def entity_exists(self, entity_name: str) -> bool:
        """Bir varlığın kodda var olup olmadığını kontrol eder."""
        match = self.map_entity(entity_name)
        return match.is_matched()

    def get_entity_type(self, entity_name: str) -> Optional[str]:
        """Bir varlığın tipini döndürür."""
        match = self.map_entity(entity_name)
        return match.entity_type if match.is_matched() else None

    def print_summary(self):
        """Eşleştirme özetini yazdırır."""
        print("=" * 60)
        print("ENTITY MAPPING ÖZETİ")
        print("=" * 60)

        print("\n📊 Kod Varlıkları:")
        for category, entities in self.code_entities.items():
            if category != "all" and entities:
                print(f"   {category}: {len(entities)} adet")
                for e in list(entities)[:5]:  # İlk 5'i göster
                    print(f"      - {e}")
                if len(entities) > 5:
                    print(f"      ... ve {len(entities) - 5} tane daha")

        print("\n📈 Eşleştirme İstatistikleri:")
        print(f"   Toplam: {self.stats['total_mappings']}")
        print(f"   Exact: {self.stats['exact_matches']}")
        print(f"   Fuzzy: {self.stats['fuzzy_matches']}")
        print(f"   Alias: {self.stats['alias_matches']}")
        print(f"   Partial: {self.stats['partial_matches']}")
        print(f"   Eşleşmeyen: {self.stats['no_matches']}")


# =============================================================================
# TEST KODU
# =============================================================================
if __name__ == "__main__":
    # Örnek AST sonucu (simüle edilmiş)
    mock_ast_result = {
        "functions": {
            "main": {"lineno": 1},
            "process_data": {"lineno": 10},
            "calculate_total": {"lineno": 20},
            "save_result": {"lineno": 30}
        },
        "classes": {
            "Calculator": {
                "lineno": 5,
                "methods": ["__init__", "add", "subtract", "_validate"]
            },
            "DataProcessor": {
                "lineno": 40,
                "methods": ["__init__", "process", "transform"]
            }
        },
        "variables": {
            "MAX_VALUE": {"lineno": 1},
            "config": {"lineno": 2},
            "data": {"lineno": 3}
        },
        "imports": [
            {"module": "os", "names": ["path", "getcwd"]},
            {"module": "json", "names": ["loads", "dumps"]}
        ]
    }

    print("=" * 60)
    print("ENTITY MAPPER TESTİ")
    print("=" * 60)

    # Mapper oluştur ve varlıkları yükle
    mapper = EntityMapper()
    mapper.load_code_entities(mock_ast_result)

    # Test eşleştirmeleri
    test_entities = [
        "main",                # Exact match
        "calculate_total",     # Exact match
        "Calculator",          # Exact match
        "calc_total",          # Fuzzy match (typo)
        "init",                # Alias match (__init__)
        "constructor",         # Alias match (__init__)
        "calc",                # Partial match (Calculator)
        "process",             # Exact match (method)
        "nonexistent_func",    # No match
        "DATA",                # Exact match (case insensitive)
    ]

    print("\n🔍 Eşleştirme Sonuçları:")
    print("-" * 60)

    for entity in test_entities:
        match = mapper.map_entity(entity)
        status = "✅" if match.is_matched() else "❌"
        print(f"\n{status} '{entity}'")
        print(f"   Eşleşme: {match.code_entity or 'YOK'}")
        print(f"   Tür: {match.match_type.value}")
        print(f"   Güven: {match.confidence:.2f}")
        if match.entity_type:
            print(f"   Varlık Tipi: {match.entity_type}")

    # Özet
    mapper.print_summary()
