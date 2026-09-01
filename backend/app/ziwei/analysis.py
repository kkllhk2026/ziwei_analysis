"""
紫微斗數 — 分析層
==================
這層只做「結構性推導」，不做論斷文字。
論斷規則屬於你的師承資產，走 rules-as-code，放 app/rules/，永不外送 LLM。
"""

from __future__ import annotations

from dataclasses import dataclass

from .chart import Chart, Palace, sihua_for_gan
from .constants import TIAN_GAN, norm

# ────────────────────────────  結構關係  ────────────────────────────

def san_fang_si_zheng(index: int) -> dict[str, int]:
    """本宮、對宮、三合二宮。紫微論命的最小單位。"""
    return {
        "本宮": norm(index),
        "對宮": norm(index + 6),
        "三合1": norm(index + 4),
        "三合2": norm(index + 8),
    }


def jia_gong(index: int) -> tuple[int, int]:
    """夾宮：左右鄰宮。羊陀夾、火鈴夾、空劫夾皆由此判。"""
    return norm(index - 1), norm(index + 1)


def an_gong(index: int) -> int:
    """暗合宮。"""
    return norm(1 - index)


# ────────────────────────────  飛星  ────────────────────────────

@dataclass
class FlyingHua:
    from_palace: int
    from_name: str
    hua: str            # 祿/權/科/忌
    star: str
    to_palace: int
    to_name: str
    is_self_hua: bool


def fly(chart: Chart, index: int) -> list[FlyingHua]:
    """某宮宮干四化飛往何宮。飛星派的基本動作。"""
    src = chart.palaces[index]
    gan = TIAN_GAN.index(src.gan)
    out: list[FlyingHua] = []
    for star, hua in sihua_for_gan(gan, chart.config).items():
        for p in chart.palaces:
            if p.find(star):
                out.append(FlyingHua(
                    from_palace=index, from_name=src.name, hua=hua, star=star,
                    to_palace=p.index, to_name=p.name, is_self_hua=(p.index == index),
                ))
                break
    return out


def fly_all(chart: Chart) -> dict[int, list[FlyingHua]]:
    return {i: fly(chart, i) for i in range(12)}


def trace_ji(chart: Chart, index: int, depth: int = 3) -> list[FlyingHua]:
    """
    忌轉忌：A 宮化忌入 B，再看 B 宮化忌入 C……
    追到重複或到達 depth 為止。飛星派看事情如何連環的關鍵手法。
    """
    chain: list[FlyingHua] = []
    seen = {index}
    cur = index
    for _ in range(depth):
        ji = next((f for f in fly(chart, cur) if f.hua == "忌"), None)
        if ji is None:
            break
        chain.append(ji)
        if ji.to_palace in seen:
            break
        seen.add(ji.to_palace)
        cur = ji.to_palace
    return chain


# ────────────────────────────  格局偵測  ────────────────────────────
# 只放「以星曜落宮即可機械判定」的結構格局。
# 需要靠師承心法拿捏輕重的，不放這裡。

def _stars_at(p: Palace) -> set[str]:
    return {s.name for s in p.stars}


def detect_patterns(chart: Chart) -> list[dict]:
    found: list[dict] = []
    ming = chart.ming_index
    sfsz = san_fang_si_zheng(ming)
    triad = [chart.palaces[i] for i in sfsz.values()]
    triad_stars: set[str] = set()
    for p in triad:
        triad_stars |= _stars_at(p)

    ming_p = chart.palaces[ming]
    ming_stars = _stars_at(ming_p)

    def add(name: str, note: str) -> None:
        found.append({"格局": name, "說明": note})

    # 空宮
    if not (ming_stars & set(chart_major_names())):
        add("命宮無正曜", "須借對宮星曜安星論之。")

    # 府相朝垣
    if {"天府", "天相"} <= triad_stars:
        add("府相朝垣", "天府天相會於三方四正。")

    # 殺破狼
    if {"七殺", "破軍", "貪狼"} <= triad_stars:
        add("殺破狼", "三方四正見殺破狼，主變動。")

    # 機月同梁
    if {"天機", "太陰", "天同", "天梁"} <= triad_stars:
        add("機月同梁", "四星俱會。")

    # 祿馬交馳
    for p in chart.palaces:
        s = _stars_at(p)
        if {"祿存", "天馬"} <= s or ({"天馬"} <= s and any(
            st.sihua == "祿" for st in p.stars
        )):
            add("祿馬交馳", f"祿與天馬同會於{p.name}（{p.gz}）。")
            break

    # 羊陀夾忌 / 火鈴夾
    left, right = jia_gong(ming)
    lset, rset = _stars_at(chart.palaces[left]), _stars_at(chart.palaces[right])
    if {"擎羊"} & lset and {"陀羅"} & rset or {"陀羅"} & lset and {"擎羊"} & rset:
        add("羊陀夾命", "命宮左右為擎羊陀羅所夾。")
    if {"火星"} & lset and {"鈴星"} & rset or {"鈴星"} & lset and {"火星"} & rset:
        add("火鈴夾命", "命宮左右為火星鈴星所夾。")

    # 日月並明 / 反背
    sun = next(p for p in chart.palaces if p.find("太陽"))
    moon = next(p for p in chart.palaces if p.find("太陰"))
    if sun.index in (2, 3, 4, 5, 6) and moon.index in (8, 9, 10, 11, 0):
        add("日月並明", "太陽居卯至午、太陰居酉至子，各得其位。")

    return found


def chart_major_names() -> tuple[str, ...]:
    from .constants import MAJOR_STARS
    return MAJOR_STARS


# ────────────────────────────  匯出摘要  ────────────────────────────

def structural_summary(chart: Chart) -> dict:
    """給前端／規則引擎吃的結構摘要。純結構，無論斷。"""
    return {
        "命宮三方四正": {
            k: chart.palaces[v].name for k, v in san_fang_si_zheng(chart.ming_index).items()
        },
        "格局": detect_patterns(chart),
        "生年四化落宮": [
            {"星": s.name, "化": s.sihua, "宮": p.name, "干支": p.gz}
            for p in chart.palaces for s in p.stars if s.sihua
        ],
        "自化": [
            {"星": s.name, "化": s.self_hua, "宮": p.name}
            for p in chart.palaces for s in p.stars if s.self_hua
        ],
    }
