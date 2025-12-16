# =============================================================================
# GRAPH BUILDER MODÜLÜ
# =============================================================================
# Bu modül, AST Parser'dan elde edilen yapısal bilgileri kullanarak
# kod yapısını graf olarak temsil eder. İki tür graf oluşturulur:
#
# 1. CALL GRAPH (Çağrı Grafı):
#    - Düğümler: Fonksiyonlar ve metodlar
#    - Kenarlar: Fonksiyon çağrıları (A fonksiyonu B'yi çağırıyor)
#    - Kullanım: "X fonksiyonu Y'yi çağırıyor mu?" sorularını doğrulamak
#
# 2. DATA FLOW GRAPH (Veri Akış Grafı):
#    - Düğümler: Değişkenler ve fonksiyonlar
#    - Kenarlar: Veri bağımlılıkları (X değişkeni Y'ye bağımlı)
#    - Kullanım: "X verisi Y'den geliyor mu?" sorularını doğrulamak
#
# NetworkX Kütüphanesi:
# --------------------
# NetworkX, Python'da graf oluşturma ve analiz için en popüler kütüphanedir.
# - DiGraph: Yönlü graf (directed graph) - kenarların yönü var
# - Düğüm (node): Grafın noktaları
# - Kenar (edge): Düğümleri birbirine bağlayan çizgiler
# =============================================================================

import networkx as nx
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
import json


@dataclass
class NodeData:
    """
    Bir graf düğümü hakkındaki meta verileri tutan sınıf.

    Attributes:
        name: Düğümün adı (fonksiyon/değişken adı)
        node_type: Düğüm tipi ("function", "class", "variable", "method")
        lineno: Kaynak koddaki satır numarası
        metadata: Ek bilgiler (argümanlar, dönüş tipi vb.)
    """
    name: str
    node_type: str
    lineno: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class GraphBuilder:
    """
    AST analiz sonuçlarından yapısal graflar oluşturan sınıf.

    Bu sınıf, ASTParser'dan gelen verileri alır ve iki tür graf oluşturur:
    1. Call Graph: Fonksiyon çağrı ilişkileri
    2. Data Flow Graph: Veri bağımlılık ilişkileri

    Kullanım:
        builder = GraphBuilder()
        builder.build_from_ast_result(ast_result)

        # Graflara erişim
        call_graph = builder.call_graph
        data_flow_graph = builder.data_flow_graph

        # Sorgulama
        builder.has_call("main", "helper")  # main, helper'ı çağırıyor mu?
        builder.find_path("A", "B")         # A'dan B'ye yol var mı?
    """

    def __init__(self):
        """
        GraphBuilder'ı başlatır.

        İki adet yönlü graf (DiGraph) oluşturur:
        - call_graph: Fonksiyon çağrı ilişkileri için
        - data_flow_graph: Veri akış ilişkileri için
        """
        # Call Graph: Fonksiyonlar arası çağrı ilişkilerini temsil eder
        # Yönlü graf çünkü A→B, B'nin A'yı çağırdığı anlamına gelmez
        self.call_graph: nx.DiGraph = nx.DiGraph()

        # Data Flow Graph: Veri bağımlılıklarını temsil eder
        # A→B: A, B'ye veri sağlıyor (B, A'ya bağımlı)
        self.data_flow_graph: nx.DiGraph = nx.DiGraph()

        # Combined Graph: Tüm ilişkileri içeren birleşik graf
        # Genel sorgular için kullanışlı
        self.combined_graph: nx.DiGraph = nx.DiGraph()

        # Düğüm bilgilerini saklayan sözlük
        self.node_info: Dict[str, NodeData] = {}

        # Ham AST sonucu (referans için)
        self.ast_result: Dict[str, Any] = {}

    def build_from_ast_result(self, ast_result: Dict[str, Any]):
        """
        AST analiz sonuçlarından grafları oluşturur.

        Bu ana metod, tüm graf oluşturma işlemlerini koordine eder:
        1. Önce tüm düğümleri oluştur (fonksiyonlar, sınıflar, değişkenler)
        2. Sonra kenarları ekle (çağrılar, bağımlılıklar)

        Args:
            ast_result: ASTParser.parse_code() metodunun döndürdüğü sözlük
        """
        # Önceki grafları temizle
        self._reset()

        # AST sonucunu sakla
        self.ast_result = ast_result

        # Adım 1: Tüm düğümleri oluştur
        self._create_nodes()

        # Adım 2: Call Graph kenarlarını oluştur
        self._build_call_edges()

        # Adım 3: Data Flow Graph kenarlarını oluştur
        self._build_data_flow_edges()

        # Adım 4: Combined graph'ı oluştur
        self._build_combined_graph()

    def _reset(self):
        """
        Tüm grafları ve veri yapılarını sıfırlar.
        """
        self.call_graph = nx.DiGraph()
        self.data_flow_graph = nx.DiGraph()
        self.combined_graph = nx.DiGraph()
        self.node_info = {}
        self.ast_result = {}

    def _create_nodes(self):
        """
        AST sonuçlarından tüm düğümleri oluşturur.

        Her varlık türü için (fonksiyon, sınıf, değişken) düğümler oluşturulur
        ve ilgili grafğlara eklenir.
        """
        # 1. Fonksiyonları düğüm olarak ekle
        for func_name, func_data in self.ast_result.get("functions", {}).items():
            # NodeData oluştur
            node_data = NodeData(
                name=func_name,
                node_type="function",
                lineno=func_data.get("lineno", 0),
                metadata={
                    "args": func_data.get("args", []),
                    "returns": func_data.get("returns"),
                    "docstring": func_data.get("docstring")
                }
            )
            self.node_info[func_name] = node_data

            # Call graph'a ekle (fonksiyonlar çağrı yapabilir)
            self.call_graph.add_node(
                func_name,
                node_type="function",
                lineno=func_data.get("lineno", 0),
                args=func_data.get("args", [])
            )

        # 2. Sınıfları düğüm olarak ekle
        for class_name, class_data in self.ast_result.get("classes", {}).items():
            node_data = NodeData(
                name=class_name,
                node_type="class",
                lineno=class_data.get("lineno", 0),
                metadata={
                    "bases": class_data.get("bases", []),
                    "methods": class_data.get("methods", []),
                    "docstring": class_data.get("docstring")
                }
            )
            self.node_info[class_name] = node_data

            # Sınıfları data flow graph'a ekle
            self.data_flow_graph.add_node(
                class_name,
                node_type="class",
                lineno=class_data.get("lineno", 0)
            )

        # 3. Global değişkenleri düğüm olarak ekle
        for var_name, var_data in self.ast_result.get("variables", {}).items():
            node_data = NodeData(
                name=var_name,
                node_type="variable",
                lineno=var_data.get("lineno", 0),
                metadata={
                    "scope": var_data.get("scope"),
                    "assigned_value": var_data.get("assigned_value")
                }
            )
            self.node_info[var_name] = node_data

            # Data flow graph'a ekle
            self.data_flow_graph.add_node(
                var_name,
                node_type="variable",
                lineno=var_data.get("lineno", 0),
                value=var_data.get("assigned_value")
            )

    def _build_call_edges(self):
        """
        Fonksiyon çağrı ilişkilerinden kenarlar oluşturur.

        call_relationships sözlüğünü kullanarak:
        - Anahtar: Çağıran fonksiyon
        - Değer: Çağrılan fonksiyonlar listesi

        Her (çağıran, çağrılan) çifti için bir kenar eklenir.
        """
        call_relationships = self.ast_result.get("call_relationships", {})

        for caller, callees in call_relationships.items():
            for callee in callees:
                # Eğer çağrılan fonksiyon grafikte yoksa, ekle
                # (harici fonksiyonlar için - print, len gibi)
                if callee not in self.call_graph:
                    self.call_graph.add_node(
                        callee,
                        node_type="external_function",
                        lineno=0
                    )

                # Kenarı ekle: caller → callee
                # Bu, "caller fonksiyonu callee'yi çağırıyor" anlamına gelir
                self.call_graph.add_edge(
                    caller,
                    callee,
                    relationship="calls"
                )

    def _build_data_flow_edges(self):
        """
        Veri bağımlılık ilişkilerinden kenarlar oluşturur.

        Şu ilişkileri modeller:
        1. Değişken bağımlılıkları: x = a + b → a→x, b→x
        2. Fonksiyon-değişken ilişkileri: fonksiyon içinde kullanılan değişkenler
        """
        # 1. Değişken bağımlılıkları
        for var_name, var_data in self.ast_result.get("variables", {}).items():
            dependencies = var_data.get("dependencies", [])
            for dep in dependencies:
                # Bağımlılık grafikte yoksa ekle
                if dep not in self.data_flow_graph:
                    self.data_flow_graph.add_node(
                        dep,
                        node_type="variable",
                        lineno=0
                    )

                # Kenar ekle: dependency → variable
                # "dependency, variable'a veri sağlıyor"
                self.data_flow_graph.add_edge(
                    dep,
                    var_name,
                    relationship="provides_data"
                )

        # 2. Fonksiyon içi değişkenler
        for func_name, func_data in self.ast_result.get("functions", {}).items():
            # Fonksiyonu data flow graph'a ekle
            if func_name not in self.data_flow_graph:
                self.data_flow_graph.add_node(
                    func_name,
                    node_type="function",
                    lineno=func_data.get("lineno", 0)
                )

            # Fonksiyonun kullandığı değişkenleri bağla
            local_vars = func_data.get("variables", [])
            for var in local_vars:
                if var not in self.data_flow_graph:
                    self.data_flow_graph.add_node(
                        var,
                        node_type="local_variable",
                        lineno=0
                    )
                # Fonksiyon → değişken (fonksiyon bu değişkeni tanımlıyor)
                self.data_flow_graph.add_edge(
                    func_name,
                    var,
                    relationship="defines"
                )

    def _build_combined_graph(self):
        """
        Call graph ve data flow graph'ı birleştirerek tek bir graf oluşturur.

        Bu graf, her türlü ilişkiyi sorgulamak için kullanılabilir.
        """
        # Call graph düğümlerini ve kenarlarını ekle
        self.combined_graph.add_nodes_from(self.call_graph.nodes(data=True))
        for u, v, data in self.call_graph.edges(data=True):
            self.combined_graph.add_edge(u, v, **data, graph_source="call")

        # Data flow graph düğümlerini ve kenarlarını ekle
        self.combined_graph.add_nodes_from(self.data_flow_graph.nodes(data=True))
        for u, v, data in self.data_flow_graph.edges(data=True):
            self.combined_graph.add_edge(u, v, **data, graph_source="data_flow")

    # =========================================================================
    # SORGULAMA METODLARİ
    # Bu metodlar, graflar üzerinde çeşitli sorgulamalar yapmak için kullanılır
    # =========================================================================

    def has_call(self, caller: str, callee: str) -> bool:
        """
        Bir fonksiyonun başka bir fonksiyonu çağırıp çağırmadığını kontrol eder.

        Args:
            caller: Çağıran fonksiyonun adı
            callee: Çağrılan fonksiyonun adı

        Returns:
            True eğer caller, callee'yi doğrudan çağırıyorsa
        """
        return self.call_graph.has_edge(caller, callee)

    def has_path(self, source: str, target: str, graph_type: str = "call") -> bool:
        """
        İki düğüm arasında yol olup olmadığını kontrol eder.

        Doğrudan çağrı yerine dolaylı çağrıları da bulur.
        Örnek: A→B→C varsa, has_path("A", "C") True döner.

        Args:
            source: Başlangıç düğümü
            target: Hedef düğüm
            graph_type: Hangi graf kullanılacak ("call", "data_flow", "combined")

        Returns:
            True eğer source'dan target'a bir yol varsa
        """
        # Hangi grafı kullanacağımızı belirle
        graph = self._get_graph(graph_type)

        # Her iki düğüm de grafikte var mı kontrol et
        if source not in graph or target not in graph:
            return False

        # NetworkX'in yol bulma algoritmasını kullan
        return nx.has_path(graph, source, target)

    def find_path(self, source: str, target: str, graph_type: str = "call") -> Optional[List[str]]:
        """
        İki düğüm arasındaki en kısa yolu bulur.

        Args:
            source: Başlangıç düğümü
            target: Hedef düğüm
            graph_type: Hangi graf kullanılacak

        Returns:
            Yolu temsil eden düğüm listesi veya None (yol yoksa)
        """
        graph = self._get_graph(graph_type)

        if source not in graph or target not in graph:
            return None

        try:
            # En kısa yolu bul (BFS tabanlı)
            path = nx.shortest_path(graph, source, target)
            return path
        except nx.NetworkXNoPath:
            return None

    def get_all_paths(self, source: str, target: str, graph_type: str = "call") -> List[List[str]]:
        """
        İki düğüm arasındaki tüm basit yolları bulur.

        Basit yol: Aynı düğümden iki kez geçmeyen yol.

        Args:
            source: Başlangıç düğümü
            target: Hedef düğüm
            graph_type: Hangi graf kullanılacak

        Returns:
            Tüm yolların listesi
        """
        graph = self._get_graph(graph_type)

        if source not in graph or target not in graph:
            return []

        try:
            # Tüm basit yolları bul
            paths = list(nx.all_simple_paths(graph, source, target))
            return paths
        except nx.NetworkXNoPath:
            return []

    def get_callers(self, func_name: str) -> List[str]:
        """
        Bir fonksiyonu çağıran tüm fonksiyonları bulur.

        Args:
            func_name: Fonksiyon adı

        Returns:
            Bu fonksiyonu çağıran fonksiyonların listesi
        """
        if func_name not in self.call_graph:
            return []

        # Gelen kenarları (predecessors) bul
        return list(self.call_graph.predecessors(func_name))

    def get_callees(self, func_name: str) -> List[str]:
        """
        Bir fonksiyonun çağırdığı tüm fonksiyonları bulur.

        Args:
            func_name: Fonksiyon adı

        Returns:
            Bu fonksiyonun çağırdığı fonksiyonların listesi
        """
        if func_name not in self.call_graph:
            return []

        # Giden kenarları (successors) bul
        return list(self.call_graph.successors(func_name))

    def get_dependencies(self, entity_name: str) -> List[str]:
        """
        Bir varlığın bağımlı olduğu diğer varlıkları bulur.

        Data flow graph'ta bu varlığa veri sağlayan düğümleri döndürür.

        Args:
            entity_name: Varlık adı (değişken veya fonksiyon)

        Returns:
            Bağımlılıklar listesi
        """
        if entity_name not in self.data_flow_graph:
            return []

        return list(self.data_flow_graph.predecessors(entity_name))

    def get_dependents(self, entity_name: str) -> List[str]:
        """
        Bir varlığa bağımlı olan diğer varlıkları bulur.

        Args:
            entity_name: Varlık adı

        Returns:
            Bağımlı varlıklar listesi
        """
        if entity_name not in self.data_flow_graph:
            return []

        return list(self.data_flow_graph.successors(entity_name))

    def node_exists(self, node_name: str, graph_type: str = "combined") -> bool:
        """
        Bir düğümün grafikte var olup olmadığını kontrol eder.

        Args:
            node_name: Düğüm adı
            graph_type: Hangi grafikte aranacak

        Returns:
            True eğer düğüm mevcutsa
        """
        graph = self._get_graph(graph_type)
        return node_name in graph

    def get_node_type(self, node_name: str) -> Optional[str]:
        """
        Bir düğümün tipini döndürür.

        Args:
            node_name: Düğüm adı

        Returns:
            Düğüm tipi ("function", "class", "variable" vb.) veya None
        """
        if node_name in self.node_info:
            return self.node_info[node_name].node_type

        # Node info'da yoksa, graflardaki attribute'a bak
        if node_name in self.combined_graph:
            return self.combined_graph.nodes[node_name].get("node_type")

        return None

    def _get_graph(self, graph_type: str) -> nx.DiGraph:
        """
        Graf tipine göre ilgili graf nesnesini döndürür.

        Args:
            graph_type: "call", "data_flow" veya "combined"

        Returns:
            İlgili NetworkX DiGraph nesnesi
        """
        if graph_type == "call":
            return self.call_graph
        elif graph_type == "data_flow":
            return self.data_flow_graph
        else:
            return self.combined_graph

    # =========================================================================
    # ANALİZ METODLARİ
    # Graf yapısı hakkında istatistiksel bilgiler
    # =========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """
        Graflar hakkında istatistiksel bilgiler döndürür.

        Returns:
            İstatistik sözlüğü
        """
        return {
            "call_graph": {
                "node_count": self.call_graph.number_of_nodes(),
                "edge_count": self.call_graph.number_of_edges(),
                "functions": len([n for n, d in self.call_graph.nodes(data=True)
                                if d.get("node_type") == "function"]),
                "external_calls": len([n for n, d in self.call_graph.nodes(data=True)
                                     if d.get("node_type") == "external_function"])
            },
            "data_flow_graph": {
                "node_count": self.data_flow_graph.number_of_nodes(),
                "edge_count": self.data_flow_graph.number_of_edges(),
                "variables": len([n for n, d in self.data_flow_graph.nodes(data=True)
                                if d.get("node_type") in ("variable", "local_variable")])
            },
            "combined_graph": {
                "node_count": self.combined_graph.number_of_nodes(),
                "edge_count": self.combined_graph.number_of_edges()
            }
        }

    def get_all_nodes(self, graph_type: str = "combined") -> List[str]:
        """
        Bir graftaki tüm düğümlerin listesini döndürür.

        Args:
            graph_type: Hangi graf

        Returns:
            Düğüm adları listesi
        """
        graph = self._get_graph(graph_type)
        return list(graph.nodes())

    def get_all_edges(self, graph_type: str = "combined") -> List[Tuple[str, str, Dict]]:
        """
        Bir graftaki tüm kenarların listesini döndürür.

        Args:
            graph_type: Hangi graf

        Returns:
            (kaynak, hedef, özellikler) tuple'larının listesi
        """
        graph = self._get_graph(graph_type)
        return list(graph.edges(data=True))

    # =========================================================================
    # DIŞA AKTARMA METODLARİ
    # Grafları farklı formatlara dönüştürme
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        Tüm graf verilerini sözlük formatına dönüştürür.

        JSON serileştirme için kullanışlıdır.

        Returns:
            Graf verilerini içeren sözlük
        """
        return {
            "call_graph": {
                "nodes": [
                    {"id": n, **d}
                    for n, d in self.call_graph.nodes(data=True)
                ],
                "edges": [
                    {"source": u, "target": v, **d}
                    for u, v, d in self.call_graph.edges(data=True)
                ]
            },
            "data_flow_graph": {
                "nodes": [
                    {"id": n, **d}
                    for n, d in self.data_flow_graph.nodes(data=True)
                ],
                "edges": [
                    {"source": u, "target": v, **d}
                    for u, v, d in self.data_flow_graph.edges(data=True)
                ]
            },
            "statistics": self.get_statistics()
        }

    def to_json(self, indent: int = 2) -> str:
        """
        Graf verilerini JSON string'e dönüştürür.

        Args:
            indent: JSON girinti miktarı

        Returns:
            JSON formatında string
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def print_summary(self):
        """
        Graf yapısının özetini konsola yazdırır.
        """
        stats = self.get_statistics()

        print("=" * 60)
        print("GRAF YAPISI ÖZETİ")
        print("=" * 60)

        print("\n📊 CALL GRAPH (Çağrı Grafı):")
        print(f"   Düğüm sayısı: {stats['call_graph']['node_count']}")
        print(f"   Kenar sayısı: {stats['call_graph']['edge_count']}")
        print(f"   Fonksiyon sayısı: {stats['call_graph']['functions']}")
        print(f"   Harici çağrı sayısı: {stats['call_graph']['external_calls']}")

        print("\n📊 DATA FLOW GRAPH (Veri Akış Grafı):")
        print(f"   Düğüm sayısı: {stats['data_flow_graph']['node_count']}")
        print(f"   Kenar sayısı: {stats['data_flow_graph']['edge_count']}")
        print(f"   Değişken sayısı: {stats['data_flow_graph']['variables']}")

        print("\n🔗 KENARLAR (Call Graph):")
        for u, v, d in self.call_graph.edges(data=True):
            print(f"   {u} → {v}")

        print("\n" + "=" * 60)


# =============================================================================
# VİZUALİZASYON YARDIMCI FONKSİYONLARİ
# =============================================================================

def visualize_graph_matplotlib(graph: nx.DiGraph, title: str = "Graf",
                               output_path: Optional[str] = None):
    """
    NetworkX grafını matplotlib ile görselleştirir.

    Args:
        graph: Görselleştirilecek graf
        title: Grafik başlığı
        output_path: Kaydedilecek dosya yolu (None ise ekranda göster)
    """
    import matplotlib.pyplot as plt

    # Figür oluştur
    plt.figure(figsize=(12, 8))

    # Düğüm pozisyonlarını hesapla (spring layout)
    pos = nx.spring_layout(graph, k=2, iterations=50)

    # Düğüm tipine göre renkler
    node_colors = []
    for node in graph.nodes():
        node_type = graph.nodes[node].get("node_type", "unknown")
        if node_type == "function":
            node_colors.append("#3498db")  # Mavi
        elif node_type == "class":
            node_colors.append("#e74c3c")  # Kırmızı
        elif node_type == "variable":
            node_colors.append("#2ecc71")  # Yeşil
        elif node_type == "external_function":
            node_colors.append("#95a5a6")  # Gri
        else:
            node_colors.append("#f39c12")  # Turuncu

    # Grafı çiz
    nx.draw(graph, pos,
            with_labels=True,
            node_color=node_colors,
            node_size=2000,
            font_size=10,
            font_weight="bold",
            arrows=True,
            arrowsize=20,
            edge_color="#7f8c8d",
            width=2)

    plt.title(title, fontsize=14, fontweight="bold")

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"Graf kaydedildi: {output_path}")
    else:
        plt.show()

    plt.close()


# =============================================================================
# TEST KODU
# =============================================================================
if __name__ == "__main__":
    # AST Parser'ı import et
    from ast_parser import ASTParser

    # Örnek kod
    test_code = '''
import os

MAX_VALUE = 100
data = [1, 2, 3]

class Calculator:
    def __init__(self):
        self.result = 0

    def add(self, a, b):
        self.result = a + b
        self._validate()
        return self.result

    def _validate(self):
        if self.result > MAX_VALUE:
            print("Uyarı: Maksimum değer aşıldı!")

def process_data(items):
    calc = Calculator()
    total = 0
    for item in items:
        total = calc.add(total, item)
    return total

def main():
    result = process_data(data)
    print(f"Sonuç: {result}")
    save_result(result)

def save_result(value):
    with open("result.txt", "w") as f:
        f.write(str(value))
'''

    # 1. Kodu parse et
    parser = ASTParser()
    ast_result = parser.parse_code(test_code)

    # 2. Graf oluştur
    builder = GraphBuilder()
    builder.build_from_ast_result(ast_result)

    # 3. Özeti yazdır
    builder.print_summary()

    # 4. Sorgulama örnekleri
    print("\n🔍 SORGULAMA ÖRNEKLERİ:")
    print(f"   main → process_data çağrısı var mı? {builder.has_call('main', 'process_data')}")
    print(f"   main → save_result çağrısı var mı? {builder.has_call('main', 'save_result')}")
    print(f"   main → print çağrısı var mı? {builder.has_call('main', 'print')}")

    print(f"\n   main'den print'e yol: {builder.find_path('main', 'print')}")
    print(f"   process_data'nın çağırdıkları: {builder.get_callees('process_data')}")
