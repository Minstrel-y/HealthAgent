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
    "tsh": r"促甲状腺激素|TSH",
}


def _norm(text: str) -> str:
    t = text.replace("：", ":").replace("，", ",").replace("、", ",").replace("；", ";")
    t = t.replace("（", "(").replace("）", ")")
    return re.sub(r"\s+", " ", t)


def _first_num_after(text: str, keyword: str):
    # 关键词含 | 必须用非捕获分组，否则交替会剥掉后面的数字组
    pattern = rf"(?:{keyword})[^0-9\-]{{0,12}}({NUM})"
    m = re.search(pattern, text, flags=re.IGNORECASE)
    if not m or m.group(1) is None:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def parse_health_text(raw_text: str) -> dict:
    text = _norm(raw_text or "")
    data = {}
    for field, keyword in FIELD_KEYWORDS.items():
        value = _first_num_after(text, keyword)
        if value is not None:
            data[field] = value

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
