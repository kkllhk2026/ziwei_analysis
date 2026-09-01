"""
紫微斗數 — 流派設定
====================
一張盤之所以會有兩個答案，永遠出在下面這幾個開關。
把它們集中成一個物件，好處是：
  · 任何一張盤都可以連同它的 SchoolConfig 一起存檔、重現
  · 兩個流派的差異可以自動 diff（見 tests/test_school_diff.py）
  · 客戶問「點解你排出嚟同某某網站唔同」，可以直接指出是哪個開關
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from .calendar import YearBoundary, ZiHourRule


@dataclass(frozen=True)
class SchoolConfig:
    name: str = "通行本"

    # ── 曆法 ──
    year_boundary: YearBoundary = YearBoundary.LUNAR_NEW_YEAR
    zi_rule: ZiHourRule = ZiHourRule.SWITCH_AT_23
    use_true_solar_time: bool = True

    # ── 閏月歸屬 ──
    # 閏月生人的「月」取哪個？影響命宮、身宮、左輔右弼、大限起運。
    #   "same"   閏月當本月算（通行）
    #   "next"   閏月當下月算
    #   "split"  月中之前算本月、之後算下月（中州派常見）
    leap_month_rule: Literal["same", "next", "split"] = "same"

    # ── 選表 ──
    sihua_table: str = "tongxing"      # tables.REGISTRY["sihua"]
    kuiyue_table: str = "tongxing"
    huoling_table: str = "quanshu"

    # ── 星曜取捨 ──
    include_minor_stars: bool = True   # 雜曜
    include_shensha: bool = True       # 長生／博士／歲前／將前 十二神
    include_flowing_stars: bool = True # 流曜

    # ── 宮名 ──
    use_pu_yi: bool = False            # 交友 -> 僕役
    use_shi_ye: bool = False           # 官祿 -> 事業

    # ── 大限 ──
    # "xu"  虛歲（通行）
    # "shi" 實歲
    daxian_age_basis: Literal["xu", "shi"] = "xu"

    # ── 嚴格模式 ──
    # True 時，任何未經覆核的流派表都會拋錯而非默默使用。
    strict_tables: bool = False

    notes: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["year_boundary"] = self.year_boundary.value
        d["zi_rule"] = self.zi_rule.value
        return d


# ── 預設幾套，開箱即用 ──

TONGXING = SchoolConfig(
    name="通行本",
    notes="紫微斗數全書系。四化、火鈴、魁鉞皆採最通行的一版。",
)

ZHONGZHOU = SchoolConfig(
    name="中州派",
    leap_month_rule="split",
    huoling_table="yinyang",
    use_pu_yi=True,
    notes="閏月以月中分屬、火鈴依陰陽男女分順逆。四化表待你依師承覆核後切換至 lineage。",
)

FEIXING = SchoolConfig(
    name="飛星／欽天四化",
    include_minor_stars=False,
    include_shensha=False,
    notes="論斷以宮干飛化為主，雜曜神煞不入盤以免干擾。四化表務必改用 lineage。",
)

PRESETS = {p.name: p for p in (TONGXING, ZHONGZHOU, FEIXING)}
