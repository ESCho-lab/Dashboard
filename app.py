import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import altair as alt

# --- 1. 페이지 설정 (넓은 레이아웃, 아이콘) ---
st.set_page_config(
    page_title="대성에코에너지 통합 관제",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. 전문적인 디자인을 위한 CSS (카드 스타일, 폰트 등) ---
st.markdown("""
    <style>
    /* 전체 배경색 조정 */
    .stApp {
        background-color: #f8f9fa;
    }
    /* 카드 박스 스타일 (흰색 배경, 그림자) */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 10px;
    }
    /* 텍스트 스타일 */
    .metric-label {
        font-size: 14px;
        color: #6c757d;
        font-weight: 500;
    }
    .metric-value {
        font-size: 28px;
        color: #212529;
        font-weight: 700;
        margin: 10px 0;
    }
    .metric-delta {
        font-size: 14px;
        font-weight: 600;
    }
    .positive { color: #28a745; }
    .negative { color: #dc3545; }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        padding: 10px 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 데이터 로드 및 전처리 ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        # [핵심 수정] worksheet=0 (첫번째 시트)으로 지정하여 한글 에러 방지
        df = conn.read(worksheet=0)
        
        # 1. 날짜 처리 (첫번째 컬럼을 날짜로 간주)
        date_col = df.columns[0]
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.date
        df = df.rename(columns={date_col: 'Date'}) # 코드 편의를 위해 컬럼명 통일
        
        # 2. 숫자 변환 (콤마 제거)
        cols_to_numeric = ['포집량', '소각량', '공급량', '판매액'] # 엑셀의 핵심 컬럼명 포함 여부 확인
        
        # 컬럼명 매핑 (비슷한 이름 찾기)
        mapped_cols = {}
        for col in df.columns:
            if '포집' in col: mapped_cols['Capture'] = col
            elif '소각' in col: mapped_cols['Incineration'] = col
            elif '공급량' in col: mapped_cols['Supply'] = col
            elif '판매' in col: mapped_cols['Sales'] = col
            elif '메탄' in col: mapped_cols['Methane'] = col
            elif 'Day' in col: mapped_cols['DayWorker'] = col
            elif 'Night' in col: mapped_cols['NightWorker'] = col

        # 숫자 데이터 정제
        for key, col_name in mapped_cols.items():
            if key in ['Capture', 'Incineration', 'Supply', 'Sales', 'Methane']:
                if df[col_name].dtype == 'object':
                    df[col_name] = df[col_name].astype(str).str.replace(',', '').apply(pd.to_numeric, errors='coerce')
        
        # 데이터프레임 컬럼명 표준화 (코딩 편의성)
        inverted_map = {v: k for k, v in mapped_cols.items()}
        df = df.rename(columns=inverted_map)
        
        return df.sort_values(by='Date')
        
    except Exception as e:
        st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

# --- 4. 메인 화면 구성 ---
df = load_data()

# 날짜 기준 설정 (어제 날짜)
today = datetime.now().date()
yesterday = today - timedelta(days=1)

# 헤더 섹션
c1, c2 = st.columns([3, 1])
with c1:
    st.title("🏭 Daesung Eco-Energy Dashboard")
    st.markdown(f"**기준일자: {yesterday.strftime('%Y년 %m월 %d일')} (전일 마감)**")
with c2:
    if not df.empty:
        last_update = datetime.now().strftime('%H:%M:%S')
        st.caption(f"Last Update: {last_update}")

st.divider()

# 데이터가 있을 경우 대시보드 표시
if not df.empty:
    
    # ---------------------------------------------------------
    # [섹션 1] Daily Report (전일 실적) - 메인 포커스
    # ---------------------------------------------------------
    st.subheader("1️⃣ Previous Day Report (전일 실적)")
    
    # 어제 데이터 필터링
    daily_data = df[df['Date'] == yesterday]
    
    if not daily_data.empty:
        row = daily_data.iloc[0]
        
        # 3단 컬럼 구성
        col1, col2, col3 = st.columns(3)
        
        # HTML/CSS를 이용한 커스텀 카드 위젯 함수
        def metric_card(label, value, delta=None, unit=""):
            delta_html = ""
            if delta is not None:
                color = "positive" if delta >= 0 else "negative"
                sign = "+" if delta > 0 else ""
                delta_html = f"<div class='metric-delta {color}'>{sign}{delta:,.0f} {unit} (전일비)</div>"
            
            return f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value:,.0f} {unit}</div>
                {delta_html}
            </div>
            """

        # 전전일 데이터 (비교용)
        day_before = yesterday - timedelta(days=1)
        prev_data = df[df['Date'] == day_before]
        prev_row = prev_data.iloc[0] if not prev_data.empty else None

        # 1. 공급량 카드
        supply_val = row.get('Supply', 0)
        supply_delta = supply_val - prev_row.get('Supply', 0) if prev_row is not None else 0
        with col1:
            st.markdown(metric_card("일일 LFG 공급량", supply_val, supply_delta, "Nm³"), unsafe_allow_html=True)

        # 2. 매출액 카드
        sales_val = row.get('Sales', 0)
        sales_delta = sales_val - prev_row.get('Sales', 0) if prev_row is not None else 0
        with col2:
            st.markdown(metric_card("일일 매출액 (예상)", sales_val, sales_delta, "원"), unsafe_allow_html=True)

        # 3. 메탄 농도 (단순 표시)
        methane_val = row.get('Methane', 0)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">평균 메탄 농도 (CH₄)</div>
                <div class="metric-value" style="color:#d35400;">{methane_val:.2f} %</div>
                <div class="metric-delta">Target: 45% 이상</div>
            </div>
            """, unsafe_allow_html=True)
            
        # 근무자 정보 표시 (Alert 스타일)
        st.info(f"👮 **전일 근무자 현황** | 주간: {row.get('DayWorker', '-')} | 야간: {row.get('NightWorker', '-')}")

    else:
        st.warning(f"⚠️ {yesterday} 일자 데이터가 아직 입력되지 않았습니다.")

    st.markdown("---")

    # ---------------------------------------------------------
    # [섹션 2] Monthly & Annual Overview (누적 데이터)
    # ---------------------------------------------------------
    st.subheader("2️⃣ Period Overview (기간별 누적)")
    
    # 월간/연간 필터링
    this_month = df[(df['Date'] >= yesterday.replace(day=1)) & (df['Date'] <= yesterday)]
    this_year = df[(df['Date'] >= yesterday.replace(month=1, day=1)) & (df['Date'] <= yesterday)]

    m_col1, m_col2, m_col3 = st.columns(3)

    # 월간 누적 공급량
    with m_col1:
        monthly_supply = this_month['Supply'].sum()
        st.markdown(metric_card("이번 달 누적 공급량 (Monthly)", monthly_supply, unit="Nm³"), unsafe_allow_html=True)

    # 연간 누적 포집량 (요청사항 반영)
    with m_col2:
        yearly_capture = this_year['Capture'].sum() if 'Capture' in df.columns else 0
        st.markdown(metric_card("연간 누적 포집량 (Yearly)", yearly_capture, unit="Nm³"), unsafe_allow_html=True)

    # 연간 누적 소각량 (요청사항 반영)
    with m_col3:
        yearly_incin = this_year['Incineration'].sum() if 'Incineration' in df.columns else 0
        st.markdown(metric_card("연간 누적 소각량 (Yearly)", yearly_incin, unit="Nm³"), unsafe_allow_html=True)

    st.markdown("---")

    # ---------------------------------------------------------
    # [섹션 3] Charts & Data Management (탭 구성)
    # ---------------------------------------------------------
    tab_chart, tab_data = st.tabs(["📈 트렌드 분석 (Trend)", "📝 데이터 관리 (Input)"])

    with tab_chart:
        st.markdown("##### 최근 30일 공급량 추이")
        recent_df = df.tail(30)
        
        # Altair를 이용한 고급 차트
        chart = alt.Chart(recent_df).mark_area(
            line={'color':'#2980b9'},
            color=alt.Gradient(
                gradient='linear',
                stops=[alt.GradientStop(color='#2980b9', offset=0),
                       alt.GradientStop(color='rgba(255,255,255,0)', offset=1)],
                x1=1, x2=1, y1=1, y2=0
            )
        ).encode(
            x=alt.X('Date:T', title='날짜'),
            y=alt.Y('Supply:Q', title='공급량 (Nm³)'),
            tooltip=['Date', 'Supply', 'Methane']
        ).properties(height=300)
        
        st.altair_chart(chart, use_container_width=True)

    with tab_data:
        st.warning("데이터 수정 시, 엔터를 치고 우측 하단 [Save] 버튼을 눌러주세요.")
        
        # 원본 컬럼명으로 표시하기 위해 다시 로드하거나 매핑 전 데이터를 보여줄 수도 있음
        # 여기서는 편집 편의를 위해 매핑된 데이터프레임을 보여주되, 
        # 실제로는 Google Sheet 구조를 유지해야 하므로 load_data 로직과 별개로 raw read를 권장하지만,
        # 편의상 data_editor로 보여줍니다.
        
        raw_df = conn.read(worksheet=0) # 원본 그대로 호출
        edited_df = st.data_editor(raw_df, num_rows="dynamic", use_container_width=True)
        
        if st.button("구글 시트에 저장하기"):
            try:
                conn.update(worksheet=0, data=edited_df)
                st.success("저장 완료! 새로고침 됩니다.")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

else:
    st.info("데이터를 불러오는 중입니다. 잠시만 기다려주세요...")
