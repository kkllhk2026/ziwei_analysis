"""
紫微斗數 — 排盤引擎
====================
每一步都對應一條可查證的口訣，並在 docstring 註明依據，
方便日後有人質疑某顆星的落宮時，可以逐步回溯而不是重讀全部程式。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from . import tables
from .calendar import LunarMoment, jiazi_index, resolve
from .constants import (
    BOSHI_12,
    CHANGSHENG_12,
    DI_ZHI,
    GAN_YINYANG,
    JIANGQIAN_12,
    JU_CHANGSHENG,
    JU_NUMBER,
    MINGZHU,
    PALACE_ALIASES,
    PALACE_NAMES,
    SANHE_GROUP,
    SHENZHU,
    SIHUA_ORDER,
    SUIQIAN_12,
    TIAN_GAN,
    TIANFU_OFFSETS,
    ZIWEI_OFFSETS,
    WuXingJu,
    norm,
)
from .schools import TONGXING, SchoolConfig

# ══════════════════════════════════════════════════════════════════
#  資料結構
# ══════════════════════════════════════════════════════════════════

@dataclass
class Star:
    name: str
    kind: str                       # StarType 值
    brightness: str | None = None   # 廟旺利陷
    sihua: str | None = None        # 生年四化：祿/權/科/忌
    self_hua: str | None = None     # 自化


@dataclass
class Palace:
    index: int                      # 地支序 0..11
    zhi: str
    gan: str
    name: str                       # 命宮/兄弟/…
    stars: list[Star] = field(default_factory=list)
    is_body: bool = False           # 身宮
    is_lai_yin: bool = False        # 來因宮
    changsheng: str | None = None
    boshi: str | None = None
    suiqian: str | None = None
    jiangqian: str | None = None
    daxian: tuple[int, int] | None = None   # (起歲, 迄歲)
    xiaoxian_ages: list[int] = field(default_factory=list)

    def add(self, name: str, kind: str) -> None:
        self.stars.append(Star(name=name, kind=kind))

    def find(self, name: str) -> Star | None:
        return next((s for s in self.stars if s.name == name), None)

    @property
    def gz(self) -> str:
        return f"{self.gan}{self.zhi}"


@dataclass
class Chart:
    moment: LunarMoment
    gender: str                     # "男" / "女"
    config: SchoolConfig
    palaces: list[Palace]           # 長度 12，index 即地支序
    ming_index: int
    body_index: int
    wuxingju: WuXingJu
    ju_number: int
    ming_zhu: str
    shen_zhu: str
    yin_yang_gender: str            # 陽男 / 陰男 / 陽女 / 陰女
    is_forward: bool                # 大限順行？

    def palace(self, name: str) -> Palace:
        for p in self.palaces:
            if p.name == name:
                return p
        raise KeyError(name)

    def by_zhi(self, zhi_index: int) -> Palace:
        return self.palaces[norm(zhi_index)]


# ══════════════════════════════════════════════════════════════════
#  1. 定命宮、身宮
# ══════════════════════════════════════════════════════════════════

def ming_palace(lunar_month: int, hour_index: int) -> int:
    """
    寅宮起正月順數至生月，再由該宮起子時逆數至生時。
    命宮 = (寅 + 月 - 1 - 時) mod 12
    驗：正月子時 → 寅。正月丑時 → 丑。
    """
    return norm(2 + (lunar_month - 1) - hour_index)


def body_palace(lunar_month: int, hour_index: int) -> int:
    """同上但順數 → 身宮 = (寅 + 月 - 1 + 時) mod 12。正月子時命身同宮。"""
    return norm(2 + (lunar_month - 1) + hour_index)


# ══════════════════════════════════════════════════════════════════
#  2. 五虎遁 —— 定各宮天干
# ══════════════════════════════════════════════════════════════════

def yin_palace_gan(year_gan: int) -> int:
    """
    甲己之年丙作首、乙庚之歲戊為頭、丙辛必定尋庚起、
    丁壬壬位順行流、戊癸何方發，甲寅之上好追求。
    """
    return ((year_gan % 5) * 2 + 2) % 10


def palace_gan(year_gan: int, zhi_index: int) -> int:
    """由寅宮天干順行推得任一宮天干。"""
    return (yin_palace_gan(year_gan) + norm(zhi_index - 2)) % 10


# ══════════════════════════════════════════════════════════════════
#  3. 五行局 —— 命宮干支納音
# ══════════════════════════════════════════════════════════════════

def wuxing_ju(year_gan: int, ming_index: int) -> WuXingJu:
    gan = palace_gan(year_gan, ming_index)
    idx = jiazi_index(gan, ming_index)
    element = tables.NAYIN_WUXING[idx // 2]
    return WuXingJu(tables.NAYIN_TO_JU[element])


# ══════════════════════════════════════════════════════════════════
#  4. 安紫微 —— 依局數與生日
# ══════════════════════════════════════════════════════════════════

def ziwei_position(ju: int, lunar_day: int) -> int:
    """
    求最小的 n 使 ju*n >= day，餘數 r = ju*n - day。
    r 為偶 → 由寅順行 (n-1+r) 步；r 為奇 → 由寅逆行 (r-n+1) 步。
    驗：水二局初一在丑、木三局初一在辰、金四局初一在亥、
        土五局初一在午、火六局初一在酉。
    """
    n = -(-lunar_day // ju)          # ceil
    r = ju * n - lunar_day
    step = (n - 1 + r) if r % 2 == 0 else (n - 1 - r)
    return norm(2 + step)


def tianfu_position(ziwei_index: int) -> int:
    """紫微天府相對寅申軸對稱：天府 = (4 - 紫微) mod 12。"""
    return norm(4 - ziwei_index)


# ══════════════════════════════════════════════════════════════════
#  5. 各系星曜落宮
# ══════════════════════════════════════════════════════════════════

def hour_stars(hour: int) -> dict[str, int]:
    """時系星。"""
    return {
        "文昌": norm(10 - hour),   # 戌起子時逆
        "文曲": norm(4 + hour),    # 辰起子時順
        "地空": norm(11 - hour),   # 亥起子時逆
        "地劫": norm(11 + hour),   # 亥起子時順
        "台輔": norm(6 + hour),
        "封誥": norm(2 + hour),
    }


def month_stars(month: int) -> dict[str, int]:
    """月系星。"""
    return {
        "左輔": norm(4 + month - 1),    # 辰起正月順
        "右弼": norm(10 - month + 1),   # 戌起正月逆
        "天刑": norm(9 + month - 1),    # 酉起正月順
        "天姚": norm(1 + month - 1),    # 丑起正月順
    }


def day_stars(day: int, zuofu: int, youbi: int, wenchang: int, wenqu: int) -> dict[str, int]:
    """日系星（依附於左輔右弼文昌文曲）。"""
    return {
        "三台": norm(zuofu + day - 1),
        "八座": norm(youbi - day + 1),
        "恩光": norm(wenchang + day - 2),
        "天貴": norm(wenqu + day - 2),
    }


def year_gan_stars(year_gan: int, cfg: SchoolConfig) -> dict[str, int]:
    """年干系星：祿存、羊陀、魁鉞。"""
    lucun = tables.LUCUN_BY_GAN[year_gan]
    kuiyue = tables.get_table("kuiyue", cfg.kuiyue_table, strict=cfg.strict_tables)
    kui, yue = kuiyue["table"][year_gan]
    return {
        "祿存": lucun,
        "擎羊": norm(lucun + 1),
        "陀羅": norm(lucun - 1),
        "天魁": kui,
        "天鉞": yue,
    }


def year_zhi_stars(year_zhi: int) -> dict[str, int]:
    """年支系星。"""
    group = SANHE_GROUP[year_zhi]
    return {
        "天馬": tables.TIANMA_BY_GROUP[group],
        "紅鸞": norm(3 - year_zhi),      # 卯起子年逆
        "天喜": norm(3 - year_zhi + 6),
        "天哭": norm(6 - year_zhi),      # 午起子年逆
        "天虛": norm(6 + year_zhi),      # 午起子年順
        "龍池": norm(4 + year_zhi),      # 辰起子年順
        "鳳閣": norm(10 - year_zhi),     # 戌起子年逆
        "華蓋": norm({"火局": 10, "水局": 4, "金局": 1, "木局": 7}[group]),
        "咸池": norm({"火局": 3, "水局": 9, "金局": 6, "木局": 0}[group]),
    }


def huoling_stars(year_zhi: int, hour: int, is_forward: bool, cfg: SchoolConfig) -> dict[str, int]:
    """火星鈴星 —— 流派分歧最大者。"""
    tbl = tables.get_table("huoling", cfg.huoling_table, strict=cfg.strict_tables)
    huo_start, ling_start = tbl["table"][SANHE_GROUP[year_zhi]]
    sign = 1 if (tbl["_DIRECTION"] == "always_forward" or is_forward) else -1
    return {
        "火星": norm(huo_start + sign * hour),
        "鈴星": norm(ling_start + sign * hour),
    }


# ══════════════════════════════════════════════════════════════════
#  6. 神煞十二神
# ══════════════════════════════════════════════════════════════════

def _spread(names: tuple[str, ...], start: int, forward: bool) -> dict[int, str]:
    step = 1 if forward else -1
    return {norm(start + step * i): n for i, n in enumerate(names)}


def changsheng_12(ju: WuXingJu, forward: bool) -> dict[int, str]:
    return _spread(CHANGSHENG_12, JU_CHANGSHENG[ju], forward)


def boshi_12(lucun: int, forward: bool) -> dict[int, str]:
    return _spread(BOSHI_12, lucun, forward)


def suiqian_12(year_zhi: int) -> dict[int, str]:
    return _spread(SUIQIAN_12, year_zhi, True)


def jiangqian_12(year_zhi: int) -> dict[int, str]:
    jiang_star = {"火局": 6, "水局": 0, "金局": 9, "木局": 3}[SANHE_GROUP[year_zhi]]
    return _spread(JIANGQIAN_12, jiang_star, True)


# ══════════════════════════════════════════════════════════════════
#  7. 大限 / 小限
# ══════════════════════════════════════════════════════════════════

def daxian_ranges(ming_index: int, ju_number: int, forward: bool) -> dict[int, tuple[int, int]]:
    """命宮起，陽男陰女順、陰男陽女逆，每宮十年，起運歲即局數。"""
    step = 1 if forward else -1
    out = {}
    for i in range(12):
        start = ju_number + i * 10
        out[norm(ming_index + step * i)] = (start, start + 9)
    return out


def xiaoxian_start(year_zhi: int) -> int:
    """寅午戌起辰、申子辰起戌、巳酉丑起未、亥卯未起丑。"""
    return {"火局": 4, "水局": 10, "金局": 7, "木局": 1}[SANHE_GROUP[year_zhi]]


def xiaoxian_map(year_zhi: int, gender: str) -> dict[int, list[int]]:
    """1..120 虛歲的小限落宮。男順女逆。"""
    start = xiaoxian_start(year_zhi)
    step = 1 if gender == "男" else -1
    out: dict[int, list[int]] = {i: [] for i in range(12)}
    for age in range(1, 121):
        out[norm(start + step * (age - 1))].append(age)
    return out


# ══════════════════════════════════════════════════════════════════
#  8. 四化
# ══════════════════════════════════════════════════════════════════

def sihua_for_gan(gan: int, cfg: SchoolConfig) -> dict[str, str]:
    """某天干的四化 → {星名: 化曜}。"""
    tbl = tables.get_table("sihua", cfg.sihua_table, strict=cfg.strict_tables)
    return {star: SIHUA_ORDER[i] for i, star in enumerate(tbl["table"][gan])}


# ══════════════════════════════════════════════════════════════════
#  9. 組盤
# ══════════════════════════════════════════════════════════════════

def cast(
    birth: datetime,
    gender: str,
    *,
    config: SchoolConfig = TONGXING,
    longitude: float | None = 114.17,
    tz_offset_hours: float = 8.0,
) -> Chart:
    """排一張本命盤。"""
    if gender not in ("男", "女"):
        raise ValueError("gender 必須是 '男' 或 '女'")

    moment = resolve(
        birth,
        longitude=longitude if config.use_true_solar_time else None,
        tz_offset_hours=tz_offset_hours,
        year_boundary=config.year_boundary,
        zi_rule=config.zi_rule,
    )

    month = _effective_month(moment, config)
    day, hour = moment.lunar_day, moment.hour_index
    ygan, yzhi = moment.year_gan, moment.year_zhi

    # ── 宮位骨架 ──
    ming = ming_palace(month, hour)
    body = body_palace(month, hour)
    palaces = [
        Palace(
            index=i,
            zhi=DI_ZHI[i],
            gan=TIAN_GAN[palace_gan(ygan, i)],
            name="",
        )
        for i in range(12)
    ]
    for offset, pname in enumerate(PALACE_NAMES):
        p = palaces[norm(ming - offset)]        # 十二宮名逆佈
        if pname == "交友" and config.use_pu_yi:
            pname = PALACE_ALIASES["交友"]
        elif pname == "官祿" and config.use_shi_ye:
            pname = PALACE_ALIASES["官祿"]
        p.name = pname
    palaces[body].is_body = True

    # ── 五行局與陰陽順逆 ──
    ju = wuxing_ju(ygan, ming)
    ju_num = JU_NUMBER[ju]
    yy = GAN_YINYANG[ygan]
    yy_gender = f"{yy}{gender}"
    forward = (yy == "陽" and gender == "男") or (yy == "陰" and gender == "女")

    # ── 十四正曜 ──
    zw = ziwei_position(ju_num, day)
    tf = tianfu_position(zw)
    for name, off in ZIWEI_OFFSETS.items():
        palaces[norm(zw + off)].add(name, "主星")
    for name, off in TIANFU_OFFSETS.items():
        palaces[norm(tf + off)].add(name, "主星")

    # ── 吉星煞星 ──
    hs = hour_stars(hour)
    ms = month_stars(month)
    ygs = year_gan_stars(ygan, config)
    hls = huoling_stars(yzhi, hour, forward, config)

    for name in ("文昌", "文曲", "左輔", "右弼", "天魁", "天鉞"):
        pos = hs.get(name, ms.get(name, ygs.get(name)))
        palaces[pos].add(name, "吉星")
    for name in ("擎羊", "陀羅"):
        palaces[ygs[name]].add(name, "煞星")
    for name in ("火星", "鈴星"):
        palaces[hls[name]].add(name, "煞星")
    for name in ("地空", "地劫"):
        palaces[hs[name]].add(name, "煞星")
    palaces[ygs["祿存"]].add("祿存", "吉星")

    yzs = year_zhi_stars(yzhi)
    palaces[yzs["天馬"]].add("天馬", "吉星")

    # ── 雜曜 ──
    if config.include_minor_stars:
        ds = day_stars(day, ms["左輔"], ms["右弼"], hs["文昌"], hs["文曲"])
        for name in ("台輔", "封誥"):
            palaces[hs[name]].add(name, "雜曜")
        for name in ("天刑", "天姚"):
            palaces[ms[name]].add(name, "雜曜")
        for name, pos in ds.items():
            palaces[pos].add(name, "雜曜")
        for name in ("紅鸞", "天喜", "天哭", "天虛", "龍池", "鳳閣", "華蓋", "咸池"):
            palaces[yzs[name]].add(name, "雜曜")

    # ── 生年四化 ──
    for star_name, hua in sihua_for_gan(ygan, config).items():
        for p in palaces:
            s = p.find(star_name)
            if s:
                s.sihua = hua

    # ── 自化（宮干四化落本宮）──
    for p in palaces:
        gan_idx = TIAN_GAN.index(p.gan)
        for star_name, hua in sihua_for_gan(gan_idx, config).items():
            s = p.find(star_name)
            if s:
                s.self_hua = hua

    # ── 神煞 ──
    if config.include_shensha:
        cs = changsheng_12(ju, forward)
        bs = boshi_12(ygs["祿存"], forward)
        sq = suiqian_12(yzhi)
        jq = jiangqian_12(yzhi)
        for i, p in enumerate(palaces):
            p.changsheng, p.boshi, p.suiqian, p.jiangqian = cs[i], bs[i], sq[i], jq[i]

    # ── 大限 / 小限 ──
    for i, rng in daxian_ranges(ming, ju_num, forward).items():
        palaces[i].daxian = rng
    for i, ages in xiaoxian_map(yzhi, gender).items():
        palaces[i].xiaoxian_ages = ages

    return Chart(
        moment=moment,
        gender=gender,
        config=config,
        palaces=palaces,
        ming_index=ming,
        body_index=body,
        wuxingju=ju,
        ju_number=ju_num,
        ming_zhu=MINGZHU[ming],
        shen_zhu=SHENZHU[yzhi],
        yin_yang_gender=yy_gender,
        is_forward=forward,
    )


def _effective_month(moment: LunarMoment, cfg: SchoolConfig) -> int:
    """閏月歸屬。"""
    if not moment.is_leap_month:
        return moment.lunar_month
    if cfg.leap_month_rule == "next":
        return moment.lunar_month + 1
    if cfg.leap_month_rule == "split":
        return moment.lunar_month if moment.lunar_day <= 15 else moment.lunar_month + 1
    return moment.lunar_month
