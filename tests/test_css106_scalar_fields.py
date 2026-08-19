"""Regression test for issue #3: single-SFP / single-unit switches (CSS106).

SwOS returns per-SFP fields (and PoE) as bare scalars instead of lists on
single-unit models, which crashed setup with "object of type 'int' has no
len()". These are the real /sfp.b and /link.b dumps from the reporter
(JesusSanchezLopez, CSS106-1G-4P-1S, SwOS 0.2.2, issue #3).

Runnable with `python3 tests/test_css106_scalar_fields.py` or pytest.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "mikrotik_swos"))
import swos_api as m

SFP = ("{vnd:'4d696b726f54696b2020202020202020',pnr:'532d524a303120202020202020202020',"
       "rev:'322e3020',ser:'48474330314d43325850582020202020',dat:'32342d30332d3236',"
       "typ:'3130306d20636f70706572',wln:0x00000000,tmp:0xffffff80,vcc:0x0000,tbs:0x0000,"
       "tpw:0x0000,rpw:0x0000}")
LINK = ("{nm:['55706c696e6b','506c617973746174696f6e2035','4c6567696f6e203569','506f72742034',"
        "'486973656e7365205456','4e696e74656e646f20537769746368'],en:0x2f,lnk:0x21,"
        "spd:[0x02,0x03,0x03,0x03,0x03,0x02],dpx:0x21,an:0x3f,spdc:[0x00,0x00,0x00,0x00,0x00,0x00],"
        "dpxc:0x3f,fct:0x3f,poe:[0x01,0x00,0x00,0x00,0x00,0x01],prio:[0x00,0x00,0x01,0x02,0x03,0x00],"
        "poes:[0x00,0x01,0x01,0x01,0x01,0x00],curr:[0x0000,0x0000,0x0000,0x0000,0x0000,0x0000],"
        "pwr:[0x0000,0x0000,0x0000,0x0000,0x0000,0x0000]}")


def _client():
    cls = next(c for c in vars(m).values() if isinstance(c, type) and hasattr(c, "_parse_sfp"))
    return cls.__new__(cls)  # parse methods need no network / __init__


def test_sfp_scalar_fields_do_not_crash():
    sfp = m._parse_swb("sfp.b:" + SFP).get("sfp.b", {})
    assert isinstance(sfp.get("tmp"), int)  # scalar, not list -> used to crash len()
    slots = _client()._parse_sfp(sfp)
    assert len(slots) == 1
    assert slots[0].present is True
    assert slots[0].vendor == "MikroTik"
    assert slots[0].sfp_type == "100m copper"


def test_poe_from_link_when_no_poe_endpoint():
    link = m._parse_swb("link.b:" + LINK).get("link.b", {})
    ports = _client()._parse_poe(link, [str(n) for n in link.get("nm", [])])
    assert len(ports) == 6  # CSS106: PoE data lives in /link.b, 6-element lists


def test_safe_get_is_scalar_safe():
    assert m._safe_get(0xFFFFFF80, 0, default=-1) == -1  # int, not list -> default, no crash


if __name__ == "__main__":
    test_sfp_scalar_fields_do_not_crash()
    test_poe_from_link_when_no_poe_endpoint()
    test_safe_get_is_scalar_safe()
    print("all CSS106 regression tests passed")
