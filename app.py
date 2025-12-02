import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. 페이지 설정 (전문적인 느낌) ---
st.set_page_config(page_title="LFG 통합 관제 시스템", layout="wide", page_icon="🏭")

# 스타일링 (박스 디자인, 폰트 등)
st.markdown("""
    <style>
    .stMetric {
        background-color: #ffffff;
        border: 1px solid #dcdcdc;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stHeader {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 불러오기 ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60) # 1분마다 새로고침
def load_data():
    # 구글 시트 데이터 읽기
    try:
        # 엑셀 헤더가 복잡하므로, 일단 불러온 뒤 필요한 컬럼만 추려냅니다.
        df = conn.read(worksheet="시트1") # 시트 이름이 '시트1'이 아니면 에러가 날 수 있음 (확인 필요)
        
        # 날짜 컬럼 처리 ('년월일' 컬럼이 있다고 가정)
        if '년월일' in df.columns:
            df['년월일'] = pd.to_datetime(df['년월일'], errors='coerce').dt.date
            df = df.sort_values(by='년월일')
            
        return df
    except Exception as e:
        st.error(f"데이터를 불러오는데 실패했습니다. 시트 이름이 '시트1'이 맞는지 확인해주세요. 에러메시지: {e}")
        return pd.DataFrame()

# --- 3. 헤더 섹션 ---
st.title("🏭 LFG 발전소 통합 운영 현황")
st.markdown(f"**Last Update:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# --- 4. 탭 구성 (임원용 vs 입력용) ---
tab1, tab2 = st.tabs(["📊 경영진 대시보드 (Dashboard)", "📝 데이터 입력/수정 (Data Entry)"])

# === TAB 1: 대시보드 ===
with tab1:
    df = load_data()
    
    if not df.empty:
        # 최신 데이터 가져오기 (마지막 행)
        latest = df.iloc[-1]
        # 전일 데이터 (마지막에서 두번째 행)
        prev = df.iloc[-2] if len(df) > 1 else latest

        # KPI 섹션 (핵심 지표)
        st.subheader("📌 Today's Key Metrics")
        k1, k2, k3, k4 = st.columns(4)

        # 1. 공급량
        val_supply = latest.get('공급량', 0)
        delta_supply = val_supply - prev.get('공급량', 0)
        k1.metric("일일 공급량", f"{val_supply:,.0f} Nm3", f"{delta_supply:,.0f} Nm3")

        # 2. 메탄 농도 (컬럼명이 복잡해서 '포함'된 단어로 찾음)
        # 사진상의 컬럼명: "평균메탄함량\n(%) [ B ]" 처럼 줄바꿈이 있을 수 있음
        methane_col = [c for c in df.columns if '메탄' in c][0] # '메탄'이 들어간 첫번째 컬럼 찾기
        val_methane = latest.get(methane_col, 0)
        delta_methane = val_methane - prev.get(methane_col, 0)
        k2.metric("평균 메탄 농도", f"{val_methane:.2f} %", f"{delta_methane:.2f} %")

        # 3. 판매액
        val_sales = latest.get('판매액', 0)
        delta_sales = val_sales - prev.get('판매액', 0)
        k3.metric("예상 판매액", f"{val_sales:,.0f} 원", f"{delta_sales:,.0f} 원")

        # 4. 근무자 정보
        day_worker = latest.get('Daytime', '-')
        night_worker = latest.get('Nighttime', '-')
        k4.info(f"☀️ **주간:** {day_worker}\n\n🌙 **야간:** {night_worker}")

        st.divider()

        # 차트 섹션
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📈 일별 공급량 추이")
            # 최근 30일치만 그래프로 그리기
            chart_df = df.tail(30).set_index('년월일')
            st.line_chart(chart_df['공급량'], color="#0068C9")
            
        with c2:
            st.subheader("🔥 메탄 농도 변화")
            st.area_chart(chart_df[methane_col], color="#FF2B2B")

    else:
        st.warning("데이터가 없습니다. 구글 시트를 확인해주세요.")


# === TAB 2: 데이터 관리 ===
with tab2:
    st.info("💡 엑셀처럼 값을 수정하고, 엔터(Enter)를 치세요. 다 고친 후에는 꼭 [변경사항 저장] 버튼을 눌러야 합니다.")
    
    # 데이터 에디터 (수정 가능)
    edited_df = st.data_editor(
        df,
        num_rows="dynamic", # 행 추가 가능
        use_container_width=True,
        height=600
    )

    if st.button("💾 변경사항 저장 (Google Sheet 동기화)", type="primary"):
        try:
            conn.update(worksheet="시트1", data=edited_df)
            st.success("저장되었습니다! 잠시 후 새로고침 됩니다.")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"저장 실패! 에러 내용: {e}")
