"""
紫微斗數 — 曆法層
==================
紫微排盤只吃四樣東西：農曆年干支、農曆月、農曆日、時辰。
但由西曆生辰推到這四樣，中間有三個會改盤的決策點：

1. 真太陽時  —— 要不要按出生地經度校正？跨一個時辰就換命宮。
2. 早晚子時  —— 23:00–23:59 算今日還是明日？換日就換農曆日 → 換紫微。
3. 年 界     —— 紫微以正月初一分年（主流），八字以立春分年。
                 生於立春後、正月初一前（或反之）的人，年干支會不同 →
                 祿存、四化、魁鉞全變。

三個都做成明示選項，預設值採紫微主流，並在輸出中回報實際採用值，
好讓爭議盤可以一眼看出是哪個開關造成差異。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

import sxtwl

from .constants import DI_ZHI, TIAN_GAN


class YearBoundary(str, Enum):
    LUNAR_NEW_YEAR = "正月初一"   # 紫微主流
    LICHUN = "立春"               # 八字慣例


class ZiHourRule(str, Enum):
    SWITCH_AT_23 = "23時換日"     # 早子時歸翌日（紫微主流）
    LATE_ZI_SAME_DAY = "夜子時不換日"   # 23:00–23:59 仍算當日


@dataclass(frozen=True)
class SolarTimeCorrection:
    """真太陽時校正結果（分鐘）。"""
    longitude_minutes: float   # 經度時差
    equation_minutes: float    # 均時差
    total_minutes: float

    @property
    def applied(self) -> bool:
        return abs(self.total_minutes) > 1e-9


@dataclass(frozen=True)
class LunarMoment:
    """排盤所需的完整曆法快照。"""
    solar: datetime              # 原始西曆時刻
    effective: datetime          # 校正後、且套用換日規則之後的時刻
    lunar_year: int
    lunar_month: int             # 1..12
    lunar_day: int               # 1..30
    is_leap_month: bool
    year_gan: int
    year_zhi: int
    month_gan: int
    month_zhi: int
    day_gan: int
    day_zhi: int
    hour_index: int              # 子=0 … 亥=11
    correction: SolarTimeCorrection
    year_boundary: YearBoundary
    zi_rule: ZiHourRule

    @property
    def year_gz(self) -> str:
        return f"{TIAN_GAN[self.year_gan]}{DI_ZHI[self.year_zhi]}"

    @property
    def hour_zhi(self) -> str:
        return DI_ZHI[self.hour_index]


# ────────────────────────────  真太陽時  ────────────────────────────

def equation_of_time_minutes(dt: datetime) -> float:
    """
    均時差近似式（NOAA 簡化版），誤差 < 30 秒，對定時辰綽綽有餘。
    """
    import math

    n = dt.timetuple().tm_yday
    b = 2 * math.pi * (n - 81) / 364.0
    return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def true_solar_time(
    dt: datetime, longitude: float | None, tz_offset_hours: float
) -> tuple[datetime, SolarTimeCorrection]:
    """
    把鐘錶時間換成真太陽時。longitude=None 表示不校正。
    香港：longitude=114.17, tz_offset_hours=8 → 約 -23 分鐘經度時差。
    """
    if longitude is None:
        return dt, SolarTimeCorrection(0.0, 0.0, 0.0)

    standard_meridian = tz_offset_hours * 15.0
    lon_minutes = (longitude - standard_meridian) * 4.0
    eot = equation_of_time_minutes(dt)
    total = lon_minutes + eot
    return dt + timedelta(minutes=total), SolarTimeCorrection(lon_minutes, eot, total)


# ────────────────────────────  時辰  ────────────────────────────

def hour_to_zhi(hour: int) -> int:
    """24 小時制 -> 時辰地支序。23 時與 0 時同為子。"""
    return ((hour + 1) // 2) % 12


# ────────────────────────────  主入口  ────────────────────────────

def resolve(
    birth: datetime,
    *,
    longitude: float | None = None,
    tz_offset_hours: float = 8.0,
    year_boundary: YearBoundary = YearBoundary.LUNAR_NEW_YEAR,
    zi_rule: ZiHourRule = ZiHourRule.SWITCH_AT_23,
) -> LunarMoment:
    """由西曆生辰求出排盤所需的曆法快照。"""
    corrected, correction = true_solar_time(birth, longitude, tz_offset_hours)

    hour_index = hour_to_zhi(corrected.hour)

    # 早子時換日
    effective = corrected
    if corrected.hour == 23 and zi_rule is ZiHourRule.SWITCH_AT_23:
        effective = corrected + timedelta(days=1)

    day = sxtwl.fromSolar(effective.year, effective.month, effective.day)

    use_lichun = year_boundary is YearBoundary.LICHUN
    # sxtwl: getLunarYear(True) 以春節為界；False 以立春為界
    lunar_year = day.getLunarYear(not use_lichun)
    year_gz = day.getYearGZ(not use_lichun)
    month_gz = day.getMonthGZ()
    day_gz = day.getDayGZ()

    return LunarMoment(
        solar=birth,
        effective=effective,
        lunar_year=lunar_year,
        lunar_month=day.getLunarMonth(),
        lunar_day=day.getLunarDay(),
        is_leap_month=bool(day.isLunarLeap()),
        year_gan=year_gz.tg,
        year_zhi=year_gz.dz,
        month_gan=month_gz.tg,
        month_zhi=month_gz.dz,
        day_gan=day_gz.tg,
        day_zhi=day_gz.dz,
        hour_index=hour_index,
        correction=correction,
        year_boundary=year_boundary,
        zi_rule=zi_rule,
    )


def jiazi_index(gan: int, zhi: int) -> int:
    """由干支求六十甲子序（0..59）。"""
    for i in range(60):
        if i % 10 == gan and i % 12 == zhi:
            return i
    raise ValueError(f"干支不成立：gan={gan}, zhi={zhi}")
