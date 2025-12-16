# =============================================================================
# AST PARSER MODÜlÜ
# =============================================================================
# Bu modül, Python kaynak kodunu Abstract Syntax Tree (Soyut Sözdizimi Ağacı)
# yapısına dönüştürür. AST, kodun hiyerarşik yapısını temsil eder ve
# programın sözdizimsel bileşenlerini (fonksiyonlar, sınıflar, değişkenler vb.)
# analiz etmemizi sağlar.
#
# AST Nedir?
# ----------
# AST, kaynak kodun ağaç yapısında temsilidir. Örneğin:
#   def topla(a, b):
#       return a + b
#
# Bu kod şu AST yapısına dönüşür:
#   FunctionDef (name='topla')
#   ├── arguments: [a, b]
#   └── body:
#       └── Return
#           └── BinOp (Add)
#               ├── left: Name('a')
#               └── right: Name('b')
# =============================================================================

import ast
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field


@dataclass
class FunctionInfo:
    """
    Bir fonksiyon hakkındaki bilgileri tutan veri sınıfı.

    Attributes:
        name: Fonksiyonun adı (örn: "hesapla_toplam")
        lineno: Fonksiyonun tanımlandığı satır numarası
        args: Fonksiyonun parametre listesi (örn: ["a", "b", "c"])
        returns: Dönüş tipi (varsa, type annotation'dan alınır)
        calls: Bu fonksiyonun çağırdığı diğer fonksiyonların listesi
        variables: Fonksiyon içinde tanımlanan yerel değişkenler
        docstring: Fonksiyonun dokümantasyon stringi (varsa)
    """
    name: str
    lineno: int
    args: List[str] = field(default_factory=list)
    returns: Optional[str] = None
    calls: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class ClassInfo:
    """
    Bir sınıf hakkındaki bilgileri tutan veri sınıfı.

    Attributes:
        name: Sınıfın adı (örn: "Hesaplayici")
        lineno: Sınıfın tanımlandığı satır numarası
        bases: Miras alınan sınıflar (örn: ["BaseClass", "Mixin"])
        methods: Sınıfa ait metodların listesi
        attributes: Sınıf nitelikleri (class attributes)
        docstring: Sınıfın dokümantasyon stringi
    """
    name: str
    lineno: int
    bases: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class VariableInfo:
    """
    Bir değişken hakkındaki bilgileri tutan veri sınıfı.

    Attributes:
        name: Değişkenin adı
        lineno: Tanımlandığı satır numarası
        scope: Kapsam (global, local, class)
        assigned_value: Atanan değerin string temsili (varsa)
        dependencies: Bu değişkenin bağımlı olduğu diğer değişkenler
    """
    name: str
    lineno: int
    scope: str = "global"
    assigned_value: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ImportInfo:
    """
    Bir import ifadesi hakkındaki bilgileri tutan veri sınıfı.

    Attributes:
        module: Import edilen modül adı (örn: "numpy")
        names: Import edilen isimler (örn: ["array", "zeros"])
        alias: Takma ad (örn: "np" for "import numpy as np")
        lineno: Import ifadesinin satır numarası
    """
    module: str
    names: List[str] = field(default_factory=list)
    alias: Optional[str] = None
    lineno: int = 0


class ASTParser:
    """
    Python kaynak kodunu analiz eden ve yapısal bilgi çıkaran sınıf.

    Bu sınıf, verilen Python kodunu AST'ye dönüştürür ve kodun yapısal
    bileşenlerini (fonksiyonlar, sınıflar, değişkenler, importlar)
    sistematik olarak çıkarır.

    Kullanım:
        parser = ASTParser()
        result = parser.parse_file("ornek.py")
        # veya
        result = parser.parse_code(kod_stringi)

        # Sonuçlara erişim:
        print(result["functions"])  # Fonksiyon listesi
        print(result["classes"])    # Sınıf listesi
    """

    def __init__(self):
        """
        ASTParser sınıfını başlatır.

        Başlangıçta tüm veri yapıları boş olarak oluşturulur.
        Her parse işleminde bu yapılar sıfırlanır ve yeniden doldurulur.
        """
        # Fonksiyon bilgilerini saklayan sözlük
        # Anahtar: fonksiyon adı, Değer: FunctionInfo nesnesi
        self.functions: Dict[str, FunctionInfo] = {}

        # Sınıf bilgilerini saklayan sözlük
        self.classes: Dict[str, ClassInfo] = {}

        # Global değişken bilgilerini saklayan sözlük
        self.variables: Dict[str, VariableInfo] = {}

        # Import bilgilerini saklayan liste
        self.imports: List[ImportInfo] = []

        # Fonksiyon çağrı ilişkilerini saklayan sözlük
        # Anahtar: çağıran fonksiyon, Değer: çağrılan fonksiyonlar kümesi
        self.call_relationships: Dict[str, Set[str]] = {}

        # Ham AST ağacı (debug için saklanır)
        self.ast_tree: Optional[ast.AST] = None

        # Kaynak kod (hata mesajları için saklanır)
        self.source_code: str = ""

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Bir Python dosyasını okuyup analiz eder.

        Args:
            file_path: Analiz edilecek Python dosyasının yolu

        Returns:
            Analiz sonuçlarını içeren sözlük

        Raises:
            FileNotFoundError: Dosya bulunamazsa
            SyntaxError: Python sözdizimi hatası varsa
        """
        # Dosyayı oku
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # Kodu analiz et ve sonuçları döndür
        return self.parse_code(source_code)

    def parse_code(self, source_code: str) -> Dict[str, Any]:
        """
        Python kaynak kodunu analiz eder ve yapısal bilgileri çıkarır.

        Bu metodun çalışma mantığı:
        1. Kaynak kodu AST'ye dönüştür
        2. AST ağacını dolaşarak her düğümü ziyaret et
        3. Her düğüm tipine göre ilgili bilgiyi çıkar
        4. Tüm sonuçları organize edilmiş bir sözlükte döndür

        Args:
            source_code: Analiz edilecek Python kodu (string)

        Returns:
            Aşağıdaki anahtarları içeren sözlük:
            - "functions": Fonksiyon bilgileri
            - "classes": Sınıf bilgileri
            - "variables": Değişken bilgileri
            - "imports": Import bilgileri
            - "call_relationships": Fonksiyon çağrı ilişkileri
        """
        # Önceki analiz sonuçlarını temizle
        self._reset()

        # Kaynak kodu sakla
        self.source_code = source_code

        # Kaynak kodu AST'ye dönüştür
        # ast.parse() fonksiyonu kodu sözdizimsel olarak analiz eder
        # ve bir AST ağacı döndürür
        try:
            self.ast_tree = ast.parse(source_code)
        except SyntaxError as e:
            raise SyntaxError(f"Kod sözdizimi hatası içeriyor: {e}")

        # AST ağacını dolaş ve bilgileri çıkar
        self._extract_all_info()

        # Sonuçları sözlük olarak döndür
        return self._get_results()

    def _reset(self):
        """
        Tüm veri yapılarını sıfırlar.

        Her yeni parse işleminden önce çağrılır, böylece
        önceki analizin sonuçları yeni analizi etkilemez.
        """
        self.functions = {}
        self.classes = {}
        self.variables = {}
        self.imports = []
        self.call_relationships = {}
        self.ast_tree = None
        self.source_code = ""

    def _extract_all_info(self):
        """
        AST ağacını dolaşarak tüm yapısal bilgileri çıkarır.

        ast.walk() fonksiyonu, ağaçtaki tüm düğümleri derinlik öncelikli
        (depth-first) sırayla ziyaret eder. Her düğüm tipine göre
        ilgili extraction metodu çağrılır.
        """
        # Ana seviye düğümleri işle
        for node in ast.walk(self.ast_tree):
            # Fonksiyon tanımı mı?
            if isinstance(node, ast.FunctionDef):
                self._extract_function(node)

            # Async fonksiyon tanımı mı?
            elif isinstance(node, ast.AsyncFunctionDef):
                self._extract_function(node, is_async=True)

            # Sınıf tanımı mı?
            elif isinstance(node, ast.ClassDef):
                self._extract_class(node)

            # Import ifadesi mi?
            elif isinstance(node, ast.Import):
                self._extract_import(node)

            # From import ifadesi mi?
            elif isinstance(node, ast.ImportFrom):
                self._extract_import_from(node)

        # Global değişkenleri ayrıca çıkar
        # (Fonksiyon ve sınıf dışındaki atamalar)
        self._extract_global_variables()

    def _extract_function(self, node: ast.FunctionDef, is_async: bool = False):
        """
        Bir fonksiyon tanımından bilgi çıkarır.

        Bu metod şunları yapar:
        1. Fonksiyon adı ve satır numarasını al
        2. Parametre listesini çıkar
        3. Dönüş tipini al (varsa)
        4. Docstring'i çıkar (varsa)
        5. Fonksiyon gövdesini analiz et (çağrılar, değişkenler)

        Args:
            node: ast.FunctionDef düğümü
            is_async: Async fonksiyon mu?
        """
        # Fonksiyon adı
        func_name = node.name

        # Parametre listesini çıkar
        # node.args.args, normal parametreleri içerir
        args = []
        for arg in node.args.args:
            args.append(arg.arg)

        # *args parametresi varsa ekle
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")

        # **kwargs parametresi varsa ekle
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")

        # Dönüş tipi annotation'ı (varsa)
        returns = None
        if node.returns:
            returns = ast.unparse(node.returns)

        # Docstring'i çıkar
        # Docstring, fonksiyon gövdesinin ilk ifadesi olan string literaldir
        docstring = ast.get_docstring(node)

        # Fonksiyon gövdesindeki çağrıları ve değişkenleri bul
        calls = self._find_calls_in_body(node.body)
        variables = self._find_variables_in_body(node.body)

        # FunctionInfo nesnesi oluştur ve sakla
        func_info = FunctionInfo(
            name=func_name,
            lineno=node.lineno,
            args=args,
            returns=returns,
            calls=calls,
            variables=variables,
            docstring=docstring
        )

        self.functions[func_name] = func_info

        # Çağrı ilişkilerini kaydet
        if calls:
            self.call_relationships[func_name] = set(calls)

    def _extract_class(self, node: ast.ClassDef):
        """
        Bir sınıf tanımından bilgi çıkarır.

        Args:
            node: ast.ClassDef düğümü
        """
        # Sınıf adı
        class_name = node.name

        # Miras alınan sınıfları çıkar
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                # module.Class şeklindeki kalıtımlar için
                bases.append(ast.unparse(base))

        # Sınıf metodlarını bul
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)
                # Metodu ayrıca fonksiyon olarak da kaydet
                self._extract_function(item)

        # Sınıf niteliklerini bul
        attributes = self._find_class_attributes(node)

        # Docstring
        docstring = ast.get_docstring(node)

        # ClassInfo nesnesi oluştur ve sakla
        class_info = ClassInfo(
            name=class_name,
            lineno=node.lineno,
            bases=bases,
            methods=methods,
            attributes=attributes,
            docstring=docstring
        )

        self.classes[class_name] = class_info

    def _extract_import(self, node: ast.Import):
        """
        'import x' tarzı import ifadelerinden bilgi çıkarır.

        Örnek:
            import numpy as np
            → module: "numpy", alias: "np"

        Args:
            node: ast.Import düğümü
        """
        for alias in node.names:
            import_info = ImportInfo(
                module=alias.name,
                names=[alias.name],
                alias=alias.asname,
                lineno=node.lineno
            )
            self.imports.append(import_info)

    def _extract_import_from(self, node: ast.ImportFrom):
        """
        'from x import y' tarzı import ifadelerinden bilgi çıkarır.

        Örnek:
            from os.path import join, exists
            → module: "os.path", names: ["join", "exists"]

        Args:
            node: ast.ImportFrom düğümü
        """
        module = node.module or ""
        names = [alias.name for alias in node.names]

        import_info = ImportInfo(
            module=module,
            names=names,
            lineno=node.lineno
        )
        self.imports.append(import_info)

    def _extract_global_variables(self):
        """
        Global seviyedeki değişken atamalarını çıkarır.

        Sadece modül seviyesindeki (fonksiyon/sınıf dışı) atamaları işler.
        """
        for node in ast.iter_child_nodes(self.ast_tree):
            if isinstance(node, ast.Assign):
                # Basit atama: x = 5
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Bağımlılıkları bul (atanan değerdeki değişkenler)
                        deps = self._find_names_in_node(node.value)

                        var_info = VariableInfo(
                            name=target.id,
                            lineno=node.lineno,
                            scope="global",
                            assigned_value=ast.unparse(node.value),
                            dependencies=deps
                        )
                        self.variables[target.id] = var_info

            elif isinstance(node, ast.AnnAssign):
                # Tip annotasyonlu atama: x: int = 5
                if isinstance(node.target, ast.Name):
                    deps = []
                    if node.value:
                        deps = self._find_names_in_node(node.value)

                    var_info = VariableInfo(
                        name=node.target.id,
                        lineno=node.lineno,
                        scope="global",
                        assigned_value=ast.unparse(node.value) if node.value else None,
                        dependencies=deps
                    )
                    self.variables[node.target.id] = var_info

    def _find_calls_in_body(self, body: List[ast.stmt]) -> List[str]:
        """
        Bir kod bloğundaki tüm fonksiyon çağrılarını bulur.

        Args:
            body: AST statement listesi (fonksiyon gövdesi)

        Returns:
            Çağrılan fonksiyon adlarının listesi
        """
        calls = []

        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(node, ast.Call):
                # Çağrılan fonksiyonun adını al
                call_name = self._get_call_name(node)
                if call_name:
                    calls.append(call_name)

        return list(set(calls))  # Tekrarları kaldır

    def _get_call_name(self, node: ast.Call) -> Optional[str]:
        """
        Bir fonksiyon çağrısından fonksiyon adını çıkarır.

        Farklı çağrı türlerini ele alır:
        - Basit çağrı: func()
        - Metod çağrısı: obj.method()
        - Zincirleme çağrı: obj.method1().method2()

        Args:
            node: ast.Call düğümü

        Returns:
            Fonksiyon/metod adı veya None
        """
        if isinstance(node.func, ast.Name):
            # Basit fonksiyon çağrısı: print(), len()
            return node.func.id

        elif isinstance(node.func, ast.Attribute):
            # Metod çağrısı: obj.method()
            # Sadece metod adını döndür
            return node.func.attr

        return None

    def _find_variables_in_body(self, body: List[ast.stmt]) -> List[str]:
        """
        Bir kod bloğundaki yerel değişken atamalarını bulur.

        Args:
            body: AST statement listesi

        Returns:
            Değişken adlarının listesi
        """
        variables = []

        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variables.append(target.id)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    variables.append(node.target.id)

        return list(set(variables))

    def _find_class_attributes(self, node: ast.ClassDef) -> List[str]:
        """
        Bir sınıftaki sınıf niteliklerini (class attributes) bulur.

        Sınıf gövdesindeki (metod dışı) atamaları arar.

        Args:
            node: ast.ClassDef düğümü

        Returns:
            Nitelik adlarının listesi
        """
        attributes = []

        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attributes.append(target.id)
            elif isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name):
                    attributes.append(item.target.id)

        return attributes

    def _find_names_in_node(self, node: ast.AST) -> List[str]:
        """
        Bir AST düğümündeki tüm isim referanslarını bulur.

        Bu, bir ifadede kullanılan değişkenleri bulmak için kullanılır.
        Örnek: "a + b * c" ifadesinde ["a", "b", "c"] döner.

        Args:
            node: Herhangi bir AST düğümü

        Returns:
            Referans edilen isimler listesi
        """
        names = []
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                names.append(child.id)
        return list(set(names))

    def _get_results(self) -> Dict[str, Any]:
        """
        Tüm analiz sonuçlarını organize edilmiş bir sözlük olarak döndürür.

        Returns:
            Analiz sonuçlarını içeren sözlük
        """
        return {
            "functions": {
                name: {
                    "name": info.name,
                    "lineno": info.lineno,
                    "args": info.args,
                    "returns": info.returns,
                    "calls": info.calls,
                    "variables": info.variables,
                    "docstring": info.docstring
                }
                for name, info in self.functions.items()
            },
            "classes": {
                name: {
                    "name": info.name,
                    "lineno": info.lineno,
                    "bases": info.bases,
                    "methods": info.methods,
                    "attributes": info.attributes,
                    "docstring": info.docstring
                }
                for name, info in self.classes.items()
            },
            "variables": {
                name: {
                    "name": info.name,
                    "lineno": info.lineno,
                    "scope": info.scope,
                    "assigned_value": info.assigned_value,
                    "dependencies": info.dependencies
                }
                for name, info in self.variables.items()
            },
            "imports": [
                {
                    "module": info.module,
                    "names": info.names,
                    "alias": info.alias,
                    "lineno": info.lineno
                }
                for info in self.imports
            ],
            "call_relationships": {
                caller: list(callees)
                for caller, callees in self.call_relationships.items()
            }
        }

    def get_all_entities(self) -> Dict[str, List[str]]:
        """
        Koddaki tüm varlıkları (entity) kategorize ederek döndürür.

        Bu metod, entity mapping modülü için kullanılır.
        LLM çıktısındaki metinsel referansları bu listeyle eşleştiririz.

        Returns:
            Kategorize edilmiş varlık listesi:
            - "functions": Tüm fonksiyon adları
            - "classes": Tüm sınıf adları
            - "methods": Tüm metod adları
            - "variables": Tüm değişken adları
            - "imports": Tüm import edilen modüller
        """
        # Tüm metodları topla (sınıf metodları)
        all_methods = []
        for class_info in self.classes.values():
            all_methods.extend(class_info.methods)

        return {
            "functions": list(self.functions.keys()),
            "classes": list(self.classes.keys()),
            "methods": all_methods,
            "variables": list(self.variables.keys()),
            "imports": [imp.module for imp in self.imports]
        }

    def print_summary(self):
        """
        Analiz sonuçlarının özetini konsola yazdırır.

        Debug ve hızlı inceleme için kullanışlıdır.
        """
        print("=" * 60)
        print("AST ANALİZ ÖZETİ")
        print("=" * 60)

        print(f"\n📦 Import sayısı: {len(self.imports)}")
        for imp in self.imports:
            print(f"   - {imp.module}")

        print(f"\n🔧 Fonksiyon sayısı: {len(self.functions)}")
        for name, info in self.functions.items():
            args_str = ", ".join(info.args)
            print(f"   - {name}({args_str}) [satır {info.lineno}]")
            if info.calls:
                print(f"     Çağırıyor: {', '.join(info.calls)}")

        print(f"\n📦 Sınıf sayısı: {len(self.classes)}")
        for name, info in self.classes.items():
            print(f"   - {name} [satır {info.lineno}]")
            if info.methods:
                print(f"     Metodlar: {', '.join(info.methods)}")

        print(f"\n📊 Global değişken sayısı: {len(self.variables)}")
        for name, info in self.variables.items():
            print(f"   - {name} = {info.assigned_value}")

        print("\n" + "=" * 60)


# =============================================================================
# TEST KODU
# Bu bölüm, modül doğrudan çalıştırıldığında test amaçlı çalışır
# =============================================================================
if __name__ == "__main__":
    # Örnek test kodu
    test_code = '''
import os
from typing import List, Optional

MAX_VALUE = 100
config = {"debug": True}

class Calculator:
    """Basit bir hesap makinesi sınıfı."""

    def __init__(self, name: str):
        self.name = name
        self.history = []

    def add(self, a: int, b: int) -> int:
        """İki sayıyı toplar."""
        result = a + b
        self._log_operation("add", result)
        return result

    def _log_operation(self, op: str, result: int):
        self.history.append(f"{op}: {result}")

def main():
    """Ana fonksiyon."""
    calc = Calculator("MyCalc")
    result = calc.add(5, 3)
    print(result)

if __name__ == "__main__":
    main()
'''

    # Parser'ı oluştur ve kodu analiz et
    parser = ASTParser()
    result = parser.parse_code(test_code)

    # Özeti yazdır
    parser.print_summary()

    # Tüm varlıkları göster
    print("\n🏷️  Tüm Varlıklar:")
    entities = parser.get_all_entities()
    for category, items in entities.items():
        print(f"   {category}: {items}")
