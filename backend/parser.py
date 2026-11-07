"""体检文本本地解析：模型不可用时的降级方案（免费额度限流时常会用到）。"""
import re

NUM = r"(-?\d+(?:\.\d+)?)"

FIELD_KEYWORDS = {
    "fast_glucose": r"空腹血糖|血糖",
    "tg": r"甘油三酯|TG",
    "non_hdl": r"非高密度脂蛋白",
    "alt": r"ALT|谷丙转氨酶",
    "uric_acid": r"尿酸",
    "creatinine": r"肌酐",
    "sbp": r"收缩压|高压",
    "dbp": r"舒张压|低压",
    "tc": r"总胆固醇|TC",
    "ldl": r"(?<!高)低密度脂蛋白|LDL",
    "hdl": r"(?<!非)高密度脂蛋白|HDL",
    "hba1c": r"糖化血红蛋白|HbA1c|HbA1C",
    "hgb": r"血红蛋白|HGB",
    "wbc": r"白细胞|WBC",
    "plt": r"血小板|PLT",
    "ast": r"AST|谷草转氨酶",
    "ggt": r"GGT|谷氨酰转肽酶|γ-?谷氨酰",
    "tbill": r"总胆红素|TBIL",
    "bun": r"尿素氮|BUN|尿素",
    "tsh": r"促甲状腺激素|(?<![a-z])TSH(?![a-z])",
    # 《医学指标及其建议.xlsx》新增的 18 个指标：本地兜底仅做初步提取，保存前仍需核对单位。
    "ft3": r"游离三碘甲状腺原氨酸|(?<![a-z])FT3(?![a-z])",
    "ft4": r"游离四碘甲状腺素|(?<![a-z])FT4(?![a-z])",
    "pa": r"前白蛋白|(?<![a-z])PA(?![a-z])",
    "tp": r"总蛋白|(?<![a-z])TP(?![a-z])",
    "alb": r"(?<!前)白蛋白|(?<![a-z])ALB(?![a-z])",
    "dbil": r"直接胆红素|(?<![a-z])DBIL(?![a-z])",
    "alp": r"碱性磷酸酶|(?<![a-z])ALP(?![a-z])",
    "tba": r"总胆汁酸|(?<![a-z])TBA(?![a-z])",
    "che": r"胆碱酯酶|(?<![a-z])CHE(?![a-z])",
    "ibil": r"间接胆红素|(?<![a-z])I-?BIL(?![a-z])",
    "beta2_mg": r"(?:β2|β₂|B2)[-－]?微球蛋白|(?<![a-z])(?:β2-MG|B2-MG)(?![a-z])",
    "ldh": r"乳酸脱氢酶|(?<![a-z])LDH(?![a-z])",
    "ctnt": r"心肌肌钙蛋白(?:T)?|(?<![a-z])(?:hs-)?cTnT(?![a-z])",
    "mcv": r"平均红细胞体积|(?<![a-z])MCV(?![a-z])",
    "mchc": r"平均红细胞血红蛋白浓度|(?<![a-z])MCHC(?![a-z])",
    "mch": r"平均红细胞血红蛋白量|(?<![a-z])MCH(?![a-z])",
    "hct": r"红细胞压积|(?<![a-z])HCT(?![a-z])",
    "rbc": r"红细胞计数|(?<![a-z])RBC(?![a-z])",
}


def _norm(text: str) -> str:
    t = text.replace("：", ":").replace("，", ",").replace("、", ",").replace("；", ";")
    t = t.replace("（", "(").replace("）", ")")
    return re.sub(r"\s+", " ", t)


def _first_num_after(text: str, keyword: str):
    """优先读关键词同一段冒号后的结果，避免把 FT4、β2-MG 名称中的数字当成测量值。"""
    match = re.search(rf"(?:{keyword})", text, flags=re.IGNORECASE)
    if not match:
        return None
    # 区分字段与后续字段；无冒号的简写报告再使用旧式宽松查找。
    tail = re.split(r"[;\n,]", text[match.end():match.end() + 80], maxsplit=1)[0]
    colon = tail.find(":")
    if 0 <= colon <= 28:
        value_m = re.search(NUM, tail[colon + 1:])
    else:
        value_m = re.search(rf"[^0-9\-]{{0,12}}{NUM}", tail)
    if not value_m:
        return None
    try:
        return float(value_m.group(1))
    except (ValueError, TypeError):
        return None


def parse_health_text(raw_text: str) -> dict:
    text = _norm(raw_text or "")
    data = {}
    for field, keyword in FIELD_KEYWORDS.items():
        value = _first_num_after(text, keyword)
        if value is not None:
            data[field] = value
    # HCT 标准化输入为 L/L；报告写 42% 时换算为 0.42。
    # 局部降级解析只处理这一项明确的等价单位；其他单位不确定时应人工核对。
    if "hct" in data:
        m = re.search(r"(?:红细胞压积|\bHCT\b)[^0-9]{0,12}\d+(?:\.\d+)?\s*%", text, re.I)
        if m:
            data["hct"] = round(data["hct"] / 100, 4)

    m_h = re.search(r"(\d{2,3}(?:\.\d+)?)\s*cm", text, flags=re.IGNORECASE)
    m_w = re.search(r"(\d{2,3}(?:\.\d+)?)\s*kg", text, flags=re.IGNORECASE)
    if m_h and m_w:
        h = float(m_h.group(1)) / 100
        w = float(m_w.group(1))
        if h > 0:
            data["bmi"] = round(w / (h ** 2), 2)

    m_sex = re.search(r"(男性|女性|男|女)", text)
    if m_sex:
        data["sex"] = "male" if m_sex.group(1).startswith("男") else "female"

    m_age = re.search(r"(\d{1,3})\s*岁", text)
    if m_age:
        age = int(m_age.group(1))
        if 0 < age < 130:
            data["age"] = age
    return data


def build_history_text(records: list, max_records: int = 8) -> str:
    """把历史记录压缩成给模型看的短文本（别塞 Python repr，浪费 token）。"""
    if not records:
        return "无历史记录"
    lines = []
    for r in records[-max_records:]:
        parsed = r.get("parsed_data") or {}
        # 结构化元数据不是测量项，不能把 Python repr 原样送进大模型。
        items = [f"{k}={v}" for k, v in parsed.items() if not k.startswith("_") and v is not None]
        for metric in (parsed.get("_custom_metrics") or []):
            if isinstance(metric, dict) and metric.get("name") and metric.get("value") is not None:
                items.append(f"{metric['name']}={metric['value']} {metric.get('unit', '')}(未判读)")
        lines.append(f"{r.get('record_time', '未知时间')}: {', '.join(items) or '无指标'}")
    return "\n".join(lines)
