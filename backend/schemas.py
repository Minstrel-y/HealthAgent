from pydantic import BaseModel, ConfigDict, Field
from typing import Any


class RegisterIn(BaseModel):
    username: str
    password: str


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class MetricsIn(BaseModel):
    """录入的结构化指标，全部可选：做多少项目就发多少，没做的不要填。

    extra="allow"：指标库以后新增的项目（前端表单自动多出来的输入框）也能带过来，
    不会因为模型没声明字段就被静默丢弃；真正入库前由 clean_metrics 按指标库过滤。
    """
    model_config = ConfigDict(extra="allow")

    sex: str | None = None
    age: int | None = None
    height: float | None = None
    weight: float | None = None
    bmi: float | None = None
    sbp: float | None = None
    dbp: float | None = None
    fast_glucose: float | None = None
    tg: float | None = None
    non_hdl: float | None = None
    alt: float | None = None
    uric_acid: float | None = None
    creatinine: float | None = None


class RecordIn(BaseModel):
    raw_text: str = ""
    extra_text: str = ""
    metrics: MetricsIn | None = None


class ProfileIn(BaseModel):
    """个人资料：全部可选，传什么改什么。"""
    nickname: str | None = None
    avatar: str | None = None
    sex: str | None = None          # male / female / unknown
    birthday: str | None = None     # YYYY-MM-DD
    font_scale: float | None = None # 0.85 ~ 1.4


class WechatConfirmIn(BaseModel):
    ticket: str
    openid: str | None = None
    nickname: str | None = None
    avatar: str | None = None


class QuestionIn(BaseModel):
    question: str
    record_id: int | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)


class RecordUpdateIn(BaseModel):
    """修改已有记录：结构化指标全量覆盖，原文可选。"""
    raw_text: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
