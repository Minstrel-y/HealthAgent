"""参考区间与状态判定：指标徽章与健康得分全部本地计算，不经过大模型。

为什么要本地算：数值判读是确定性逻辑，交给模型会引入幻觉；
模型只负责"解读"和"建议"，不负责"判读"。
"""

METRICS = {
    # --- 基础体格 ---
    "bmi":          {"name": "BMI",           "unit": "",       "low": 18.5, "high": 23.9, "warn_high": 27.9},
    "sbp":          {"name": "收缩压",         "unit": "mmHg",   "low": 90,   "high": 120,  "warn_high": 139},
    "dbp":          {"name": "舒张压",         "unit": "mmHg",   "low": 60,   "high": 80,   "warn_high": 89},
    # --- 血糖 ---
    "fast_glucose": {"name": "空腹血糖",       "unit": "mmol/L", "low": 3.9,  "high": 6.1,  "warn_high": 7.0},
    "hba1c":        {"name": "糖化血红蛋白",    "unit": "%",      "low": 3.6,  "high": 6.0,  "warn_high": 6.5},
    # --- 血脂 ---
    "tg":           {"name": "甘油三酯 TG",    "unit": "mmol/L", "low": 0.56, "high": 1.7,  "warn_high": 2.3},
    "non_hdl":      {"name": "非高密度脂蛋白",  "unit": "mmol/L", "low": None, "high": 3.1,  "warn_high": 4.1},
    "tc":           {"name": "总胆固醇 TC",    "unit": "mmol/L", "low": None, "high": 5.2,  "warn_high": 6.2},
    "ldl":          {"name": "低密度脂蛋白 LDL", "unit": "mmol/L", "low": None, "high": 3.4, "warn_high": 4.1},
    "hdl":          {"name": "高密度脂蛋白 HDL", "unit": "mmol/L", "low": 1.0, "high": 3.5},
    # --- 肝功能 ---
    "alt":          {"name": "ALT 谷丙转氨酶", "unit": "U/L",    "low": None, "high": 40,   "warn_high": 80},
    "ast":          {"name": "AST 谷草转氨酶", "unit": "U/L",    "low": None, "high": 40,   "warn_high": 80},
    "ggt":          {"name": "GGT 谷氨酰转肽酶", "unit": "U/L",  "low": None, "high": 45,   "warn_high": 90},
    "tbill":        {"name": "总胆红素 TBIL",  "unit": "μmol/L", "low": 3.4,  "high": 20.5, "warn_high": 34.2},
    # --- 肾功能 ---
    "uric_acid":    {"name": "尿酸",          "unit": "μmol/L", "low": None},
    "creatinine":   {"name": "肌酐",          "unit": "μmol/L", "low": None},
    "bun":          {"name": "尿素氮 BUN",     "unit": "mmol/L", "low": 2.9,  "high": 8.2,  "warn_high": 10.0},
    # --- 血常规 ---
    "hgb":          {"name": "血红蛋白 HGB",   "unit": "g/L",    "low": None, "high": None},
    "wbc":          {"name": "白细胞 WBC",     "unit": "10^9/L", "low": 3.5,  "high": 9.5,  "warn_high": 12.0},
    "plt":          {"name": "血小板 PLT",     "unit": "10^9/L", "low": 125,  "high": 350,  "warn_high": 450},
    # --- 内分泌 / 甲状腺 ---
    "tsh":          {"name": "促甲状腺激素 TSH", "unit": "μIU/mL", "low": 0.55, "high": 4.78, "warn_high": 10.0},
}

# 《医学指标及其建议.xlsx》“补充指标”：19 行中 TBIL 已在指标库，净增 18 项。
# 说明：有些实验室项目需要检测系统/年龄/性别等条件，未满足时仅展示原始值、标记“未判读”。
# 因此“已收录”不代表“可以套一个全国统一参考区间”，也不代表已经具备疾病判读规则。
METRICS.update({
    # 甲状腺：FT3/FT4 参考区间依检测系统，不能给固定通用值
    "ft3": {"name": "游离三碘甲状腺原氨酸 FT3", "unit": "pmol/L", "low": None, "high": None,
            "requires_lab_range": True, "reference_note": "按报告的甲状腺检测系统参考区间判读，不能套用统一范围。"},
    "ft4": {"name": "游离四碘甲状腺素 FT4", "unit": "pmol/L", "low": None, "high": None,
            "requires_lab_range": True, "reference_note": "按报告的甲状腺检测系统参考区间判读；特殊人群需专用区间。"},
    # 肝功能
    "pa": {"name": "前白蛋白 PA", "unit": "mg/L", "low": None, "high": None,
           "reference_note": "18～79 岁；男性 200–430，女性 180–350 mg/L（WS/T 404.9-2026）。"},
    "tp": {"name": "总蛋白 TP", "unit": "g/L", "low": 65, "high": 85},
    "alb": {"name": "白蛋白 ALB", "unit": "g/L", "low": 40, "high": 55},
    "dbil": {"name": "直接胆红素 DBIL", "unit": "μmol/L", "low": None, "high": None,
             "requires_lab_range": True, "reference_note": "检测系统 a 上限 8.0，系统 b/c 上限 4.0 μmol/L，不能混用。"},
    "alp": {"name": "碱性磷酸酶 ALP", "unit": "U/L", "low": None, "high": None,
            "reference_note": "男 45–125；女 20～49 岁 35–100、女 50～79 岁 50–135 U/L。"},
    "tba": {"name": "总胆汁酸 TBA", "unit": "μmol/L", "low": None, "high": None,
            "requires_lab_range": True, "reference_note": "以报告实验室检测方法及空腹参考区间为准。"},
    "che": {"name": "胆碱酯酶 CHE", "unit": "U/L", "low": None, "high": None,
            "requires_lab_range": True, "reference_note": "各检测方法差异较大，以报告实验室区间为准。"},
    "ibil": {"name": "间接胆红素 I-BIL", "unit": "μmol/L", "low": None, "high": None,
             "requires_lab_range": True, "reference_note": "TBIL−DBIL 计算值，不设独立全国统一参考区间。"},
    # 肾功能：按年龄区分
    "beta2_mg": {"name": "β2-微球蛋白 β2-MG", "unit": "mg/L", "low": None, "high": None,
                 "reference_note": "18～59 岁 1.0–2.3；60～79 岁 1.3–3.0 mg/L；妊娠者不适用。"},
    # 心肌功能：LDH 非特异性；肌钙蛋白必须按具体检测系统判读
    "ldh": {"name": "乳酸脱氢酶 LDH", "unit": "U/L", "low": 120, "high": 250,
            "reference_note": "非心肌特异性指标，单次结果不能用于诊断心肌损伤。"},
    "ctnt": {"name": "心肌肌钙蛋白 cTnT", "unit": "ng/L", "low": None, "high": None,
             "requires_lab_range": True, "reference_note": "须按检测平台、性别及第 99 百分位参考上限判读；注意单位 ng/L 与 ng/mL 不同。"},
    # 血常规
    "mcv": {"name": "平均红细胞体积 MCV", "unit": "fL", "low": 82, "high": 100},
    "mchc": {"name": "平均红细胞血红蛋白浓度 MCHC", "unit": "g/L", "low": 316, "high": 354},
    "mch": {"name": "平均红细胞血红蛋白量 MCH", "unit": "pg", "low": 27, "high": 34},
    "hct": {"name": "红细胞压积 HCT", "unit": "L/L", "low": None, "high": None,
            "reference_note": "男性 0.40–0.50；女性 0.35–0.45 L/L；如果报告用 % 请先按单位换算。"},
    "rbc": {"name": "红细胞计数 RBC", "unit": "10^12/L", "low": None, "high": None,
            "reference_note": "男 4.3–5.8；女 3.8–5.1 ×10^12/L；高海拔人群需其他参考依据。"},
})
METRICS["bmi"]["unit"] = "kg/m²"
METRICS["tsh"]["unit"] = "mIU/L"  # 与原 μIU/mL 数值等价；统一沿用表格记法
METRICS["tsh"].update({"low": None, "high": None, "requires_lab_range": True,
                       "reference_note": "不同检测系统的 TSH 参考范围不同；请在录入时选择报告对应的检测系统。"})
# 不在资料中给出无条件统一区间的项目，在未具备必要信息时一律不参与评分。
TSH_SYSTEM_RANGES = {
    "罗氏": (0.75, 5.60), "贝克曼": (0.60, 4.90),
    "雅培": (0.60, 4.40), "西门子": (0.60, 4.80),
    "迈瑞": (0.75, 5.60), "安图": (0.75, 5.60),
    "迈克": (0.60, 5.40), "新产业": (0.60, 5.40),
}

# 性别相关区间（未填性别时按男性区间）
SEX_RANGES = {
    "uric_acid":  {"male": (208, 428), "female": (155, 357)},
    "creatinine": {"male": (57, 97),   "female": (41, 73)},
    "hgb":        {"male": (130, 175), "female": (115, 150)},
    "ggt":        {"male": (10, 60),   "female": (7, 45)},
    "alt":        {"male": (9, 50),    "female": (7, 40)},
    "ast":        {"male": (15, 40),   "female": (13, 35)},
    "tbill":      {"male": (None, 26), "female": (None, 21)},
    "pa":         {"male": (200, 430), "female": (180, 350)},
    "hct":        {"male": (0.40, 0.50), "female": (0.35, 0.45)},
    "rbc":        {"male": (4.3, 5.8), "female": (3.8, 5.1)},
}

# 身体光点：指标 -> 部位锚点（百分比坐标，对应全息人体正面底图）
# 前端不再硬编码坐标，新增指标只要在这里登记就会出现在人体图上
BODY_POINTS = {
    "thyroid":  {"x": 49.5, "y": 17.5, "organ": "甲状腺"},
    "cardio":   {"x": 49.0, "y": 21.5, "organ": "心血管"},
    "lipid":    {"x": 56.5, "y": 24.5, "organ": "血液"},
    "liver":    {"x": 43.0, "y": 32.5, "organ": "肝脏"},
    "pancreas": {"x": 49.5, "y": 34.5, "organ": "胰腺"},
    "kidney_l": {"x": 42.5, "y": 37.5, "organ": "肾脏"},
    "kidney_r": {"x": 57.0, "y": 37.5, "organ": "肾脏"},
    "body":     {"x": 49.5, "y": 42.0, "organ": "整体"},
    "blood":    {"x": 49.5, "y": 46.0, "organ": "造血"},
}

METRIC_ANCHOR = {
    "sbp": "cardio", "dbp": "cardio", "ldh": "cardio", "ctnt": "cardio",
    "tg": "lipid", "non_hdl": "lipid", "tc": "lipid", "ldl": "lipid", "hdl": "lipid",
    "alt": "liver", "ast": "liver", "ggt": "liver", "tbill": "liver",
    "pa": "liver", "tp": "liver", "alb": "liver", "dbil": "liver", "alp": "liver",
    "tba": "liver", "che": "liver", "ibil": "liver",
    "fast_glucose": "pancreas", "hba1c": "pancreas",
    "uric_acid": "kidney_l", "creatinine": "kidney_r", "bun": "kidney_r", "beta2_mg": "kidney_r",
    "hgb": "blood", "wbc": "blood", "plt": "blood",
    "rbc": "blood", "hct": "blood", "mcv": "blood", "mch": "blood", "mchc": "blood",
    "tsh": "thyroid", "ft3": "thyroid", "ft4": "thyroid",
    "bmi": "body",
}

# 检查类型用于录入筛选，不改变原有医学科室及判读规则。
CHECK_TYPES = {
    # 综合分类与既有分类保留，标准表「补充指标」中新增的检查范围与类别在下面对应扩展。
    "general": {"name": "常规体检", "keys": ["bmi", "sbp", "dbp", "fast_glucose", "tg", "tc", "alt", "creatinine"]},
    "all": {"name": "全部已支持指标", "keys": list(METRICS)},
    "blood": {"name": "血常规", "keys": ["hgb", "wbc", "plt", "rbc", "hct", "mcv", "mch", "mchc"]},
    "liver": {"name": "肝功能", "keys": ["alt", "ast", "ggt", "tbill", "pa", "tp", "alb", "dbil", "alp", "tba", "che", "ibil"]},
    "kidney": {"name": "肾功能", "keys": ["uric_acid", "creatinine", "bun", "beta2_mg"]},
    "cardiac": {"name": "心肌功能", "keys": ["ldh", "ctnt"]},
    "lipid": {"name": "血脂检查", "keys": ["tg", "non_hdl", "tc", "ldl", "hdl"]},
    "glucose": {"name": "血糖检查", "keys": ["fast_glucose", "hba1c"]},
    "thyroid": {"name": "甲状腺检查", "keys": ["tsh", "ft3", "ft4"]},
    "endocrine": {"name": "内分泌科检查", "keys": ["fast_glucose", "hba1c", "tsh", "ft3", "ft4", "bmi"]},
    "cardio": {"name": "血压与体格", "keys": ["sbp", "dbp", "bmi"]},
    "other": {"name": "其他检查", "keys": []},
}

# 一份记录在此分组中至多出现一次，避免重复展示与重复计数。
DEPARTMENTS = [
    ("心血管内科", ["sbp", "dbp"]),
    ("心肌功能", ["ldh", "ctnt"]),
    ("内分泌科", ["bmi", "fast_glucose", "hba1c"]),
    ("血脂检查", ["tg", "non_hdl", "tc", "ldl", "hdl"]),
    ("血常规", ["hgb", "wbc", "plt", "rbc", "hct", "mcv", "mch", "mchc"]),
    ("肝功能", ["alt", "ast", "ggt", "tbill", "pa", "tp", "alb", "dbil", "alp", "tba", "che", "ibil"]),
    ("肾功能", ["creatinine", "uric_acid", "bun", "beta2_mg"]),
    ("甲状腺", ["tsh", "ft3", "ft4"]),
]


# 兜底分组：任何已解析但没被上面科室收录的指标都会落到这里，
# 保证"新增体检项目"即使没配置科室也一定会在页面上显示出来
OTHER_DEPT = "其他指标"

STATUS_LABEL = {"normal": "正常", "warning": "临界", "danger": "偏高", "low": "偏低", "none": "未判读"}


def _range_for(key: str, sex: str = "unknown", parsed: dict = None):
    """根据表格的适用条件选择参考区间；条件不足时返回 (None, None)。"""
    meta = METRICS[key]
    parsed = parsed or {}
    age = parsed.get("age")
    if key == "tsh":
        return TSH_SYSTEM_RANGES.get(parsed.get("_lab_system"), (None, None))
    if meta.get("requires_lab_range"):
        return None, None
    if key == "bun":
        if sex not in ("male", "female") or not isinstance(age, (int, float)) or not 20 <= age <= 79:
            return None, None
        return ({"male": (3.1, 8.0), "female": (2.6, 7.5)} if age < 60
                else {"male": (3.6, 9.5), "female": (3.1, 8.8)})[sex]
    if key == "creatinine":
        if sex not in ("male", "female") or not isinstance(age, (int, float)) or not 20 <= age <= 79:
            return None, None
        return ({"male": (57, 97), "female": (41, 73)} if age < 60
                else {"male": (57, 111), "female": (41, 81)})[sex]
    if key == "alp":
        if sex not in ("male", "female") or not isinstance(age, (int, float)) or not 20 <= age <= 79:
            return None, None
        if sex == "male": return (45, 125)
        return (35, 100) if age < 50 else (50, 135)
    if key == "ldh" and (not isinstance(age, (int, float)) or not 20 <= age <= 79):
        return None, None
    if key == "beta2_mg":
        if not isinstance(age, (int, float)) or not 18 <= age <= 79:
            return None, None
        return (1.0, 2.3) if age < 60 else (1.3, 3.0)
    if key == "pa" and (not isinstance(age, (int, float)) or not 18 <= age <= 79):
        return None, None
    if key in SEX_RANGES:
        if sex not in ("male", "female"):
            return None, None
        return SEX_RANGES[key][sex]
    return meta.get("low"), meta.get("high")


def metric_status(key: str, value: float, sex: str = "unknown", parsed: dict = None) -> str:
    """返回 normal / warning / danger / low / none（资料不支持判读）。"""
    if key not in METRICS or not isinstance(value, (int, float)):
        return "none"
    lo, hi = _range_for(key, sex, parsed)
    if lo is None and hi is None:
        return "none"
    if lo is not None and value < lo:
        return "low"
    if hi is not None and value > hi:
        if key == "bmi":
            return "warning" if value <= 27.9 else "danger"
        warn_high = METRICS[key].get("warn_high")
        if key in SEX_RANGES:
            return "warning" if value <= hi * 1.15 else "danger"
        if warn_high is not None and warn_high > hi:
            return "warning" if value <= warn_high else "danger"
        return "warning"
    return "normal"


def deviation(key: str, value: float, sex: str = "unknown", parsed: dict = None) -> float:
    """返回 [-1, 1] 的标准化偏差：0 = 正常带中点，正 = 偏高，负 = 偏低。

    前端「健康信号」曲线用：正常项在参考区间内的位置也带来自然起伏，
    避免曲线拉成一条平线；偏高/偏低则形成明显的峰与谷。
    """
    lo, hi = _range_for(key, sex, parsed)
    if lo is None and hi is None:
        return 0.0
    if lo is None or hi is None:
        # 只有单侧或无区间可参考：退回用状态给一个粗略值
        return {"normal": 0.0, "low": -0.4, "warning": 0.55, "danger": 0.85, "none": 0.0}[
            metric_status(key, value, sex, parsed)
        ]
    BAND = 0.5  # 正常带内的最大幅值：让正常项之间也有起伏，同时保持单调连续
    mid = (lo + hi) / 2.0
    half = (hi - lo) / 2.0 or 1.0
    if lo <= value <= hi:
        return round((value - mid) / half * BAND, 3)
    if value > hi:
        warn = METRICS[key].get("warn_high")
        top = warn if warn else hi * 1.3
        span = (top - hi) or hi
        return round(min(1.0, BAND + (1.0 - BAND) * (value - hi) / span), 3)
    # value < lo
    span = (lo - lo * 0.5) or lo
    return round(max(-1.0, -BAND - (1.0 - BAND) * (lo - value) / span), 3)


def anchor_of(key: str):
    """指标对应的身体光点位置，供前端人体图渲染（未登记的返回 None）。"""
    group = METRIC_ANCHOR.get(key)
    if not group:
        return None
    p = BODY_POINTS.get(group)
    if not p:
        return None
    return {"group": group, "organ": p["organ"], "x": p["x"], "y": p["y"]}


# 这些键属于体检人信息，不是指标，不参与分组/计分
NON_METRIC_KEYS = {"sex", "age", "height", "weight", "height_cm", "weight_kg"}


def _item(k: str, v, sex: str, parsed: dict = None) -> dict:
    """单个指标条目；指标库里没登记的项也会保留（标注"未判读"，只显示原始值）。"""
    meta = METRICS.get(k, {})
    known = k in METRICS
    st = metric_status(k, v, sex, parsed) if known else "none"
    low, high = _range_for(k, sex, parsed) if known else (None, None)
    unit = meta.get("unit", "")
    if low is not None and high is not None:
        reference = f"{low:g}～{high:g} {unit}".strip()
    elif low is not None:
        reference = f"≥{low:g} {unit}".strip()
    elif high is not None:
        reference = f"≤{high:g} {unit}".strip()
    else:
        reference = ""
    return {
        "key": k,
        "name": meta.get("name") or k,
        "value": v,
        "unit": meta.get("unit", ""),
        "reference": reference,
        "status": st,
        "status_label": STATUS_LABEL.get(st, "未判读"),
        "dev": deviation(k, v, sex, parsed) if known else 0.0,
        "reference_note": meta.get("reference_note", ""),
        "auto_judgement": st != "none",
        "anchor": anchor_of(k),
        "known": known,
    }


def build_departments(parsed: dict):
    """返回 [{"name": 科室, "items": [{"key","name","value","unit","status","status_label","anchor"}]}]

    兜底：只要是指标库里登记过、且本次有数值的项目，即使没配科室也会进「其他指标」，不会丢。
    """
    sex = parsed.get("sex", "unknown")
    groups = []
    used = set()
    for dept, keys in DEPARTMENTS:
        items = []
        for k in keys:
            if k in parsed and parsed[k] is not None:
                items.append(_item(k, parsed[k], sex, parsed))
                used.add(k)
        if items:
            groups.append({"name": dept, "items": items})

    rest = [k for k in parsed
            if k not in NON_METRIC_KEYS and k not in used
            and parsed[k] is not None and isinstance(parsed[k], (int, float))]
    other_items = []
    if rest:
        order = {"danger": 0, "warning": 1, "low": 2, "normal": 3}
        rest.sort(key=lambda k: order.get(metric_status(k, parsed[k], sex, parsed) if k in METRICS else "none", 4))
        other_items.extend(_item(k, parsed[k], sex, parsed) for k in rest)

    # 自定义指标的名字、单位、参考范围随记录保存，但不进行医学状态推断。
    for i, custom in enumerate(parsed.get("_custom_metrics") or []):
        if not isinstance(custom, dict) or not isinstance(custom.get("value"), (int, float)):
            continue
        other_items.append({
            "key": f"custom_{i}", "name": custom.get("name", "其他指标"),
            "value": custom["value"], "unit": custom.get("unit", ""),
            "reference": custom.get("reference", ""),
            "status": "none", "status_label": "未判读", "dev": 0.0,
            "anchor": None, "known": False,
        })
    if other_items:
        groups.append({"name": OTHER_DEPT, "items": other_items})
    return groups


def count_abnormal(parsed: dict) -> int:
    sex = parsed.get("sex", "unknown")
    return sum(1 for k, v in parsed.items()
               if k in METRICS and isinstance(v, (int, float))
               and metric_status(k, v, sex, parsed) in ("warning", "danger"))


_SCORE_WEIGHT = {"normal": 0, "low": 1.0, "warning": 2.0, "danger": 4.0}


def health_score(parsed: dict) -> int:
    """综合健康得分 0~100。

    按"已检项目中异常项的加权占比"扣分，而不是固定扣分：
    体检项目从 9 项增加到 20+ 项时，同样的异常比例仍然得到接近的分数，
    不会因为项目变多就一律压到 0 分。
    """
    sex = parsed.get("sex", "unknown")
    keys = [k for k in parsed
            if k in METRICS and isinstance(parsed[k], (int, float))
            and metric_status(k, parsed[k], sex, parsed) != "none"]
    if not keys:
        return 100
    loss = sum(_SCORE_WEIGHT[metric_status(k, parsed[k], sex, parsed)] for k in keys)
    worst = _SCORE_WEIGHT["danger"] * len(keys)  # 全部偏高时的扣分上限
    return max(0, min(100, round(100 - 100 * loss / worst)))


def score_label(score: int) -> str:
    if score >= 90:
        return "优秀"
    if score >= 80:
        return "良好"
    if score >= 70:
        return "一般"
    if score >= 60:
        return "偏差"
    return "较差"


def scorable_count(parsed: dict) -> int:
    """已有可适用参考区间的指标数量，不含“仅已收录但尚无法判读”的指标。"""
    sex = parsed.get("sex", "unknown")
    return sum(1 for k, v in parsed.items() if k in METRICS and isinstance(v, (int, float))
               and metric_status(k, v, sex, parsed) != "none")
