import streamlit as st
import os
from datetime import datetime

from bulten_olusturucu import (
    haberleri_topla_ve_bulten_olustur,
    evaluation_yap,
    haberler_yenile,
    pdf_olustur,
    CIKTI_KLASORU,
)

st.set_page_config(page_title="Sigorta & Teknoloji Bülteni", page_icon="📰", layout="centered")

st.title("📰 Sigorta & Teknoloji Aylık Bülten Sistemi")
st.caption("Yapay zeka ajanı, son 30 günün sigorta ve teknoloji haberlerini tarar, "
           "kalite kontrolünden geçirir ve profesyonel bir PDF bülten üretir.")

st.divider()

# ── Geçmiş bültenler ──
st.subheader("📂 Geçmiş Bültenler")

os.makedirs(CIKTI_KLASORU, exist_ok=True)
mevcut_dosyalar = sorted(
    [f for f in os.listdir(CIKTI_KLASORU) if f.endswith(".pdf")],
    reverse=True
)

if mevcut_dosyalar:
    for dosya in mevcut_dosyalar:
        dosya_yolu = os.path.join(CIKTI_KLASORU, dosya)
        with open(dosya_yolu, "rb") as f:
            st.download_button(
                label=f"⬇️ {dosya}",
                data=f.read(),
                file_name=dosya,
                mime="application/pdf",
                key=f"indir_{dosya}",
            )
else:
    st.info("Henüz oluşturulmuş bülten yok.")

st.divider()

# ── Yeni bülten oluştur ──
st.subheader("🆕 Yeni Bülten Oluştur")
st.caption("Bu işlem yaklaşık 4-6 dakika sürer (20 haber aranıp değerlendirilir).")

if st.button("🚀 Bülten Oluştur", type="primary", use_container_width=True):
    durum = st.status("Bülten oluşturuluyor...", expanded=True)

    try:
        durum.write("🔍 Haberler aranıyor (bu adım birkaç dakika sürebilir)...")
        bulten_metni = haberleri_topla_ve_bulten_olustur()
        durum.write("✅ Haberler toplandı.")

        durum.write("📊 Kalite değerlendirmesi yapılıyor...")
        evaluation_sonuc = evaluation_yap(bulten_metni)
        durum.write(f"✅ Değerlendirme tamamlandı — Ortalama: "
                     f"{evaluation_sonuc.get('genel_ortalama', 0):.1f}/10")

        if evaluation_sonuc.get("kalan_haber_sayisi", 0) > 0:
            durum.write(f"🔄 {evaluation_sonuc.get('kalan_haber_sayisi')} haber yenileniyor...")
            bulten_metni = haberler_yenile(bulten_metni, evaluation_sonuc)
            evaluation_sonuc = evaluation_yap(bulten_metni)
            durum.write("✅ Yenileme tamamlandı.")

        durum.write("📄 PDF oluşturuluyor...")
        bugun = datetime.now()
        dosya_adi = f"bulten_{bugun.strftime('%Y_%m_%d_%H%M')}.pdf"
        dosya_yolu = os.path.join(CIKTI_KLASORU, dosya_adi)
        pdf_olustur(bulten_metni, dosya_yolu, evaluation_sonuc)

        durum.update(label="✅ Bülten başarıyla oluşturuldu!", state="complete", expanded=False)

        st.success(f"Bülten hazır: {dosya_adi}")
        with open(dosya_yolu, "rb") as f:
            st.download_button(
                label="⬇️ Bülteni İndir",
                data=f.read(),
                file_name=dosya_adi,
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
        st.rerun()

    except Exception as e:
        durum.update(label="❌ Hata oluştu", state="error")
        st.error(f"Bülten oluşturulurken hata: {e}")