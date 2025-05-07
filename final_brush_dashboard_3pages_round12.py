import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Brush Dashboard", layout="wide")

def avg_positive(rate_dict):
    valid = [v for v in rate_dict.values() if v > 0]
    return sum(valid) / len(valid) if valid else 0

page = st.sidebar.radio("📂 เลือกหน้า", ["📊 หน้าแสดงผล rate และ ชั่วโมงที่เหลือ", "📝 กรอกข้อมูลแปลงถ่านเพิ่มเติม", "📈 พล็อตกราฟตามเวลา (แยก Upper และ Lower)"])

# ------------------ PAGE 1 ------------------
if page == "📊 หน้าแสดงผล rate และ ชั่วโมงที่เหลือ":
    st.title("🛠️ วิเคราะห์อัตราสึกหรอและชั่วโมงที่เหลือของ Brush")
    sheet_url = "https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ/export?format=xlsx"
    xls = pd.ExcelFile(sheet_url)
    sheet_names = xls.sheet_names

    num_sheets = st.number_input("📌 เลือกจำนวน Sheet ที่ใช้คำนวณ", min_value=1, max_value=len(sheet_names), value=7)
    selected_sheets = sheet_names[:num_sheets]
    brush_numbers = list(range(1, 33))

    upper_rates, lower_rates = {n:{} for n in brush_numbers}, {n:{} for n in brush_numbers}

    for sheet in selected_sheets:
        df_raw = xls.parse(sheet, header=None)
        try:
            hours = float(df_raw.iloc[0, 7])
        except:
            continue
        df = xls.parse(sheet, skiprows=1, header=None).apply(pd.to_numeric, errors='coerce')

        upper_df = df.iloc[:, 4:6]
        upper_df.columns = ["Upper_Current", "Upper_Previous"]
        upper_df["No"] = range(1, len(upper_df)+1)

        lower_df = df.iloc[:, 0:3]
        lower_df.columns = ["No", "Lower_Previous", "Lower_Current"]

        for n in brush_numbers:
            u = upper_df[upper_df["No"] == n]
            l = lower_df[lower_df["No"] == n]
            if not u.empty:
                diff = u.iloc[0]["Upper_Current"] - u.iloc[0]["Upper_Previous"]
                rate = diff / hours if hours > 0 else 0
                upper_rates[n][sheet] = rate if rate > 0 else 0
            if not l.empty:
                diff = l.iloc[0]["Lower_Previous"] - l.iloc[0]["Lower_Current"]
                rate = diff / hours if hours > 0 else 0
                lower_rates[n][sheet] = rate if rate > 0 else 0

    avg_rate_upper = [avg_positive(upper_rates[n]) for n in brush_numbers]
    avg_rate_lower = [avg_positive(lower_rates[n]) for n in brush_numbers]

    if "Sheet7" in xls.sheet_names:
        df_current = xls.parse("Sheet7", header=None)
        upper_current = pd.to_numeric(df_current.iloc[2:34, 5], errors='coerce').values
        lower_current = pd.to_numeric(df_current.iloc[2:34, 2], errors='coerce').values
    else:
        st.error("❌ ไม่พบ Sheet7")
        st.stop()

    def calc_remaining(c, r): return [(v - 35) / r[i] if pd.notna(v) and r[i] > 0 and v > 35 else 0 for i, v in enumerate(c)]
    hour_upper = calc_remaining(upper_current, avg_rate_upper)
    hour_lower = calc_remaining(lower_current, avg_rate_lower)

    st.subheader("📋 ตาราง Avg Rate - Upper")
    df_upper = pd.DataFrame(avg_rate_upper, columns=["Avg Rate (Upper)"])
    st.dataframe(df_upper.style.format("{:.6f}"), use_container_width=True)

    st.subheader("📋 ตาราง Avg Rate - Lower")
    df_lower = pd.DataFrame(avg_rate_lower, columns=["Avg Rate (Lower)"])
    st.dataframe(df_lower.style.format("{:.6f}"), use_container_width=True)

    st.subheader("⏳ ชั่วโมงที่เหลือก่อนถึง 35mm")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))
    ax1.bar(brush_numbers, hour_upper, color='red')
    ax1.set_title("Remaining Hours - Upper")
    ax2.bar(brush_numbers, hour_lower, color='darkred')
    ax2.set_title("Remaining Hours - Lower")
    st.pyplot(fig)

# ------------------ PAGE 2 ------------------
elif page == "📝 กรอกข้อมูลแปลงถ่านเพิ่มเติม":
    st.title("📝 กรอกข้อมูลแปรงถ่าน + ชั่วโมง")
    service_account_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    ws = gc.open_by_url("https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ").worksheet("Sheet8")

    hours = st.number_input("⏱️ ชั่วโมง", min_value=0.0, step=0.1)
    upper = [st.number_input(f"Upper {i+1}", key=f"u{i}", step=0.01) for i in range(32)]
    lower = [st.number_input(f"Lower {i+1}", key=f"l{i}", step=0.01) for i in range(32)]

    if st.button("📤 บันทึก"):
        try:
            ws.update("H1", [[hours]])
            ws.update("C3:C34", [[v] for v in upper])
            ws.update("F3:F34", [[v] for v in lower])
            st.success("✅ บันทึกแล้ว")
        except Exception as e:
            st.error(f"❌ {e}")

# ------------------ PAGE 3 ------------------
elif page == "📈 พล็อตกราฟตามเวลา (แยก Upper และ Lower)":
    st.title("📈 พล็อตกราฟตามเวลา (แยก Upper และ Lower)")

    service_account_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ")

    selected_sheet = st.selectbox("📄 เลือก Sheet ปัจจุบัน", [ws.title for ws in sheet.worksheets()])
    count = st.number_input("📌 จำนวน Sheet ที่ใช้คำนวณ Rate", min_value=1, max_value=9, value=6)

    ws = sheet.worksheet(selected_sheet)
    upper_current = [float(row[0]) if row and row[0] not in ["", "-"] else 0 for row in ws.get("F3:F34")]
    lower_current = [float(row[0]) if row and row[0] not in ["", "-"] else 0 for row in ws.get("C3:C34")]

    xls = pd.ExcelFile("https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ/export?format=xlsx")
    sheets = xls.sheet_names[:count]

    brush_numbers = list(range(1, 33))
    ur, lr = {n:{} for n in brush_numbers}, {n:{} for n in brush_numbers}

    for s in sheets:
        df = xls.parse(s, skiprows=1, header=None).apply(pd.to_numeric, errors='coerce')
        try: h = float(xls.parse(s, header=None).iloc[0, 7])
        except: continue

        for i in brush_numbers:
            cu, pu = df.iloc[i-1, 4], df.iloc[i-1, 5]
            cl, pl = df.iloc[i-1, 1], df.iloc[i-1, 2]
            if pd.notna(cu) and pd.notna(pu) and h > 0:
                diff = cu - pu
                rate = diff / h
                if rate > 0: ur[i][s] = rate
            if pd.notna(cl) and pd.notna(pl) and h > 0:
                diff = pl - cl
                rate = diff / h
                if rate > 0: lr[i][s] = rate

    avg_rate_upper = [avg_positive(ur[n]) for n in brush_numbers]
    avg_rate_lower = [avg_positive(lr[n]) for n in brush_numbers]
    time_hours = np.arange(0, 201, 10)

    fig_upper = go.Figure()
    for i, (start, rate) in enumerate(zip(upper_current, avg_rate_upper)):
        y = [start - rate*t for t in time_hours]
        fig_upper.add_trace(go.Scatter(x=time_hours, y=y, name=f"Upper {i+1}", mode='lines'))

    fig_upper.update_layout(title="🔺 ความยาว Upper ตามเวลา", xaxis_title="ชั่วโมง", yaxis_title="mm", xaxis=dict(dtick=10, range=[0, 200]), yaxis=dict(range=[30, 65]))
    st.plotly_chart(fig_upper, use_container_width=True)

    fig_lower = go.Figure()
    for i, (start, rate) in enumerate(zip(lower_current, avg_rate_lower)):
        y = [start - rate*t for t in time_hours]
        fig_lower.add_trace(go.Scatter(x=time_hours, y=y, name=f"Lower {i+1}", mode='lines', line=dict(dash='dot')))

    fig_lower.update_layout(title="🔻 ความยาว Lower ตามเวลา", xaxis_title="ชั่วโมง", yaxis_title="mm", xaxis=dict(dtick=10, range=[0, 200]), yaxis=dict(range=[30, 65]))
    st.plotly_chart(fig_lower, use_container_width=True)