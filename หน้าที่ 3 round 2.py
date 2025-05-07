
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Brush Dashboard", layout="wide")

# Navigation
page = st.sidebar.radio("📂 เลือกหน้า", ["📈 พล็อตกราฟความยาวแปรงตามเวลา"])

if page == "📈 พล็อตกราฟความยาวแปรงตามเวลา":
    st.title("📈 พล็อตกราฟความยาวแปรงตามเวลา (Upper / Lower)")

    service_account_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)

    # เลือก sheet ที่ใช้ค่าปัจจุบัน
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ"
    sheet = gc.open_by_url(spreadsheet_url)
    sheet_names = [ws.title for ws in sheet.worksheets()]
    selected_sheet = st.selectbox("📄 เลือก Sheet สำหรับ Upper/Lower Current", sheet_names)

    # ป้อนจำนวน sheet ที่ใช้สำหรับคำนวณ avg rate
    sheet_count = st.number_input("📌 ใช้จำนวน Sheet แรกในการคำนวณ Rate เฉลี่ย", min_value=1, max_value=9, value=6)

    # อ่านค่า Upper/Lower current
    ws = sheet.worksheet(selected_sheet)
    upper_current_values = ws.get("F3:F34")
    lower_current_values = ws.get("C3:C34")

    upper_current = [float(row[0]) if row and row[0] not in ["", "-"] else 0 for row in upper_current_values]
    lower_current = [float(row[0]) if row and row[0] not in ["", "-"] else 0 for row in lower_current_values]

    # อ่าน avg rate จาก sheet 1 ถึง sheet_count
    xls_url = f"https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ/export?format=xlsx"
    xls = pd.ExcelFile(xls_url)
    selected_sheets = xls.sheet_names[:sheet_count]
    brush_numbers = list(range(1, 33))

    upper_rates = {n:{} for n in brush_numbers}
    lower_rates = {n:{} for n in brush_numbers}

    for sheet_name in selected_sheets:
        df_raw = xls.parse(sheet_name, header=None)
        try:
            hours = float(df_raw.iloc[0, 7])
        except:
            continue
        df = xls.parse(sheet_name, skiprows=1, header=None)
        df = df.apply(pd.to_numeric, errors='coerce')

        # Upper
        upper_df = df.iloc[:, 4:6]
        upper_df.columns = ["Upper_Current", "Upper_Previous"]
        upper_df["No"] = range(1, len(upper_df)+1)
        for n in brush_numbers:
            row = upper_df[upper_df["No"] == n]
            if not row.empty:
                diff = row.iloc[0]["Upper_Current"] - row.iloc[0]["Upper_Previous"]
                rate = diff / hours if hours > 0 else 0
                upper_rates[n][f"{sheet_name}"] = rate if rate > 0 else 0

        # Lower
        lower_df = df.iloc[:, 0:3]
        lower_df.columns = ["No", "Lower_Previous", "Lower_Current"]
        for n in brush_numbers:
            row = lower_df[lower_df["No"] == n]
            if not row.empty:
                diff = row.iloc[0]["Lower_Previous"] - row.iloc[0]["Lower_Current"]
                rate = diff / hours if hours > 0 else 0
                lower_rates[n][f"{sheet_name}"] = rate if rate > 0 else 0

    def avg_positive(rate_dict):
        valid = [v for v in rate_dict.values() if v > 0]
        return sum(valid) / len(valid) if valid else 0

    avg_rate_upper = [avg_positive(upper_rates[n]) for n in brush_numbers]
    avg_rate_lower = [avg_positive(lower_rates[n]) for n in brush_numbers]

    # กำหนดช่วงเวลา 0-200 ชั่วโมง
    time_hours = np.arange(0, 201, 10)

    # สร้างกราฟ
    fig = go.Figure()

    for i, (up_start, up_rate) in enumerate(zip(upper_current, avg_rate_upper)):
        y = [up_start - (up_rate * h) for h in time_hours]
        fig.add_trace(go.Scatter(x=time_hours, y=y, mode='lines', name=f"Upper {i+1}"))

    for i, (lo_start, lo_rate) in enumerate(zip(lower_current, avg_rate_lower)):
        y = [lo_start - (lo_rate * h) for h in time_hours]
        fig.add_trace(go.Scatter(x=time_hours, y=y, mode='lines', name=f"Lower {i+1}", line=dict(dash='dot')))

    fig.update_layout(
        title="พล็อตความยาวแปรงถ่านตามเวลา (0-200 ชม.)",
        xaxis_title="ชั่วโมง",
        yaxis_title="ความยาวแปรง (mm)",
        xaxis=dict(tickmode='linear', dtick=10, range=[0, 200]),
        yaxis=dict(range=[30, 65]),
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)
