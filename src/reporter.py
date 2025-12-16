# =============================================================================
# HTML REPORTER MODÜLÜ
# =============================================================================
# Bu modül, doğrulama sonuçlarını görsel ve interaktif HTML raporlarına
# dönüştürür.
#
# Rapor İçeriği:
# -------------
# 1. Özet Dashboard: Ana metrikler ve genel değerlendirme
# 2. Halüsinasyon Listesi: Tespit edilen yanlış iddialar
# 3. Claim Tablosu: Tüm claim'lerin detaylı listesi
# 4. Graf Görselleştirmesi: Call graph ve data flow graph
# 5. Metrik Grafikleri: Pasta ve çubuk grafikler
#
# Kullanılan Teknolojiler:
# -----------------------
# - Jinja2: HTML şablonlama
# - Bootstrap: CSS framework (inline)
# - Chart.js: Grafikler (CDN üzerinden)
# =============================================================================

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Jinja2 opsiyonel
try:
    from jinja2 import Template, Environment, BaseLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    print("⚠️  Jinja2 bulunamadı. Basit HTML şablonu kullanılacak.")

from .verifier import VerificationReport, VerificationDetail, VerificationResult
from .metrics import MetricsReport, MetricResult


class HTMLReporter:
    """
    Doğrulama sonuçlarını HTML raporuna dönüştüren sınıf.

    Bu sınıf, verification ve metrics verilerini alarak
    görsel ve interaktif bir HTML raporu oluşturur.

    Kullanım:
        reporter = HTMLReporter()
        html = reporter.generate_report(
            verification_report=verif_report,
            metrics_report=metrics_report,
            code_info={"filename": "example.py"}
        )
        reporter.save_report(html, "output/report.html")
    """

    # HTML şablonu (Jinja2 veya string format)
    HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Doğrulama Raporu</title>

    <!-- Bootstrap CSS (CDN) -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <style>
        :root {
            --success-color: #28a745;
            --danger-color: #dc3545;
            --warning-color: #ffc107;
            --info-color: #17a2b8;
        }

        body {
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem 0;
            margin-bottom: 2rem;
        }

        .metric-card {
            background: white;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }

        .metric-card:hover {
            transform: translateY(-5px);
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
        }

        .metric-label {
            color: #6c757d;
            font-size: 0.9rem;
        }

        .status-valid {
            color: var(--success-color);
        }

        .status-hallucination {
            color: var(--danger-color);
        }

        .status-unverifiable {
            color: var(--warning-color);
        }

        .status-partial {
            color: var(--info-color);
        }

        .hallucination-card {
            border-left: 4px solid var(--danger-color);
            background: #fff5f5;
        }

        .valid-card {
            border-left: 4px solid var(--success-color);
            background: #f0fff4;
        }

        .claim-table th {
            background-color: #343a40;
            color: white;
        }

        .badge-valid { background-color: var(--success-color); }
        .badge-hallucination { background-color: var(--danger-color); }
        .badge-unverifiable { background-color: var(--warning-color); }
        .badge-partial { background-color: var(--info-color); }

        .assessment-badge {
            font-size: 1.2rem;
            padding: 0.5rem 1rem;
        }

        .chart-container {
            background: white;
            border-radius: 10px;
            padding: 1rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .recommendation {
            background: #e7f3ff;
            border-left: 4px solid #0d6efd;
            padding: 1rem;
            margin-bottom: 0.5rem;
            border-radius: 0 5px 5px 0;
        }

        .footer {
            background: #343a40;
            color: white;
            padding: 2rem 0;
            margin-top: 3rem;
        }

        pre {
            background: #f4f4f4;
            padding: 1rem;
            border-radius: 5px;
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div class="container">
            <h1><i class="bi bi-shield-check"></i> LLM Doğrulama Raporu</h1>
            <p class="mb-0">Graph-Grounded Verification of LLM Reasoning</p>
            <small>Oluşturulma: {{ generation_time }}</small>
        </div>
    </div>

    <div class="container">
        <!-- Genel Değerlendirme -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="metric-card text-center">
                    <h3>Genel Değerlendirme</h3>
                    <span class="assessment-badge badge
                        {% if summary.overall_assessment == 'MÜKEMMEL' %}bg-success
                        {% elif summary.overall_assessment == 'İYİ' %}bg-info
                        {% elif summary.overall_assessment == 'ORTA' %}bg-warning
                        {% else %}bg-danger{% endif %}">
                        {{ summary.overall_assessment }}
                    </span>
                    <p class="mt-2 mb-0">
                        <strong>{{ summary.total_claims }}</strong> iddia analiz edildi,
                        <strong class="text-danger">{{ summary.hallucination_count }}</strong> halüsinasyon tespit edildi.
                    </p>
                </div>
            </div>
        </div>

        <!-- Ana Metrikler -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-value status-hallucination">
                        {{ "%.1f"|format(summary.hallucination_rate * 100) }}%
                    </div>
                    <div class="metric-label">Halüsinasyon Oranı</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-value status-valid">
                        {{ "%.1f"|format(summary.validity_rate * 100) }}%
                    </div>
                    <div class="metric-label">Geçerlilik Oranı</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-value text-primary">
                        {{ verification_summary.valid_count }}
                    </div>
                    <div class="metric-label">Doğrulanan İddia</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card text-center">
                    <div class="metric-value text-danger">
                        {{ verification_summary.hallucination_count }}
                    </div>
                    <div class="metric-label">Halüsinasyon</div>
                </div>
            </div>
        </div>

        <!-- Grafikler -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="chart-container">
                    <h5>Sonuç Dağılımı</h5>
                    <canvas id="resultChart"></canvas>
                </div>
            </div>
            <div class="col-md-6">
                <div class="chart-container">
                    <h5>Claim Türü Analizi</h5>
                    <canvas id="typeChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Halüsinasyonlar -->
        {% if hallucinations %}
        <div class="row mb-4">
            <div class="col-12">
                <h3 class="text-danger"><i class="bi bi-exclamation-triangle"></i> Tespit Edilen Halüsinasyonlar</h3>
                <p class="text-muted">LLM'nin yaptığı yanlış veya desteklenmeyen iddialar:</p>

                {% for h in hallucinations %}
                <div class="card hallucination-card mb-3">
                    <div class="card-body">
                        <h5 class="card-title text-danger">
                            #{{ loop.index }} - {{ h.claim.claim_type }}
                        </h5>
                        <p class="card-text">
                            <strong>İddia:</strong> {{ h.claim.text }}
                        </p>
                        <p class="card-text">
                            <strong>Sebep:</strong> {{ h.reason }}
                        </p>
                        <div class="row">
                            <div class="col-md-6">
                                <small class="text-muted">
                                    Özne: {{ h.claim.subject or '-' }}
                                    {% if h.subject_match %}
                                    → {{ h.subject_match.code_entity or 'EŞLEŞMEDİ' }}
                                    {% endif %}
                                </small>
                            </div>
                            <div class="col-md-6">
                                <small class="text-muted">
                                    Nesne: {{ h.claim.object or '-' }}
                                    {% if h.object_match %}
                                    → {{ h.object_match.code_entity or 'EŞLEŞMEDİ' }}
                                    {% endif %}
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <!-- Tüm Claim'ler Tablosu -->
        <div class="row mb-4">
            <div class="col-12">
                <h3>Tüm İddialar</h3>
                <div class="table-responsive">
                    <table class="table table-striped claim-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Tür</th>
                                <th>İddia</th>
                                <th>Sonuç</th>
                                <th>Güven</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for detail in all_details %}
                            <tr>
                                <td>{{ loop.index }}</td>
                                <td><span class="badge bg-secondary">{{ detail.claim.claim_type }}</span></td>
                                <td>{{ detail.claim.text[:50] }}{% if detail.claim.text|length > 50 %}...{% endif %}</td>
                                <td>
                                    <span class="badge badge-{{ detail.result }}">
                                        {{ detail.result }}
                                    </span>
                                </td>
                                <td>{{ "%.0f"|format(detail.confidence * 100) }}%</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Öneriler -->
        {% if recommendations %}
        <div class="row mb-4">
            <div class="col-12">
                <h3><i class="bi bi-lightbulb"></i> Öneriler</h3>
                {% for rec in recommendations %}
                <div class="recommendation">{{ rec }}</div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <!-- Metrik Detayları -->
        <div class="row mb-4">
            <div class="col-12">
                <h3>Detaylı Metrikler</h3>
                <div class="accordion" id="metricsAccordion">
                    {% for metric in metrics %}
                    <div class="accordion-item">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed" type="button"
                                    data-bs-toggle="collapse"
                                    data-bs-target="#metric{{ loop.index }}">
                                {{ metric.name }}: {{ "%.2f"|format(metric.value) }}
                            </button>
                        </h2>
                        <div id="metric{{ loop.index }}" class="accordion-collapse collapse">
                            <div class="accordion-body">
                                <p>{{ metric.description }}</p>
                                <pre>{{ metric.details | tojson(indent=2) }}</pre>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <div class="footer">
        <div class="container text-center">
            <p>Graph-Grounded Verification of LLM Reasoning</p>
            <small>Selen Erdoğan - Gebze Teknik Üniversitesi</small>
        </div>
    </div>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

    <!-- Chart.js Grafikleri -->
    <script>
        // Sonuç Dağılımı Pasta Grafiği
        const resultCtx = document.getElementById('resultChart').getContext('2d');
        new Chart(resultCtx, {
            type: 'doughnut',
            data: {
                labels: ['Geçerli', 'Halüsinasyon', 'Doğrulanamayan', 'Kısmen Geçerli'],
                datasets: [{
                    data: [
                        {{ verification_summary.valid_count }},
                        {{ verification_summary.hallucination_count }},
                        {{ verification_summary.unverifiable_count }},
                        {{ verification_summary.partially_valid_count }}
                    ],
                    backgroundColor: ['#28a745', '#dc3545', '#ffc107', '#17a2b8']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });

        // Claim Türü Çubuk Grafiği
        const typeCtx = document.getElementById('typeChart').getContext('2d');
        new Chart(typeCtx, {
            type: 'bar',
            data: {
                labels: {{ claim_type_labels | tojson }},
                datasets: [{
                    label: 'Toplam',
                    data: {{ claim_type_totals | tojson }},
                    backgroundColor: '#6c757d'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    </script>
</body>
</html>
'''

    def __init__(self):
        """HTMLReporter'ı başlatır."""
        self.template = None
        if JINJA2_AVAILABLE:
            env = Environment(loader=BaseLoader())
            self.template = env.from_string(self.HTML_TEMPLATE)

    def generate_report(self,
                       verification_report: VerificationReport,
                       metrics_report: MetricsReport,
                       code_info: Optional[Dict[str, Any]] = None) -> str:
        """
        HTML raporunu oluşturur.

        Args:
            verification_report: Doğrulama raporu
            metrics_report: Metrik raporu
            code_info: Kod hakkında ek bilgiler (dosya adı vb.)

        Returns:
            HTML string
        """
        # Şablon verilerini hazırla
        template_data = self._prepare_template_data(
            verification_report,
            metrics_report,
            code_info
        )

        if JINJA2_AVAILABLE and self.template:
            # Jinja2 ile render
            return self.template.render(**template_data)
        else:
            # Basit string format (Jinja2 yoksa)
            return self._simple_render(template_data)

    def _prepare_template_data(self,
                               verification_report: VerificationReport,
                               metrics_report: MetricsReport,
                               code_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Şablon için veri hazırlar.

        Args:
            verification_report: Doğrulama raporu
            metrics_report: Metrik raporu
            code_info: Kod bilgileri

        Returns:
            Şablon verisi sözlüğü
        """
        # Halüsinasyonları dönüştür
        hallucinations = []
        for h in verification_report.hallucinations:
            hallucinations.append({
                "claim": {
                    "text": h.claim.text,
                    "claim_type": h.claim.claim_type.value,
                    "subject": h.claim.subject,
                    "object": h.claim.object
                },
                "reason": h.reason,
                "subject_match": {
                    "code_entity": h.subject_match.code_entity if h.subject_match else None
                } if h.subject_match else None,
                "object_match": {
                    "code_entity": h.object_match.code_entity if h.object_match else None
                } if h.object_match else None
            })

        # Tüm detayları dönüştür
        all_details = []
        for d in verification_report.details:
            all_details.append({
                "claim": {
                    "text": d.claim.text,
                    "claim_type": d.claim.claim_type.value
                },
                "result": d.result.value,
                "confidence": d.confidence
            })

        # Metrikleri dönüştür
        metrics = []
        for m in metrics_report.metrics:
            metrics.append({
                "name": m.name,
                "value": m.value,
                "description": m.description,
                "details": m.details
            })

        # Claim türü istatistikleri
        type_metric = metrics_report.get_metric("claim_type_breakdown")
        claim_type_labels = []
        claim_type_totals = []
        if type_metric and isinstance(type_metric.details, dict):
            for claim_type, stats in type_metric.details.items():
                if isinstance(stats, dict):
                    claim_type_labels.append(claim_type)
                    claim_type_totals.append(stats.get("total", 0))

        return {
            "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": metrics_report.summary,
            "verification_summary": verification_report.summary,
            "hallucinations": hallucinations,
            "all_details": all_details,
            "metrics": metrics,
            "recommendations": metrics_report.recommendations,
            "claim_type_labels": claim_type_labels,
            "claim_type_totals": claim_type_totals,
            "code_info": code_info or {}
        }

    def _simple_render(self, data: Dict[str, Any]) -> str:
        """
        Jinja2 olmadan basit HTML oluşturur.

        Args:
            data: Şablon verisi

        Returns:
            Basit HTML string
        """
        # Basit bir HTML şablonu (Jinja2 yoksa)
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>LLM Doğrulama Raporu</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 2rem; }}
        .header {{ background: #667eea; color: white; padding: 2rem; }}
        .metric {{ display: inline-block; margin: 1rem; padding: 1rem; border: 1px solid #ddd; }}
        .hallucination {{ background: #fff5f5; border-left: 4px solid red; padding: 1rem; margin: 1rem 0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
        th {{ background: #343a40; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>LLM Doğrulama Raporu</h1>
        <p>Oluşturulma: {data['generation_time']}</p>
    </div>

    <h2>Genel Değerlendirme: {data['summary'].get('overall_assessment', 'N/A')}</h2>

    <div class="metrics">
        <div class="metric">
            <h3>Halüsinasyon Oranı</h3>
            <p>{data['summary'].get('hallucination_rate', 0)*100:.1f}%</p>
        </div>
        <div class="metric">
            <h3>Geçerlilik Oranı</h3>
            <p>{data['summary'].get('validity_rate', 0)*100:.1f}%</p>
        </div>
        <div class="metric">
            <h3>Toplam İddia</h3>
            <p>{data['summary'].get('total_claims', 0)}</p>
        </div>
    </div>

    <h2>Halüsinasyonlar ({len(data['hallucinations'])} adet)</h2>
"""

        for i, h in enumerate(data['hallucinations'], 1):
            html += f"""
    <div class="hallucination">
        <h4>#{i} - {h['claim']['claim_type']}</h4>
        <p><strong>İddia:</strong> {h['claim']['text']}</p>
        <p><strong>Sebep:</strong> {h['reason']}</p>
    </div>
"""

        html += """
    <h2>Tüm İddialar</h2>
    <table>
        <tr>
            <th>#</th>
            <th>Tür</th>
            <th>İddia</th>
            <th>Sonuç</th>
            <th>Güven</th>
        </tr>
"""

        for i, d in enumerate(data['all_details'], 1):
            html += f"""
        <tr>
            <td>{i}</td>
            <td>{d['claim']['claim_type']}</td>
            <td>{d['claim']['text'][:50]}...</td>
            <td>{d['result']}</td>
            <td>{d['confidence']*100:.0f}%</td>
        </tr>
"""

        html += """
    </table>

    <h2>Öneriler</h2>
    <ul>
"""
        for rec in data['recommendations']:
            html += f"        <li>{rec}</li>\n"

        html += """
    </ul>

    <footer style="margin-top: 2rem; padding: 1rem; background: #343a40; color: white; text-align: center;">
        <p>Graph-Grounded Verification of LLM Reasoning</p>
        <small>Selen Erdoğan - Gebze Teknik Üniversitesi</small>
    </footer>
</body>
</html>
"""
        return html

    def save_report(self, html: str, output_path: str):
        """
        HTML raporunu dosyaya kaydeder.

        Args:
            html: HTML içeriği
            output_path: Çıktı dosya yolu
        """
        # Dizin yoksa oluştur
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Dosyaya yaz
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✅ Rapor kaydedildi: {output_path}")

    def generate_and_save(self,
                         verification_report: VerificationReport,
                         metrics_report: MetricsReport,
                         output_path: str,
                         code_info: Optional[Dict[str, Any]] = None):
        """
        Raporu oluşturur ve kaydeder (tek adımda).

        Args:
            verification_report: Doğrulama raporu
            metrics_report: Metrik raporu
            output_path: Çıktı dosya yolu
            code_info: Kod bilgileri
        """
        html = self.generate_report(verification_report, metrics_report, code_info)
        self.save_report(html, output_path)


# =============================================================================
# TEST KODU
# =============================================================================
if __name__ == "__main__":
    from .verifier import VerificationReport, VerificationDetail, VerificationResult
    from .metrics import MetricsReport, MetricResult
    from .claim_extractor import Claim, ClaimType

    # Test verisi
    test_details = [
        VerificationDetail(
            claim=Claim("main calls process_data", ClaimType.CALL, "main", "process_data", "calls", source_step=1),
            result=VerificationResult.VALID,
            confidence=0.95,
            reason="Doğrulandı"
        ),
        VerificationDetail(
            claim=Claim("process_data calls add", ClaimType.CALL, "process_data", "add", "calls", source_step=2),
            result=VerificationResult.VALID,
            confidence=0.85,
            reason="Doğrulandı"
        ),
        VerificationDetail(
            claim=Claim("main calls save_result", ClaimType.CALL, "main", "save_result", "calls", source_step=3),
            result=VerificationResult.HALLUCINATION,
            confidence=0.9,
            reason="save_result fonksiyonu kodda yok"
        ),
    ]

    verif_report = VerificationReport(
        details=test_details,
        summary={
            "total_claims": 3,
            "valid_count": 2,
            "hallucination_count": 1,
            "unverifiable_count": 0,
            "partially_valid_count": 0
        },
        hallucinations=[d for d in test_details if d.is_hallucination()]
    )

    metrics_report = MetricsReport(
        metrics=[
            MetricResult("hallucination_rate", 0.33, "Halüsinasyon oranı"),
            MetricResult("validity_rate", 0.67, "Geçerlilik oranı"),
            MetricResult("coverage", 0.75, "Kapsam"),
        ],
        summary={
            "overall_assessment": "ORTA",
            "hallucination_rate": 0.33,
            "validity_rate": 0.67,
            "total_claims": 3,
            "hallucination_count": 1
        },
        recommendations=[
            "⚠️ Orta düzeyde halüsinasyon oranı. Kritik kararlar için manuel doğrulama yapın.",
            "📊 Kapsam iyi seviyede."
        ]
    )

    # Rapor oluştur
    reporter = HTMLReporter()
    reporter.generate_and_save(
        verif_report,
        metrics_report,
        "/tmp/test_report.html",
        {"filename": "test.py"}
    )
