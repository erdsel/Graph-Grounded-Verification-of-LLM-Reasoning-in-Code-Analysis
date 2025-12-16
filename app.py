#!/usr/bin/env python3
# =============================================================================
# WEB UYGULAMASI - Flask Backend
# =============================================================================
# Bu dosya, LLM doğrulama sisteminin web arayüzü için API sağlar.
#
# Özellikler:
# - Python kodu analizi (AST + Graf)
# - LLM analizi (Gemini/Mock)
# - Gerçek vs LLM karşılaştırması
# - Halüsinasyon tespiti
#
# Kullanım:
#   python app.py
#   Tarayıcıda: http://localhost:5000
# =============================================================================

import os
import sys
from pathlib import Path

# Modül yolunu ekle
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

from src.ast_parser import ASTParser
from src.graph_builder import GraphBuilder
from src.llm_client import LLMClient
from src.claim_extractor import ClaimExtractor
from src.entity_mapper import EntityMapper
from src.verifier import Verifier
from src.metrics import MetricsCalculator

app = Flask(__name__,
            template_folder='web/templates',
            static_folder='web/static')
CORS(app)


# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

# Dunder metodlar - bunlar için sınıf bağlamı korunmalı
DUNDER_METHODS = {
    "__init__", "__new__", "__del__", "__repr__", "__str__",
    "__call__", "__enter__", "__exit__", "__get__", "__set__",
    "__getattr__", "__setattr__", "__getitem__", "__setitem__",
    "__iter__", "__next__", "__len__", "__contains__",
    "__add__", "__sub__", "__mul__", "__eq__", "__hash__"
}


def normalize_name(name, keep_class_context=False):
    """
    İsmi normalize eder.

    Args:
        name: Normalize edilecek isim
        keep_class_context: True ise sınıf prefiksini koru (dunder metodlar için)

    Örnekler (keep_class_context=False):
        "product.__init__" → "__init__"
        "orderprocessor.process_order" → "process_order"

    Örnekler (keep_class_context=True):
        "product.__init__" → "product.__init__"
        "DataProcessor.__init__" → "dataprocessor.__init__"
    """
    if not name:
        return name

    name = name.lower().strip()

    if keep_class_context:
        # Sadece küçük harfe çevir, prefiksi koru
        return name

    # Nokta varsa, son kısmı al (metod adı)
    if "." in name:
        name = name.split(".")[-1]

    return name


def smart_normalize(name):
    """
    Akıllı normalizasyon: Dunder metodlar için sınıf bağlamını korur,
    diğerleri için prefiksi kaldırır.

    Örnekler:
        "DataProcessor.__init__" → "dataprocessor.__init__"
        "Product.__init__" → "product.__init__"
        "ShoppingCart.add_item" → "add_item"
        "main" → "main"
    """
    if not name:
        return name

    name_lower = name.lower().strip()

    # Nokta varsa
    if "." in name_lower:
        parts = name_lower.split(".")
        method_name = parts[-1]

        # Dunder metod mu?
        if method_name in DUNDER_METHODS:
            # Sınıf bağlamını koru
            return name_lower
        else:
            # Sadece metod adını döndür
            return method_name

    return name_lower


# Global ayarlar
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


@app.route('/')
def index():
    """Ana sayfa - kod editörü ve analiz arayüzü."""
    return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def analyze_code():
    """
    Python kodunu analiz eder ve sonuçları döndürür.

    Request JSON:
        {
            "code": "def main(): ...",
            "use_llm": true,
            "provider": "gemini"  // veya "mock"
        }

    Response JSON:
        {
            "success": true,
            "ground_truth": { ... },  // Gerçek kod analizi
            "llm_analysis": { ... },  // LLM'nin analizi
            "comparison": { ... },    // Karşılaştırma
            "metrics": { ... }        // Metrikler
        }
    """
    try:
        data = request.get_json()
        code = data.get('code', '')
        use_llm = data.get('use_llm', True)
        provider = data.get('provider', 'gemini')

        if not code.strip():
            return jsonify({
                "success": False,
                "error": "Kod boş olamaz!"
            }), 400

        # =================================================================
        # ADIM 1: GERÇEK KOD ANALİZİ (Ground Truth)
        # =================================================================

        # AST Parser ile analiz et
        parser = ASTParser()
        ast_result = parser.parse_code(code)

        # Graf oluştur
        graph_builder = GraphBuilder()
        graph_builder.build_from_ast_result(ast_result)

        # Entity mapper
        entity_mapper = EntityMapper()
        entity_mapper.load_code_entities(ast_result)

        # Ground truth verisi oluştur
        ground_truth = {
            "functions": [],
            "classes": [],
            "call_graph": [],
            "variables": [],
            "global_calls": [],  # Global seviyedeki çağrılar (fonksiyon dışı)
            "has_functions": False  # Fonksiyon var mı?
        }

        # Fonksiyonları ekle (ast_result["functions"] bir dict)
        # NOT: AST Parser sınıf metodlarını da buraya ekliyor (__init__, _validate_price vb.)
        functions_dict = ast_result.get("functions", {})
        ground_truth["has_functions"] = len(functions_dict) > 0

        for func_name, func_data in functions_dict.items():
            func_calls = func_data.get("calls", [])
            ground_truth["functions"].append({
                "name": func_name,
                "line": func_data.get("lineno", 0),
                "calls": func_calls,
                "params": func_data.get("args", [])
            })

            # Her fonksiyonun çağrılarını call_graph'a ekle
            # Bu, sınıf metodlarının çağrılarını da içerir
            for callee in func_calls:
                ground_truth["call_graph"].append({
                    "caller": func_name,
                    "callee": callee
                })

        # Global seviyedeki çağrıları bul (fonksiyon dışındaki print, range vb.)
        import ast
        try:
            tree = ast.parse(code)
            # Sadece modül seviyesindeki statement'ları kontrol et
            for node in tree.body:
                # Fonksiyon veya sınıf tanımı değilse
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    # Bu node ve alt nodlarındaki tüm çağrıları bul
                    for subnode in ast.walk(node):
                        if isinstance(subnode, ast.Call):
                            if isinstance(subnode.func, ast.Name):
                                ground_truth["global_calls"].append(subnode.func.id)
                            elif isinstance(subnode.func, ast.Attribute):
                                ground_truth["global_calls"].append(subnode.func.attr)
            # Tekrarları kaldır
            ground_truth["global_calls"] = list(set(ground_truth["global_calls"]))
        except:
            pass

        # Sınıfları ekle (ast_result["classes"] bir dict)
        # NOT: Sınıf metodlarının çağrıları zaten yukarıda functions_dict üzerinden eklendi
        classes_dict = ast_result.get("classes", {})
        for cls_name, cls_data in classes_dict.items():
            methods = cls_data.get("methods", [])
            # methods zaten bir liste (string listesi)
            if isinstance(methods, dict):
                methods = list(methods.keys())

            ground_truth["classes"].append({
                "name": cls_name,
                "line": cls_data.get("lineno", 0),
                "methods": methods
            })

        # Call graph kenarları - GraphBuilder'dan da ekle (eğer functions_dict'te yoksa)
        call_graph = graph_builder.call_graph
        if call_graph:
            existing_edges = {(e["caller"], e["callee"]) for e in ground_truth["call_graph"]}
            for edge in call_graph.edges():
                if (edge[0], edge[1]) not in existing_edges:
                    ground_truth["call_graph"].append({
                        "caller": edge[0],
                        "callee": edge[1]
                    })

        # Global çağrıları da call graph'a ekle (caller: "<module>" olarak)
        for global_call in ground_truth["global_calls"]:
            ground_truth["call_graph"].append({
                "caller": "<module>",
                "callee": global_call
            })

        # Tekrar eden edge'leri kaldır
        seen_edges = set()
        unique_call_graph = []
        for edge in ground_truth["call_graph"]:
            edge_tuple = (edge["caller"], edge["callee"])
            if edge_tuple not in seen_edges:
                seen_edges.add(edge_tuple)
                unique_call_graph.append(edge)
        ground_truth["call_graph"] = unique_call_graph

        # Global değişkenler
        variables_dict = ast_result.get("variables", {})
        for var_name, var_data in variables_dict.items():
            ground_truth["variables"].append({
                "name": var_name,
                "value": str(var_data.get("value", ""))[:50] if isinstance(var_data, dict) else str(var_data)[:50]
            })

        # =================================================================
        # ADIM 2: LLM ANALİZİ
        # =================================================================

        llm_analysis = {
            "raw_response": "",
            "claims": [],
            "function_calls": []
        }

        if use_llm:
            # LLM client oluştur
            if provider == "mock":
                llm_client = LLMClient.create(provider="mock")
            elif provider == "groq":
                llm_client = LLMClient.create(
                    provider="groq",
                    api_key=GROQ_API_KEY
                )
            elif provider == "gemini":
                llm_client = LLMClient.create(
                    provider="gemini",
                    api_key=GEMINI_API_KEY
                )
            else:
                # Auto mod - Groq öncelikli
                llm_client = LLMClient.create(
                    provider="auto",
                    api_key=GROQ_API_KEY or GEMINI_API_KEY
                )

            # LLM'den analiz al
            llm_response = llm_client.generate_reasoning(code, "analysis")
            llm_analysis["raw_response"] = llm_response.content

            # Claim'leri çıkar
            claim_extractor = ClaimExtractor()
            claims = claim_extractor.extract_claims(
                llm_response.content,
                llm_response.reasoning_steps
            )

            # Claim'leri JSON formatına dönüştür
            for claim in claims:
                llm_analysis["claims"].append({
                    "text": claim.text,
                    "type": claim.claim_type.value,
                    "subject": claim.subject,
                    "object": claim.object,
                    "confidence": claim.confidence
                })

            # LLM'nin bulduğu fonksiyon çağrılarını çıkar
            for claim in claims:
                if claim.claim_type.value == "call" and claim.subject and claim.object:
                    llm_analysis["function_calls"].append({
                        "caller": claim.subject,
                        "callee": claim.object
                    })

        # =================================================================
        # ADIM 3: KARŞILAŞTIRMA
        # =================================================================

        comparison = {
            "matched": [],      # Her iki tarafta da var
            "only_in_truth": [], # Sadece gerçekte var (LLM kaçırmış)
            "only_in_llm": [],   # Sadece LLM'de var (halüsinasyon)
            "hallucinations": []
        }

        # Fonksiyon ve metod isimlerini topla
        user_funcs = {f["name"].lower() for f in ground_truth["functions"]}
        user_methods = set()
        for cls in ground_truth["classes"]:
            for method in cls.get("methods", []):
                user_methods.add(method.lower())

        # Tüm bilinen isimler (fonksiyonlar + metodlar)
        all_known_names = user_funcs | user_methods

        # Ground truth call'larını set'e çevir
        truth_calls = set()
        # Ayrıca base name (sınıf prefiksi olmadan) versiyonlarını da tut
        truth_calls_base = {}  # {(base_caller, base_callee): (full_caller, full_callee)}

        for edge in ground_truth["call_graph"]:
            caller = edge["caller"].lower().strip()
            callee = edge["callee"].lower().strip()

            # Base isimleri al (sınıf prefiksi olmadan)
            caller_base = caller.split(".")[-1] if "." in caller else caller
            callee_base = callee.split(".")[-1] if "." in callee else callee

            # Bilinen fonksiyon/metodlardan yapılan çağrıları ekle
            if caller_base in all_known_names or caller in all_known_names:
                truth_calls.add((caller, callee))
                # Base versiyonunu da sakla (fuzzy matching için)
                truth_calls_base[(caller_base, callee_base)] = (caller, callee)
            # Global çağrılar (<module> -> user_func)
            elif caller == "<module>":
                if callee_base in user_funcs or callee in user_funcs:
                    truth_calls.add(("<module>", callee))
                    truth_calls_base[("<module>", callee_base)] = ("<module>", callee)

        # LLM call'larını set'e çevir
        llm_calls = set()
        llm_calls_base = {}  # {(base_caller, base_callee): (full_caller, full_callee)}
        # LLM'in global çağrıları için kullanabileceği caller isimleri
        global_caller_aliases = {"module", "<module>", "program", "script", "global"}

        for call in llm_analysis["function_calls"]:
            caller = call["caller"].lower().strip()
            callee = call["callee"].lower().strip()

            # Base isimleri al
            caller_base = caller.split(".")[-1] if "." in caller else caller
            callee_base = callee.split(".")[-1] if "." in callee else callee

            # Eğer caller bilinen bir fonksiyon/metodsa, direkt ekle
            if caller_base in all_known_names or caller in all_known_names:
                llm_calls.add((caller, callee))
                llm_calls_base[(caller_base, callee_base)] = (caller, callee)
            # LLM "module", "script" gibi şeyler dediyse, <module> olarak yorumla
            elif caller in global_caller_aliases:
                if callee_base in user_funcs or callee in user_funcs:
                    llm_calls.add(("<module>", callee))
                    llm_calls_base[("<module>", callee_base)] = ("<module>", callee)
            else:
                llm_calls.add((caller, callee))
                llm_calls_base[(caller_base, callee_base)] = (caller, callee)

        # Fuzzy karşılaştırma: Önce tam eşleşme, sonra base eşleşme
        def calls_match(truth_call, llm_call):
            """İki çağrının eşleşip eşleşmediğini kontrol et."""
            # Tam eşleşme
            if truth_call == llm_call:
                return True
            # Base eşleşme (sınıf prefiksi farklı olabilir)
            t_caller, t_callee = truth_call
            l_caller, l_callee = llm_call
            t_caller_base = t_caller.split(".")[-1] if "." in t_caller else t_caller
            t_callee_base = t_callee.split(".")[-1] if "." in t_callee else t_callee
            l_caller_base = l_caller.split(".")[-1] if "." in l_caller else l_caller
            l_callee_base = l_callee.split(".")[-1] if "." in l_callee else l_callee
            return t_caller_base == l_caller_base and t_callee_base == l_callee_base

        # Karşılaştır - fuzzy matching kullan
        matched_truth = set()
        matched_llm = set()

        for truth_call in truth_calls:
            for llm_call in llm_calls:
                if calls_match(truth_call, llm_call):
                    comparison["matched"].append({
                        "caller": truth_call[0],
                        "callee": truth_call[1],
                        "status": "correct"
                    })
                    matched_truth.add(truth_call)
                    matched_llm.add(llm_call)
                    break

        # Kaçırılanlar (LLM görmedi)
        for call in truth_calls:
            if call not in matched_truth:
                comparison["only_in_truth"].append({
                    "caller": call[0],
                    "callee": call[1],
                    "status": "missed"
                })

        # Halüsinasyonlar (LLM uydurdu)
        for call in llm_calls:
            if call not in matched_llm:
                comparison["only_in_llm"].append({
                    "caller": call[0],
                    "callee": call[1],
                    "status": "hallucination"
                })
                comparison["hallucinations"].append({
                    "claim": f"{call[0]} -> {call[1]}",
                    "reason": f"'{call[0]}' fonksiyonu '{call[1]}' fonksiyonunu çağırmıyor"
                })

        # =================================================================
        # ADIM 4: METRİKLER
        # =================================================================

        total_truth = len(truth_calls)
        total_llm = len(llm_calls)
        matched = len(comparison["matched"])
        hallucinations = len(comparison["only_in_llm"])
        missed = len(comparison["only_in_truth"])

        metrics = {
            "precision": round(matched / total_llm * 100, 1) if total_llm > 0 else 0,
            "recall": round(matched / total_truth * 100, 1) if total_truth > 0 else 0,
            "hallucination_rate": round(hallucinations / total_llm * 100, 1) if total_llm > 0 else 0,
            "coverage": round((total_truth - missed) / total_truth * 100, 1) if total_truth > 0 else 0,
            "total_ground_truth": total_truth,
            "total_llm_claims": total_llm,
            "correct_claims": matched,
            "hallucinations": hallucinations,
            "missed": missed
        }

        # F1 skoru hesapla
        if metrics["precision"] + metrics["recall"] > 0:
            metrics["f1_score"] = round(
                2 * metrics["precision"] * metrics["recall"] /
                (metrics["precision"] + metrics["recall"]), 1
            )
        else:
            metrics["f1_score"] = 0

        return jsonify({
            "success": True,
            "ground_truth": ground_truth,
            "llm_analysis": llm_analysis,
            "comparison": comparison,
            "metrics": metrics
        })

    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """API sağlık kontrolü."""
    return jsonify({
        "status": "healthy",
        "version": "1.0.0"
    })


if __name__ == '__main__':
    # Web klasörlerini oluştur
    Path("web/templates").mkdir(parents=True, exist_ok=True)
    Path("web/static/css").mkdir(parents=True, exist_ok=True)
    Path("web/static/js").mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("  LLM DOĞRULAMA SİSTEMİ - Web Arayüzü")
    print("=" * 60)
    print("\n  🌐 Tarayıcıda aç: http://localhost:5000")
    print("  📝 API endpoint:  http://localhost:5000/api/analyze")
    print("\n" + "=" * 60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
