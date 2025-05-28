

elif page == "📈 พล็อตกราฟตามเวลา (แยก Upper และ Lower)":
    st.title("📈 พล็อตกราฟตามเวลา (แยก Upper และ Lower)")

    # ✅ ใช้ Google Sheet เดียวทุกจุด
    sheet_id = "1Pd6ISon7-7n7w22gPs4S3I9N7k-6uODdyiTvsfXaSqY"
    @st.cache_data(ttl=300)
    def load_excel_bytes(sheet_url):
        response = requests.get(sheet_url)
        return response.content

    xls_bytes = load_excel_bytes(sheet_url_export)
    xls = pd.ExcelFile(BytesIO(xls_bytes), engine="openpyxl")

    sh = get_google_sheet()

    ws_sheet1 = sh.worksheet("Sheet1")  # ✅ เรียกแค่ครั้งเดียว



    # โหลดค่าความยาวจาก B45
    try:
        
        length_threshold = float(ws_sheet1.acell("B45").value)
    except:
        length_threshold = 35.0  # fallback
        
    # โหลด config จาก Sheet1
    sheet_count_config, min_required, threshold_percent, alert_threshold_hours, length_threshold = load_config_from_sheet(sh, "Sheet1")
    threshold = threshold_percent / 100

        
    sheet_names = [ws.title for ws in sh.worksheets()]
    filtered_sheet_names = [s for s in sheet_names if s.lower().startswith("sheet") and s.lower() != "sheet1"]
    
    avg_rate_upper = st.session_state.get("upper_avg", [0]*32)
    avg_rate_lower = st.session_state.get("lower_avg", [0]*32)

    
    
    
    if "Sheet1" in sheet_names:
        sheet_names.remove("Sheet1")
        sheet_names = ["Sheet1"] + sheet_names
        
        
        # ✅ 1. อ่านค่าจาก Google Sheet ก่อน
    try:
        sheet_save = int(ws_sheet1.acell("F40").value)
    except:
        sheet_save = 6

    # ✅ 2. แล้วจึงใช้ค่าที่ได้ไปตัดชื่อชีต
    selected_sheet_names = sheet_names[:sheet_save]
    
    
        # 📥 โหลดค่าคงที่จาก Sheet1
    try:
        min_required = int(ws_sheet1.acell("B42").value)
        threshold_percent = float(ws_sheet1.acell("B43").value)
        alert_threshold_hours = int(ws_sheet1.acell("B44").value)
        length_threshold = float(ws_sheet1.acell("B45").value)
    except:
        min_required = 5
        threshold_percent = 5.0
        alert_threshold_hours = 100
        length_threshold = 35.0

    threshold = threshold_percent / 100



    


    # ดึงชื่อชีตจริงจากไฟล์
    
    
    # 📥 โหลดค่าจำนวนชีตย้อนหลังเริ่มต้นจาก Sheet1!F40
    def safe_int(val, default=6):
        try:
            val_str = str(val).strip()
            if val_str.isdigit():
                return int(val_str)
            elif val_str.replace('.', '', 1).isdigit():
                return int(float(val_str))
            else:
                return default
        except:
            return default

    try:
        sheet_count_default = safe_int(ws_sheet1.acell("F40").value)
    except:
        sheet_count_default = 6


    # 📌 ให้ผู้ใช้กรอกจำนวนชีต (ใช้แบบ number_input)
    sheet_count = st.number_input("📌 เลือกจำนวน Sheet ที่ต้องใช้ ", min_value=1, max_value=len(sheet_names), value=sheet_save)

    # ✅ อัปเดตกลับไปยัง Sheet1!F40 ทันที
    try:
        ws_sheet1.update("F40", [[str(sheet_count)]])
    except Exception as e:
        st.warning(f"⚠️ ไม่สามารถอัปเดต Sheet1!F40 ได้: {e}")

    
    all_sheet_names = xls.sheet_names
    sheet_names = [s for s in all_sheet_names if s.lower().startswith("sheet")][:sheet_count]

    brush_numbers = list(range(1, 33))
    upper_rates, lower_rates = {n: {} for n in brush_numbers}, {n: {} for n in brush_numbers}

    for sheet in sheet_names:
        df_raw = xls.parse(sheet, header=None)
        try:
            hours = float(df_raw.iloc[0, 7])
        except:
            continue
        df = xls.parse(sheet, skiprows=2, header=None)

        lower_df = df.iloc[:, 0:3]
        lower_df.columns = ["No_Lower", "Lower_Previous", "Lower_Current"]
        lower_df = lower_df.dropna().apply(pd.to_numeric, errors='coerce')

        upper_df = df.iloc[:, 4:6]
        upper_df.columns = ["Upper_Current", "Upper_Previous"]
        upper_df = upper_df.dropna().apply(pd.to_numeric, errors='coerce')
        upper_df["No_Upper"] = range(1, len(upper_df) + 1)

        for n in brush_numbers:
            u_row = upper_df[upper_df["No_Upper"] == n]
            if not u_row.empty:
                diff = u_row.iloc[0]["Upper_Current"] - u_row.iloc[0]["Upper_Previous"]
                rate = diff / hours if hours > 0 else np.nan
                upper_rates[n][f"Upper_{sheet}"] = rate if rate > 0 else np.nan

            l_row = lower_df[lower_df["No_Lower"] == n]
            if not l_row.empty:
                diff = l_row.iloc[0]["Lower_Previous"] - l_row.iloc[0]["Lower_Current"]
                rate = diff / hours if hours > 0 else np.nan
                lower_rates[n][f"Lower_{sheet}"] = rate if rate > 0 else np.nan

    def avg_positive(row_dict):
        values = [v for v in row_dict.values() if pd.notna(v) and v > 0]
        return sum(values) / len(values) if values else np.nan
    
    def determine_final_rate(previous_rates, new_rate, row_index, sheet_name, mark_dict, min_required=5, threshold=0.1):
        previous_rates = [r for r in previous_rates if pd.notna(r) and r > 0]
        if len(previous_rates) >= min_required:
            avg_rate = sum(previous_rates) / len(previous_rates)
            percent_diff = abs(new_rate - avg_rate) / avg_rate
            if percent_diff <= threshold:
                mark_dict[row_index] = sheet_name
                return round(avg_rate, 6), True
        combined = previous_rates + [new_rate] if new_rate > 0 else previous_rates
        final_avg = sum(combined) / len(combined) if combined else 0
        return round(final_avg, 6), False

    def calc_avg_with_flag(rates_dict, rate_fixed_set, mark_dict,min_required, threshold):
        df = pd.DataFrame.from_dict(rates_dict, orient='index')
        df = df.reindex(range(1, 33)).fillna(0)
        avg_col = []
        for i, row in df.iterrows():
            values = row[row > 0].tolist()
            if len(values) >= min_required:
                prev = values[:-1]
                new = values[-1]
                sheet_name = row[row > 0].index[-1] if len(row[row > 0].index) > 0 else ""
                avg, fixed = determine_final_rate(prev, new, i, sheet_name, mark_dict)
                avg_col.append(avg)
                if fixed:
                    rate_fixed_set.add(i)
            else:
                avg_col.append(round(np.mean(values), 6) if values else 0.000000)
        return df, avg_col
    

    # ใช้ calc_avg_with_flag ที่คุณมีอยู่แล้ว
    rate_fixed_upper = set()
    rate_fixed_lower = set()
    yellow_mark_upper = {}
    yellow_mark_lower = {}

    upper_df, avg_rate_upper = calc_avg_with_flag(upper_rates, rate_fixed_upper, yellow_mark_upper, min_required, threshold)
    lower_df, avg_rate_lower = calc_avg_with_flag(lower_rates, rate_fixed_lower, yellow_mark_lower, min_required, threshold)




 

    # ใช้ current จาก sheet ล่าสุด เช่น Sheet{sheet_count}
    df_current = xls.parse(f"Sheet{sheet_count}", header=None, skiprows=2)
    upper_current = pd.to_numeric(df_current.iloc[0:32, 5], errors='coerce').values
    lower_current = pd.to_numeric(df_current.iloc[0:32, 2], errors='coerce').values

    time_hours = np.arange(0, 201, 10)

    # UPPER
    fig_upper = go.Figure()
    for i, (start, rate) in enumerate(zip(upper_current, avg_rate_upper)):
        if pd.notna(start) and pd.notna(rate) and rate > 0:
            y = [start - rate*t for t in time_hours]
            fig_upper.add_trace(go.Scatter(x=time_hours, y=y, name=f"Upper {i+1}", mode='lines'))

# เส้นแจ้งเตือนตามค่าความยาวที่ต้องการ
    fig_upper.add_shape(type="line", x0=0, x1=200, y0=length_threshold, y1=length_threshold,
                        line=dict(color="firebrick", width=2, dash="dash"))

    fig_upper.add_annotation(x=5, y=length_threshold,
                            text=f"⚠️ {length_threshold:.1f} mm",
                            showarrow=False,
                            font=dict(color="firebrick", size=12),
                            bgcolor="white")


    fig_upper.update_layout(title="🔺 ความยาว Upper ตามเวลา", xaxis_title="ชั่วโมง", yaxis_title="mm",
                            xaxis=dict(dtick=10, range=[0, 200]), yaxis=dict(range=[30, 65]))
    st.plotly_chart(fig_upper, use_container_width=True)

    # LOWER
    fig_lower = go.Figure()
    for i, (start, rate) in enumerate(zip(lower_current, avg_rate_lower)):
        if pd.notna(start) and pd.notna(rate) and rate > 0:
            y = [start - rate*t for t in time_hours]
            fig_lower.add_trace(go.Scatter(x=time_hours, y=y, name=f"Lower {i+1}", mode='lines', line=dict(dash='dot')))

    fig_lower.add_shape(type="line", x0=0, x1=200, y0=length_threshold, y1=length_threshold,
                        line=dict(color="firebrick", width=2, dash="dash"))
    fig_lower.add_annotation(x=5, y=length_threshold,
                            text=f"⚠️  {length_threshold:.1f} mm",
                            showarrow=False,
                            font=dict(color="firebrick", size=12),
                            bgcolor="white")
    fig_lower.update_layout(title="🔺 ความยาว Lower ตามเวลา", xaxis_title="ชั่วโมง", yaxis_title="mm",
                        xaxis=dict(dtick=10, range=[0, 200]), yaxis=dict(range=[30, 65]))
    st.plotly_chart(fig_lower, use_container_width=True)

