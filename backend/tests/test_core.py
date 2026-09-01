"""排盤核心迴歸測試。每條都對應一句可查證的口訣。"""
from datetime import datetime

import pytest

from app.ziwei.chart import (
    body_palace,
    cast,
    ming_palace,
    palace_gan,
    tianfu_position,
    wuxing_ju,
    yin_palace_gan,
    ziwei_position,
)
from app.ziwei.constants import DI_ZHI, TIAN_GAN


@pytest.mark.parametrize("ju,expected", [(2, "丑"), (3, "辰"), (4, "亥"), (5, "午"), (6, "酉")])
def test_ziwei_day_one(ju, expected):
    """五局初一紫微起例。"""
    assert DI_ZHI[ziwei_position(ju, 1)] == expected


@pytest.mark.parametrize("ju,day,expected", [
    (2, 2, "寅"), (2, 3, "寅"), (3, 3, "寅"), (4, 4, "寅"), (5, 5, "寅"), (6, 6, "寅"),
])
def test_ziwei_exact_multiples(ju, day, expected):
    """日數為局數整倍時，紫微必在寅起算的整步位。"""
    assert DI_ZHI[ziwei_position(ju, day)] == expected


def test_ziwei_covers_all_days():
    """每局每日都必須落在合法宮位，不得越界。"""
    for ju in (2, 3, 4, 5, 6):
        for day in range(1, 31):
            assert 0 <= ziwei_position(ju, day) <= 11


def test_ming_body_same_at_zi():
    """子時生人命身同宮。"""
    for month in range(1, 13):
        assert ming_palace(month, 0) == body_palace(month, 0)


def test_ming_palace_known():
    assert DI_ZHI[ming_palace(1, 0)] == "寅"     # 正月子時命在寅
    assert DI_ZHI[ming_palace(1, 1)] == "丑"     # 正月丑時命在丑
    assert DI_ZHI[ming_palace(12, 0)] == "丑"    # 十二月子時命在丑


def test_tianfu_symmetry():
    """紫微天府對稱於寅申軸，且僅在寅申同宮。"""
    same = [i for i in range(12) if tianfu_position(i) == i]
    assert sorted(same) == [2, 8]


def test_wuhu_dun():
    """五虎遁：甲己丙作首、乙庚戊為頭、丙辛尋庚起、丁壬壬位、戊癸甲寅。"""
    assert [TIAN_GAN[yin_palace_gan(g)] for g in range(10)] == \
        list("丙戊庚壬甲丙戊庚壬甲")


def test_palace_gan_wraps():
    """寅起遁行滿十干，子丑回頭重複寅卯 —— 這是紫微盤天干必然的樣子。"""
    for ygan in range(10):
        gans = [palace_gan(ygan, z) for z in range(12)]
        assert len(set(gans)) == 10
        assert gans[0] == gans[2]      # 子 = 寅
        assert gans[1] == gans[3]      # 丑 = 卯


def test_wuxingju_from_nayin():
    """癸未納音楊柳木 → 木三局。"""
    assert wuxing_ju(1, 7).value == "木三局"     # 乙年、命宮未 → 癸未


# ────────────────  整盤迴歸  ────────────────

GOLDEN = {
    "birth": datetime(1985, 3, 12, 14, 30),
    "gender": "男",
    "expect": {
        "lunar": "乙丑年 1月21日 未時",
        "ming": "未", "body": "酉", "ju": "木三局",
        "ziwei": "申", "tianfu": "申",
        "sihua": {"天機": "祿", "天梁": "權", "紫微": "科", "太陰": "忌"},
        "daxian_first": (3, 12), "forward": False,
    },
}


def test_golden_chart():
    c = cast(GOLDEN["birth"], GOLDEN["gender"])
    e = GOLDEN["expect"]
    m = c.moment
    assert f"{m.year_gz}年 {m.lunar_month}月{m.lunar_day}日 {m.hour_zhi}時" == e["lunar"]
    assert c.palaces[c.ming_index].zhi == e["ming"]
    assert c.palaces[c.body_index].zhi == e["body"]
    assert c.wuxingju.value == e["ju"]
    assert next(p.zhi for p in c.palaces if p.find("紫微")) == e["ziwei"]
    assert next(p.zhi for p in c.palaces if p.find("天府")) == e["tianfu"]
    assert c.is_forward == e["forward"]
    assert c.palaces[c.ming_index].daxian == e["daxian_first"]
    got = {s.name: s.sihua for p in c.palaces for s in p.stars if s.sihua}
    assert got == e["sihua"]


def test_every_major_star_placed_once():
    """十四正曜必須各出現一次，不多不少。"""
    from app.ziwei.constants import MAJOR_STARS
    c = cast(datetime(1990, 7, 4, 9, 15), "女")
    names = [s.name for p in c.palaces for s in p.stars if s.kind == "主星"]
    assert sorted(names) == sorted(MAJOR_STARS)


def test_fuzz_no_crash_and_invariants():
    """兩千張隨機盤：不得拋錯，且十四正曜恆為十四顆。"""
    import random

    from app.ziwei.constants import MAJOR_STARS
    rnd = random.Random(42)
    for _ in range(2000):
        dt = datetime(
            rnd.randint(1930, 2040), rnd.randint(1, 12), rnd.randint(1, 28),
            rnd.randint(0, 23), rnd.randint(0, 59),
        )
        c = cast(dt, rnd.choice(["男", "女"]))
        majors = [s.name for p in c.palaces for s in p.stars if s.kind == "主星"]
        assert len(majors) == len(MAJOR_STARS), dt
        assert len({p.name for p in c.palaces}) == 12, dt
