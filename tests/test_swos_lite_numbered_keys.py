"""Regression test for issue #5: SwOS Lite answers with numbered keys.

An FTC11XG on SwOS Lite 2.18 sends every endpoint as i01, i02, ... instead of the
named keys (upt, brd, nm, ...) the parser reads, so the device was added but had
no data. These are the reporter's dumps (JesusSanchezLopez, issue #5), taken
together with screenshots of the switch web UI; the expected values below are
the ones the web UI showed (System, Link, SFP and Stats pages).

Runnable with `python3 tests/test_swos_lite_numbered_keys.py` or pytest.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "mikrotik_swos"))
import swos_api as m

SYS = (
    "{i01:0x00028344,i02:0x0900a8c0,i03:'f41e57c2890f',i04:'484a333041324250583544',i05:'46544331315847',"
    "i06:'322e3138',i0b:0x65e5e01c,i07:'46544331315847',i12:0x0007,i08:0x0007,i21:0x00,i09:0x0900a8c0,i0a"
    ":0x01,i0c:0x00,i0d:0x01,i0e:0x8000,i0f:0x00,i10:0x8000,i11:'04f41cfe494c',i13:0x0007,i14:0x01,i15:0x"
    "0000,i1e:0x0000,i16:0x0000,i1f:0x0000,i1c:0x00,i1d:0x00,i17:0x00,i29:0x00,i27:0x0000,i28:0x01,i19:0x"
    "00000000,i1a:0x00,i1b:0x0000,i20:0x00,i22:0x003b,i23:0x00,i24:0x0000,i25:0x0000,i26:0x0000}"
)
LINK = (
    "{i01:0x0007,i0c:0x0000,i02:0x0007,i03:0x0007,i16:0x0000,i12:0x0000,i05:[0x00,0x00,0x00],i06:0x0006,i"
    "07:0x0006,i13:0x0000,i14:0x0000,i15:0x0000,i0b:0x0000,i08:[0x07,0x05,0x03],i09:[0x00000000,0x00001ce"
    "f,0x0000008b],i0a:['506f727431','506f727432','5346502b31'],i0d:[0x00,0x00,0x00],i0e:[0x00,0x00,0x00]"
    ",i0f:[0x00,0x00,0x00],i10:[0x00,0x00,0x00],i11:[0xffff,0xffff,0xffff]}"
)
SFP = (
    "{i01:'4d696b726f54696b20202020202020',i02:'532b3331444c433130442020202020',i03:'312e3020',i04:'44473"
    "2353130313530313938202020',i05:'32352d31302d3135',i06:'7b303531657d6e6d2073696e676c652d6d6f646520666"
    "9626572',i07:0x0001ffb8,i08:0x002d,i09:0x0ca5,i0a:0x0028,i0b:0x16d9,i0c:0x184d}"
)
STATS = (
    "{i01:[0x00000000,0x0a004a88,0x6e9b8760],i02:[0x00000000,0x00000000,0x00000001],i03:[0x00000000,0x000"
    "00000,0x00000000],i04:[0x00000000,0x00000000,0x00000000],i05:[0x00000000,0x000f9f74,0x00629783],i06:"
    "[0x00000000,0x00000000,0x00000000],i07:[0x00000000,0x0000128c,0x00064c62],i08:[0x00000000,0x0000282c"
    ",0x00023063],i09:[0x00000000,0x0009cdc2,0x000c9bf3],i0a:[0x00000000,0x000d065c,0x000dace3],i0b:[0x00"
    "000000,0x00110b4a,0x001189fc],i0c:[0x00000000,0x000b2cf6,0x000bb36d],i0d:[0x00000000,0x00020297,0x00"
    "021921],i0e:[0x00000000,0x0042a761,0x0042a7ee],i0f:[0x00000000,0x6d1533ef,0x0ac7d0f4],i10:[0x0000000"
    "0,0x00000001,0x00000000],i11:[0x00000000,0x0060e04d,0x0010ff5f],i12:[0x00000000,0x00000000,0x0000000"
    "0],i13:[0x00000000,0x0001bdfe,0x00001664],i14:[0x00000000,0x00053ddf,0x00001d43],i15:[0x00000000,0x0"
    "0000000,0x00000000],i16:[0x00000000,0x00000000,0x00000000],i17:[0x00000000,0x00000000,0x00000000],i1"
    "8:[0x00000000,0x00000000,0x00000000],i19:[0x00000000,0x00000000,0x00000000],i1a:[0x00000000,0x000000"
    "00,0x00000000],i1b:[0x00000000,0x00000000,0x00000000],i1c:[0x00000000,0x00000000,0x00000000],i1d:[0x"
    "00000000,0x00000000,0x00000000],i1e:[0x00000000,0x00000000,0x00000000],i1f:[0x00000000,0x00000000,0x"
    "00000000],i20:[0x00000000,0x00000000,0x00000000],i21:[0x00000000,0x00000000,0x00000c99],i22:[0x00000"
    "000,0x00000000,0x000015d4],i23:[0x00000000,0x000fda2c,0x006b1448],i24:[0x00000000,0x0067dc2a,0x00113"
    "306],i25:[0x00000000,0x00000000,0x0000001f],i26:[0x00000000,0x00000000,0x0000000e],i27:[0x00000000,0"
    "x00000000,0x00000000],i28:[0x00000000,0x00000000,0x00000000],i29:[0x00000000,0x00000000,0x00000000],"
    "i2a:[0x00000000,0x00000000,0x00000000],i2b:[0x00000000,0x00000000,0x00000000],i2c:[0x00000000,0x0000"
    "0000,0x00000000]}"
)


def _parse(section, text):
    data = m._parse_swb(section + ":" + text).get(section, {})
    assert m.is_numbered(data)
    return m.normalize_lite(section, data)


def _client():
    cls = next(c for c in vars(m).values() if isinstance(c, type) and hasattr(c, "_parse_sfp"))
    return cls.__new__(cls)  # parse methods need no network / __init__


def test_system_page():
    si = _client()._parse_system_info(_parse("sys.b", SYS))
    assert si.model == "FTC11XG"
    assert si.hostname == "FTC11XG"
    assert si.firmware == "2.18"
    assert si.serial_number == "HJ30A2BPX5D"
    assert si.mac == "f4:1e:57:c2:89:0f"
    assert si.ip == "192.168.0.9"
    assert si.uptime_seconds == 164676  # web UI: 1 days 21:44:47 (taken a few seconds later)


def test_link_page_and_layout():
    link = _parse("link.b", LINK)
    assert link["nm"] == ["Port1", "Port2", "SFP+1"]
    assert link["en"] == 0b111       # all three enabled
    assert link["lnk"] == 0b110      # Port1 no link, Port2 and SFP+1 link on
    layout = m.port_layout(link, _parse("sfp.b", SFP))
    assert (layout.num_ports, layout.num_sfp, layout.sfp_offset) == (3, 1, 2)


def test_sfp_page():
    slots = _client()._parse_sfp(_parse("sfp.b", SFP), 2)
    assert len(slots) == 1
    s = slots[0]
    assert s.port == 3
    assert (s.vendor, s.part_number, s.revision) == ("MikroTik", "S+31DLC10D", "1.0")
    assert s.serial == "DG2510150198"
    assert s.date_code == "25-10-15"
    assert s.sfp_type == "1310nm single-mode fiber"
    assert s.temperature_c == 45
    assert s.voltage_v == 3.237
    assert s.bias_current_ma == 40
    assert s.rx_power_dbm == -2.1   # web UI -2.062 dBm
    assert s.tx_power_dbm == -2.3   # web UI -2.305 dBm


def test_stats_page():
    link = _parse("link.b", LINK)
    stats = _client()._parse_port_stats(_parse("stats.b", STATS), link["nm"], link["lnk"], 3)
    p2, sfp = stats[1], stats[2]
    assert p2.rx_bytes == 167791240
    assert p2.tx_bytes == 6125073391
    assert p2.rx_packets == 1038892
    assert p2.tx_packets == 6806570
    assert (p2.rx_broadcast, p2.tx_broadcast) == (4748, 343519)
    assert (p2.rx_multicast, p2.tx_multicast) == (10284, 114174)
    # the screenshot was taken a little before the dump: same order of magnitude, counters grew
    assert 6150643940 <= sfp.rx_bytes < 6160000000
    assert 180844844 <= sfp.tx_bytes < 181000000


def test_named_keys_pass_through():
    data = {"upt": 1, "brd": "CSS326"}
    assert not m.is_numbered(data)
    assert m.normalize_lite("sys.b", data) is data


if __name__ == "__main__":
    test_system_page()
    test_link_page_and_layout()
    test_sfp_page()
    test_stats_page()
    test_named_keys_pass_through()
    print("all SwOS Lite tests passed")
