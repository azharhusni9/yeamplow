import streamlit as st
from datetime import datetime
from fpdf2 import FPDF
import re

# ====================== SECURITY ======================
st.set_page_config(
    page_title="TechCheck Pro | Ultimate QC Tool",
    page_icon="📱",
    layout="wide"
)

def sanitize_text(text):
    if not text:
        return ""
    text = re.sub(r'[<>"/\\{}[\]();|&]', '', str(text))
    return text.strip()[:2000]

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .report-box {
        padding: 20px;
        border-radius: 12px;
        background-color: #ffffff;
        border-top: 5px solid #004a99;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .s-grade { color: #28a745; font-weight: bold; }
    .a-grade { color: #17a2b8; font-weight: bold; }
    .bc-grade { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ====================== KAMUS TERJEMAHAN ======================
translations = {
    "id": {
        "app_title": "TechCheck Pro",
        "qc_menu": "Input QC Baru",
        "panic_menu": "Panic Log Parser",
        "panic_header": "🔍 Advanced Panic Log Analyzer",
        "upload_label": "📁 Drop File Panic Log di sini (.txt, .log)",
        "paste_label": "Atau paste manual Panic Log di sini:",
        "analyze_btn": "🔎 Analisa Hardware Panic Log",
    },
    "en": {
        "app_title": "TechCheck Pro",
        "qc_menu": "New QC Input",
        "panic_menu": "Panic Log Parser",
        "panic_header": "🔍 Advanced Panic Log Analyzer",
        "upload_label": "📁 Drop Panic Log File here (.txt, .log)",
        "paste_label": "Or paste Panic Log manually here:",
        "analyze_btn": "🔎 Analyze Hardware Panic Log",
    }
}

# ====================== PANIC LOG ANALYZER ======================
def analyze_panic_log(log_text):
    if not log_text or not log_text.strip():
        return ["❌ Tidak ada data log yang dimasukkan."]

    log = sanitize_text(log_text).lower()
    results = []

    patterns = {
    # Thermal & Restart Classic
        "thermalmonitord": "⚠️ THERMALMONITORD → Sensor Suhu Rusak (Flex Charging / Dock)",
        "mic1": "⚠️ MIC1 → Mic Bawah / Dock Connector",
        "mic2": "⚠️ MIC2 → Mic Atas / Flex Power",
        "prs0": "⚠️ PRS0 → Proximity / Ambient Light Sensor",
        "tg0b": "⚠️ TG0B → Battery Temperature Sensor",
        "tg0v": "⚠️ TG0V → Battery Voltage",

        # Storage & NAND
        "ans": "⚠️ ANS / ANS2 → NAND / Storage Controller Rusak",
        "ememory": "⚠️ EMEMORY → NAND Error",
        "nand": "⚠️ NAND Failure",

        # Secure Enclave
        "sep rom": "⚠️ SEP ROM → Secure Enclave / FaceID / TouchID Rusak",
        "seprom": "⚠️ SEP ROM → Secure Enclave Damage",

        # I2C & Sensor
        "i2c0": "⚠️ I2C0 → Proximity / Flex Atas (Sering X-12)",
        "i2c1": "⚠️ I2C1 → LCD / Kamera Depan",

        # Power Management
        "smc": "⚠️ SMC → Power Management / Baterai IC",
        "assertion failed": "⚠️ SMC ASSERTION FAILED → Power Management Error",
        "watchdog timeout": "⚠️ WATCHDOG TIMEOUT → Hardware Hang",

        # Baseband & PCIe
        "pcie": "⚠️ PCIE → CPU ke Baseband (Seri 13-16)",
        "baseband": "⚠️ BASEBAND Communication Error",

        # Hex Code SMC
        "0x800": "⚠️ 0x800 → Charging Port Flex",
        "0x1000": "⚠️ 0x1000 → Proximity Flex",
        "0x1800": "⚠️ 0x1800 → Charging + Proximity",
        "0x40000": "⚠️ 0x40000 → Charging Port",
        "0x80000": "⚠️ 0x80000 → Proximity Flex",
        "0x100000": "⚠️ 0x100000 → Power Button Flex",

        # Lainnya
        "pronto": "⚠️ PRONTO → Wi-Fi / Bluetooth Module",
        "stackshot": "⚠️ STACKSHOT / KERNEL PANIC → Crash Berat",
        "kernel panic": "⚠️ KERNEL PANIC → Hardware Level Crash",
        "aop": "⚠️ AOP → Always On Processor",
        "tristar": "⚠️ TRISTAR → Charging IC Rusak",
        "wlan": "⚠️ WLAN → Wi-Fi Antenna Issue",   
    }

    for key, desc in patterns.items():
        if key in log:
            results.append(desc)

    if "missing sensor" in log:
        results.insert(0, "🔴 MULTIPLE SENSOR MISSING → Flex Charging Port kemungkinan rusak!")

    if not results:
        return ["✅ Log Bersih: Tidak ditemukan pola panic umum."]
    return results

def get_grade(checks):
    fail_count = list(checks.values()).count(False)
    if fail_count == 0: return "S (Like New)", "s-grade"
    if fail_count <= 2: return "A (Good Condition)", "a-grade"
    return "B/C (Minus/Repair)", "bc-grade"

# ====================== IMEI VALIDATION ======================
def is_valid_imei(imei):
    if not imei or len(imei) not in [14, 15]:
        return False, "❌ IMEI harus 14 atau 15 digit"
    try:
        digits = [int(d) for d in imei]
        total = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9: digit -= 9
            total += digit
        return total % 10 == 0, "✅ IMEI Valid"
    except:
        return False, "❌ Format IMEI tidak valid"

# ====================== APPLE COVERAGE (Unofficial) ======================
def check_apple_coverage(serial):
    try:
        url = f"https://selfsolve.apple.com/wcResults.do?sn={serial}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=8)
        if "is covered" in r.text.lower() or "active" in r.text.lower():
            return "✅ Covered (Masih Garansi)"
        elif "expired" in r.text.lower():
            return "⚠️ Expired (Garansi Habis)"
        else:
            return "ℹ️ Status tidak jelas, cek manual di support.apple.com"
    except:
        return "❌ Tidak dapat terhubung ke Apple"

# ====================== GENERATE PDF (SUDAH LENGKAP) ======================

def generate_pdf(data, checks, catatan="", baseband_info=""):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
   
    # Header
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(0, 74, 153)
    pdf.cell(190, 15, "TECHCHECK PRO - QC CERTIFICATE", ln=True, align='C')
   
    pdf.set_font("Arial", 'I', 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(190, 8, "Professional Hardware Diagnostic Report", ln=True, align='C')
   
    pdf.ln(8)
   
    # Device Information
    pdf.set_font("Arial", 'B', 13)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(190, 10, " DEVICE INFORMATION", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(0, 0, 0)
   
    pdf.cell(95, 9, f" Model          : {data.get('Unit', '-')}", ln=False)
    pdf.cell(95, 9, f" Date           : {data.get('Waktu', '-')}", ln=True)
    pdf.cell(95, 9, f" IMEI / Serial  : {data.get('IMEI', '-')}", ln=False)
    pdf.cell(95, 9, f" Grade          : {data.get('Grade', '-')}", ln=True)
   
    if baseband_info:
        pdf.cell(190, 9, f" Baseband       : {baseband_info}", ln=True)
   
    # Hardware Checklist
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(190, 10, " HARDWARE CHECKLIST", ln=True, fill=True)
    pdf.set_font("Arial", '', 10.5)
   
    # Table Header
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(120, 10, " Item", border=1, fill=True)
    pdf.cell(70, 10, " Status", border=1, fill=True, align='C')
    pdf.ln()
   
    # Isi Checklist
    for key, val in checks.items():
        item_name = key.replace('_', ' ').title()
        status = "PASSED" if val else "FAILED"
        status_color = (0, 150, 0) if val else (200, 0, 0)
       
        pdf.set_text_color(0, 0, 0)
        pdf.cell(120, 9, f" {item_name}", border=1)
        pdf.set_text_color(*status_color)
        pdf.cell(70, 9, f" {status}", border=1, align='C')
        pdf.ln()
   
    # Catatan
    pdf.ln(8)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 10, " CATATAN TAMBAHAN", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(190, 8, catatan if catatan.strip() else "-")
   
    # Footer
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(190, 6, "Disclaimer: Laporan ini dihasilkan secara digital berdasarkan pengecekan pada saat tanggal tersebut. "
                           "Kerusakan yang muncul kemudian bukan tanggung jawab aplikasi ini.")
   
    return pdf.output(dest='S').encode('latin-1')  

# ====================== SIDEBAR ======================
with st.sidebar:
    st.title("📱 TechCheck Pro")
    menu = st.radio("MAIN MENU", ["Input QC Baru", "Panic Log Parser"])
    st.divider()
   
    lang_option = st.selectbox(
        "🌐 Bahasa / Language",
        ["🇮🇩 Bahasa Indonesia", "🇬🇧 English"],
        index=0
    )
    language = "id" if lang_option.startswith("🇮🇩") else "en"
   
    st.divider()
    st.caption("")
    st.info("🔒 Data tidak disimpan di server")

# ====================== INPUT QC BARU ======================
if menu == "Input QC Baru":
    st.header("📋 Form Diagnostic Perangkat")
   
    with st.expander("📝 Data Identitas Perangkat", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1: brand = st.selectbox("Brand", ["iPhone", "Android"])
        with c2: model = sanitize_text(st.text_input("Tipe Perangkat", placeholder="iPhone 14 Pro"))
        with c3: imei = sanitize_text(st.text_input("IMEI / Serial", max_chars=17))

    st.subheader("🔍 Hardware Checklist")
    col1, col2, col3 = st.columns(3)
    checks = {}

    with col1:
        st.write("**💎 Fisik & Lampu**")
        checks['lcd_display'] = st.checkbox("LCD Original/Bersih", value=True)
        checks['body_condition'] = st.checkbox("Body Mulus", value=True)
        checks['buttons'] = st.checkbox("Tombol Clicky", value=True)
        checks['flashlight'] = st.checkbox("Flash Light Nyala Normal", value=True)
        checks['flash_heat_test'] = st.checkbox("Flash Light 5-10 Menit - Tidak Panas", value=True)

    with col2:
        st.write("**🎤 Microphone**")
        checks['mic_kamera'] = st.checkbox("Mic Kamera", value=True)
        checks['mic_perekam'] = st.checkbox("Mic Perekam Suara", value=True)
        checks['audio_system'] = st.checkbox("Speaker & Mic", value=True)
        checks['wifi_bluetooth'] = st.checkbox("Wi-Fi & Bluetooth", value=True)
        checks['charging'] = st.checkbox("Charging Port", value=True)

    with col3:
        st.write("**🛡️ Spesifik**")
        checks['panicfull'] = st.checkbox("Panic Full Kosong", value=True)
        checks['factory_reset'] = st.checkbox("Reset Pabrik Sudah Dilakukan", value=True)
       
        if brand == "iPhone":
            checks['icloud_off'] = st.checkbox("iCloud OFF", value=True)
            checks['biometrics'] = st.checkbox("FaceID/TouchID", value=True)
        else:
            checks['google_account'] = st.checkbox("FRP/Google Clear", value=True)
            checks['fingerprint'] = st.checkbox("Fingerprint Aktif", value=True)

    catatan = sanitize_text(st.text_area("Catatan Tambahan (Opsional)", height=120))

    if st.button("🚀 SELESAIKAN & SIMPAN", type="primary"):
        grade_val, grade_style = get_grade(checks)
       
        new_data = {
            "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Unit": model,
            "IMEI": imei,
            "Grade": grade_val
        }
       
        st.markdown(f"""
            <div class="report-box">
                <h4>HASIL QC BERHASIL</h4>
                <p>Model: {model} | IMEI: {imei}</p>
                <p>GRADE: <span class="{grade_style}">{grade_val}</span></p>
            </div>
        """, unsafe_allow_html=True)
       
        try:
            pdf_bytes = generate_pdf(new_data, checks, catatan)
            st.download_button(
                label="📥 Download Laporan PDF",
                data=pdf_bytes,
                file_name=f"QC_Report_{imei or 'unknown'}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Gagal generate PDF: {e}")
        st.balloons()

# ====================== PANIC LOG PARSER ======================
elif menu == "Panic Log Parser":
    st.header(translations[language]["panic_header"])
   
    uploaded_file = st.file_uploader(translations[language]["upload_label"], type=["txt", "log", "csv"])
   
    log_text = ""
    if uploaded_file:
        log_text = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        st.success(f"✅ File diupload: {uploaded_file.name}")
   
    log_input = sanitize_text(st.text_area(translations[language]["paste_label"], value=log_text, height=400))
   
    if st.button(translations[language]["analyze_btn"], type="primary"):
        if log_input.strip():
            results = analyze_panic_log(log_input)
            st.subheader("📊 Hasil Analisis")
            for r in results:
                st.success(r) if "✅" in r else st.error(r)
        else:
            st.warning(translations[language]["no_log"])

st.caption("")
