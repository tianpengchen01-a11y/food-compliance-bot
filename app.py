"""
食品合规审查助手 - Streamlit 版本
"""
import streamlit as st
import json

st.set_page_config(page_title="食品合规审查助手", page_icon="🔍", layout="wide")

# 知识库
PROHIBITED_WORDS = {
    "医疗术语": ["治疗", "治愈", "药效", "疗效", "处方", "药方"],
    "疾病声称": ["糖尿病", "高血压", "心脏病", "抗癌", "防癌"],
    "绝对化用语": ["100%", "零添加", "无添加", "第一", "唯一"],
    "功效承诺": ["降血糖", "降血压", "减肥", "瘦身"]
}

def review_content(content: str) -> dict:
    violations = []
    risk_level = "low"
    for category, words in PROHIBITED_WORDS.items():
        for word in words:
            if word in content:
                violations.append({"risk_point": word, "category": category})
                if category in ["医疗术语", "疾病声称"]:
                    risk_level = "high"
                elif risk_level != "high":
                    risk_level = "medium"
    return {"risk_level": risk_level, "violations": violations}

# UI
st.title("🔍 食品合规审查助手")
st.markdown("基于 GB 7718、GB 28050、广告法 等法规标准")

text = st.text_area("输入待审查内容", height=200)
if st.button("开始审查"):
    result = review_content(text)
    st.write(f"风险等级: {result['risk_level']}")
    st.write("违规项:", result['violations'])
