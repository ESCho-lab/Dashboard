import streamlit as st
import pandas as pd
from datetime import datetime

# 1. 페이지 제목 설정
st.set_page_config(page_title="LFG 관제 시스템", layout="wide")
st.title("🏭 LFG(매립가스) 통합 관제 대시보드")

# 2. 임시 데이터 저장소 (웹사이트 켜져있는 동안만 유지)
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["날짜", "포집량", "공급량", "이슈"])

# 3. 사이드바 (입력창)
with st.sidebar:
    st.header("📝 현장 데이터 입력")
    with st.form("my_form", clear_on_submit=True):
        date = st.date_input("날짜", datetime.now())
        input_vol = st.number_input("포집량 (Nm3)", min_value=0)
        output_vol = st.number_input("공급량 (Nm3)", min_value=0)
        issue = st.text_area("특이사항")
        submitted = st.form_submit_button("데이터 저장")
        
        if submitted:
            new_data = {"날짜": date, "포집량": input_vol, "공급량": output_vol, "이슈": issue}
            st.session_state.data = pd.concat([st.session_state.data, pd.DataFrame([new_data])], ignore_index=True)
            st.success("저장 완료!")

# 4. 메인 화면 (대시보드)
st.subheader("📊 실시간 운영 현황")

if not st.session_state.data.empty:
    # 차트 그리기
    df = st.session_state.data
    st.line_chart(df.set_index("날짜")[["포집량", "공급량"]])
    
    # 데이터 표 보여주기
    st.dataframe(df, use_container_width=True)
else:
    st.info("👈 왼쪽 사이드바에서 데이터를 입력하면 그래프가 그려집니다.")
