"""Regression test for issue #9: an endpoint answering HTTP 200 with an empty body.

The CRS304-4XG (SwOS 2.19) has no SFP cage, and /sfp.b answers HTTP 200 with
zero bytes instead of a 303/404. The parser raised `unexpected ('EOF', None)`
and setup failed. The dumps are the reporter's (Zer0great, CRS304-4XG,
SwOS 2.19, issue #9; MAC and serial masked by the reporter).

Runnable with `python3 tests/test_crs304_empty_endpoint.py` or pytest.
"""
import asyncio
import os
import sys

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "mikrotik_swos"))
import swos_api as m

SYS = (
    "{upt:0x0feb5305,cip:0xc86f6f0a,mac:'000000000000',mrkt:'',brd:'4352533330342d345847',"
    "sid:'484e333042500000000000',id:'435253333034',ver:'322e3139',rev:'',wdt:0x01,dsc:0x01,pdsc:0x0f,"
    "bld:0x6a181d51,ivl:0x01,alla:0x00000000,allm:0x00,avln:0x0001,allp:0x0f,mgmt:0x01,temp:0x00000038,"
    "btm1:0x00000000,btm2:0x00000000,fan1:0x00000000,fan2:0x00000000,fan3:0x00000000,fan4:0x00000000,"
    "p1v:0x00000000,p2v:0x00000000,p1c:0x00000000,p2c:0x00000000,p1s:0x00,p2s:0x00,prio:0x1000,rpr:0x0000,"
    "cost:0x01,frmc:0x00,rmac:'000000000000',poe:0x00,poes:0x00,igmp:0x01,igmq:0x00,igfl:0x00,igve:0x01,"
    "ip:0xc86f6f0a,dtrp:0x01,ainf:0x01,iptp:0x00,upgr:0x00,npoe:0x00,p1f:0x00000000,p2f:0x00000000,"
    "p1p:0x00000000,p2p:0x00000000,p1t:0x00000000,p2t:0x00000000,phyt:0x0000003d,amac:'000000000000'}"
)
LINK = (
    "{comb:0x00,qsfp:0x00,en:0x1f,blkp:0x00,an:0x1f,dpxc:0x1f,fctc:0x00,fctr:0x00,lnk:0x0f,dpx:0x0f,"
    "tfct:0x00,rfct:0x00,paus:0x00,spd:[0x02,0x00,0x05,0x05,0x07],spdc:[0x01,0x01,0x01,0x01,0x02],"
    "cm:[0x00,0x00,0x00,0x00,0x00],qtyp:[0x00,0x00,0x00,0x00,0x00],prt:0x04,sfp:0x00,sfpo:0x00,"
    "nm:['506f7274312d55706c696e6b','506f7274322d48545043','506f7274332d4e4153','506f7274342d5043',"
    "'4d474d54'],hop:[0x00,0x00,0x00,0x00,0x00],hops:[0x00,0x00,0x00,0x00,0x00],"
    "len:[0x00,0x00,0x00,0x00,0x00],flt:[0x00,0x00,0x00,0x00,0x00],pair:[0xffff,0xffff,0xffff,0xffff,0x0000],"
    "sfpr:[0x00,0x00,0x00,0x00,0x00],qsfo:0x00,mgmo:0x04,mgmc:0x01}"
)
# Shortened to the counters the integration reads; the values are the reporter's.
STATS = (
    "{rb:[0xf6b04941,0x366fd1d2,0x4556cc6c,0x529145aa,0x00000000],"
    "rbh:[0x00000131,0x00000000,0x00000174,0x000001ed,0x00000000],"
    "tb:[0xee8b72b5,0x5d6790b8,0x85ee30d3,0x27848a8a,0x00000000],"
    "tbh:[0x00000051,0x00000006,0x000002fb,0x00000140,0x00000000],"
    "rtp:[0x5506fbb4,0x0097f482,0x6f6995da,0x62a2d8d3,0x00000000],"
    "ttp:[0x3dfa8d69,0x018f10fc,0xae04e294,0x3aa62310,0x00000000],"
    "rfcs:[0x00000000,0x00000000,0x00000013,0x00000000,0x00000000],"
    "fr:[0x00000000,0x00000000,0x00000002,0x00000000,0x00000000]}"
)

# What the reporter's switch answered: path -> (status, body).
ANSWERS = {
    "/sys.b": (200, SYS),
    "/link.b": (200, LINK),
    "/sfp.b": (200, ""),
    "/!stats.b": (303, ""),
    "/stats.b": (200, STATS),
    "/poe.b": (303, ""),
}


def _api():
    api = m.SwosApi("192.0.2.1", "admin", "x", enable_stats=True, enable_errors=True)

    def handler(request):
        status, body = ANSWERS[request.url.raw_path.decode()]
        return httpx.Response(status, text=body)

    api._client = lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return api


def test_empty_sfp_body_does_not_break_setup():
    data = asyncio.run(_api().fetch_data())
    assert data.system.model == "CRS304-4XG"
    assert data.system.firmware == "2.19"
    assert data.num_ports == 4
    assert data.num_sfp == 0
    assert data.sfp_slots == []
    assert data.poe_available is False


def test_stats_fall_back_to_stats_b():
    data = asyncio.run(_api().fetch_data())
    assert len(data.port_stats) == 4
    assert data.port_stats[0].rx_bytes == (0x131 << 32) + 0xF6B04941


def test_config_flow_port_layout():
    layout, names = asyncio.run(_api().fetch_port_layout())
    assert (layout.num_ports, layout.num_sfp) == (4, 0)
    assert names[:4] == ["Port1-Uplink", "Port2-HTPC", "Port3-NAS", "Port4-PC"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
