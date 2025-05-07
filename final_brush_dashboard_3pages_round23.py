import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Brush Dashboard", layout="wide")

page = st.sidebar.radio("📂 เลือกหน้า", [
    "📊 หน้าแสดงผล rate และ ชั่วโมงที่เหลือ",
    "📝 กรอกข้อมูลแปลงถ่านเพิ่มเติม",
    "📈 พล็อตกราฟตามเวลา (แยก Upper และ Lower)"
])


# ------------------ PAGE 1 ------------------
if page == "📊 หน้าแสดงผล rate และ ชั่วโมงที่เหลือ":
    st.title("🛠️ วิเคราะห์อัตราสึกหรอและชั่วโมงที่เหลือของ Brush")

    sheet_id = "1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    xls = pd.ExcelFile(sheet_url)
    sheet_names = xls.sheet_names

    num_sheets = st.number_input("📌 เลือกจำนวน Sheet ที่ต้องการใช้ (สำหรับคำนวณ Avg Rate)", min_value=1, max_value=len(sheet_names), value=7)
    selected_sheets = sheet_names[:num_sheets]
    brush_numbers = list(range(1, 33))

    upper_rates, lower_rates = {n:{} for n in brush_numbers}, {n:{} for n in brush_numbers}

    for sheet in selected_sheets:
        df_raw = xls.parse(sheet, header=None)
        try:
            hours = float(df_raw.iloc[0, 7])
        except:
            continue
        df = xls.parse(sheet, skiprows=1, header=None)

        lower_df_sheet = df.iloc[:, 0:3]
        lower_df_sheet.columns = ["No_Lower", "Lower_Previous", "Lower_Current"]
        lower_df_sheet = lower_df_sheet.dropna().apply(pd.to_numeric, errors='coerce')

        upper_df_sheet = df.iloc[:, 4:6]
        upper_df_sheet.columns = ["Upper_Current", "Upper_Previous"]
        upper_df_sheet = upper_df_sheet.dropna().apply(pd.to_numeric, errors='coerce')
        upper_df_sheet["No_Upper"] = range(1, len(upper_df_sheet) + 1)

        for n in brush_numbers:
            u_row = upper_df_sheet[upper_df_sheet["No_Upper"] == n]
            if not u_row.empty:
                diff = u_row.iloc[0]["Upper_Current"] - u_row.iloc[0]["Upper_Previous"]
                rate = diff / hours if hours > 0 else np.nan
                upper_rates[n][f"Upper_{sheet}"] = rate if rate > 0 else np.nan

            l_row = lower_df_sheet[lower_df_sheet["No_Lower"] == n]
            if not l_row.empty:
                diff = l_row.iloc[0]["Lower_Previous"] - l_row.iloc[0]["Lower_Current"]
                rate = diff / hours if hours > 0 else np.nan
                lower_rates[n][f"Lower_{sheet}"] = rate if rate > 0 else np.nan

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


def avg_positive(rate_dict):
    valid = [v for v in rate_dict.values() if v > 0]
    return sum(valid) / len(valid) if valid else 0
