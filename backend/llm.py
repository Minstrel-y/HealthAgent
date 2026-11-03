"""大模型层：所有 dashscope 调用集中在这里，路由层不直接接触模型。"""
import json
import re
import time

import dashscope
from dashscope import MultiModalConversation

from config import DASHSCOPE_API_KEY, MODEL_CANDIDATES, VL_MODELS
from refs import DEPARTMENTS, METRICS, OTHER_DEPT, STATUS_LABEL, build_departments

dashscope.api_key = DASHSCOPE_API_KEY


class LLMError(RuntimeError):
    pass


def _call(messages, expect_json=False):
    """多模型自动回退 + 限流退避重试。

    实测：同一 Key 下 qwen-turbo 会 429 RateQuota，qwen-plus 正常，
    所以按顺序逐个尝试；只有"限流/额度"类错误才换模型或等待重试，
    鉴权、参数错误立即抛，避免无意义等待。
    """
    last_err = None
    for model in MODEL_CANDIDATES:
        for attempt, wait in enumerate([0, 15, 35], start=1):
            if wait:
                time.sleep(wait)
            try:
                resp = dashscope.Generation.call(model=model, messages=messages, result_format="message")
            except Exception as e:
                last_err = str(e)
                continue
            code = str(getattr(resp, "code", "") or "")
            if getattr(resp, "status_code", 200) == 200:
                content = resp.output.choices[0].message.content
                return _extract_json(content) if expect_json else content
            last_err = f"{getattr(resp, 'code', '')} {getattr(resp, 'message', '')}".strip()
            throttled = ("Throttl" in code or "RateQuota" in code or "rate" in last_err.lower())
            if throttled and attempt < 3:
                continue
            if throttled:
                break
            raise LLMError(last_err)
    raise LLMError("模型限流：当前 API 免费额度已用完（每分钟调用数超限），请约 1 分钟后重试。")


def _extract_json(text: str):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.+?)```", text, flags=re.DOTALL)
    if m:
        text = m.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise LLMError("模型未返回 JSON")
    return json.loads(text[start:end + 1])


# ---------------- 指标抽取 ----------------
# 可抽取的字段随 refs.METRICS 自动扩展：新增指标只要登记进指标库，抽取、判读、
# 身体图光点、科室分组都会自动跟上，不需要再改这里。
_EXTRA_ALIASES = {
    "hba1_c": "hba1c", "hb_a1c": "hba1c", "glycated_hemoglobin": "hba1c",
    "tbil": "tbill", "total_bilirubin": "tbill",
    "urea": "bun", "urea_nitrogen": "bun",
    "hemoglobin": "hgb", "hb": "hgb",
    "white_blood_cell": "wbc", "leukocyte": "wbc",
    "platelet": "plt",
    "thyroid_stimulating_hormone": "tsh",
    "cholesterol": "tc", "total_cholesterol": "tc",
    "ldl_c": "ldl", "hdl_c": "hdl",
}
_METRIC_ALIASES = {"sex": "sex", "age": "age", "height_cm": "height", "weight_kg": "weight"}
_METRIC_ALIASES.update({k: k for k in METRICS})
_METRIC_ALIASES.update(_EXTRA_ALIASES)

_JSON_FIELDS = ",".join(f'"{k}":数字' for k in METRICS)
_METRIC_HINT = "；".join(
    f'{k}={m["name"]}' + (f'（{m["unit"]}）' if m.get("unit") else "")
    for k, m in METRICS.items()
)

EXTRACT_SYSTEM_PROMPT = f"""你是体检报告信息抽取助手。抽出指标后只输出 JSON，不要其他文字：
{{"sex":"男或女","age":数字,"height_cm":数字,"weight_kg":数字,{_JSON_FIELDS}}}
字段含义：{_METRIC_HINT}；height_cm 身高厘米、weight_kg 体重公斤。
规则：
1. 只抽文本里确实写了的数值，没有的填 null，绝不推测编造。
2. 数值不带单位。
3. sbp 是收缩压/高压，dbp 是舒张压/低压；TG 也叫甘油三酯，ALT 也叫谷丙转氨酶，AST 也叫谷草转氨酶。
4. 报告里出现、但上面没列出的其他检查项目也要抽出：键名用该项目中文名的英文/拼音小写（如 "afp"、"psa"），值为数值。"""

OCR_PROMPT = (
    "读取这张体检报告图片，只输出 JSON，不要其他文字：\n"
    '{"sex":"男或女","age":数字,"height_cm":数字,"weight_kg":数字,' + _JSON_FIELDS + "}\n"
    "规则：sex 只能男或女；数值不带单位；图中没有的填 null；"
    "身高厘米、体重公斤，尿酸/肌酐/总胆红素 μmol/L，血红蛋白 g/L，白细胞与血小板 10^9/L。"
)


def _normalize_metrics(raw: dict, source_text: str = "") -> dict:
    """归一化 + 防幻觉：数值必须在原文找得到，否则丢弃。"""
    out = {}
    if raw.get("sex") in ("男", "女"):
        if not source_text or raw["sex"] in source_text:
            out["sex"] = "male" if raw["sex"] == "男" else "female"
    age = raw.get("age")
    if isinstance(age, (int, float)) and 0 < age < 130:
        if not source_text or str(int(age)) in source_text:
            out["age"] = int(age)

    for key, field in _METRIC_ALIASES.items():
        if field in ("sex", "age"):
            continue
        value = raw.get(key)
        if value is None:
            continue
        try:
            num = float(value)
        except (TypeError, ValueError):
            continue
        if source_text:
            variants = {f"{num:g}", f"{num:.1f}", f"{num:.2f}", str(int(num)) if num == int(num) else ""}
            if not any(v and v in source_text for v in variants):
                continue
        out[field] = round(num, 2)

    # 报告里有、但指标库还没登记的项目：保留原始数值，页面上标"未判读"而不是直接丢掉
    for key, value in raw.items():
        if key in _METRIC_ALIASES or key in ("sex", "age"):
            continue
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,23}", str(key)):
            continue
        try:
            num = float(value)
        except (TypeError, ValueError):
            continue
        if source_text:
            variants = {f"{num:g}", f"{num:.1f}", f"{num:.2f}"}
            if not any(v and v in source_text for v in variants):
                continue
        out[str(key)] = round(num, 2)
    return out


def extract_metrics_from_text(text: str) -> dict:
    messages = [
        {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
        {"role": "user", "content": text[:4000]},
    ]
    return _normalize_metrics(_call(messages, expect_json=True), source_text=text)


# ---------------- OCR（图片 / PDF） ----------------
def _to_num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"-?\d+(?:\.\d+)?", str(v))
    return float(m.group(0)) if m else None


def _content_to_text(content) -> str:
    if isinstance(content, list):
        return "".join(c.get("text", "") for c in content if isinstance(c, dict))
    return str(content)


def ocr_image_base64(b64: str, mime: str = "image/png") -> dict:
    import base64 as _b64  # 保持接口清晰，调用方已转好 base64
    _ = _b64
    messages = [{
        "role": "user",
        "content": [{"image": f"data:{mime};base64,{b64}"}, {"text": OCR_PROMPT}],
    }]
    last_err = None
    for model in VL_MODELS:
        try:
            resp = MultiModalConversation.call(model=model, messages=messages)
            if getattr(resp, "status_code", 200) != 200:
                last_err = f"{model}: {getattr(resp, 'code', '')} {getattr(resp, 'message', '')}"
                continue
            text = _content_to_text(resp.output.choices[0].message.content)
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if not m:
                last_err = f"{model}: 未返回 JSON"
                continue
            raw = json.loads(m.group(0))
            out = {}
            for key, field in _METRIC_ALIASES.items():
                if key == "sex":
                    if raw.get("sex") in ("男", "女"):
                        out["sex"] = "male" if raw["sex"] == "男" else "female"
                    continue
                num = _to_num(raw.get(key))
                if num is not None:
                    out[field] = num
            if out:
                return out
            last_err = f"{model}: 未识别到任何指标"
        except Exception as e:
            last_err = f"{model}: {e}"
            continue
    raise LLMError(f"图片识别失败（{last_err}）")


def pdf_to_png_bytes(pdf_bytes: bytes, max_pages: int = 2) -> list:
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        images.append(page.get_pixmap(dpi=150).tobytes("png"))
    return images


# ---------------- 报告 / 问答 / 趋势 ----------------
def _metrics_brief(parsed: dict) -> str:
    sex = parsed.get("sex", "unknown")
    sex_txt = {"male": "男", "female": "女"}.get(sex, "未填写")
    header = f"性别：{sex_txt}"
    if "age" in parsed:
        header += f"，年龄：{parsed['age']}岁"
    lines = [header]
    for group in build_departments(parsed):
        parts = []
        for it in group["items"]:
            unit = f" {it['unit']}" if it["unit"] else ""
            parts.append(f"{it['name']}={it['value']:g}{unit}（{it['status_label']}）")
        lines.append(f"{group['name']}：" + "；".join(parts))
    return "\n".join(lines) or "未识别到结构化指标"


REPORT_SYSTEM_PROMPT = """你是健康体检AI分析助手。系统已完成指标判读（正常/临界/偏低/偏高），你只做解读和建议，不要重新判读数值，不要编造未提供的指标。

严格输出以下 JSON，不要输出任何其他文字：
{
  "risk_level": "low|medium|high",
  "summary": "综合健康总结，120字以内，口语化",
  "departments": [
    {"name": "科室名", "comment": "该科室指标解读，80字以内", "advice": ["建议1", "建议2"]}
  ]
}

要求：
1. departments 只覆盖用户实际有指标的科室，科室名必须从给定列表中选择。
2. risk_level 依据异常项数量与程度判断。
3. 建议具体可执行（饮食、运动、复查项目与时间），不要空话。
4. 你输出的内容仅为健康科普参考，不能替代执业医师诊断——请在 advice 中体现需要就医的情形。"""


def generate_report(parsed: dict, history_text: str, extra_text: str = "") -> dict:
    extra_block = (f"\n用户补充的其他检查项目/描述（同样只解读提到过的，不要编造数值）：\n{extra_text[:1500]}\n"
                   if extra_text else "")
    messages = [
        {"role": "system", "content": REPORT_SYSTEM_PROMPT},
        {"role": "user", "content": f"""本次体检指标（已判读）：
{_metrics_brief(parsed)}
{extra_block}
历史体检记录：
{history_text}"""},
    ]
    data = _call(messages, expect_json=True)
    valid = {d for d, _ in DEPARTMENTS} | {OTHER_DEPT}
    data.setdefault("risk_level", "medium")
    data.setdefault("summary", "")
    data.setdefault("departments", [])
    data["departments"] = [d for d in data["departments"] if d.get("name") in valid]
    return data


QA_SYSTEM_PROMPT = """你是康鉴智航健康咨询AI助手。
用户已提交体检报告就结合报告内容回答；没有报告就做通用健康科普。
回答通俗易懂、条理清晰。
⚠️ 你的回答仅为健康科普参考，不能替代执业医师诊断，如有明显异常请及时就医。"""


def ask_question(question: str, report_context: str, history_text: str) -> str:
    messages = [
        {"role": "system", "content": QA_SYSTEM_PROMPT},
        {"role": "user", "content": f"""本次体检报告摘要：{(report_context or '（暂无）')[:4000]}
历史体检记录：{history_text}
用户提问：{question[:1000]}"""},
    ]
    return _call(messages)


TREND_SYSTEM_PROMPT = (
    "你是健康数据分析助手。只输出 JSON，不要其他文字："
    '{"trend":"整体健康趋势总结，150字以内，描述各指标变化方向与风险走向",'
    '"impact":"综合影响分析，150字以内，说明多项指标联合起来对身体的整体影响与关联",'
    '"advice":["具体可执行的运动或作息建议，每条一句话，3~5条，要具体到频率和时长"]}'
)


def trend_summary(history_text: str) -> dict:
    messages = [
        {"role": "system", "content": TREND_SYSTEM_PROMPT},
        {"role": "user", "content": f"基于以下历次体检数据，生成趋势三段分析：{history_text}"},
    ]
    return _call(messages, expect_json=True)


def _unused_keep_refs():  # 保持 import 有意义（给未来扩展用）
    return METRICS, STATUS_LABEL
