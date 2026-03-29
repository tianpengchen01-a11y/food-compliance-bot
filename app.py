"""
食品合规审查助手 - Streamlit 简化版
保留 PDF 读取功能
"""
import streamlit as st
import json
import tempfile
from io import BytesIO

# ============================================
# Streamlit 配置
# ============================================
st.set_page_config(
    page_title="食品合规审查助手",
    page_icon="🔍",
    layout="wide"
)

# ============================================
# 知识库数据（内嵌）
# ============================================
PROHIBITED_WORDS = {
    "医疗术语": ["治疗", "治愈", "药效", "疗效", "处方", "药方", "临床验证", "医学验证"],
    "疾病声称": ["糖尿病", "高血压", "心脏病", "癌症", "肿瘤", "抗癌", "防癌", "降血糖", "降血压"],
    "绝对化用语": ["100%", "零添加", "无添加", "第一", "唯一", "顶级", "最佳", "最好", "最强"],
    "功效承诺": ["减肥", "瘦身", "美白", "抗衰老", "延缓衰老", "美容养颜"],
    "低GI相关": ["低GI", "低升糖", "低血糖指数"]
}

REGULATIONS = {
    "广告法第十七条": {
        "content": "除医疗、药品、医疗器械广告外，禁止其他任何广告涉及疾病治疗功能，并不得使用医疗用语或者易使推销的商品与药品、医疗器械相混淆的用语。",
        "applies_to": ["普通食品不得宣传疾病治疗功能", "不得使用医疗术语"]
    },
    "广告法第九条": {
        "content": "广告不得使用'国家级'、'最高级'、'最佳'等用语。",
        "applies_to": ["禁止绝对化用语"]
    },
    "GB 7718-2011": {
        "content": "预包装食品标签应真实、准确，不得含有虚假内容，不得明示或暗示具有预防、治疗疾病作用。",
        "applies_to": ["食品标签标识"]
    },
    "GB 28050-2011": {
        "content": "营养成分表应标示能量、蛋白质、脂肪、碳水化合物、钠的含量及其占营养素参考值（NRV）百分比。",
        "applies_to": ["营养标签"]
    },
    "WS/T 652-2019": {
        "content": "低GI食品：GI值≤55，需提供依据本标准测定的GI值检测报告。",
        "applies_to": ["低GI声称必须有检测报告"]
    }
}

# ============================================
# 审查逻辑
# ============================================
def review_content(content: str) -> dict:
    """
    基于规则的本地审查
    """
    violations = []
    suggestions = []
    risk_level = "low"
    
    content_lower = content.lower()
    
    # 检查禁用词
    for category, words in PROHIBITED_WORDS.items():
        for word in words:
            if word.lower() in content_lower:
                import re
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                matches = pattern.findall(content)
                matched_word = matches[0] if matches else word
                
                regulation = "《中华人民共和国广告法》"
                regulation_detail = ""
                
                if category in ["医疗术语", "疾病声称"]:
                    regulation = "《中华人民共和国广告法》第十七条"
                    regulation_detail = REGULATIONS["广告法第十七条"]["content"]
                    risk_level = "high"
                elif category == "绝对化用语":
                    regulation = "《中华人民共和国广告法》第九条"
                    regulation_detail = REGULATIONS["广告法第九条"]["content"]
                    if risk_level != "high":
                        risk_level = "medium"
                elif category == "低GI相关":
                    regulation = "WS/T 652-2019《食物血糖生成指数测定方法》"
                    regulation_detail = REGULATIONS["WS/T 652-2019"]["content"]
                    if risk_level != "high":
                        risk_level = "medium"
                else:
                    if risk_level not in ["high", "medium"]:
                        risk_level = "medium"
                
                violations.append({
                    "risk_point": matched_word,
                    "category": category,
                    "regulation": regulation,
                    "regulation_detail": regulation_detail,
                    "description": f"发现「{matched_word}」，属于【{category}】类别"
                })
    
    # 生成修改建议
    if violations:
        seen_categories = set()
        for v in violations:
            cat = v["category"]
            if cat not in seen_categories:
                seen_categories.add(cat)
                
                if cat in ["医疗术语", "疾病声称"]:
                    suggestions.append("❌ 删除所有医疗相关表述，普通食品禁止涉及疾病治疗功能")
                elif cat == "绝对化用语":
                    suggestions.append("❌ 避免使用绝对化用语，改为客观描述（如'精选原料'替代'100%天然'）")
                elif cat == "低GI相关":
                    suggestions.append("⚠️ 如需保留低GI声称，必须提供WS/T 652-2019标准检测报告（GI≤55）")
                elif cat == "功效承诺":
                    suggestions.append("❌ 删除功效承诺表述，普通食品不得宣称保健功效")
    
    return {
        "risk_level": risk_level,
        "violations": violations,
        "suggestions": suggestions
    }


def extract_pdf_text(pdf_file) -> str:
    """
    从 PDF 文件提取文本
    """
    try:
        from pypdf import PdfReader
        
        pdf_bytes = pdf_file.read()
        reader = PdfReader(BytesIO(pdf_bytes))
        
        text_content = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_content.append(text)
        
        return "\n\n".join(text_content)
    
    except Exception as e:
        return f"PDF 解析失败: {str(e)}"


# ============================================
# UI 界面
# ============================================
st.title("🔍 食品合规审查助手")
st.markdown("基于 **GB 7718、GB 28050、广告法、WS/T 652-2019** 等法规标准")
st.markdown("---")

# 输入方式选择
tab1, tab2 = st.tabs(["📝 文本审查", "📄 PDF 文件审查"])

# 文本审查
with tab1:
    st.markdown("### 输入待审查内容")
    
    example = st.selectbox(
        "快速填充示例",
        ["", "示例1：低GI声称（高风险）", "示例2：营养成分表", "示例3：宣传文案"]
    )
    
    default_text = ""
    if "低GI" in example:
        default_text = """产品名称：慢糖饱饱低GI饼干

产品声称：
本产品采用低GI配方，GI值仅为45，适合糖尿病患者食用，具有降血糖功效。

配料表：
小麦粉、赤藓糖醇、抗性糊精、植物油、鸡蛋、食用盐"""
    elif "营养成分" in example:
        default_text = """营养成分表（每100g）
能量：1500 kJ
蛋白质：8.5 g
脂肪：12.0 g
  - 饱和脂肪：3.2 g
碳水化合物：65.0 g
  - 糖：5.0 g
膳食纤维：12.0 g
钠：350 mg"""
    elif "宣传文案" in example:
        default_text = """宣传文案：
100%天然原料，无任何添加剂
健康首选，营养专家力荐
适合全家人食用
国家认证，品质保证"""
    
    text_content = st.text_area(
        "文本内容",
        value=default_text,
        height=200,
        placeholder="请输入需要审查的文本内容..."
    )
    
    if st.button("🔍 开始审查", type="primary", key="review_text"):
        if not text_content.strip():
            st.warning("请输入内容")
        else:
            with st.spinner("正在分析..."):
                result = review_content(text_content)
            
            st.markdown("---")
            st.markdown("### 📋 审查结果")
            
            risk_badges = {
                "high": ("🔴", "高风险", "#ffebee", "#c62828"),
                "medium": ("🟡", "中风险", "#fff8e1", "#f57c00"),
                "low": ("🟢", "低风险", "#e8f5e9", "#2e7d32")
            }
            icon, label, bg_color, text_color = risk_badges.get(
                result.get('risk_level', 'low'), 
                ("⚪", "未知", "#f5f5f5", "#666")
            )
            
            st.markdown(f"""
            <div style="background-color: {bg_color}; color: {text_color}; 
                        padding: 10px 20px; border-radius: 20px; display: inline-block; 
                        font-weight: bold; margin-bottom: 20px;">
                {icon} {label}
            </div>
            """, unsafe_allow_html=True)
            
            if result.get("violations"):
                st.markdown("#### ⚠️ 发现违规项")
                for v in result["violations"]:
                    with st.expander(f"**{v.get('risk_point', '')}** - {v.get('category', '')}", expanded=True):
                        st.markdown(f"**问题描述**: {v.get('description', '')}")
                        st.markdown(f"**法规依据**: {v.get('regulation', '')}")
                        if v.get('regulation_detail'):
                            st.markdown(f"**法规原文**: {v.get('regulation_detail')}")
            else:
                st.success("✅ 未发现明显违规项")
            
            if result.get("suggestions"):
                st.markdown("#### 💡 修改建议")
                for s in result["suggestions"]:
                    st.info(s)

# PDF 文件审查
with tab2:
    st.markdown("### 上传 PDF 文件")
    st.markdown("支持解析 PDF 文档内容并审查")
    
    pdf_file = st.file_uploader("选择 PDF 文件", type=["pdf"])
    
    if pdf_file:
        st.info(f"📄 已选择文件: {pdf_file.name}")
    
    if st.button("🔍 开始审查", type="primary", key="review_pdf"):
        if not pdf_file:
            st.warning("请上传 PDF 文件")
        else:
            with st.spinner("正在解析 PDF 文件..."):
                pdf_text = extract_pdf_text(pdf_file)
            
            if pdf_text.startswith("PDF 解析失败"):
                st.error(pdf_text)
            else:
                st.success(f"✅ 成功提取文本内容（共 {len(pdf_text)} 字符）")
                
                with st.expander("📄 查看提取的内容"):
                    st.text_area("PDF 内容", pdf_text, height=200)
                
                with st.spinner("正在审查..."):
                    result = review_content(pdf_text)
                
                st.markdown("---")
                st.markdown("### 📋 审查结果")
                
                risk_badges = {
                    "high": ("🔴", "高风险", "#ffebee", "#c62828"),
                    "medium": ("🟡", "中风险", "#fff8e1", "#f57c00"),
                    "low": ("🟢", "低风险", "#e8f5e9", "#2e7d32")
                }
                icon, label, bg_color, text_color = risk_badges.get(
                    result.get('risk_level', 'low'), 
                    ("⚪", "未知", "#f5f5f5", "#666")
                )
                
                st.markdown(f"""
                <div style="background-color: {bg_color}; color: {text_color}; 
                            padding: 10px 20px; border-radius: 20px; display: inline-block; 
                            font-weight: bold; margin-bottom: 20px;">
                    {icon} {label}
                </div>
                """, unsafe_allow_html=True)
                
                if result.get("violations"):
                    st.markdown("#### ⚠️ 发现违规项")
                    for v in result["violations"]:
                        with st.expander(f"**{v.get('risk_point', '')}** - {v.get('category', '')}"):
                            st.markdown(f"**问题描述**: {v.get('description', '')}")
                            st.markdown(f"**法规依据**: {v.get('regulation', '')}")
                else:
                    st.success("✅ 未发现明显违规项")
                
                if result.get("suggestions"):
                    st.markdown("#### 💡 修改建议")
                    for s in result["suggestions"]:
                        st.info(s)

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>© 2024 慢糖饱饱 · 食品合规审查系统</p>
    <p>依据法规：GB 7718、GB 28050、广告法、WS/T 652-2019</p>
</div>
""", unsafe_allow_html=True)
