# Diyabetik Retinopati Analizi için Derin Öğrenme Tabanlı Çoklu Görev Sistemi

**EEM0458 Görüntü İşleme Projesi - Bursa Teknik Üniversitesi - 2025/2026 Bahar Dönemi**

Bu proje fundus (göz dibi) görüntülerinden diyabetik retinopati (DR) şiddet sınıflandırması ve lezyon segmentasyonu yapan iki aşamalı bir derin öğrenme sistemidir.

---

## Özet

Diyabetik retinopati, dünya genelinde çalışma yaşındaki yetişkinlerde görme kaybının başlıca nedenlerinden biridir. Erken teşhis edildiğinde tedavi şansı yüksek olduğundan, otomatik tarama sistemleri klinik uygulamada önemli bir yere sahiptir.

Bu projede şu üç ana modül geliştirilmiştir:
1. **5-sınıflı DR şiddet sınıflandırması** (No DR, Mild, Moderate, Severe, PDR) — EfficientNet-B3
2. **4 lezyon tipi piksel-düzeyinde segmentasyonu** (MA, HE, EX, SE) — U-Net + EfficientNet-B0 encoder
3. **Grad-CAM++ ile karar açıklanabilirliği**

## Sonuçlar

### Sınıflandırma (APTOS 2019 + IDRiD)
| Metrik | APTOS Val | IDRiD External Test |
|---|---|---|
| Accuracy | 0.808 | 0.214 |
| F1-Macro | 0.656 | 0.156 |
| **Kappa (quad.)** | **0.885** | 0.146 |

Internal validation sonucu APTOS 2019 Kaggle yarışmasında üst %10'a denk gelen performansı temsil eder. External test seti sonuçları domain shift problemini açıkça ortaya koymaktadır.

### Segmentasyon (IDRiD)
| Lezyon | Dice | IoU |
|---|---|---|
| Sert Eksuda (EX) | 0.593 | 0.422 |
| Kanama (HE) | 0.463 | 0.301 |
| Yumuşak Eksuda (SE) | 0.402 | 0.252 |
| Mikroanevrizma (MA) | 0.000 | 0.000 |
| **Ortalama (MA hariç)** | **0.486** | **0.325** |

Mikroanevrizma segmentasyonunun başarısızlığı 512×512 çözünürlükte küçük lezyonların yok olmasından kaynaklanmaktadır. Bu sınırlama rapor içinde detaylı şekilde tartışılmıştır.

## Proje Yapısı

```
DR_Project/
├── notebooks/
│   ├── 01_eda.ipynb                    # Keşifsel veri analizi
│   ├── 02_preprocessing.ipynb          # Ön işleme + train/val split
│   ├── 03_train_classifier.ipynb       # EfficientNet-B3 eğitimi + fine-tune
│   ├── 04_train_segmenter.ipynb        # U-Net eğitimi
│   ├── 05_gradcam.ipynb                # Grad-CAM++ analizi
│   └── 06_demo.ipynb                   # Gradio web demo (opsiyonel)
├── src/
│   ├── preprocessing.py                # Fundus crop + CLAHE + resize
│   ├── dataset.py                      # PyTorch Dataset + augmentation
│   ├── seg_dataset.py                  # Segmentasyon Dataset
│   ├── models.py                       # timm tabanlı classifier
│   ├── seg_models.py                   # smp tabanlı U-Net
│   ├── train_utils.py                  # Eğitim/evaluation helpers
│   └── seg_train_utils.py
├── reports/
│   ├── figures/                        # 15+ rapor figürü (PNG)
│   ├── classifier_final_metrics.json
│   ├── classifier_history.json
│   ├── segmenter_final_metrics.json
│   └── segmenter_history.json
├── generate_report.py                  # Word rapor üreticisi
├── Rapor.docx                          # Final rapor (Türkçe)
└── README.md
```

## Kurulum ve Kullanım

### Gereksinimler
- Python 3.10+
- CUDA destekli GPU (T4, A100 veya benzeri)
- 16 GB+ VRAM önerilir

### Kütüphaneler
```bash
pip install torch torchvision timm segmentation-models-pytorch
pip install albumentations opencv-python Pillow pandas numpy
pip install scikit-learn matplotlib tqdm
pip install grad-cam python-docx
```

### Veri Setleri
- [APTOS 2019 Blindness Detection](https://www.kaggle.com/competitions/aptos2019-blindness-detection) — 3.662 fundus görüntüsü
- [IDRiD Dataset](https://www.kaggle.com/datasets/aaryapatel98/indian-diabetic-retinopathy-image-dataset) — 81 segmentasyon + 516 sınıflandırma

Veri setlerini indirip `datasets/` klasörüne yerleştirin.

### Notebook Çalıştırma Sırası
1. `01_eda.ipynb` — veri keşfi
2. `02_preprocessing.ipynb` — ön işleme + split
3. `03_train_classifier.ipynb` — sınıflandırıcı eğitimi
4. `04_train_segmenter.ipynb` — segmentasyon eğitimi
5. `05_gradcam.ipynb` — açıklanabilirlik analizi

## Teknik Detaylar

### Eğitim Hiperparametreleri
| Parametre | Sınıflandırma | Segmentasyon |
|---|---|---|
| Model | EfficientNet-B3 | U-Net + EfficientNet-B0 |
| Parametre | 10.7M | 6.25M |
| Girdi Boyutu | 384×384 | 512×512 |
| Batch Size | 32 | 4 |
| Epoch | 20 | 60 |
| Optimizer | AdamW | AdamW |
| LR | 3e-4 | 1e-4 |
| Scheduler | Cosine + Warmup | Cosine + Warmup |
| Loss | Weighted CE + Label Smoothing | BCE + Dice |
| Eğitim Süresi | ~21 dk (T4) | ~63 dk (T4) |

### Ön İşleme Pipeline
1. **Fundus crop** — Ben Graham (Kaggle 2015) yöntemi
2. **CLAHE** — LAB renk uzayında L kanalına (clipLimit=2.0)
3. **Zero-padded square resize** — 384×384 veya 512×512
4. **ImageNet normalize** — mean/std

## Sınırlılıklar

Bu proje akademik bir lisans projesidir ve aşağıdaki sınırlılıkları açıkça raporlamaktadır:

1. **Domain Shift**: APTOS-IDRiD arasında performans %50+ düşüş gösterdi. Klinik kullanım için domain adaptation teknikleri (adversarial training, MMD loss) gereklidir.
2. **Mikroanevrizma Çözünürlüğü**: 4288×2848'den 512×512'ye küçültme MA lezyonlarını yok ediyor. Patch-tabanlı eğitim (1024×1024+) ve A100/A6000 sınıfı donanım gerektiriyor.
3. **Donanım**: Google Colab T4 ile geliştirildi. Profesyonel donanım (saatlik 2-5 USD bulut veya 5-15K USD lokal) tam performans için gerekli.

Detaylar `Rapor.docx` Bölüm 5'te tartışılmıştır.

## Lisans

MIT License — eğitim ve araştırma amaçlı serbest kullanım.

## Yazar

**Can Tekin**
Bursa Teknik Üniversitesi - Elektrik Elektronik Mühendisliği
[GitHub](https://github.com/cantekinn)

## Referanslar

Rapor içinde 13 akademik kaynak (IEEE format) yer almaktadır. Ana referanslar:
- Gulshan et al. (2016), JAMA — Google'ın DR detection çalışması
- Porwal et al. (2018), Data — IDRiD dataset
- Tan & Le (2019), ICML — EfficientNet
- Ronneberger et al. (2015), MICCAI — U-Net
- Selvaraju et al. (2017), ICCV — Grad-CAM

---

*Bu sistem akademik bir prototiptir, klinik tanı için kullanılamaz.*
