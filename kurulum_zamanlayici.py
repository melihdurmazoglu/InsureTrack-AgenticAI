"""
Windows Task Scheduler Kurulum Scripti
Her ayın 23'ünde sabah 09:00'da bülteni otomatik çalıştırır.

KULLANIM: Bu scripti yönetici (Administrator) olarak çalıştırın.
  - CMD veya PowerShell'i sağ tıklayıp "Yönetici olarak çalıştır" seçin
  - python kurulum_zamanlayici.py
"""

import subprocess
import sys
import os

# ─────────────────────────────────────────────────────
# AYARLAR — sadece bu bölümü düzenleyin
# ─────────────────────────────────────────────────────

GOREV_ADI      = "AylikSigortaBulteni"
CALISMA_SAATI  = "09:00"          # Her ayın 23'ünde saat 09:00
PYTHON_YOLU    = sys.executable   # Otomatik algılanır
SCRIPT_YOLU    = os.path.abspath("bulten_olusturucu.py")  # Aynı klasörde olmalı

# ─────────────────────────────────────────────────────

def gorevi_olustur():
    """Windows Task Scheduler'a aylık görev ekler."""

    # PowerShell komutu
    ps_komutu = f"""
$action  = New-ScheduledTaskAction -Execute "{PYTHON_YOLU}" -Argument '"{SCRIPT_YOLU}"'
$trigger = New-ScheduledTaskTrigger -Monthly -DaysOfMonth 23 -At {CALISMA_SAATI}
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable
Register-ScheduledTask -TaskName "{GOREV_ADI}" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Her ayin 23ünde sigorta ve teknoloji bülteni olusturur." `
    -Force
"""

    print(f"📅  Zamanlanmış görev oluşturuluyor: '{GOREV_ADI}'")
    print(f"    Python: {PYTHON_YOLU}")
    print(f"    Script: {SCRIPT_YOLU}")
    print(f"    Zamanlama: Her ayın 23'ü saat {CALISMA_SAATI}")
    print()

    sonuc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_komutu],
        capture_output=True, text=True
    )

    if sonuc.returncode == 0:
        print("✅  Görev başarıyla oluşturuldu!")
        print()
        print("Görevi kontrol etmek için:")
        print("  → Başlat > Görev Zamanlayıcı (Task Scheduler) > AylikSigortaBulteni")
        print()
        print("Manuel test için:")
        print(f"  → python \"{SCRIPT_YOLU}\"")
    else:
        print("❌  Hata oluştu:")
        print(sonuc.stderr)
        print()
        print("Not: Bu scripti yönetici (Administrator) olarak çalıştırdığınızdan emin olun.")


def gorevi_sil():
    """Mevcut görevi siler (isteğe bağlı)."""
    ps_komutu = f'Unregister-ScheduledTask -TaskName "{GOREV_ADI}" -Confirm:$false'
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_komutu],
        capture_output=True
    )
    print(f"🗑️   '{GOREV_ADI}' görevi silindi.")


if __name__ == "__main__":
    print("=" * 50)
    print("  BÜLTEN ZAMANLAYICI KURULUM")
    print("=" * 50)
    print()

    if len(sys.argv) > 1 and sys.argv[1] == "--sil":
        gorevi_sil()
    else:
        gorevi_olustur()
