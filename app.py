import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import altair as alt

# --- 1. 페이지 설정 (Corporate Style) ---
st.set_page_config(
    page_title="DAESUNG ECO-ENERGY | 통합 관제 시스템",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 전문적인 기업용 CSS (SCADA/Dashboard 느낌) ---
st.markdown("""
    <style>
    /* 전체 배경 및 폰트 */
    .stApp {
        background-color: #f0f2f6;
    }
    
    /* 상단 헤더 스타일 */
    .header-container {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* 카드(박스) 스타일 */
    .metric-card {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        border-left: 5px solid #3b82f6; /* 포인트 컬러 */
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* 근무자 박스 스타일 */
    .shift-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .shift-title {
        font-size: 14px;
        color: #64748b;
        font-weight: 600;
        margin-bottom: 5px;
    }
    .shift-name {
        font-size: 16px;
        color: #0f172a;
        font-weight: 700;
    }
    .shift-today {
        background-color: #eff6ff; /* 오늘 날짜 강조 배경 */
        border-color: #3b82f6;
    }

    /* KPI 텍스트 스타일 */
    .kpi-label { font-size: 14px; color: #64748b; font-weight: 500; }
    .kpi-value { font-size: 32px; color: #1e293b; font-weight: 800; margin: 5px 0; }
    .kpi-delta { font-size: 14px; font-weight: 600; }
    .positive { color: #10b981; } /* 초록 */
    .negative { color: #ef4444; } /* 빨강 */
    
    </style>
    """, unsafe_allow_html=True)

# --- 3. 데이터 로드 및 전처리 (강력한 매핑 적용) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        # worksheet=0 (첫번째 시트)
        df = conn.read(worksheet=0)
        
        # 1. 컬럼명 전처리 (줄바꿈 제거 및 공백 제거)
        # 엑셀 헤더에 '공급량\n(Nm3)' 처럼 줄바꿈이 있으면 파이썬이 못 찾습니다. 이를 해결합니다.
        df.columns = [c.replace('\n', '').replace(' ', '') for c in df.columns]

        # 2. 핵심 컬럼 찾기 (포함된 단어로 찾기)
        col_map = {}
        for c in df.columns:
            if '년월일' in c or 'Date' in c: col_map['Date'] = c
            elif '공급량' in c and '곱' not in c: col_map['Supply'] = c # '공급시간 곱' 제외
            elif '포집량' in c: col_map['Capture'] = c
            elif '소각량' in c: col_map['Incineration'] = c
            elif '판매액' in c: col_map['Sales'] = c
            elif '메탄' in c or 'CH4' in c: col_map['Methane'] = c
            elif 'Day' in c or '주간' in c: col_map['DayWorker'] = c
            elif 'Night' in c or '야간' in c: col_map['NightWorker'] = c

        # 3. 데이터 정제
        if 'Date' in col_map:
            df[col_map['Date']] = pd.to_datetime(df[col_map['Date']], errors='coerce').dt.date
            df = df.rename(columns={col_map['Date']: 'Date'})
        else:
            # 날짜 컬럼을 못 찾으면 무조건 첫번째 컬럼을 날짜로 지정
            df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date

        # 숫자 컬럼 쉼표 제거 및 변환
        numeric_keys = ['Supply', 'Capture', 'Incineration', 'Sales', 'Methane']
        for key in numeric_keys:
            if key in col_map:
                col_name = col_map[key]
                if df[col_name].dtype == 'object':
                    df[col_name] = df[col_name].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce')
                df = df.rename(columns={col_name: key}) # 코드에서 쓰기 쉽게 영어이름으로 변경

        # 근무자 컬럼 이름 변경
        if 'DayWorker' in col_map: df = df.rename(columns={col_map['DayWorker']: 'DayWorker'})
        if 'NightWorker' in col_map: df = df.rename(columns={col_map['NightWorker']: 'NightWorker'})

        return df.sort_values(by='Date')

    except Exception as e:
        st.error(f"데이터 로드 에러: {e}")
        return pd.DataFrame()

# --- 4. 사이드바 (날짜 선택 & 메뉴) ---
df = load_data()

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2936/2936758.png", width=50)
    st.title("통합 관제실")
    st.markdown("---")
    
    # [핵심 기능] 날짜 선택기 (기본값: 어제)
    # 실적은 보통 '어제 마감된 데이터'를 보므로 기본값을 어제로 설정
    default_date = datetime.now().date() - timedelta(days=1)
    selected_date = st.date_input("📅 데이터 조회 기준일", value=default_date)
    
    st.markdown("---")
    st.info("""
    **💡 사용 가이드**
    * **조회 기준일**을 변경하면 해당 일자의 실적을 볼 수 있습니다.
    * **근무자 현황**은 항상 오늘을 기준으로 표시됩니다.
    """)

# --- 5. 메인 화면 구성 ---

# (1) 헤더 섹션 (오늘 날짜 강조)
today = datetime.now().date()
st.markdown(f"""
<div class="header-container">
    <h1 style="margin:0; font-size:24px;">🏭 DAESUNG ECO-ENERGY DASHBOARD</h1>
    <p style="margin:5px 0 0 0; opacity:0.8;">시스템 가동 현황 | Today: {today.strftime('%Y-%m-%d (%A)')}</p>
</div>
""", unsafe_allow_html=True)

# (2) 근무자 현황 섹션 (어제 - 오늘 - 내일)
st.subheader("👮 Daily Shift Schedule (근무자 현황)")

# 근무자 데이터 찾기 함수
def get_worker(target_date):
    row = df[df['Date'] == target_date]
    if not row.empty:
        return row.iloc[0].get('DayWorker', '-'), row.iloc[0].get('NightWorker', '-')
    return '-', '-'

col_w1, col_w2, col_w3 = st.columns(3)

# 어제 근무자
y_day, y_night = get_worker(today - timedelta(days=1))
with col_w1:
    st.markdown(f"""
    <div class="shift-card">
        <div class="shift-title">Yesterday ({today - timedelta(days=1)})</div>
        <div class="shift-name">☀️ {y_day}<br>🌙 {y_night}</div>
    </div>
    """, unsafe_allow_html=True)

# 오늘 근무자 (강조)
t_day, t_night = get_worker(today)
with col_w2:
    st.markdown(f"""
    <div class="shift-card shift-today">
        <div class="shift-title" style="color:#3b82f6;">TODAY ({today})</div>
        <div class="shift-name" style="font-size:18px;">☀️ {t_day}<br>🌙 {t_night}</div>
    </div>
    """, unsafe_allow_html=True)

# 내일 근무자
tm_day, tm_night = get_worker(today + timedelta(days=1))
with col_w3:
    st.markdown(f"""
    <div class="shift-card">
        <div class="shift-title">Tomorrow ({today + timedelta(days=1)})</div>
        <div class="shift-name">☀️ {tm_day}<br>🌙 {tm_night}</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# (3) KPI 실적 섹션 (선택한 날짜 기준)
st.subheader(f"📊 Daily Performance Report ({selected_date} 기준)")

# 선택한 날짜의 데이터 가져오기
target_row = df[df['Date'] == selected_date]
prev_row = df[df['Date'] == selected_date - timedelta(days=1)]

if not target_row.empty:
    curr = target_row.iloc[0]
    prev = prev_row.iloc[0] if not prev_row.empty else None
    
    # KPI 카드 생성 함수
    def kpi_card(title, value, unit, prev_value=None, color_class="positive"):
        delta_html = ""
        if prev_value is not None:
            diff = value - prev_value
            icon = "▲" if diff > 0 else "▼"
            color = "positive" if diff >= 0 else "negative"
            delta_html = f"<div class='kpi-delta {color}'>{icon} {diff:,.0f} {unit} (전일비)</div>"
        
        return f"""
        <div class="metric-card">
            <div class="kpi-label">{title}</div>
            <div class="kpi-value">{value:,.0f} {unit}</div>
            {delta_html}
        </div>
        """

    col_k1, col_k2, col_k3 = st.columns(3)
    
    # 1. 공급량
    val_supply = curr.get('Supply', 0)
    prev_supply = prev.get('Supply', 0) if prev is not None else 0
    with col_k1:
        st.markdown(kpi_card("일일 LFG 공급량", val_supply, "Nm³", prev_supply), unsafe_allow_html=True)

    # 2. 매출액
    val_sales = curr.get('Sales', 0)
    prev_sales = prev.get('Sales', 0) if prev is not None else 0
    with col_k2:
        st.markdown(kpi_card("일일 예상 매출액", val_sales, "원", prev_sales), unsafe_allow_html=True)

    # 3. 메탄 농도 (단순 표시)
    val_methane = curr.get('Methane', 0)
    with col_k3:
        st.markdown(f"""
        <div class="metric-card" style="border-left-color: #10b981;">
            <div class="kpi-label">평균 메탄 농도 (CH₄)</div>
            <div class="kpi-value" style="color:#d35400;">{val_methane:.2f} %</div>
            <div class="kpi-delta" style="color:#64748b;">Target: 45% 이상</div>
        </div>
        """, unsafe_allow_html=True)

else:
    st.warning(f"⚠️ {selected_date} 일자의 데이터가 입력되지 않았습니다. 사이드바에서 날짜를 변경하거나 아래 입력 탭에서 데이터를 추가해주세요.")


# (4) 하단 탭 (차트 & 입력)
st.markdown("---")
tab1, tab2 = st.tabs(["📈 트렌드 분석 (Trend Analysis)", "📝 데이터 입력 및 수정 (Data Entry)"])

with tab1:
    st.markdown("##### 최근 30일간 공급량 및 메탄 농도 추이")
    if not df.empty:
        chart_data = df.tail(30)
        
        # Altair 차트: 공급량(막대) + 메탄(선)
        base = alt.Chart(chart_data).encode(x=alt.X('Date:T', title='날짜'))
        
        bar = base.mark_bar(color='#3b82f6', opacity=0.7).encode(
            y=alt.Y('Supply:Q', title='공급량 (Nm³)')
        )
        
        line = base.mark_line(color='#ef4444').encode(
            y=alt.Y('Methane:Q', title='메탄 농도 (%)', scale=alt.Scale(domain=[40, 60]))
        )
        
        c = (bar + line).resolve_scale(y='independent').properties(height=350)
        st.altair_chart(c, use_container_width=True)

with tab2:
    st.info("💡 데이터를 수정하면 구글 시트에 즉시 반영됩니다.")
    # 원본 데이터 읽어와서 에디터 표시
    raw_df = conn.read(worksheet=0)
    edited_df = st.data_editor(raw_df, num_rows="dynamic", use_container_width=True, height=500)
    
    if st.button("💾 변경사항 구글 시트에 저장", type="primary"):
        try:
            conn.update(worksheet=0, data=edited_df)
            st.success("저장되었습니다! 새로고침 됩니다.")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"저장 실패: {e}")
