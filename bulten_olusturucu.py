import os
import re
import json
from anthropic import Anthropic
from datetime import datetime
from langchain_anthropic import ChatAnthropic
from langchain_tavily import TavilySearch
from langgraph.prebuilt import create_react_agent
import warnings
warnings.filterwarnings("ignore")

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from dotenv import load_dotenv
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TAVILY_API_KEY    = os.getenv("TAVILY_API_KEY")
CIKTI_KLASORU     = os.path.join(os.path.expanduser("~"), "Documents", "Bultenler")

if not ANTHROPIC_API_KEY or not TAVILY_API_KEY:
    raise ValueError(
        "API anahtarları bulunamadı! Yerel çalıştırıyorsanız .env dosyanızı, "
        "Hugging Face Spaces'te çalıştırıyorsanız Settings > Secrets bölümünü kontrol edin."
    )



# TÜRKÇE FONT


def font_kaydet():
    """
    Türkçe karakter destekli font kaydeder. macOS, Linux ve Windows
    yollarını sırayla dener. Hiçbir TTF bulunamazsa Reportlab'ın
    dahili Helvetica fontuna düşer (Türkçe karakterler bozuk görünür
    ama PDF üretimi KeyError ile ÇÖKMEZ).

    Dönüş: (normal_font_adi, bold_font_adi)
    """
    font_adaylari = [
        
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/opt/homebrew/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        # macOS
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
    ]
    font_bold_adaylari = [
        
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/opt/homebrew/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/local/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
     
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\calibrib.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\tahomabd.ttf",
    ]

    normal_font = None
    for yol in font_adaylari:
        if os.path.exists(yol):
            try:
                pdfmetrics.registerFont(TTFont("TurkceFont", yol))
                normal_font = "TurkceFont"
                break
            except Exception:
                continue

    bold_font = None
    for yol in font_bold_adaylari:
        if os.path.exists(yol):
            try:
                pdfmetrics.registerFont(TTFont("TurkceFont-Bold", yol))
                bold_font = "TurkceFont-Bold"
                break
            except Exception:
                continue

    if normal_font is None:
        print("⚠️  Türkçe destekli font bulunamadı, Helvetica'ya düşülüyor "
              "(ş/ğ/ı/ö/ü/ç karakterleri bozuk görünebilir). PDF yine de üretilecek.")
        normal_font = "Helvetica"

    if bold_font is None:
        bold_font = "Helvetica-Bold"

    
    pdfmetrics.registerFontFamily(
        normal_font,
        normal=normal_font,
        bold=bold_font,
        italic=normal_font,
        boldItalic=bold_font,
    )

    return normal_font, bold_font



# Haberleri Toplama

def haberleri_topla_ve_bulten_olustur():
    """
    Haberleri toplar ve bülten metnini üretir.
    
    İki aşamalı otonom süreç:
    1. Keşif aşaması: Agent bu ayın gündemini kendisi araştırır,
       hangi konuların öne çıktığına karar verir.
    2. Derinleştirme aşaması: Agent kendi kararına dayanarak
       özelleştirilmiş sorgular üretir ve 20 haberi toplar.
    """
    os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    os.environ["TAVILY_API_KEY"]    = TAVILY_API_KEY

    print("Ajan baslatiliyor...")
    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.3, max_tokens=8192)
    search_tool = TavilySearch(max_results=10)
    agent = create_react_agent(llm, [search_tool])

    bugun = datetime.now()
    ay_adi_tr = {
        1:"Ocak", 2:"Subat", 3:"Mart", 4:"Nisan", 5:"Mayis", 6:"Haziran",
        7:"Temmuz", 8:"Agustos", 9:"Eylul", 10:"Ekim", 11:"Kasim", 12:"Aralik"
    }
    ay_str = f"{ay_adi_tr[bugun.month]} {bugun.year}"

    #  Faz 1: Agent bu ayın gündemini araştırırız
    print("Asama 1/2: Gundem kesfi yapiliyor...")

    kesif_sorgusu = f"""
Sen bir sigorta ve teknoloji analistisin. Bugun {bugun.strftime('%d.%m.%Y')}.

GOREV: {ay_str} ayinin en onemli gelismelerini kesfetmek.

Asagidaki 4 aramayı yap ve sonuclari analiz et:
1. "insurance technology news {ay_str}"
2. "insurtech AI developments {ay_str}"
3. "artificial intelligence breakthroughs {ay_str}"
4. "tech industry news {ay_str}"

Aramalari yaptiktan sonra SADECE su formati kullanarak cevap ver, baska hicbir sey yazma:

SIGORTA_KONULAR: [virgülle ayrilmis, bu ay one cikan 3-4 sigorta/insurtech konusu]
TEKNOLOJI_KONULAR: [virgülle ayrilmis, bu ay one cikan 3-4 teknoloji konusu]
SIGORTA_SORGULAR: [virgülle ayrilmis, 5 adet ozellesmis arama sorgusu - Ingilizce]
TEKNOLOJI_SORGULAR: [virgülle ayrilmis, 5 adet ozellesmis arama sorgusu - Ingilizce]

Ornek format:
SIGORTA_KONULAR: insurtech AI funding, claims automation, cyber insurance growth
TEKNOLOJI_KONULAR: GPT-5 release, chip shortage, EU AI Act
SIGORTA_SORGULAR: "insurtech AI investment June 2026", "AI claims processing 2026"
TEKNOLOJI_SORGULAR: "GPT-5 capabilities 2026", "Nvidia H200 availability 2026"
"""

    kesif_yaniti = agent.invoke({"messages": [{"role": "user", "content": kesif_sorgusu}]})
    kesif_metni = kesif_yaniti["messages"][-1].content
    print("Gundem kesfi tamamlandi.")

    # Keşif metninden sorguları parse et
    sigorta_sorgular = []
    teknoloji_sorgular = []

    for satir in kesif_metni.split("\n"):
        satir = satir.strip()
        if satir.startswith("SIGORTA_SORGULAR:"):
            deger = satir.replace("SIGORTA_SORGULAR:", "").strip()
            sigorta_sorgular = [s.strip().strip('"') for s in deger.split(",") if s.strip()]
        elif satir.startswith("TEKNOLOJI_SORGULAR:"):
            deger = satir.replace("TEKNOLOJI_SORGULAR:", "").strip()
            teknoloji_sorgular = [s.strip().strip('"') for s in deger.split(",") if s.strip()]

    # parse başarısız olursa sabit sorgular kullanırız
    if not sigorta_sorgular:
        sigorta_sorgular = [
            f"insurance technology AI {ay_str}",
            f"insurtech artificial intelligence {ay_str}",
            "insurance digitalization innovation 2026",
            "AI claims processing insurance 2026",
            "insurtech startup funding 2026",
        ]
    if not teknoloji_sorgular:
        teknoloji_sorgular = [
            f"new AI model release {ay_str}",
            f"artificial intelligence news {ay_str}",
            "tech company announcement 2026",
            "semiconductor chip AI 2026",
            "AI regulation 2026",
        ]

    sigorta_sorgu_listesi = "\n".join(
        [f'{i+1}. "{s}"' for i, s in enumerate(sigorta_sorgular[:6])]
    )
    teknoloji_sorgu_listesi = "\n".join(
        [f'{i+1}. "{s}"' for i, s in enumerate(teknoloji_sorgular[:6])]
    )

    # Faz 2: Agent kendi ürettiği sorgularla haberleri toplar 
    print("Asama 2/2: Haberler toplanıyor (4-6 dakika)...")

    sorgu = f"""
Sen bir sigorta ve teknoloji analistisin. Gorev: {ay_str} ayina ait son 30 gunun haberlerini toplayarak profesyonel bir bulten olusturmak.

Bu ay one cikan konulari kesfettin. Simdi bu konulara odakli haberler toplayacaksin.

ONEMLI: Her kategoride TAM OLARAK 10 (on) haber olmali.

KATEGORI 1: SIGORTA & TEKNOLOJI HABERLERI (10 HABER)
Bu ayi One cikan konular temel alinarak olusturulan sorgular:
{sigorta_sorgu_listesi}

KATEGORI 2: TEKNOLOJI HABERLERI (10 HABER)
Bu ayi one cikan konular temel alinarak olusturulan sorgular:
{teknoloji_sorgu_listesi}

---
ONEMLI FORMAT KURALI: Haberleri ASLA numaralandirma.
Her haber icin MUTLAKA su formati kullan:

BASLIK: [haberin tam basligi]
OZET: [2-3 cumle ozet]
ONEM: [neden onemli oldugu]
KAYNAK: [kaynak adi]
TARIH: [yayin tarihi]
URL: [haberin tam URL adresi]

---
Bulteni su yapida olustur:

## KATEGORI 1: SIGORTA & TEKNOLOJI HABERLERI

[10 haber]

## KATEGORI 2: TEKNOLOJI HABERLERI

[10 haber]

## EDITOR NOTU

[Bu ayin one cikan trendleri ve her iki kategorinin ozet degerlendirmesi, 2-3 paragraf]

Kritik: Her kategoride tam 10 haber olmali. URL'leri kesinlikle atlama.
"""

    response = agent.invoke({"messages": [{"role": "user", "content": sorgu}]})
    bulten_metni = response["messages"][-1].content
    print("Bulten icerigi olusturuldu.")
    return bulten_metni




# Faz 3 : Değerlendirme


def bulten_ozetle(bulten_metni: str) -> str:
    """
    Evaluation için bülten metninden sadece başlık, kaynak,
    tarih ve URL satırlarını çıkarır. Token limitine takılmamak için.
    """
    satirlar = bulten_metni.split("\n")
    ozet_satirlar = []
    for satir in satirlar:
        satir = satir.strip()
        if satir.startswith("##") or re.match(r"^(\d+\.\s*)?(BASLIK|KAYNAK|TARIH|URL):", satir):
            ozet_satirlar.append(satir)
    return "\n".join(ozet_satirlar)


def evaluation_yap(bulten_metni: str) -> dict:
    """
    Üretilen bülten metnini Claude ile değerlendirir.
    Her haber için 0-10 puan verir, GECTI/KALDI kararı üretir.
    """
    print("\n📊 Evaluation başlatılıyor...")

    client = Anthropic()

    
    ozet = bulten_ozetle(bulten_metni)

    sistem_prompt = """Sen bir haber kalite değerlendirme uzmanısın.
Sana bir sigorta ve teknoloji bülteninin özeti verilecek (başlık, kaynak, tarih, URL).
Her haberi 4 kritere göre puanla ve sonucu SADECE JSON olarak döndür.

Puanlama kriterleri (her biri 0-10 arası):
1. url_puan: Geçerli bir URL var mı? (0=yok, 5=var ama şüpheli, 10=açık ve tam URL var)
2. tarih_puan: Tarih son 30 gün içinde mi? (0=yok/eski, 5=yaklaşık, 10=açık ve güncel)
3. kategori_puan: Haber başlığına göre doğru kategoride mi? (0=yanlış, 10=uygun)
4. icerik_puan: Başlık anlamlı ve konuyla ilgili mi? (0=anlamsız, 10=net ve ilgili)

Genel karar: ortalama >= 7 → "GECTI", ortalama < 7 → "KALDI"

SADECE şu JSON formatını döndür, başka hiçbir şey yazma:
{
  "haberler": [
    {
      "baslik": "haberin başlığı",
      "kategori": "SIGORTA & TEKNOLOJI veya TEKNOLOJI",
      "url_puan": 8,
      "tarih_puan": 7,
      "kategori_puan": 9,
      "icerik_puan": 8,
      "ortalama": 8.0,
      "karar": "GECTI",
      "not": "kısa açıklama"
    }
  ],
  "genel_ortalama": 8.0,
  "gecen_haber_sayisi": 18,
  "kalan_haber_sayisi": 2,
  "genel_karar": "GECTI"
}"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8000,
        system=sistem_prompt,
        messages=[
            {"role": "user", "content": f"Şu bülten özetini değerlendir:\n\n{ozet}"}
        ]
    )

    ham_yanit = response.content[0].text.strip()

    try:
        if "```" in ham_yanit:
            ham_yanit = ham_yanit.split("```")[1]
            if ham_yanit.startswith("json"):
                ham_yanit = ham_yanit[4:]
        sonuc = json.loads(ham_yanit)
    except json.JSONDecodeError as e:
        print(f"⚠️  Evaluation JSON parse hatası: {e}")
        print(f"⚠️  Ham yanıtın son 300 karakteri: ...{ham_yanit[-300:]}")
        sonuc = {
            "haberler": [],
            "genel_ortalama": 0,
            "gecen_haber_sayisi": 0,
            "kalan_haber_sayisi": 0,
            "genel_karar": "KALDI"
        }

    print(f"\n{'─'*50}")
    print(f"  📋 EVALUATİON SONUCU")
    print(f"{'─'*50}")
    for h in sonuc.get("haberler", []):
        durum = "✅" if h.get("karar") == "GECTI" else "❌"
        print(f"  {durum} [{h.get('ortalama', 0):.1f}/10] {h.get('baslik', '')[:55]}...")
    print(f"{'─'*50}")
    print(f"  Genel Ortalama : {sonuc.get('genel_ortalama', 0):.1f}/10")
    print(f"  Geçen Haberler : {sonuc.get('gecen_haber_sayisi', 0)}")
    print(f"  Kalan Haberler : {sonuc.get('kalan_haber_sayisi', 0)}")
    print(f"  Genel Karar    : {sonuc.get('genel_karar', '?')}")
    print(f"{'─'*50}\n")

    return sonuc



# YENİLEME — KALAN HABERLERİ TEKRAR ARA


def haberler_yenile(bulten_metni: str, evaluation_sonuc: dict) -> str:
    """Evaluation'da KALDI denen haberleri yeniler."""
    kalan_haberler = [
        h for h in evaluation_sonuc.get("haberler", [])
        if h.get("karar") == "KALDI"
    ]

    if not kalan_haberler:
        print("✅ Tüm haberler geçti, yenileme gerekmiyor.")
        return bulten_metni

    print(f"🔄 {len(kalan_haberler)} haber KALDI, yenileniyor...")

    llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.3, max_tokens=2048)
    search_tool = TavilySearch(max_results=5)
    agent = create_react_agent(llm, [search_tool])

    yenileme_sonuclari = []
    for haber in kalan_haberler:
        baslik = haber.get("baslik", "")
        kategori = haber.get("kategori", "")
        neden = haber.get("not", "kalite düşük")
        print(f"  🔍 Yenileniyor: {baslik[:50]}...")

        sorgu = f"""
Şu haber kalite değerlendirmesinden geçemedi: "{baslik}"
Neden geçemedi: {neden}

Kategori: {kategori}
Görev: Bu haberin yerine aynı kategoride, son 30 gün içinde yayınlanmış,
geçerli URL'si olan, kaliteli bir haber bul.

Format:
BASLIK: [tam başlık]
OZET: [2-3 cümle]
ONEM: [neden önemli]
KAYNAK: [kaynak adı]
TARIH: [yayın tarihi]
URL: [tam URL]
"""
        response = agent.invoke({"messages": [{"role": "user", "content": sorgu}]})
        yeni_haber = response["messages"][-1].content
        yenileme_sonuclari.append(f"\n[YENİLENDİ - {kategori}]\n{yeni_haber}")

    ek = "\n\n## YENİLENEN HABERLER\n" + "\n".join(yenileme_sonuclari)
    return bulten_metni + ek



# PDF'E kalite raporu ekleme

def kalite_raporu_ekle(hikaye, evaluation_sonuc, doc, YN="Helvetica", YB="Helvetica-Bold"):
    """PDF'e Kalite Raporu sayfası ekler."""
    LACIVERT  = colors.HexColor("#1A2C5B")
    YESIL     = colors.HexColor("#1A6B3C")
    KIRMIZI   = colors.HexColor("#B91C1C")
    GRI       = colors.HexColor("#F2F4F8")
    KOYU_GRI  = colors.HexColor("#6B7280")
    YAZI      = colors.HexColor("#1C1C1C")

    s_bolum_baslik = ParagraphStyle("BB", fontName=YB, fontSize=15,
                                    textColor=colors.white, alignment=TA_LEFT,
                                    leading=20, leftIndent=10)
    s_tablo_baslik = ParagraphStyle("TB", fontName=YB, fontSize=8.5,
                                    textColor=colors.white)
    s_tablo_icerik = ParagraphStyle("TI", fontName=YN, fontSize=8.5,
                                    textColor=YAZI, leading=12)
    s_ozet_bold    = ParagraphStyle("OZB", fontName=YB, fontSize=9.5,
                                    textColor=LACIVERT, leading=14)

    hikaye.append(Spacer(1, 0.6*cm))
    baslik_veri = [[Paragraph("KALİTE DEĞERLENDİRME RAPORU", s_bolum_baslik)]]
    baslik_tablo = Table(baslik_veri, colWidths=[doc.width])
    baslik_tablo.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LACIVERT),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
    ]))
    hikaye.append(baslik_tablo)
    hikaye.append(Spacer(1, 0.3*cm))

    genel_ort = evaluation_sonuc.get("genel_ortalama", 0)
    gecen     = evaluation_sonuc.get("gecen_haber_sayisi", 0)
    kalan     = evaluation_sonuc.get("kalan_haber_sayisi", 0)
    karar     = evaluation_sonuc.get("genel_karar", "?")
    karar_renk = YESIL if karar == "GECTI" else KIRMIZI

    ozet_veri = [
        [Paragraph("Genel Ortalama", s_tablo_baslik),
         Paragraph("Geçen", s_tablo_baslik),
         Paragraph("Kalan", s_tablo_baslik),
         Paragraph("Genel Karar", s_tablo_baslik)],
        [Paragraph(f"{genel_ort:.1f} / 10", s_ozet_bold),
         Paragraph(str(gecen), s_ozet_bold),
         Paragraph(str(kalan), s_ozet_bold),
         Paragraph(karar, ParagraphStyle("KR", fontName=YB, fontSize=9.5,
                                          textColor=karar_renk))],
    ]
    ozet_tablo = Table(ozet_veri, colWidths=[doc.width/4]*4)
    ozet_tablo.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#2E75B6")),
        ("BACKGROUND",    (0,1), (-1,1), GRI),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
    ]))
    hikaye.append(ozet_tablo)
    hikaye.append(Spacer(1, 0.4*cm))

    haberler = evaluation_sonuc.get("haberler", [])
    if haberler:
        hikaye.append(Paragraph("Haber Bazlı Değerlendirme",
                                 ParagraphStyle("HB2", fontName=YB, fontSize=10,
                                                textColor=LACIVERT, spaceAfter=6)))

        tablo_veri = [[
            Paragraph("Haber Başlığı", s_tablo_baslik),
            Paragraph("URL", s_tablo_baslik),
            Paragraph("Tarih", s_tablo_baslik),
            Paragraph("Kategori", s_tablo_baslik),
            Paragraph("İçerik", s_tablo_baslik),
            Paragraph("Ort.", s_tablo_baslik),
            Paragraph("Karar", s_tablo_baslik),
        ]]

        for h in haberler:
            karar_h = h.get("karar", "?")
            karar_renk_h = YESIL if karar_h == "GECTI" else KIRMIZI
            tablo_veri.append([
                Paragraph(h.get("baslik", "")[:45] + "...", s_tablo_icerik),
                Paragraph(str(h.get("url_puan", 0)), s_tablo_icerik),
                Paragraph(str(h.get("tarih_puan", 0)), s_tablo_icerik),
                Paragraph(str(h.get("kategori_puan", 0)), s_tablo_icerik),
                Paragraph(str(h.get("icerik_puan", 0)), s_tablo_icerik),
                Paragraph(f"{h.get('ortalama', 0):.1f}", s_tablo_icerik),
                Paragraph(karar_h, ParagraphStyle("KRH", fontName=YB, fontSize=8,
                                                   textColor=karar_renk_h)),
            ])

        genislikler = [doc.width*0.38, doc.width*0.08, doc.width*0.08,
                       doc.width*0.1, doc.width*0.1, doc.width*0.1, doc.width*0.1]
        haber_tablo = Table(tablo_veri, colWidths=genislikler, repeatRows=1)
        haber_tablo.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#2E75B6")),
            ("ROWBACKGROUNDS",(0,1), (-1,-1),
             [colors.white, colors.HexColor("#F8F9FB")]),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
            ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#DDDDDD")),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ]))
        hikaye.append(haber_tablo)

    hikaye.append(Spacer(1, 0.3*cm))
    hikaye.append(HRFlowable(width="100%", thickness=0.5,
                              color=KOYU_GRI, spaceBefore=4, spaceAfter=4))
    hikaye.append(Paragraph(
        "Değerlendirme kriterleri: URL geçerliliği, tarih güncelliği, "
        "kategori uyumu, içerik kalitesi (her biri 0-10 puan). "
        "Ortalama >= 7 → GEÇTİ.",
        ParagraphStyle("DP2", fontName=YN, fontSize=7.5,
                       textColor=KOYU_GRI, alignment=TA_CENTER)
    ))



# PDF OLUŞTUR

def turkce_temizle(metin):
    metin = metin.replace("&", "&amp;")
    metin = metin.replace("<", "&lt;").replace(">", "&gt;")
    metin = metin.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    metin = metin.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
    return metin


def metni_isle(metin):
    satirlar = metin.split("\n")
    bolumler = []
    for satir in satirlar:
        satir = satir.strip()
        if not satir:
            bolumler.append(("bosluk", ""))
            continue
        if satir.startswith("## "):
            bolumler.append(("kategori_baslik", satir[3:].strip()))
        elif satir.startswith("# "):
            bolumler.append(("ana_baslik", satir[2:].strip()))
        elif satir.startswith("### "):
            bolumler.append(("alt_baslik", satir[4:].strip()))
        elif satir.startswith("**") and satir.endswith("**") and len(satir) > 4:
            bolumler.append(("kalin", satir[2:-2].strip()))
        elif re.match(r"^(\d+\.\s*)?BASLIK:", satir):
            baslik_metni = re.sub(r"^(\d+\.\s*)?BASLIK:", "", satir).strip()
            bolumler.append(("haber_baslik", baslik_metni))
        elif satir.startswith("OZET:"):
            bolumler.append(("haber_alan", ("Özet", satir[5:].strip())))
        elif satir.startswith("ONEM:"):
            bolumler.append(("haber_alan", ("Önem", satir[5:].strip())))
        elif satir.startswith("KAYNAK:"):
            bolumler.append(("haber_alan", ("Kaynak", satir[7:].strip())))
        elif satir.startswith("TARIH:"):
            bolumler.append(("haber_alan", ("Tarih", satir[6:].strip())))
        elif satir.startswith("URL:"):
            bolumler.append(("haber_url", satir[4:].strip()))
        elif satir.startswith("- ") or satir.startswith("* "):
            bolumler.append(("madde", satir[2:].strip()))
        elif re.match(r"^---+$", satir):
            bolumler.append(("ayrac", ""))
        else:
            bolumler.append(("paragraf", satir))
    return bolumler


def pdf_olustur(bulten_metni, dosya_yolu, evaluation_sonuc=None):
    """Profesyonel, Türkçe destekli PDF bülten oluşturur."""

    YN, YB = font_kaydet()

    doc = SimpleDocTemplate(
        dosya_yolu,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2.5*cm,
        bottomMargin=2.5*cm,
        allowSplitting=1,   # Haber bloklarını sayfa ortasında bölme
    )

    LACIVERT  = colors.HexColor("#1A2C5B")
    MAVI      = colors.HexColor("#2E75B6")
    YESIL     = colors.HexColor("#1A6B3C")
    GRI       = colors.HexColor("#F2F4F8")
    KOYU_GRI  = colors.HexColor("#6B7280")
    YAZI      = colors.HexColor("#1C1C1C")
    LINK_MAVI = colors.HexColor("#1155CC")
    SARI_BG   = colors.HexColor("#FFF9E6")
    SARI_BORD = colors.HexColor("#E8A000")

    def stil(isim, **kwargs):
        return ParagraphStyle(isim, **kwargs)

    s_kapak_baslik = stil("KB", fontName=YB, fontSize=24, textColor=colors.white,
                          alignment=TA_CENTER, leading=30, spaceAfter=4)
    s_kapak_alt    = stil("KA", fontName=YN, fontSize=12, textColor=colors.HexColor("#D0DCF0"),
                          alignment=TA_CENTER, spaceAfter=3)
    s_kategori     = stil("KT", fontName=YB, fontSize=15, textColor=colors.white,
                          alignment=TA_LEFT, leading=20, spaceAfter=0,
                          spaceBefore=0, leftIndent=10)
    s_haber_baslik = stil("HB", fontName=YB, fontSize=11, textColor=LACIVERT,
                          spaceBefore=14, spaceAfter=4, leading=15)
    s_alan_etiket  = stil("AE", fontName=YB, fontSize=9, textColor=KOYU_GRI,
                          spaceAfter=1, leading=13)
    s_alan_icerik  = stil("AI", fontName=YN, fontSize=9.5, textColor=YAZI,
                          spaceAfter=5, leading=14, alignment=TA_JUSTIFY)
    s_url          = stil("UR", fontName=YN, fontSize=8, textColor=LINK_MAVI,
                          spaceAfter=8, leading=12)
    s_madde        = stil("MD", fontName=YN, fontSize=9.5, textColor=YAZI,
                          leftIndent=14, spaceAfter=4, leading=14)
    s_paragraf     = stil("PR", fontName=YN, fontSize=9.5, textColor=YAZI,
                          spaceAfter=5, leading=14, alignment=TA_JUSTIFY)
    s_editor       = stil("ED", fontName=YN, fontSize=9.5, textColor=YAZI,
                          spaceAfter=6, leading=15, alignment=TA_JUSTIFY,
                          leftIndent=10, rightIndent=10)
    s_dipnot       = stil("DP", fontName=YN, fontSize=7.5, textColor=KOYU_GRI,
                          alignment=TA_CENTER, spaceAfter=3)

    hikaye = []
    bugun = datetime.now()
    ay_adi_tr = {
        1:"Ocak", 2:"Şubat", 3:"Mart", 4:"Nisan", 5:"Mayıs", 6:"Haziran",
        7:"Temmuz", 8:"Ağustos", 9:"Eylül", 10:"Ekim", 11:"Kasım", 12:"Aralık"
    }
    tarih_str = f"{ay_adi_tr[bugun.month]} {bugun.year}"

    kapak_veri = [
        [Paragraph("SİGORTA &amp; TEKNOLOJİ", s_kapak_baslik)],
        [Paragraph("AYLIK BÜLTEN", s_kapak_baslik)],
        [Spacer(1, 0.2*cm)],
        [Paragraph(tarih_str, s_kapak_alt)],
        [Paragraph("Yapay Zeka Destekli Haber Özeti", s_kapak_alt)],
    ]
    kapak_tablo = Table(kapak_veri, colWidths=[doc.width])
    kapak_tablo.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LACIVERT),
        ("TOPPADDING",    (0,0), (-1,-1), 20),
        ("BOTTOMPADDING", (0,0), (-1,-1), 20),
        ("LEFTPADDING",   (0,0), (-1,-1), 16),
        ("RIGHTPADDING",  (0,0), (-1,-1), 16),
    ]))
    hikaye.append(kapak_tablo)
    hikaye.append(Spacer(1, 0.6*cm))

    bilgi_veri = [[
        Paragraph(f"<b>Yayın Tarihi:</b> {bugun.strftime('%d.%m.%Y')}", s_alan_icerik),
        Paragraph("<b>Kapsam:</b> Son 30 Gün", s_alan_icerik),
        Paragraph("<b>Model:</b> Claude AI + Tavily", s_alan_icerik),
    ]]
    bilgi_tablo = Table(bilgi_veri, colWidths=[doc.width/3]*3)
    bilgi_tablo.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), GRI),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("LINEBELOW",     (0,0), (-1,-1), 1.5, MAVI),
    ]))
    hikaye.append(bilgi_tablo)
    hikaye.append(Spacer(1, 0.5*cm))

    bolumler = metni_isle(bulten_metni)
    editor_modu = False

    # Her haberi KeepTogether bloğuna al — sayfa ortasında kesilmez
    mevcut_haber_blok = []
    aktif_haber = False

    def haber_bloku_bitir():
        """Mevcut haber bloğunu hikayeye KeepTogether olarak ekle."""
        if mevcut_haber_blok:
            hikaye.append(KeepTogether(mevcut_haber_blok[:]))
            mevcut_haber_blok.clear()

    for tur, icerik in bolumler:

        
        if tur == "haber_baslik":
            haber_bloku_bitir()
            aktif_haber = True

        if tur == "bosluk":
            if aktif_haber:
                mevcut_haber_blok.append(Spacer(1, 0.15*cm))
            else:
                hikaye.append(Spacer(1, 0.15*cm))
            continue

        if tur == "ayrac":
            eleman = HRFlowable(width="100%", thickness=0.5,
                                color=KOYU_GRI, spaceBefore=6, spaceAfter=6)
            if aktif_haber:
                mevcut_haber_blok.append(eleman)
            else:
                hikaye.append(eleman)
            continue

        if tur == "kategori_baslik":
            haber_bloku_bitir()
            aktif_haber = False
            icerik_temiz = turkce_temizle(icerik)
            if "1" in icerik or "SIGORTA" in icerik.upper():
                bg_renk = LACIVERT
            elif "2" in icerik or "TEKNOLOJ" in icerik.upper():
                bg_renk = YESIL
            elif "EDITOR" in icerik.upper() or "EDITÖR" in icerik.upper():
                editor_modu = True
                bg_renk = colors.HexColor("#5C3A8E")
            else:
                bg_renk = LACIVERT

            hikaye.append(Spacer(1, 0.4*cm))
            kat_veri = [[Paragraph(icerik_temiz, s_kategori)]]
            kat_tablo = Table(kat_veri, colWidths=[doc.width])
            kat_tablo.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), bg_renk),
                ("TOPPADDING",    (0,0), (-1,-1), 10),
                ("BOTTOMPADDING", (0,0), (-1,-1), 10),
                ("LEFTPADDING",   (0,0), (-1,-1), 14),
                ("RIGHTPADDING",  (0,0), (-1,-1), 14),
            ]))
            hikaye.append(kat_tablo)
            hikaye.append(Spacer(1, 0.2*cm))
            continue

        if tur == "haber_baslik":
            icerik_temiz = turkce_temizle(icerik)
            mevcut_haber_blok.append(
                HRFlowable(width="100%", thickness=0.5,
                           color=colors.HexColor("#CCCCCC"),
                           spaceBefore=10, spaceAfter=6)
            )
            mevcut_haber_blok.append(Paragraph(icerik_temiz, s_haber_baslik))
            continue

        if tur == "haber_alan":
            etiket, deger = icerik
            deger_temiz = turkce_temizle(deger)
            deger_temiz = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", deger_temiz)
            mevcut_haber_blok.append(Paragraph(f"<b>{etiket}:</b>", s_alan_etiket))
            mevcut_haber_blok.append(Paragraph(deger_temiz, s_alan_icerik))
            continue

        if tur == "haber_url":
            url_temiz = icerik.strip()
            if url_temiz and url_temiz != "-":
                mevcut_haber_blok.append(Paragraph(f"<b>Link:</b> {url_temiz}", s_url))
            continue

        if tur == "madde":
            icerik_temiz = turkce_temizle(icerik)
            icerik_temiz = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", icerik_temiz)
            eleman = Paragraph(f"• {icerik_temiz}", s_madde)
            if aktif_haber:
                mevcut_haber_blok.append(eleman)
            else:
                hikaye.append(eleman)
            continue

        if tur in ("paragraf", "kalin", "ana_baslik", "alt_baslik"):
            icerik_temiz = turkce_temizle(icerik)
            icerik_temiz = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", icerik_temiz)
            icerik_temiz = re.sub(r"\*(.*?)\*", r"<i>\1</i>", icerik_temiz)
            if editor_modu:
                ed_veri = [[Paragraph(icerik_temiz, s_editor)]]
                ed_tablo = Table(ed_veri, colWidths=[doc.width])
                ed_tablo.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0), (-1,-1), SARI_BG),
                    ("LINEAFTER",     (0,0), (0,-1), 3, SARI_BORD),
                    ("TOPPADDING",    (0,0), (-1,-1), 5),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                    ("LEFTPADDING",   (0,0), (-1,-1), 12),
                    ("RIGHTPADDING",  (0,0), (-1,-1), 10),
                ]))
                hikaye.append(ed_tablo)
                hikaye.append(Spacer(1, 0.1*cm))
            else:
                if tur in ("ana_baslik", "alt_baslik", "kalin"):
                    p_stil = ParagraphStyle("tmp", fontName=YB, fontSize=10,
                                            textColor=LACIVERT, spaceAfter=4,
                                            leading=14)
                    hikaye.append(Paragraph(icerik_temiz, p_stil))
                else:
                    hikaye.append(Paragraph(icerik_temiz, s_paragraf))
            continue

    
    haber_bloku_bitir()

    hikaye.append(Spacer(1, 0.8*cm))
    hikaye.append(HRFlowable(width="100%", thickness=1, color=KOYU_GRI,
                              spaceBefore=4, spaceAfter=6))
    hikaye.append(Paragraph(
        f"Bu bülten Claude AI (Anthropic) tarafından otomatik olarak oluşturulmuştur. "
        f"Oluşturulma tarihi: {bugun.strftime('%d.%m.%Y %H:%M')}",
        s_dipnot
    ))

    if evaluation_sonuc:
        kalite_raporu_ekle(hikaye, evaluation_sonuc, doc, YN, YB)

    doc.build(hikaye)
    print(f"PDF olusturuldu: {dosya_yolu}")



# ANA AKIŞ

def main():
    print("=" * 55)
    print("  SİGORTA & TEKNOLOJİ AYLIK BÜLTEN SİSTEMİ")
    print(f"  {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print("=" * 55)

    os.makedirs(CIKTI_KLASORU, exist_ok=True)

    bugun = datetime.now()
    dosya_adi = f"bulten_{bugun.strftime('%Y_%m')}.pdf"
    dosya_yolu = os.path.join(CIKTI_KLASORU, dosya_adi)

    try:
        # 1. Haberleri topla
        bulten_metni = haberleri_topla_ve_bulten_olustur()

        # 2. Evaluation yap
        evaluation_sonuc = evaluation_yap(bulten_metni)

        # 3. Kalan haberler varsa yenile ve tekrar değerlendir
        if evaluation_sonuc.get("kalan_haber_sayisi", 0) > 0:
            bulten_metni = haberler_yenile(bulten_metni, evaluation_sonuc)
            print("\n🔄 Yenileme sonrası ikinci evaluation yapılıyor...")
            evaluation_sonuc = evaluation_yap(bulten_metni)

        # 4. PDF oluştur
        print("PDF oluşturuluyor...")
        pdf_olustur(bulten_metni, dosya_yolu, evaluation_sonuc)

        print("\n" + "=" * 55)
        print("  BÜLTEN BAŞARIYLA OLUŞTURULDU!")
        print(f"  Konum: {dosya_yolu}")
        print(f"  Kalite: {evaluation_sonuc.get('genel_ortalama', 0):.1f}/10 "
              f"({evaluation_sonuc.get('genel_karar', '?')})")
        print("=" * 55)

    except Exception as e:
        print(f"\nHATA: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
