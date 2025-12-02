import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="LFG 통합 관제 시스템", layout="wide", page_icon="🏭")

# 스타일링
st.markdown("""
    <style>
    .stMetric {
        background-color: #ffffff;
        border: 1px solid #dcdcdc;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 불러오기 (핵심 수정 부분) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        # [핵심 수정] worksheet="시트1" 대신 숫자 0 (첫번째 시트)을 사용
        # 이렇게 하면 한글 이름 에러가 100% 해결됩니다.
        df = conn.read(worksheet=0) 
        
        # 데이터 전처리: 날짜 변환 (컬럼명이 '년월일'이 맞는지 확인)
        # 만약 엑셀의 첫번째 컬럼이 날짜라면, 컬럼 이름과 상관없이 첫번째를 날짜로 인식시킴
        if '년월일' in df.columns:
            target_col = '년월일'
        else:
            target_col = df.columns[0] # 첫번째 컬럼을 날짜로 가정

        df[target_col] = pd.to_datetime(df[target_col], errors='coerce').dt.date
        df = df.sort_values(by=target_col)
            
        return df
    except Exception as e:
        # 에러가 나면 화면에 보여줌
        st.error(f"데이터 로드 실패! 에러 메시지: {e}")
        return pd.DataFrame()

# --- 3. 헤더 섹션 ---
st.title("🏭 LFG 발전소 통합 운영 현황")
st.markdown(f"**Last Update:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# --- 4. 탭 구성 ---
tab1, tab2 = st.tabs(["📊 경영진 대시보드", "📝 데이터 입력/수정"])

# === TAB 1: 대시보드 ===
with tab1:
    df = load_data()
    
    if not df.empty:
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        st.subheader("📌 Today's Key Metrics")
        k1, k2, k3, k4 = st.columns(4)

        # 1. 공급량 (컬럼명에 '공급량'이 포함된 가장 첫번째 컬럼 찾기)
        try:
            col_supply = [c for c in df.columns if '공급량' in c and '#' not in c][0] 
            val_supply = latest.get(col_supply, 0)
            delta_supply = val_supply - prev.get(col_supply, 0)
            k1.metric("일일 공급량", f"{val_supply:,.0f}", f"{delta_supply:,.0f}")
        except:
            k1.metric("일일 공급량", "데이터 확인 필요", "0")

        # 2. 메탄 농도 ('메탄'이나 '함량'이 들어간 컬럼 찾기)
        try:
            col_methane = [c for c in df.columns if '메탄' in c or '함량' in c][0]
            val_methane = latest.get(col_methane, 0)
            delta_methane = val_methane - prev.get(col_methane, 0)
            k2.metric("평균 메탄 농도", f"{val_methane:.2f} %", f"{delta_methane:.2f} %")
        except:
            k2.metric("평균 메탄 농도", "데이터 확인 필요", "0")

        # 3. 판매액 ('판매액' 컬럼)
        try:
            col_sales = [c for c in df.columns if '판매액' in c][0]
            val_sales = latest.get(col_sales, 0)
            delta_sales = val_sales - prev.get(col_sales, 0)
            k3.metric("예상 판매액", f"{val_sales:,.0f} 원", f"{delta_sales:,.0f} 원")
        except:
             k3.metric("예상 판매액", "데이터 확인 필요", "0")

        # 4. 근무자
        day_worker = latest.get('Daytime', '-')
        night_worker = latest.get('Nighttime', '-')
        k4.info(f"☀️ 주간: {day_worker}\n\n🌙 야간: {night_worker}")

        st.divider()

        # 차트
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📈 일별 공급량 추이")
            # 날짜 컬럼 찾기 (위에서 처리한 타겟 컬럼 사용)
            date_col = df.columns[0] 
            if '공급량' in locals() or 'col_supply' in locals():
                chart_df = df.tail(30).set_index(date_col)
                st.line_chart(chart_df[col_supply], color="#0068C9")
            
        with c2:
            st.subheader("🔥 메탄 농도 변화")
            if 'col_methane' in locals():
                st.area_chart(chart_df[col_methane], color="#FF2B2B")

    else:
        st.warning("데이터가 비어있거나 불러오지 못했습니다.")


# === TAB 2: 데이터 관리 ===
with tab2:
    st.info("💡 수정 후 [변경사항 저장] 버튼을 꼭 눌러주세요.")
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        height=600
    )

    if st.button("💾 변경사항 저장 (Google Sheet 동기화)", type="primary"):
        try:
            # 저장할 때도 worksheet=0 (첫번째 시트) 사용
            conn.update(worksheet=0, data=edited_df)
            st.success("저장되었습니다! 새로고침 됩니다.")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"저장 실패! 에러 내용: {e}")
