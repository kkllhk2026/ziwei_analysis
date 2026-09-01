"""
紫微斗數 — 運限層
==================
本命盤是底圖。大限、流年、流月、流日各自是一層可疊加的「重排」，
每層都會：重新指定十二宮名、重新起四化、加上該層流曜。

關鍵：層與層之間不互相污染。每層都回傳獨立物件，
前端可以任意組合（本命＋大限、本命＋大限＋流年…）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .chart import Chart, sihua_for_gan
from .constants import DI_ZHI, PALACE_NAMES, TIAN_GAN, norm
from .tables import LUCUN_BY_GAN, get_table


@dataclass
class FortuneLayer:
    kind: str                          # 大限 / 流年 / 流月 / 流日 / 流時
    label: str                         # 「第三大限 23–32」「乙巳年」
    ming_index: int                    # 該層命宮
    palace_names: dict[int, str]       # 地支序 -> 該層宮名
    sihua: dict[str, str]              # 星名 -> 化曜
    stars: dict[int, list[str]] = field(default_factory=dict)   # 流曜
    gan: int | None = None
    zhi: int | None = None


def _name_palaces(ming_index: int) -> dict[int, str]:
    """由該層命宮逆佈十二宮。"""
    return {norm(ming_index - i): n for i, n in enumerate(PALACE_NAMES)}


def _flowing_stars(gan: int, zhi: int) -> dict[int, list[str]]:
    """流曜：流祿流羊流陀流昌流曲流魁流鉞流馬。"""
    lucun = LUCUN_BY_GAN[gan]
    kui, yue = get_table("kuiyue", "tongxing")["table"][gan]
    # 流昌流曲依流年干（甲起巳、乙起午…順行；文曲逆行）
    chang = norm(5 + gan) if gan < 4 else norm(5 + gan + 1)
    qu = norm(9 - gan) if gan < 4 else norm(9 - gan - 1)
    ma = {2: 8, 6: 8, 10: 8, 8: 2, 0: 2, 4: 2, 5: 11, 9: 11, 1: 11, 11: 5, 3: 5, 7: 5}[zhi]

    out: dict[int, list[str]] = {}
    for name, pos in (
        ("流祿", lucun), ("流羊", norm(lucun + 1)), ("流陀", norm(lucun - 1)),
        ("流魁", kui), ("流鉞", yue), ("流昌", chang), ("流曲", qu), ("流馬", ma),
    ):
        out.setdefault(pos, []).append(name)
    return out


# ────────────────────────────  大限  ────────────────────────────

def daxian(chart: Chart, age: int) -> FortuneLayer:
    """依虛歲取所在大限。"""
    for p in chart.palaces:
        if p.daxian and p.daxian[0] <= age <= p.daxian[1]:
            gan = TIAN_GAN.index(p.gan)
            ordinal = (p.daxian[0] - chart.ju_number) // 10 + 1
            return FortuneLayer(
                kind="大限",
                label=f"第{ordinal}大限 {p.daxian[0]}–{p.daxian[1]} {p.gz}",
                ming_index=p.index,
                palace_names=_name_palaces(p.index),
                sihua=sihua_for_gan(gan, chart.config),
                gan=gan,
                zhi=p.index,
            )
    raise ValueError(f"虛歲 {age} 不在大限範圍內（{chart.ju_number}–{chart.ju_number + 119}）")


# ────────────────────────────  流年  ────────────────────────────

def liunian(chart: Chart, year_gan: int, year_zhi: int) -> FortuneLayer:
    """流年命宮即該年年支所在宮。"""
    return FortuneLayer(
        kind="流年",
        label=f"{TIAN_GAN[year_gan]}{DI_ZHI[year_zhi]}年",
        ming_index=year_zhi,
        palace_names=_name_palaces(year_zhi),
        sihua=sihua_for_gan(year_gan, chart.config),
        stars=_flowing_stars(year_gan, year_zhi),
        gan=year_gan,
        zhi=year_zhi,
    )


# ────────────────────────────  斗君與流月  ────────────────────────────

def doujun(chart: Chart, liunian_zhi: int) -> int:
    """
    流年斗君 = 流年正月所在宮。
    由生年正月起流年支，逆數至生月，再由該宮起子時順數至生時。
    """
    m = chart.moment
    return norm(liunian_zhi - (m.lunar_month - 1) + m.hour_index)


def liuyue(chart: Chart, ln: FortuneLayer, month: int) -> FortuneLayer:
    """流月：斗君起正月順行。宮干由該宮五虎遁得出。"""
    assert ln.zhi is not None
    start = doujun(chart, ln.zhi)
    idx = norm(start + month - 1)
    gan = TIAN_GAN.index(chart.palaces[idx].gan)
    return FortuneLayer(
        kind="流月",
        label=f"{ln.label} 流{month}月",
        ming_index=idx,
        palace_names=_name_palaces(idx),
        sihua=sihua_for_gan(gan, chart.config),
        gan=gan,
        zhi=idx,
    )


def liuri(chart: Chart, ly: FortuneLayer, day: int) -> FortuneLayer:
    """流日：流月宮起初一順行。"""
    idx = norm(ly.ming_index + day - 1)
    gan = TIAN_GAN.index(chart.palaces[idx].gan)
    return FortuneLayer(
        kind="流日",
        label=f"{ly.label} 流{day}日",
        ming_index=idx,
        palace_names=_name_palaces(idx),
        sihua=sihua_for_gan(gan, chart.config),
        gan=gan,
        zhi=idx,
    )
