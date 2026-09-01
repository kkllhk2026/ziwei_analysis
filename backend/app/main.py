"""紫微斗數分析系統 — API"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .core.config import get_settings
from .core.security import create_token, current_user
from .ziwei import analysis, fortune
from .ziwei.chart import cast
from .ziwei.schools import PRESETS, SchoolConfig
from .ziwei.serialize import apply_brightness, chart_to_dict

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="專業紫微斗數排盤與結構分析。排盤演算法公開可查證；論斷規則走 rules-as-code，不外送。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────────────  Schemas  ────────────────────────────

class BirthInput(BaseModel):
    birth: datetime = Field(..., examples=["1985-03-12T14:30:00"])
    gender: Literal["男", "女"]
    longitude: float | None = Field(None, description="出生地經度。null 表示不作真太陽時校正。")
    tz_offset_hours: float = 8.0
    school: str = Field("通行本", description="流派預設名，見 GET /schools")
    overrides: dict = Field(default_factory=dict, description="覆寫個別流派開關")


class FortuneInput(BirthInput):
    age: int | None = Field(None, description="虛歲，用於取大限")
    liunian_year: int | None = Field(None, description="西曆流年，例如 2026")
    liuyue: int | None = None
    liuri: int | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ────────────────────────────  Helpers  ────────────────────────────

def _resolve_config(name: str, overrides: dict) -> SchoolConfig:
    base = PRESETS.get(name)
    if base is None:
        raise HTTPException(400, f"未知流派：{name}（可用：{', '.join(PRESETS)}）")
    if not overrides:
        return base
    from dataclasses import replace
    valid = {k: v for k, v in overrides.items() if hasattr(base, k)}
    return replace(base, **valid)


def _build(payload: BirthInput):
    cfg = _resolve_config(payload.school, payload.overrides)
    try:
        chart = cast(
            payload.birth,
            payload.gender,
            config=cfg,
            longitude=payload.longitude if payload.longitude is not None else settings.default_longitude,
            tz_offset_hours=payload.tz_offset_hours,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    apply_brightness(chart, strict=settings.strict_tables)
    return chart


# ────────────────────────────  Routes  ────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.get("/schools")
def schools() -> dict:
    return {name: cfg.to_dict() for name, cfg in PRESETS.items()}


@app.post("/auth/token", response_model=TokenOut)
def token(username: str) -> TokenOut:
    # 佔位。接上你八字系統既有的使用者表之後換掉。
    return TokenOut(access_token=create_token(username))


@app.post("/chart")
def build_chart(payload: BirthInput, user: str = Depends(current_user)) -> dict:
    """排本命盤。"""
    return chart_to_dict(_build(payload))


@app.post("/chart/fortune")
def build_fortune(payload: FortuneInput, user: str = Depends(current_user)) -> dict:
    """本命盤 + 指定運限層。"""
    chart = _build(payload)
    layers = []

    if payload.age is not None:
        try:
            layers.append(fortune.daxian(chart, payload.age))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    ln = None
    if payload.liunian_year is not None:
        import sxtwl
        gz = sxtwl.fromSolar(payload.liunian_year, 6, 1).getYearGZ(True)
        ln = fortune.liunian(chart, gz.tg, gz.dz)
        layers.append(ln)

    if payload.liuyue is not None:
        if ln is None:
            raise HTTPException(400, "流月需同時提供 liunian_year")
        ly = fortune.liuyue(chart, ln, payload.liuyue)
        layers.append(ly)
        if payload.liuri is not None:
            layers.append(fortune.liuri(chart, ly, payload.liuri))

    return chart_to_dict(chart, layers=layers)


@app.post("/chart/flying")
def flying(payload: BirthInput, user: str = Depends(current_user)) -> dict:
    """全盤宮干飛化 + 命宮忌轉忌鏈。"""
    chart = _build(payload)
    return {
        "飛化": {
            chart.palaces[i].name: [
                {"星": f.star, "化": f.hua, "入": f.to_name, "自化": f.is_self_hua}
                for f in flights
            ]
            for i, flights in analysis.fly_all(chart).items()
        },
        "忌轉忌": [
            {"自": f.from_name, "星": f.star, "入": f.to_name}
            for f in analysis.trace_ji(chart, chart.ming_index)
        ],
    }


@app.post("/chart/compare")
def compare(payload: BirthInput, other_school: str, user: str = Depends(current_user)) -> dict:
    """
    同一生辰、兩個流派，逐宮 diff。
    客戶問「點解同某網站唔同」時，這支 endpoint 直接給答案。
    """
    a = _build(payload)
    b_payload = payload.model_copy(update={"school": other_school})
    b = _build(b_payload)

    diffs = []
    for pa, pb in zip(a.palaces, b.palaces, strict=True):
        sa = {(s.name, s.sihua) for s in pa.stars}
        sb = {(s.name, s.sihua) for s in pb.stars}
        if sa != sb or pa.name != pb.name:
            diffs.append({
                "地支": pa.zhi,
                f"{a.config.name}宮名": pa.name,
                f"{b.config.name}宮名": pb.name,
                "僅A有": sorted(f"{n}{h or ''}" for n, h in sa - sb),
                "僅B有": sorted(f"{n}{h or ''}" for n, h in sb - sa),
            })
    return {
        "A": a.config.name, "B": b.config.name,
        "命宮相同": a.ming_index == b.ming_index,
        "五行局相同": a.wuxingju == b.wuxingju,
        "差異宮位": diffs,
    }
