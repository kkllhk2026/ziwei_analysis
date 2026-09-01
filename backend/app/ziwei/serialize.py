"""
紫微斗數 — 亮度套用與序列化
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .analysis import structural_summary
from .chart import Chart
from .fortune import FortuneLayer

DATA_DIR = Path(__file__).parent / "data"


@lru_cache(maxsize=1)
def brightness_data() -> dict:
    return json.loads((DATA_DIR / "brightness.json").read_text(encoding="utf-8"))


def apply_brightness(chart: Chart, *, strict: bool = False) -> None:
    """就地寫入亮度。strict 模式下，未覆核的星會留白而非填入未覆核值。"""
    data = brightness_data()
    verified = set(data.get("verified_stars", []))
    table = data["table"]
    for p in chart.palaces:
        for s in p.stars:
            row = table.get(s.name)
            if not row:
                continue
            if strict and s.name not in verified:
                continue
            s.brightness = row.get(p.zhi)


def chart_to_dict(chart: Chart, *, layers: list[FortuneLayer] | None = None) -> dict:
    m = chart.moment
    return {
        "meta": {
            "西曆": m.solar.isoformat(),
            "生效時刻": m.effective.isoformat(),
            "農曆": f"{m.year_gz}年 {'閏' if m.is_leap_month else ''}{m.lunar_month}月{m.lunar_day}日 {m.hour_zhi}時",
            "年干支": m.year_gz,
            "生肖": __import__("app.ziwei.constants", fromlist=["SHENGXIAO"]).SHENGXIAO[m.year_zhi],
            "性別": chart.gender,
            "陰陽男女": chart.yin_yang_gender,
            "五行局": chart.wuxingju.value,
            "局數": chart.ju_number,
            "命主": chart.ming_zhu,
            "身主": chart.shen_zhu,
            "命宮": chart.palaces[chart.ming_index].zhi,
            "身宮": chart.palaces[chart.body_index].zhi,
            "大限方向": "順行" if chart.is_forward else "逆行",
        },
        "曆法決策": {
            "真太陽時校正分鐘": round(m.correction.total_minutes, 2),
            "經度時差": round(m.correction.longitude_minutes, 2),
            "均時差": round(m.correction.equation_minutes, 2),
            "年界": m.year_boundary.value,
            "子時規則": m.zi_rule.value,
        },
        "流派": chart.config.to_dict(),
        "宮位": [
            {
                "序": p.index,
                "地支": p.zhi,
                "天干": p.gan,
                "干支": p.gz,
                "宮名": p.name,
                "身宮": p.is_body,
                "大限": list(p.daxian) if p.daxian else None,
                "小限": p.xiaoxian_ages[:10],
                "長生十二神": p.changsheng,
                "博士十二神": p.boshi,
                "歲前十二神": p.suiqian,
                "將前十二神": p.jiangqian,
                "星曜": [
                    {
                        "名": s.name,
                        "類": s.kind,
                        "亮度": s.brightness,
                        "生年四化": s.sihua,
                        "自化": s.self_hua,
                    }
                    for s in p.stars
                ],
            }
            for p in chart.palaces
        ],
        "結構": structural_summary(chart),
        "運限": [
            {
                "層": layer.kind,
                "標籤": layer.label,
                "命宮序": layer.ming_index,
                "宮名": layer.palace_names,
                "四化": layer.sihua,
                "流曜": layer.stars,
            }
            for layer in (layers or [])
        ],
        "資料完整度": {
            "亮度表已覆核": brightness_data().get("_verified", False),
            "已覆核星曜": brightness_data().get("verified_stars", []),
        },
    }
