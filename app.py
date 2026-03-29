"""
食品合规审查助手 - Streamlit 完整版
支持营养检测报告核对、配料表含量检查、条形码比对
"""
import streamlit as st
import json
import tempfile
import re
from io import BytesIO
from datetime import datetime

# ============================================
# Streamlit 配置
# ============================================
st.set_page_config(
    page_title="食品合规审查助手",
    page_icon="🔍",
    layout="wide"
)

# ============================================
# 知识库数据（内嵌）- 更新日期：2025年3月
# ============================================

# 营养声称库 - 需要检测报告支撑（依据GB 28050-2011）
NUTRITION_CLAIMS = {
    "无糖声称": {
        "keywords": ["无糖", "零糖", "0糖", "不含糖", "0蔗糖", "无蔗糖"],
        "requirement": "糖含量 ≤ 0.5g/100g（固体或液体）",
        "required_report": "营养成分检测报告（糖含量）",
        "nutrient": "糖",
        "unit": "g/100g",
        "threshold": 0.5,
        "regulation": "GB 28050-2011 表C.1"
    },
    "低糖声称": {
        "keywords": ["低糖", "少糖", "减糖"],
        "requirement": "糖含量 ≤ 5g/100g（固体）或 ≤ 5g/100mL（液体）",
        "required_report": "营养成分检测报告（糖含量）",
        "nutrient": "糖",
        "unit": "g/100g",
        "threshold": 5,
        "regulation": "GB 28050-2011 表C.1"
    },
    "高蛋白声称": {
        "keywords": ["高蛋白", "富含蛋白", "蛋白质丰富", "优质蛋白"],
        "requirement": "蛋白质含量 ≥ 20% NRV（≥12g/100g）或 ≥ 10% NRV（≥6g/100mL）",
        "required_report": "营养成分检测报告（蛋白质含量）",
        "nutrient": "蛋白质",
        "unit": "g/100g",
        "threshold": 12,
        "regulation": "GB 28050-2011 表C.1"
    },
    "蛋白质来源声称": {
        "keywords": ["含蛋白质", "蛋白来源", "补充蛋白"],
        "requirement": "蛋白质含量 ≥ 10% NRV（≥6g/100g）或 ≥ 5% NRV（≥3g/100mL）",
        "required_report": "营养成分检测报告（蛋白质含量）",
        "nutrient": "蛋白质",
        "unit": "g/100g",
        "threshold": 6,
        "regulation": "GB 28050-2011 表C.1"
    },
    "无脂肪声称": {
        "keywords": ["无脂肪", "零脂肪", "0脂肪", "脱脂", "不含脂肪", "零脂"],
        "requirement": "脂肪含量 ≤ 0.5g/100g（固体或液体）",
        "required_report": "营养成分检测报告（脂肪含量）",
        "nutrient": "脂肪",
        "unit": "g/100g",
        "threshold": 0.5,
        "regulation": "GB 28050-2011 表C.1"
    },
    "低脂肪声称": {
        "keywords": ["低脂", "低脂肪", "少脂"],
        "requirement": "脂肪含量 ≤ 3g/100g（固体）或 ≤ 1.5g/100mL（液体）",
        "required_report": "营养成分检测报告（脂肪含量）",
        "nutrient": "脂肪",
        "unit": "g/100g",
        "threshold": 3,
        "regulation": "GB 28050-2011 表C.1"
    },
    "高纤维声称": {
        "keywords": ["高纤维", "富含纤维", "膳食纤维丰富"],
        "requirement": "膳食纤维含量 ≥ 6g/100g",
        "required_report": "营养成分检测报告（膳食纤维含量）",
        "nutrient": "膳食纤维",
        "unit": "g/100g",
        "threshold": 6,
        "regulation": "GB 28050-2011 表C.1"
    },
    "纤维来源声称": {
        "keywords": ["含纤维", "膳食纤维来源"],
        "requirement": "膳食纤维含量 ≥ 3g/100g",
        "required_report": "营养成分检测报告（膳食纤维含量）",
        "nutrient": "膳食纤维",
        "unit": "g/100g",
        "threshold": 3,
        "regulation": "GB 28050-2011 表C.1"
    },
    "无钠声称": {
        "keywords": ["无钠", "零钠", "0钠", "不含钠"],
        "requirement": "钠含量 ≤ 5mg/100g",
        "required_report": "营养成分检测报告（钠含量）",
        "nutrient": "钠",
        "unit": "mg/100g",
        "threshold": 5,
        "regulation": "GB 28050-2011 表C.1"
    },
    "低钠声称": {
        "keywords": ["低钠", "低盐", "少盐", "减盐"],
        "requirement": "钠含量 ≤ 120mg/100g",
        "required_report": "营养成分检测报告（钠含量）",
        "nutrient": "钠",
        "unit": "mg/100g",
        "threshold": 120,
        "regulation": "GB 28050-2011 表C.1"
    },
    "无能量声称": {
        "keywords": ["零卡", "0卡", "无热量", "零热量", "0热量"],
        "requirement": "能量 ≤ 17kJ/100g（固体）或 ≤ 17kJ/100mL（液体）",
        "required_report": "营养成分检测报告（能量值）",
        "nutrient": "能量",
        "unit": "kJ/100g",
        "threshold": 17,
        "regulation": "GB 28050-2011 表C.1"
    },
    "低能量声称": {
        "keywords": ["低卡", "低热量", "轻食"],
        "requirement": "能量 ≤ 170kJ/100g（固体）或 ≤ 80kJ/100mL（液体）",
        "required_report": "营养成分检测报告（能量值）",
        "nutrient": "能量",
        "unit": "kJ/100g",
        "threshold": 170,
        "regulation": "GB 28050-2011 表C.1"
    }
}

# 禁用词库 - 依据最新法规标准
PROHIBITED_WORDS = {
    "医疗术语": [
        "治疗", "治愈", "药效", "疗效", "处方", "药方", 
        "临床验证", "医学验证", "药用", "医药级"
    ],
    "疾病声称": [
        "糖尿病", "高血压", "心脏病", "癌症", "肿瘤", 
        "抗癌", "防癌", "降血糖", "降血压", "降血脂",
        "防癌抗癌", "抑制肿瘤", "预防疾病"
    ],
    "绝对化用语": [
        "100%", "零添加", "无添加", "第一", "唯一", 
        "顶级", "最佳", "最好", "最强", "最高级",
        "国家级", "世界级", "全球首创", "独家"
    ],
    "功效承诺": [
        "减肥", "瘦身", "美白", "抗衰老", "延缓衰老", 
        "美容养颜", "增强免疫力", "调节血脂", "改善睡眠",
        "辅助降糖", "抗氧化", "排毒养颜"
    ],
    "低GI相关": [
        "低GI", "低升糖", "低血糖指数", "GI值", "升糖指数低"
    ],
    "特供专供": [
        "特供", "专供", "内供", "特需", "定制专供",
        "机关特供", "军队专供", "内部专供"
    ],
    "虚假描述": [
        "纯天然", "全天然", "野生", "原生态", "零污染",
        "无污染", "绿色无公害"
    ],
    "封建迷信": [
        "开光", "祈福", "辟邪", "转运", "风水",
        "招财", "镇宅", "吉祥如意"
    ]
}

# 法规标准库 - 最新版本
REGULATIONS = {
    "广告法第十七条": {
        "content": "除医疗、药品、医疗器械广告外，禁止其他任何广告涉及疾病治疗功能，并不得使用医疗用语或者易使推销的商品与药品、医疗器械相混淆的用语。",
        "applies_to": ["普通食品不得宣传疾病治疗功能", "不得使用医疗术语"],
        "effective_date": "2021年修订"
    },
    "广告法第九条": {
        "content": "广告不得使用'国家级'、'最高级'、'最佳'等用语。",
        "applies_to": ["禁止绝对化用语"],
        "effective_date": "2021年修订"
    },
    "食品标识监督管理办法第七条": {
        "content": "食品标识不得标注下列内容：（一）涉及疾病预防、治疗功能；（二）以欺骗、误导、夸大等方式作虚假描述；（三）违背科学常识、有违公序良俗、宣扬封建迷信；（四）标称'特供''专供''内供'党政机关或者军队等；（五）法律、法规、规章和食品安全国家标准禁止标注的其他内容。保健食品之外的其他食品不得在食品标识中声称具有保健功能（功效）。",
        "applies_to": ["禁止疾病预防和治疗功能", "禁止虚假描述", "禁止封建迷信", "禁止特供专供标识", "普通食品禁止保健功能声称"],
        "effective_date": "2025年3月14日发布，2027年3月16日起施行"
    },
    "食品标识监督管理办法第八条": {
        "content": "没有法律、法规、规章、食品安全国家标准或者行业标准依据的，食品标识不得标称适合未成年人食用，欺骗、误导消费者。",
        "applies_to": ["未成年人食品声称需有依据"],
        "effective_date": "2025年3月14日发布，2027年3月16日起施行"
    },
    "食品标识监督管理办法第十六条": {
        "content": "预包装食品标签应当标注反映食品真实属性的名称，不得欺骗、误导消费者。以植物源性食品原料制成的模拟动物源性食品，应当在名称中冠以'仿''素'或者'某植物'等字样；食品中没有添加某种配料，仅使用食品用香精、香料调配出该配料风味的食品，且在食品名称中体现该配料风味的，应当在名称中冠以'某味''某风味'等字样。",
        "applies_to": ["食品名称真实性", "仿制食品命名", "风味食品命名"],
        "effective_date": "2025年3月14日发布，2027年3月16日起施行"
    },
    "GB 7718-2011": {
        "content": "预包装食品标签应真实、准确，不得含有虚假内容，不得明示或暗示具有预防、治疗疾病作用。如果在食品标签或食品说明书上强调含有某种有价值的配料，应标示其添加量或在成品中的含量。",
        "applies_to": ["食品标签标识", "强调配料需标注含量", "禁止疾病预防和治疗声称"],
        "effective_date": "2011年4月20日实施（现行有效）"
    },
    "GB 7718-2011第4.1.3.1条": {
        "content": "如果在食品标签或食品说明书上强调含有某种有价值的配料，应标示其添加量或在成品中的含量。如果在食品的标签上特别强调一种或多种配料或成分的含量较低或无时，应标示所强调配料或成分在成品中的含量。",
        "applies_to": ["强调配料需标注含量", "强调不含某种成分需标注含量"],
        "effective_date": "2011年4月20日实施（现行有效）"
    },
    "GB 28050-2011": {
        "content": "营养成分表应标示能量、蛋白质、脂肪、碳水化合物、钠的含量及其占营养素参考值（NRV）百分比。营养声称应有检测数据支持。",
        "applies_to": ["营养标签", "营养成分表", "NRV百分比", "营养声称需有检测支持"],
        "effective_date": "2013年1月1日实施（现行有效）"
    },
    "WS/T 652-2019": {
        "content": "低GI食品：GI值≤55，需提供依据本标准测定的GI值检测报告。中GI食品：GI值在56-69之间。高GI食品：GI值≥70。",
        "applies_to": ["低GI声称必须有检测报告", "GI值分类标准"],
        "effective_date": "2019年12月1日实施（现行有效）"
    },
    "GB 2760-2014": {
        "content": "规定了食品添加剂的使用原则、允许使用的品种、使用范围及最大使用量或残留量。",
        "applies_to": ["食品添加剂合规性", "配料表添加剂标注"],
        "effective_date": "2015年5月24日实施（现行有效）"
    }
}

# 常见配料关键词（用于配料表含量检查）
COMMON_INGREDIENTS = [
    "燕麦", "小麦", "大米", "玉米", "荞麦", "藜麦", "黑麦", "大麦",
    "牛奶", "酸奶", "奶酪", "奶粉", "乳粉",
    "鸡蛋", "蛋白", "蛋黄",
    "牛肉", "猪肉", "鸡肉", "羊肉", "鸭肉",
    "鱼", "虾", "蟹", "三文鱼", "金枪鱼",
    "巧克力", "可可", "坚果", "核桃", "杏仁", "腰果", "花生",
    "水果", "草莓", "蓝莓", "芒果", "苹果", "橙子", "柠檬",
    "蔬菜", "胡萝卜", "菠菜", "番茄",
    "蜂蜜", "红糖", "黑糖", "冰糖",
    "咖啡", "抹茶", "绿茶", "红茶",
    "膳食纤维", "益生菌", "胶原蛋白", "乳清蛋白"
]

# ============================================
# 审查逻辑
# ============================================

def parse_nutrition_table(content: str) -> dict:
    """解析营养成分表"""
    nutrition_data = {}
    
    # 常见营养素关键词
    nutrients = {
        "能量": ["能量", "热量"],
        "蛋白质": ["蛋白质", "蛋白"],
        "脂肪": ["脂肪", "总脂肪"],
        "碳水化合物": ["碳水化合物", "碳水"],
        "糖": ["糖", "总糖"],
        "膳食纤维": ["膳食纤维", "纤维"],
        "钠": ["钠"],
        "饱和脂肪": ["饱和脂肪", "饱和脂肪酸"],
        "反式脂肪": ["反式脂肪", "反式脂肪酸"]
    }
    
    for nutrient, keywords in nutrients.items():
        for keyword in keywords:
            # 尝试匹配数值
            pattern = rf"{keyword}[：:：\s]*(\d+\.?\d*)\s*(g|mg|kJ|kcal|千焦|千卡)?"
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2) if match.group(2) else "g"
                nutrition_data[nutrient] = {"value": value, "unit": unit}
                break
    
    return nutrition_data

def parse_ingredient_list(content: str) -> dict:
    """解析配料表，提取各配料及其含量"""
    ingredients_data = {}
    
    # 尝试找到配料表部分
    ingredient_section = ""
    patterns = [
        r"配料[表：:：]\s*([^\n]+)",
        r"配料表[：:：]\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\n|营养成分|产品名称|$)",
        r"原料[：:：]\s*([^\n]+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            ingredient_section = match.group(1)
            break
    
    if not ingredient_section:
        return {"raw": "", "ingredients": {}, "has_content": False}
    
    # 解析配料及其含量
    # 常见格式：配料名（含量%）或 配料名：含量%
    ingredient_pattern = r"([^，,、（(]+)[（(]?\s*(\d+\.?\d*)\s*%?\s*[）)]?"
    matches = re.findall(ingredient_pattern, ingredient_section)
    
    for name, amount in matches:
        name = name.strip()
        if name and amount:
            ingredients_data[name] = float(amount)
    
    return {
        "raw": ingredient_section,
        "ingredients": ingredients_data,
        "has_content": len(ingredient_section.strip()) > 0
    }

def extract_barcode(content: str) -> list:
    """从文本中提取条形码"""
    barcodes = []
    
    # EAN-13 条形码（13位数字）
    ean13_pattern = r'\b(\d{13})\b'
    ean13_matches = re.findall(ean13_pattern, content)
    for code in ean13_matches:
        barcodes.append({"type": "EAN-13", "code": code})
    
    # EAN-8 条形码（8位数字）
    ean8_pattern = r'\b(\d{8})\b'
    ean8_matches = re.findall(ean8_pattern, content)
    for code in ean8_matches:
        if code not in [b["code"] for b in barcodes]:  # 避免重复
            barcodes.append({"type": "EAN-8", "code": code})
    
    # UPC 条形码（12位数字，以0开头）
    upc_pattern = r'\b(0\d{11})\b'
    upc_matches = re.findall(upc_pattern, content)
    for code in upc_matches:
        if code not in [b["code"] for b in barcodes]:
            barcodes.append({"type": "UPC", "code": code})
    
    return barcodes

def parse_barcode_info(barcode: str) -> dict:
    """解析条形码信息（基于编码规则）"""
    info = {"barcode": barcode, "valid": False, "country": "", "manufacturer": "", "product": ""}
    
    if len(barcode) == 13:
        # EAN-13 格式
        prefix = barcode[:3]
        
        # 国家/地区前缀
        country_codes = {
            "690": "中国", "691": "中国", "692": "中国", "693": "中国", 
            "694": "中国", "695": "中国", "696": "中国", "697": "中国",
            "698": "中国", "699": "中国",
            "471": "中国台湾", "489": "中国香港", "958": "中国澳门",
            "450-459": "日本", "490-499": "日本",
            "880": "韩国", "885": "泰国", "888": "新加坡",
            "899": "印度尼西亚", "955": "马来西亚",
            "000-019": "美国/加拿大", "030-039": "美国/加拿大",
            "060-099": "美国/加拿大",
            "300-379": "法国", "380": "保加利亚", "383": "斯洛文尼亚",
            "385": "克罗地亚", "387": "波黑", "400-440": "德国",
            "460-469": "俄罗斯", "470": "吉尔吉斯斯坦", "471": "台湾",
            "474": "爱沙尼亚", "475": "拉脱维亚", "476": "阿塞拜疆",
            "477": "立陶宛", "478": "乌兹别克斯坦", "479": "斯里兰卡",
            "480": "菲律宾", "481": "白俄罗斯", "482": "乌克兰",
            "484": "摩尔多瓦", "485": "亚美尼亚", "486": "格鲁吉亚",
            "487": "哈萨克斯坦", "489": "香港",
            "500-509": "英国", "520-521": "希腊", "528": "黎巴嫩",
            "529": "塞浦路斯", "530": "阿尔巴尼亚", "531": "马其顿",
            "535": "马耳他", "539": "爱尔兰", "540-549": "比利时/卢森堡",
            "560": "葡萄牙", "569": "冰岛", "570-579": "丹麦",
            "590": "波兰", "594": "罗马尼亚", "599": "匈牙利",
            "600-601": "南非", "603": "加纳", "608": "巴林",
            "609": "毛里求斯", "611": "摩洛哥", "613": "阿尔及利亚",
            "616": "肯尼亚", "618": "象牙海岸", "619": "突尼斯",
            "621": "叙利亚", "622": "埃及", "624": "利比亚",
            "625": "约旦", "626": "伊朗", "627": "科威特",
            "628": "沙特阿拉伯", "629": "阿联酋",
            "700-709": "挪威", "729": "以色列", "730-739": "瑞典",
            "740": "危地马拉", "741": "萨尔瓦多", "742": "洪都拉斯",
            "743": "尼加拉瓜", "744": "哥斯达黎加", "745": "巴拿马",
            "746": "多米尼加", "750": "墨西哥", "754-755": "加拿大",
            "759": "委内瑞拉", "760-769": "瑞士", "770": "哥伦比亚",
            "773": "乌拉圭", "775": "秘鲁", "777": "玻利维亚",
            "779": "阿根廷", "780": "智利", "784": "巴拉圭",
            "786": "厄瓜多尔", "789-790": "巴西", "800-839": "意大利",
            "840-849": "西班牙", "850": "古巴", "858": "斯洛伐克",
            "859": "捷克", "860": "塞尔维亚", "865": "蒙古",
            "867": "朝鲜", "869": "土耳其", "870-879": "荷兰",
            "900-919": "奥地利", "930-939": "澳大利亚", "940-949": "新西兰",
            "950": "全球办公室", "955": "马来西亚", "958": "澳门"
        }
        
        # 查找国家
        for code_range, country in country_codes.items():
            if "-" in code_range:
                start, end = code_range.split("-")
                if start <= prefix <= end:
                    info["country"] = country
                    break
            elif prefix == code_range:
                info["country"] = country
                break
        
        if not info["country"]:
            info["country"] = "未知国家/地区"
        
        # 厂商代码（第4-7位或第4-8位）
        info["manufacturer_code"] = barcode[3:7]
        
        # 验证校验位
        checksum = 0
        for i in range(12):
            digit = int(barcode[i])
            if i % 2 == 0:
                checksum += digit
            else:
                checksum += digit * 3
        check_digit = (10 - (checksum % 10)) % 10
        info["valid"] = (check_digit == int(barcode[12]))
        
    elif len(barcode) == 8:
        info["type"] = "EAN-8"
        info["country"] = "需查询具体信息"
        info["valid"] = True
    else:
        info["valid"] = False
    
    return info

def extract_product_info(content: str) -> dict:
    """从文本中提取产品信息"""
    info = {
        "product_name": "",
        "manufacturer": "",
        "weight": "",
        "address": ""
    }
    
    # 产品名称
    name_patterns = [
        r"产品名称[：:：]\s*([^\n]+)",
        r"品名[：:：]\s*([^\n]+)",
        r"名称[：:：]\s*([^\n]+)"
    ]
    for pattern in name_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            info["product_name"] = match.group(1).strip()
            break
    
    # 生产商/制造商
    manufacturer_patterns = [
        r"(?:生产者|制造商|生产商|委托方|受托方)[：:：]\s*([^\n]+)",
        r"生产厂[：:：]\s*([^\n]+)",
        r"委托生产企业[：:：]\s*([^\n]+)"
    ]
    for pattern in manufacturer_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            info["manufacturer"] = match.group(1).strip()
            break
    
    # 净含量/克重
    weight_patterns = [
        r"净含量[：:：]?\s*(\d+\.?\d*)\s*(g|kg|ml|mL|克|千克|毫升)",
        r"规格[：:：]?\s*(\d+\.?\d*)\s*(g|kg|ml|mL|克|千克|毫升)",
        r"(\d+\.?\d*)\s*(g|kg|ml|mL|克|千克|毫升)(?:/|每)"
    ]
    for pattern in weight_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            info["weight"] = f"{match.group(1)}{match.group(2)}"
            break
    
    # 地址
    address_patterns = [
        r"地址[：:：]\s*([^\n]+)",
        r"生产地址[：:：]\s*([^\n]+)",
        r"产地[：:：]\s*([^\n]+)"
    ]
    for pattern in address_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            info["address"] = match.group(1).strip()
            break
    
    return info

def check_emphasized_ingredients(product_name: str, ingredient_section: str, ingredient_data: dict) -> list:
    """检查产品名称中强调的配料是否在配料表中标注了含量"""
    warnings = []
    
    # 检查产品名称中强调的配料
    emphasized = []
    
    # 模式1：产品名称中直接包含配料名（如"燕麦饼干"中的"燕麦"）
    for ingredient in COMMON_INGREDIENTS:
        if ingredient in product_name:
            emphasized.append(ingredient)
    
    # 模式2：强调"含有/富含/添加"某配料
    contain_pattern = r"(?:含有|富含|添加|特添加|特别添加)\s*(\S+)"
    contain_matches = re.findall(contain_pattern, product_name + ingredient_section)
    emphasized.extend(contain_matches)
    
    # 模式3：强调"不含/无"某成分
    not_contain_pattern = r"(?:不含|无|零|0)\s*(\S+)"
    not_contain_matches = re.findall(not_contain_pattern, product_name + ingredient_section)
    
    # 检查是否标注了含量
    for ing in emphasized:
        found = False
        # 检查配料数据中是否有该配料的含量
        for ing_name, amount in ingredient_data.get("ingredients", {}).items():
            if ing in ing_name or ing_name in ing:
                found = True
                break
        
        # 检查配料表原文中是否标注了百分比
        if not found and ingredient_section:
            percent_pattern = rf"{re.escape(ing)}[（(]?\s*\d+\.?\d*\s*%?"
            if re.search(percent_pattern, ingredient_section, re.IGNORECASE):
                found = True
        
        if not found:
            warnings.append({
                "type": "强调配料未标注含量",
                "ingredient": ing,
                "description": f"产品名称/说明中强调「{ing}」，但配料表中未找到对应的含量标注",
                "regulation": "GB 7718-2011 第4.1.3.1条",
                "suggestion": f"请在配料表中标注「{ing}」的具体含量（添加量或在成品中的含量）"
            })
    
    # 检查"不含/无"成分是否标注了含量
    for ing in not_contain_matches:
        found = False
        if ingredient_section:
            # 检查是否标注了"未检出"或具体含量
            check_pattern = rf"{re.escape(ing)}[：:：]?\s*(?:未检出|≤\d+|\d+\.?\d*\s*(?:g|mg))"
            if re.search(check_pattern, ingredient_section, re.IGNORECASE):
                found = True
        
        if not found:
            warnings.append({
                "type": "强调不含成分未标注含量",
                "ingredient": ing,
                "description": f"产品声称「不含{ing}」，但未找到相应的含量检测数据或说明",
                "regulation": "GB 7718-2011 第4.1.3.1条",
                "suggestion": f"请在配料表或营养成分表中标注「{ing}」的实际含量，或提供检测报告证明未检出"
            })
    
    return warnings

def review_content(content: str, nutrition_report: str = "", ingredient_list: str = "") -> dict:
    """
    全面审查内容
    
    参数:
        content: 待审查的文本内容
        nutrition_report: 可选的营养检测报告内容
        ingredient_list: 可选的配料表内容（如果content中未包含）
    """
    violations = []
    suggestions = []
    risk_level = "low"
    
    content_lower = content.lower()
    
    # ============================================
    # 1. 检查禁用词
    # ============================================
    for category, words in PROHIBITED_WORDS.items():
        for word in words:
            if word.lower() in content_lower:
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                matches = pattern.findall(content)
                matched_word = matches[0] if matches else word
                
                regulation = ""
                regulation_detail = ""
                
                if category in ["医疗术语", "疾病声称"]:
                    regulation = "《中华人民共和国广告法》第十七条、《食品标识监督管理办法》第七条"
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
                elif category == "特供专供":
                    regulation = "《食品标识监督管理办法》第七条"
                    regulation_detail = REGULATIONS["食品标识监督管理办法第七条"]["content"]
                    if risk_level != "high":
                        risk_level = "high"
                elif category in ["虚假描述", "封建迷信"]:
                    regulation = "《食品标识监督管理办法》第七条"
                    regulation_detail = REGULATIONS["食品标识监督管理办法第七条"]["content"]
                    if risk_level not in ["high", "medium"]:
                        risk_level = "medium"
                else:
                    regulation = "《中华人民共和国广告法》"
                    if risk_level not in ["high", "medium"]:
                        risk_level = "medium"
                
                violations.append({
                    "risk_point": matched_word,
                    "category": category,
                    "regulation": regulation,
                    "regulation_detail": regulation_detail,
                    "description": f"发现「{matched_word}」，属于【{category}】类别"
                })
    
    # ============================================
    # 2. 检查营养声称
    # ============================================
    nutrition_warnings = []
    nutrition_data = parse_nutrition_table(content + "\n" + nutrition_report)
    
    for claim_type, claim_info in NUTRITION_CLAIMS.items():
        for keyword in claim_info["keywords"]:
            if keyword.lower() in content_lower:
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                matches = pattern.findall(content)
                matched_word = matches[0] if matches else keyword
                
                nutrient = claim_info["nutrient"]
                threshold = claim_info["threshold"]
                
                # 如果提供了检测报告，核对数据
                if nutrition_report or nutrient in nutrition_data:
                    actual_value = None
                    if nutrient in nutrition_data:
                        actual_value = nutrition_data[nutrient]["value"]
                    
                    if actual_value is not None:
                        # 根据声称类型判断是否合规
                        is_compliant = False
                        if "无" in claim_type or "零" in claim_type:
                            is_compliant = actual_value <= threshold
                        elif "高" in claim_type or "富含" in claim_type:
                            is_compliant = actual_value >= threshold
                        elif "低" in claim_type:
                            is_compliant = actual_value <= threshold
                        else:
                            is_compliant = actual_value <= threshold
                        
                        if is_compliant:
                            nutrition_warnings.append({
                                "claim_type": claim_type,
                                "keyword": matched_word,
                                "requirement": claim_info["requirement"],
                                "actual_value": actual_value,
                                "threshold": threshold,
                                "status": "合规",
                                "regulation": claim_info["regulation"]
                            })
                        else:
                            nutrition_warnings.append({
                                "claim_type": claim_type,
                                "keyword": matched_word,
                                "requirement": claim_info["requirement"],
                                "actual_value": actual_value,
                                "threshold": threshold,
                                "status": "不合规",
                                "regulation": claim_info["regulation"]
                            })
                    else:
                        # 报告中没有对应营养素数据
                        nutrition_warnings.append({
                            "claim_type": claim_type,
                            "keyword": matched_word,
                            "requirement": claim_info["requirement"],
                            "actual_value": None,
                            "threshold": threshold,
                            "status": "需人工核查",
                            "regulation": claim_info["regulation"]
                        })
                else:
                    # 未提供检测报告，提示人工核查
                    nutrition_warnings.append({
                        "claim_type": claim_type,
                        "keyword": matched_word,
                        "requirement": claim_info["requirement"],
                        "required_report": claim_info["required_report"],
                        "status": "需提供检测报告",
                        "regulation": claim_info["regulation"]
                    })
                break
    
    # ============================================
    # 3. 检查配料表含量标注
    # ============================================
    ingredient_warnings = []
    
    # 解析产品名称
    product_info = extract_product_info(content)
    product_name = product_info.get("product_name", "")
    
    # 提取配料表（优先使用单独提供的配料表）
    full_content = content
    if ingredient_list:
        full_content = content + "\n" + ingredient_list
    
    ingredient_data = parse_ingredient_list(full_content)
    ingredient_section = ingredient_data.get("raw", "")
    
    # 如果产品名称中有强调的配料
    if product_name:
        ingredient_warnings = check_emphasized_ingredients(product_name, ingredient_section, ingredient_data)
    
    # 如果未提供配料表，提示
    if not ingredient_data.get("has_content") and not ingredient_list:
        suggestions.append("⚠️ 未检测到配料表内容，请确认是否已提供完整的配料表信息")
    
    # ============================================
    # 4. 检查条形码
    # ============================================
    barcode_warnings = []
    barcodes = extract_barcode(content)
    
    if barcodes:
        for barcode_info in barcodes:
            barcode = barcode_info["code"]
            parsed_info = parse_barcode_info(barcode)
            
            # 与产品信息比对
            product_info = extract_product_info(content)
            
            # 检查条形码有效性
            if not parsed_info["valid"]:
                barcode_warnings.append({
                    "type": "条形码校验失败",
                    "barcode": barcode,
                    "description": f"条形码「{barcode}」校验位不正确，可能存在录入错误",
                    "suggestion": "请核对条形码数字是否正确"
                })
            
            # 检查产地信息
            if parsed_info["country"] and parsed_info["country"] != "未知国家/地区":
                # 如果产品标注了产地，检查是否一致
                if product_info["address"]:
                    # 简单的产地匹配（可以更复杂）
                    if parsed_info["country"] not in product_info["address"]:
                        if parsed_info["country"] == "中国":
                            # 中国条形码，检查是否标注了国内地址
                            if "省" not in product_info["address"] and "市" not in product_info["address"]:
                                barcode_warnings.append({
                                    "type": "产地信息不一致",
                                    "barcode": barcode,
                                    "barcode_country": parsed_info["country"],
                                    "product_address": product_info["address"],
                                    "description": f"条形码「{barcode}」显示产地为「{parsed_info['country']}」，但产品标注地址为「{product_info['address']}」",
                                    "suggestion": "请核对条形码与产品产地信息是否一致"
                                })
            
            # 保存条形码解析结果
            barcode_warnings.append({
                "type": "条形码信息",
                "barcode": barcode,
                "barcode_type": barcode_info["type"],
                "country": parsed_info["country"],
                "valid": parsed_info["valid"],
                "product_name": product_info["product_name"],
                "product_manufacturer": product_info["manufacturer"],
                "product_weight": product_info["weight"],
                "description": f"识别到条形码「{barcode}」，产地：{parsed_info['country']}"
            })
    
    # ============================================
    # 5. 生成修改建议
    # ============================================
    if violations:
        seen_categories = set()
        for v in violations:
            cat = v["category"]
            if cat not in seen_categories:
                seen_categories.add(cat)
                
                if cat in ["医疗术语", "疾病声称"]:
                    suggestions.append("❌ 删除所有医疗相关表述，普通食品禁止涉及疾病预防、治疗功能")
                elif cat == "绝对化用语":
                    suggestions.append("❌ 避免使用绝对化用语，改为客观描述")
                elif cat == "低GI相关":
                    suggestions.append("⚠️ 如需保留低GI声称，必须提供WS/T 652-2019标准检测报告（GI≤55）")
                elif cat == "功效承诺":
                    suggestions.append("❌ 删除功效承诺表述，普通食品不得宣称保健功能")
                elif cat == "特供专供":
                    suggestions.append("❌ 删除'特供''专供''内供'等表述")
                elif cat == "虚假描述":
                    suggestions.append("⚠️ 避免夸大、虚假描述，确保所有声称有据可查")
                elif cat == "封建迷信":
                    suggestions.append("❌ 删除封建迷信相关表述")
    
    # 营养声称建议
    for nw in nutrition_warnings:
        if nw["status"] == "需提供检测报告":
            suggestions.append(f"📋 发现「{nw['keyword']}」营养声称，需提供{nw['required_report']}进行核对（{nw['regulation']}）")
        elif nw["status"] == "不合规":
            suggestions.append(f"⚠️ 「{nw['keyword']}」声称与检测数据不符：实测{nw['actual_value']}，要求{nw['requirement']}")
        elif nw["status"] == "需人工核查":
            suggestions.append(f"📋 「{nw['keyword']}」声称需人工核查检测报告中的{nw['nutrient'] if 'nutrient' in nw else '相关营养素'}数据")
    
    # 配料表建议
    for iw in ingredient_warnings:
        suggestions.append(f"📋 {iw['suggestion']}（{iw['regulation']}）")
    
    # 条形码建议
    for bw in barcode_warnings:
        if bw["type"] == "条形码校验失败" or bw["type"] == "产地信息不一致":
            suggestions.append(f"🔧 {bw['suggestion']}")
    
    return {
        "risk_level": risk_level,
        "violations": violations,
        "nutrition_warnings": nutrition_warnings,
        "ingredient_warnings": ingredient_warnings,
        "barcode_warnings": barcode_warnings,
        "suggestions": suggestions
    }


def extract_pdf_text(pdf_file) -> str:
    """从 PDF 文件提取文本"""
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
st.markdown("基于 **GB 7718、GB 28050、广告法、食品标识监督管理办法、WS/T 652-2019** 等法规标准")
st.markdown("---")

# 输入方式选择
tab1, tab2 = st.tabs(["📝 文本审查", "📄 PDF 文件审查"])

# 文本审查
with tab1:
    st.markdown("### 输入待审查内容")
    
    # 主内容输入
    main_content = st.text_area(
        "食品标签/营销物料内容 *必填*",
        value="",
        height=200,
        placeholder="请输入食品标签或营销物料的完整内容，包括：\n\n产品名称、产品声称、配料表、营养成分表、宣传文案、厂家信息、条形码等",
        key="main_input"
    )
    
    # 可选：营养检测报告
    with st.expander("📋 营养检测报告（可选）"):
        st.markdown("如果提供了检测报告，系统将核对营养声称是否合规；如未提供，将提示人工核查")
        nutrition_report = st.text_area(
            "检测报告内容",
            value="",
            height=100,
            placeholder="粘贴营养检测报告的关键数据，例如：\n\n糖含量：0.3g/100g\n蛋白质含量：15.2g/100g\n脂肪含量：0.2g/100g\n...",
            key="nutrition_input"
        )
    
    # 可选：配料表
    with st.expander("📝 配料表（如主内容中未包含）"):
        st.markdown("如果产品名称中强调了某种配料，系统将检查配料表中是否标注了含量")
        ingredient_input = st.text_area(
            "配料表内容",
            value="",
            height=80,
            placeholder="粘贴配料表内容，例如：\n\n配料：小麦粉、燕麦（25%）、赤藓糖醇、植物油...",
            key="ingredient_input"
        )
    
    if st.button("🔍 开始审查", type="primary", key="review_text"):
        if not main_content.strip():
            st.warning("请输入食品标签/营销物料内容")
        else:
            with st.spinner("正在分析..."):
                result = review_content(
                    main_content, 
                    nutrition_report=nutrition_report,
                    ingredient_list=ingredient_input
                )
            
            st.markdown("---")
            st.markdown("### 📋 审查结果")
            
            # 风险等级
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
            
            # 违规项
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
            
            # 营养声称检查
            if result.get("nutrition_warnings"):
                st.markdown("#### 📋 营养声称检查")
                for nw in result["nutrition_warnings"]:
                    status_icon = {"合规": "✅", "不合规": "❌", "需提供检测报告": "⚠️", "需人工核查": "🔍"}.get(nw.get("status", ""), "📋")
                    status_color = {"合规": "green", "不合规": "red", "需提供检测报告": "orange", "需人工核查": "blue"}.get(nw.get("status", ""), "gray")
                    
                    with st.expander(f"{status_icon} **{nw.get('keyword', '')}** - {nw.get('claim_type', '')}（{nw.get('status', '')}）", expanded=True):
                        st.markdown(f"**声称要求**: {nw.get('requirement', '')}")
                        if nw.get("actual_value") is not None:
                            st.markdown(f"**实测值**: {nw.get('actual_value')}（阈值: {nw.get('threshold')}）")
                        if nw.get("required_report"):
                            st.markdown(f"**需要提供的报告**: {nw.get('required_report')}")
                        st.markdown(f"**法规依据**: {nw.get('regulation', '')}")
            
            # 配料表检查
            if result.get("ingredient_warnings"):
                st.markdown("#### 📝 配料表含量检查")
                for iw in result["ingredient_warnings"]:
                    with st.expander(f"⚠️ **{iw.get('ingredient', '')}** - {iw.get('type', '')}", expanded=True):
                        st.markdown(f"**问题描述**: {iw.get('description', '')}")
                        st.markdown(f"**法规依据**: {iw.get('regulation', '')}")
                        st.markdown(f"**建议**: {iw.get('suggestion', '')}")
            
            # 条形码检查
            barcode_infos = [bw for bw in result.get("barcode_warnings", []) if bw.get("type") == "条形码信息"]
            barcode_errors = [bw for bw in result.get("barcode_warnings", []) if bw.get("type") != "条形码信息"]
            
            if barcode_infos:
                st.markdown("#### 🔢 条形码信息")
                for bi in barcode_infos:
                    valid_icon = "✅" if bi.get("valid") else "❌"
                    with st.expander(f"{valid_icon} **{bi.get('barcode', '')}** - {bi.get('country', '')}", expanded=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**条形码类型**: {bi.get('barcode_type', '')}")
                            st.markdown(f"**产地**: {bi.get('country', '')}")
                            st.markdown(f"**校验**: {'通过' if bi.get('valid') else '失败'}")
                        with col2:
                            if bi.get("product_name"):
                                st.markdown(f"**产品名称**: {bi.get('product_name')}")
                            if bi.get("product_manufacturer"):
                                st.markdown(f"**生产商**: {bi.get('product_manufacturer')}")
                            if bi.get("product_weight"):
                                st.markdown(f"**净含量**: {bi.get('product_weight')}")
            
            if barcode_errors:
                st.markdown("#### 🔧 条形码问题")
                for be in barcode_errors:
                    st.warning(f"{be.get('description', '')} - {be.get('suggestion', '')}")
            
            # 修改建议
            if result.get("suggestions"):
                st.markdown("#### 💡 修改建议")
                for s in result["suggestions"]:
                    if s.startswith("❌"):
                        st.error(s)
                    elif s.startswith("⚠️"):
                        st.warning(s)
                    elif s.startswith("📋"):
                        st.info(s)
                    elif s.startswith("🔧"):
                        st.warning(s)
                    else:
                        st.info(s)

# PDF 文件审查
with tab2:
    st.markdown("### 上传 PDF 文件")
    
    pdf_file = st.file_uploader("选择 PDF 文件", type=["pdf"])
    
    if pdf_file:
        st.info(f"📄 已选择文件: {pdf_file.name}")
    
    # 可选输入
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("📋 营养检测报告（可选）"):
            nutrition_report_pdf = st.text_area("检测报告内容", value="", height=80, key="nutrition_pdf")
    with col2:
        with st.expander("📝 配料表（如PDF中未包含）"):
            ingredient_input_pdf = st.text_area("配料表内容", value="", height=80, key="ingredient_pdf")
    
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
                    st.text_area("PDF 内容", pdf_text, height=150)
                
                with st.spinner("正在审查..."):
                    result = review_content(
                        pdf_text,
                        nutrition_report=nutrition_report_pdf,
                        ingredient_list=ingredient_input_pdf
                    )
                
                st.markdown("---")
                st.markdown("### 📋 审查结果")
                
                # 风险等级
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
                
                # 违规项
                if result.get("violations"):
                    st.markdown("#### ⚠️ 发现违规项")
                    for v in result["violations"]:
                        with st.expander(f"**{v.get('risk_point', '')}** - {v.get('category', '')}"):
                            st.markdown(f"**问题描述**: {v.get('description', '')}")
                            st.markdown(f"**法规依据**: {v.get('regulation', '')}")
                else:
                    st.success("✅ 未发现明显违规项")
                
                # 营养声称检查
                if result.get("nutrition_warnings"):
                    st.markdown("#### 📋 营养声称检查")
                    for nw in result["nutrition_warnings"]:
                        status_icon = {"合规": "✅", "不合规": "❌", "需提供检测报告": "⚠️", "需人工核查": "🔍"}.get(nw.get("status", ""), "📋")
                        with st.expander(f"{status_icon} **{nw.get('keyword', '')}** - {nw.get('claim_type', '')}（{nw.get('status', '')}）"):
                            st.markdown(f"**声称要求**: {nw.get('requirement', '')}")
                            if nw.get("actual_value") is not None:
                                st.markdown(f"**实测值**: {nw.get('actual_value')}（阈值: {nw.get('threshold')}）")
                            if nw.get("required_report"):
                                st.markdown(f"**需要提供的报告**: {nw.get('required_report')}")
                            st.markdown(f"**法规依据**: {nw.get('regulation', '')}")
                
                # 配料表检查
                if result.get("ingredient_warnings"):
                    st.markdown("#### 📝 配料表含量检查")
                    for iw in result["ingredient_warnings"]:
                        with st.expander(f"⚠️ **{iw.get('ingredient', '')}** - {iw.get('type', '')}"):
                            st.markdown(f"**问题描述**: {iw.get('description', '')}")
                            st.markdown(f"**法规依据**: {iw.get('regulation', '')}")
                            st.markdown(f"**建议**: {iw.get('suggestion', '')}")
                
                # 条形码检查
                barcode_infos = [bw for bw in result.get("barcode_warnings", []) if bw.get("type") == "条形码信息"]
                barcode_errors = [bw for bw in result.get("barcode_warnings", []) if bw.get("type") != "条形码信息"]
                
                if barcode_infos:
                    st.markdown("#### 🔢 条形码信息")
                    for bi in barcode_infos:
                        valid_icon = "✅" if bi.get("valid") else "❌"
                        with st.expander(f"{valid_icon} **{bi.get('barcode', '')}** - {bi.get('country', '')}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**条形码类型**: {bi.get('barcode_type', '')}")
                                st.markdown(f"**产地**: {bi.get('country', '')}")
                                st.markdown(f"**校验**: {'通过' if bi.get('valid') else '失败'}")
                            with col2:
                                if bi.get("product_name"):
                                    st.markdown(f"**产品名称**: {bi.get('product_name')}")
                                if bi.get("product_manufacturer"):
                                    st.markdown(f"**生产商**: {bi.get('product_manufacturer')}")
                                if bi.get("product_weight"):
                                    st.markdown(f"**净含量**: {bi.get('product_weight')}")
                
                if barcode_errors:
                    st.markdown("#### 🔧 条形码问题")
                    for be in barcode_errors:
                        st.warning(f"{be.get('description', '')} - {be.get('suggestion', '')}")
                
                # 修改建议
                if result.get("suggestions"):
                    st.markdown("#### 💡 修改建议")
                    for s in result["suggestions"]:
                        if s.startswith("❌"):
                            st.error(s)
                        elif s.startswith("⚠️"):
                            st.warning(s)
                        elif s.startswith("📋"):
                            st.info(s)
                        elif s.startswith("🔧"):
                            st.warning(s)
                        else:
                            st.info(s)

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>© 2025 慢棠饱饱 · 食品合规审查系统</p>
    <p>依据法规：GB 7718-2011、GB 28050-2011、广告法（2021修订）、食品标识监督管理办法（2025）、WS/T 652-2019、GB 2760-2014</p>
</div>
""", unsafe_allow_html=True)
