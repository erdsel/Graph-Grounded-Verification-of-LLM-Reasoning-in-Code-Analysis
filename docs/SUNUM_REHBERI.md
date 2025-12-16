# Sunum Rehberi

## Sunum Dosyalari

Sunumunuz icin asagidaki dosyalari hazirlayin:

### 1. PowerPoint/Google Slides (presentation.pptx)

**Slide 1: Kapak**
- Proje Adi: Graph-Grounded Verification of LLM Reasoning in Code Analysis
- Ogrenci: Selen Erdogan (210104004131)
- Ders: NLP - Gebze Teknik Universitesi
- Tarih

**Slide 2: Problem Tanimi (2 dakika)**
- LLM'ler kod analizi yaparken "halusinasyon" uretebilir
- Halusinasyon: Modelin var olmayan seyler uydurması
- Ornek: "main fonksiyonu save_data'yi cagiriyor" (aslinda cagiRMIYOR)
- Neden onemli? Guvenilir AI asistanlari icin kritik

**Slide 3: Cozum Yaklasimi (2 dakika)**
- Graf tabanli dogrulama sistemi
- Ground Truth: AST ile gercek kod yapisi
- LLM Analizi: Modelin kod hakkindaki iddialari
- Karsilastirma: Iddialarin dogrulanmasi

**Slide 4: Sistem Mimarisi (3 dakika)**
- PlantUML diyagrami ekle (architecture.puml'dan)
- Iki paralel pipeline goster:
  1. AST -> Graph Builder -> Call Graph
  2. LLM -> Claim Extractor -> Claims
- Verifier'da birlesme

**Slide 5: Teknoloji Stacki (2 dakika)**
| Katman | Teknoloji |
|--------|-----------|
| AST Analizi | Python ast module |
| Graf | NetworkX |
| LLM | Groq (Llama 3.3 70B) |
| Web | Flask + vis.js |
| String Match | FuzzyWuzzy |

**Slide 6: AST Analizi Detayi (3 dakika)**
- AST (Abstract Syntax Tree) nedir?
- Python ast module kullanimi
- Ornek kod ve AST ciktisi
- Call graph cikarimi

**Slide 7: LLM Entegrasyonu (3 dakika)**
- Prompt Engineering
- Strict JSON format
- "SIRALI CALISMA != CAGRI" kurali
- Groq API kullanimi

**Slide 8: Dogrulama Sureci (3 dakika)**
- Entity Mapping: LLM ismini kod ismine esle
- Graf Sorgulama: Kenar var mi?
- Sonuc Siniflandirmasi:
  - VALID (dogru)
  - HALLUCINATION (yanlis)
  - UNVERIFIABLE (dogrulanamaz)

**Slide 9: Metrikler (2 dakika)**
```
Precision = TP / (TP + FP)
Recall = TP / (TP + FN)
F1 = 2 * P * R / (P + R)
Hallucination Rate = Halusinasyon / Toplam
```

**Slide 10: Demo (5 dakika)**
- Canli demo goster
- Basit kod ornegi ile baslat
- Sonuclari yorumla
- Graf gorsellestirmeyi goster

**Slide 11: Test Sonuclari (2 dakika)**
- Tablo: Farkli kod ornekleri icin metrikler
- Grafik: LLM karsilastirmasi
- Basari oranlari

**Slide 12: Zorluklar ve Sinirlamalar (2 dakika)**
- Dinamik cagrilar (eval, getattr)
- Karmasik decorator pattern'lar
- Lambda ifadeleri
- Rate limit sorunlari

**Slide 13: Gelecek Calisma (1 dakika)**
- Daha fazla LLM desteji
- Dinamik analiz
- Benchmark dataset
- Buyuk kod tabanlari

**Slide 14: Sonuc (1 dakika)**
- Onerilen sistem LLM halusinasyonlarini tespit edebiliyor
- Graf tabanli yaklasim etkili
- Pratik uygulama: Guvenilir AI kod asistanlari

**Slide 15: Sorular**
- Tesekkurler
- Sorulariniz?

---

## Sunum Ipuclari

### Demo Icin Hazirlik

1. **Sunumdan once:**
   ```bash
   cd nlp-proje
   python app.py
   ```

2. **Demo sirasinda kullanilacak kodlar:**

   **Basit Ornek (Basarili):**
   ```python
   def add(a, b):
       return a + b

   def calculate(x, y):
       result = add(x, y)
       return result

   print(calculate(5, 3))
   ```

   **Halusinasyon Ornegi:**
   ```python
   def process():
       data = get_input()  # Bu fonksiyon YOK!
       return data
   ```

### Soru-Cevap Icin Hazirlik

**Olasi Sorular:**

1. **"Neden AST kullandiniz?"**
   - Statik analiz icin standart yontem
   - Python'un built-in destegi
   - Dogruluk garantisi (compile-time bilgi)

2. **"LLM neden hata yapiyor?"**
   - Training data'dan gelen bias
   - Sirali calisma vs cagri karisikligi
   - Doğal dil belirsizligi

3. **"Baska dillere uygulanabilir mi?"**
   - Evet, AST yaklasimi dil bagimsiz
   - Her dil icin parser yazilmali
   - Temel mimari ayni kalir

4. **"Gercek projelerde nasil kullanilir?"**
   - CI/CD pipeline entegrasyonu
   - Code review asistan
   - IDE eklentisi

---

## PlantUML Diyagramlarini Goruntuleme

### Online (Onerilen)
1. https://www.plantuml.com/plantuml/uml/ adresine git
2. `docs/architecture.puml` icerigini yapistir
3. PNG/SVG olarak indir
4. Sunuma ekle

### VS Code Eklentisi
1. "PlantUML" eklentisini kur
2. .puml dosyasini ac
3. Alt+D ile onizle
4. Export et

### Komut Satiri
```bash
# Java gerekli
java -jar plantuml.jar docs/architecture.puml
```

---

## Sunum Suresi Dagilimi

| Bolum | Sure |
|-------|------|
| Giris ve Problem | 4 dk |
| Sistem Mimarisi | 5 dk |
| Teknik Detaylar | 8 dk |
| Demo | 5 dk |
| Sonuclar | 3 dk |
| **Toplam** | **25 dk** |

---

## Kontrol Listesi

- [ ] Python environment calisir durumda
- [ ] Flask sunucusu baslatildi
- [ ] Ornek kodlar hazir
- [ ] PlantUML diyagramlari PNG'ye donusturuldu
- [ ] Sunum dosyasi tamamlandi
- [ ] Demo senaryosu prova edildi
- [ ] Backup plan hazir (video kaydi)

---

## Kaynaklar

Sunumda referans verilecek kaynaklar:

1. Pan, L. et al. (2023). "Fact-Checking Complex Claims with Program-Guided Reasoning" - ACL
2. Mundler, N. et al. (2023). "Self-contradictory Hallucinations of Large Language Models" - EMNLP
3. Python AST Documentation
4. NetworkX Graph Library
5. Groq API Documentation
