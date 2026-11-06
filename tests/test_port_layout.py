"""Regression test for issue #4: switches that are not laid out like a CSS326.

The integration assumed 26 ports with the two SFP+ cages at ports 25-26, so on a
CRS309-1G-8S+ (8 SFP+ cages at ports 1-8, copper management port 9) it created
sensors for only two SFP slots. The layout now comes from /link.b (prt, sfp, sfpo).
LINK and SFP are the reporter's dumps (WAWolf99623, CRS309-1G-8S+ r3, SwOS 2.19).

Runnable with `python3 tests/test_port_layout.py` or pytest.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "mikrotik_swos"))
import swos_api as m

LINK_CRS309 = (
    "{comb:0x0000,qsfp:0x0000,en:0x01ff,blkp:0x0000,an:0x01ff,dpxc:0x01ff,fctc:0x01ff,fctr:0x0000,lnk:0x0"
    "1d5,dpx:0x01d5,tfct:0x01d5,rfct:0x0000,paus:0x0000,spd:[0x03,0x07,0x03,0x07,0x03,0x07,0x03,0x03,0x02"
    "],spdc:[0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x01],cm:[0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x"
    "00],qtyp:[0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],prt:0x09,sfp:0x08,sfpo:0x00,nm:['47616d696e6"
    "74c6170746f70','656d707479','6e7574','4c6f63616c557365','4d61696e4c6170746f70','6f70656e','546f20556"
    "e696669','656d707479','4c6162656c5072696e746572'],hop:[0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]"
    ",hops:[0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],len:[0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x"
    "00],flt:[0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],pair:[0xffff,0xffff,0xffff,0xffff,0xffff,0xff"
    "ff,0xffff,0xffff,0xffff],sfpr:[0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x01,0x00],qsfo:0x00,mgmo:0x00,mgm"
    "c:0x00}"
)
SFP_CRS309 = (
    "{vnd:['4f454d20202020202020202020202020','585a534e455420202020202020202020','585a534e455420202020202"
    "020202020','585a534e455420202020202020202020','585a534e455420202020202020202020','585a534e4554202020"
    "20202020202020','4f454d20202020202020202020202020','585a534e455420202020202020202020'],pnr:['585a532"
    "d5346503130472d5420202020','585a532d5346503130472d5420202020','585a532d5346503130472d5420202020','58"
    "5a532d5346503130472d5420202020','585a532d5346503130472d5420202020','585a532d5346503130472d5420202020"
    "','585a532d5346503130472d5420202020','585a532d5346503130472d5420202020'],rev:['41202020','41202020',"
    "'41202020','41202020','41202020','41202020','41202020','41362e31'],ser:['433233202020575332383637302"
    "02020','32303220202032373031383120202020','43323320202057533137363235202020','4332362020205753343532"
    "3038202020','43323320202057533137363435202020','32303220202032373031383220202020','43323320202057533"
    "238373739202020','43323620202057533134353738202020'],dat:['32352d30362d3035','32362d30352d3237','323"
    "42d30382d3330','32362d30372d3031','32342d30382d3330','32362d30352d3237','32352d30362d3035','32362d30"
    "342d3031'],typ:['3835306e6d20266d6d66','3835306e6d20266d6d66','3835306e6d20266d6d66','3835306e6d2026"
    "6d6d66','3835306e6d20266d6d66','3835306e6d20266d6d66','3835306e6d20266d6d66','266d6d66'],wln:[0x0001"
    "4c08,0x00014c08,0x00014c08,0x00014c08,0x00014c08,0x00014c08,0x00014c08,0x00000000],tmp:[0x0000002b,0"
    "x00000023,0x0000003d,0xffffff80,0x0000002e,0x00000024,0x0000002d,0xffffff80],vcc:[0x0cd1,0x0d2d,0x0c"
    "97,0x0000,0x0cc8,0x0d2d,0x0ccd,0x0000],tbs:[0x0006,0x0006,0x0006,0x0000,0x0006,0x0006,0x0006,0x0000]"
    ",tpw:[0x1388,0x1390,0x1388,0x0000,0x1388,0x1390,0x1388,0x0000],rpw:[0x0fa0,0x09c0,0x0fa0,0x0000,0x0f"
    "a0,0x09c0,0x0fa0,0x0000]}"
)
# The layout keys of a CSS326-24G-2S+ (SwOS 2.18), read from a live switch.
LINK_CSS326 = "{prt:0x1a,sfp:0x02,sfpo:0x18,en:0x03f46fff,lnk:0x03f46fdc}"


def _parse(section, text):
    return m._parse_swb(section + ":" + text).get(section, {})


def _client():
    cls = next(c for c in vars(m).values() if isinstance(c, type) and hasattr(c, "_parse_sfp"))
    return cls.__new__(cls)  # parse methods need no network / __init__


def test_crs309_layout_from_link():
    layout = m.port_layout(_parse("link.b", LINK_CRS309), _parse("sfp.b", SFP_CRS309))
    assert (layout.num_ports, layout.num_sfp, layout.sfp_offset) == (9, 8, 0)


def test_crs309_all_eight_sfp_slots():
    sfp = _parse("sfp.b", SFP_CRS309)
    slots = _client()._parse_sfp(sfp, 0)
    assert len(slots) == 8
    assert [s.port for s in slots] == list(range(1, 9))
    assert all(s.present for s in slots)
    # slots 4 and 8 report the no-DDM sentinel; the others have diagnostics
    assert slots[3].temperature_c is None and slots[7].temperature_c is None
    assert slots[2].temperature_c == 61


def test_crs309_port_stats_cover_nine_ports():
    link = _parse("link.b", LINK_CRS309)
    stats = _client()._parse_port_stats({}, link["nm"], link["lnk"], 9)
    assert len(stats) == 9
    assert stats[8].name == "LabelPrinter"


def test_css326_layout_unchanged():
    layout = m.port_layout(_parse("link.b", LINK_CSS326), {})
    assert (layout.num_ports, layout.num_sfp, layout.sfp_offset) == (26, 2, 24)


def test_layout_fallback_without_layout_keys():
    # CSS106 builds without prt/sfp/sfpo: 6 names, one scalar SFP -> SFP is port 6
    link = {"nm": ["a", "b", "c", "d", "e", "f"]}
    layout = m.port_layout(link, {"vnd": "MikroTik"})
    assert (layout.num_ports, layout.num_sfp, layout.sfp_offset) == (6, 1, 5)


if __name__ == "__main__":
    test_crs309_layout_from_link()
    test_crs309_all_eight_sfp_slots()
    test_crs309_port_stats_cover_nine_ports()
    test_css326_layout_unchanged()
    test_layout_fallback_without_layout_keys()
    print("all port layout tests passed")
