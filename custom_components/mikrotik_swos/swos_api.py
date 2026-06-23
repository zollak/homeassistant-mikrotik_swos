"""SwOS API client for MikroTik CSS/CRS switches.

Handles HTTP Digest authentication, .swb format parsing, and
live data endpoint fetching (system info, SFP diagnostics, port stats, PoE).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

_LOGGER = logging.getLogger(__name__)

# ── SwOS .swb parser ──────────────────────────────────────────────────────────


class _Tok:
    def __init__(self, text: str):
        self.t = text
        self.pos = 0
        self._cur: tuple = ("EOF", None)
        self._advance()

    def _advance(self) -> None:
        t, pos = self.t, self.pos
        while pos < len(t) and t[pos].isspace():
            pos += 1
        if pos >= len(t):
            self.pos = pos
            self._cur = ("EOF", None)
            return
        c = t[pos]
        if c in "{}[]:,":
            self._cur = ("P", c)
            self.pos = pos + 1
            return
        if c == "'":
            j = pos + 1
            while j < len(t) and t[j] != "'":
                j += 1
            self._cur = ("HS", t[pos + 1 : j])
            self.pos = j + 1
            return
        if c == "0" and pos + 1 < len(t) and t[pos + 1] == "x":
            j = pos + 2
            while j < len(t) and t[j] in "0123456789abcdefABCDEF":
                j += 1
            self._cur = ("HN", int(t[pos + 2 : j], 16))
            self.pos = j
            return
        j = pos
        if t[j] == ".":
            j += 1
        while j < len(t) and (t[j].isalnum() or t[j] in "._"):
            j += 1
        self._cur = ("ID", t[pos:j])
        self.pos = j

    def peek(self) -> tuple:
        return self._cur

    def consume(self) -> tuple:
        tok = self._cur
        self._advance()
        return tok

    def expect(self, typ: str, val: Optional[str] = None) -> Any:
        tok = self.consume()
        if tok[0] != typ:
            raise ValueError(f"SwOS parse: expected {typ!r}, got {tok!r} at pos {self.pos}")
        if val is not None and tok[1] != val:
            raise ValueError(f"SwOS parse: expected {val!r}, got {tok[1]!r}")
        return tok[1]


def _hs_decode(h: str) -> str:
    if not h:
        return ""
    raw = bytes.fromhex(h)
    decoded = raw.decode("ascii", errors="replace")
    if "�" in decoded:
        return h
    return decoded


def _parse_value(tok: _Tok) -> Any:
    t, v = tok.peek()
    if t == "P" and v == "{":
        return _parse_obj(tok)
    if t == "P" and v == "[":
        return _parse_arr(tok)
    if t == "HS":
        tok.consume()
        return _hs_decode(v)
    if t == "HN":
        tok.consume()
        return v
    if t == "ID":
        tok.consume()
        return v
    raise ValueError(f"SwOS parse: unexpected {tok.peek()!r}")


def _parse_obj(tok: _Tok) -> dict:
    tok.expect("P", "{")
    result: dict = {}
    while tok.peek() != ("P", "}"):
        key = tok.expect("ID")
        tok.expect("P", ":")
        result[key] = _parse_value(tok)
        if tok.peek() == ("P", ","):
            tok.consume()
    tok.expect("P", "}")
    return result


def _parse_arr(tok: _Tok) -> list:
    tok.expect("P", "[")
    result: list = []
    while tok.peek() != ("P", "]"):
        result.append(_parse_value(tok))
        if tok.peek() == ("P", ","):
            tok.consume()
    tok.expect("P", "]")
    return result


def _parse_swb(text: str) -> dict:
    tok = _Tok(text.strip())
    result: dict = {}
    while tok.peek()[0] != "EOF":
        key = tok.expect("ID")
        tok.expect("P", ":")
        result[key] = _parse_value(tok)
        if tok.peek() == ("P", ","):
            tok.consume()
    return result


# ── PoE state mapping ────────────────────────────────────────────────────────

POE_STATES = {
    0: None,
    1: "disabled",
    2: "waiting_for_load",
    3: "powered_on",
    4: "overload",
    5: "short_circuit",
    6: "voltage_too_low",
    7: "current_too_low",
    8: "power_cycle",
    9: "voltage_too_high",
    10: "controller_error",
}

POE_STATE_OPTIONS = [v for v in POE_STATES.values() if v is not None]


# ── Data models ───────────────────────────────────────────────────────────────


@dataclass
class SfpSlot:
    port: int
    present: bool
    vendor: str = ""
    part_number: str = ""
    serial: str = ""
    revision: str = ""
    date_code: str = ""
    sfp_type: str = ""
    wavelength_nm: int = 0
    temperature_c: int | None = None
    voltage_v: float | None = None
    bias_current_ma: int | None = None
    tx_power_mw: float = 0.0
    tx_power_dbm: float | None = None
    rx_power_mw: float = 0.0
    rx_power_dbm: float | None = None


@dataclass
class SystemInfo:
    hostname: str = ""
    model: str = ""
    serial_number: str = ""
    firmware: str = ""
    mac: str = ""
    ip: str = ""
    uptime_seconds: int = 0
    board_temp_c: int | None = None
    psu1_voltage_v: float = 0.0
    psu1_current_ma: int = 0
    psu1_power_w: float = 0.0
    psu2_voltage_v: float = 0.0
    psu2_current_ma: int = 0
    psu2_power_w: float = 0.0
    power_consumption_w: float = 0.0


@dataclass
class PortStats:
    port: int
    name: str = ""
    link_up: bool = False
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    tx_packets: int = 0
    rx_broadcast: int = 0
    tx_broadcast: int = 0
    rx_multicast: int = 0
    tx_multicast: int = 0
    rx_pause: int = 0
    tx_pause: int = 0


@dataclass
class PortErrors:
    port: int
    rx_fcs: int = 0
    rx_align: int = 0
    rx_runts: int = 0
    rx_oversized: int = 0
    rx_fragments: int = 0
    tx_total_errors: int = 0
    tx_collisions: int = 0
    tx_late_collisions: int = 0


@dataclass
class PoePort:
    port: int
    state: str | None = None
    current_ma: int = 0
    voltage_v: float = 0.0
    power_w: float = 0.0


@dataclass
class SwitchData:
    system: SystemInfo = field(default_factory=SystemInfo)
    sfp_slots: list[SfpSlot] = field(default_factory=list)
    port_stats: list[PortStats] = field(default_factory=list)
    port_errors: list[PortErrors] = field(default_factory=list)
    poe_available: bool = False
    poe_ports: list[PoePort] = field(default_factory=list)
    port_names: list[str] = field(default_factory=list)
    port_enabled: list[bool] = field(default_factory=list)


# ── Conversion helpers ────────────────────────────────────────────────────────


def _hs_encode(s: str) -> str:
    """Encode a Python str to SwOS hex-encoded ASCII."""
    return s.encode("ascii", errors="replace").hex()


def _link_mask_hex(n: int) -> str:
    """SwOS mask format: 0x + hex, zero-padded to an even number of digits."""
    h = "%x" % n
    return "0x" + ("0" + h if len(h) % 2 else h)


def serialize_link(link: dict) -> str:
    """Serialize the link object exactly as the SwOS web UI POSTs it to /link.b.

    Only these 8 fields, in this order: en, nm, an, spdc, dpxc, fctc, fctr, sfpr.
    Verified byte-for-byte against the live SwOS 2.18 UI payload.
    """
    nm = "[" + ",".join("'%s'" % _hs_encode(s) for s in link.get("nm", [])) + "]"
    spdc = "[" + ",".join("0x%02x" % x for x in link.get("spdc", [])) + "]"
    sfpr = "[" + ",".join("0x%02x" % x for x in link.get("sfpr", [])) + "]"
    return (
        "{en:%s,nm:%s,an:%s,spdc:%s,dpxc:%s,fctc:%s,fctr:%s,sfpr:%s}"
        % (
            _link_mask_hex(link["en"]),
            nm,
            _link_mask_hex(link["an"]),
            spdc,
            _link_mask_hex(link["dpxc"]),
            _link_mask_hex(link["fctc"]),
            _link_mask_hex(link["fctr"]),
            sfpr,
        )
    )


def _sfp_temp(raw: int) -> int:
    if raw > 0x7FFFFFFF:
        raw -= 0x100000000
    return raw


def _sfp_voltage_v(raw: int) -> float:
    return round(raw / 1000.0, 3)


def _power_dbm(mw: float) -> float | None:
    if mw <= 0:
        return None
    return round(10 * math.log10(mw), 1)


def _ip_from_le(val: int) -> str:
    b = val.to_bytes(4, "little")
    return f"{b[0]}.{b[1]}.{b[2]}.{b[3]}"


def _mac_format(raw: str) -> str:
    clean = "".join(c for c in raw if c in "0123456789abcdefABCDEF")
    if len(clean) == 12:
        return ":".join(clean[i : i + 2] for i in range(0, 12, 2))
    try:
        hexed = raw.encode("latin-1").hex()
        if len(hexed) == 12:
            return ":".join(hexed[i : i + 2] for i in range(0, 12, 2))
    except (UnicodeEncodeError, ValueError):
        pass
    return raw


def _combine_u64(low: int, high: int) -> int:
    return (high << 32) | (low & 0xFFFFFFFF)


def _safe_get(arr: list, idx: int, default: int = 0) -> int:
    return arr[idx] if idx < len(arr) else default


def _signed16(val: int) -> int:
    if val >= 0x8000:
        val -= 0x10000
    return val


# ── API client ────────────────────────────────────────────────────────────────

_BACKUP_PATHS = ["/!res/back.swb", "/backup.swb", "/back.swb"]


class SwosApiError(Exception):
    pass


class SwosAuthError(SwosApiError):
    pass


class SwosConnectionError(SwosApiError):
    pass


class SwosApi:
    """Client for a MikroTik SwOS switch."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 80,
        verify_ssl: bool = False,
        enable_stats: bool = False,
        enable_errors: bool = False,
    ) -> None:
        scheme = "https" if port == 443 else "http"
        self._base_url = f"{scheme}://{host}:{port}"
        self._auth = httpx.DigestAuth(username, password)
        self._verify_ssl = verify_ssl
        self.enable_stats = enable_stats
        self.enable_errors = enable_errors

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(auth=self._auth, verify=self._verify_ssl, timeout=15.0)

    async def test_connection(self) -> SystemInfo:
        try:
            sys_data = await self._fetch_endpoint("/sys.b")
            return self._parse_system_info(sys_data)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise SwosAuthError("Authentication failed") from exc
            raise SwosApiError(f"HTTP {exc.response.status_code}") from exc
        except httpx.ConnectError as exc:
            raise SwosConnectionError(f"Cannot connect to {self._base_url}") from exc

    async def fetch_data(self) -> SwitchData:
        try:
            return await self._fetch_data_inner()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise SwosAuthError("Authentication failed") from exc
            raise SwosApiError(f"HTTP {exc.response.status_code}") from exc

    async def _fetch_data_inner(self) -> SwitchData:
        data = SwitchData()

        sys_data = await self._fetch_endpoint("/sys.b")
        data.system = self._parse_system_info(sys_data)

        link_data = await self._fetch_endpoint("/link.b")
        port_names = link_data.get("nm", [""] * 26)
        link_mask = link_data.get("lnk", 0)
        en_mask = link_data.get("en", 0)
        data.port_names = [str(n) for n in port_names]
        data.port_enabled = [bool(en_mask & (1 << i)) for i in range(26)]

        sfp_raw = await self._fetch_sfp()
        data.sfp_slots = self._parse_sfp(sfp_raw)

        if self.enable_stats or self.enable_errors:
            stats_data = await self._fetch_endpoint("/stats.b")
            if self.enable_stats:
                data.port_stats = self._parse_port_stats(stats_data, port_names, link_mask)
            if self.enable_errors:
                data.port_errors = self._parse_port_errors(stats_data)

        poe_raw = await self._fetch_poe()
        if poe_raw:
            data.poe_available = True
            data.poe_ports = self._parse_poe(poe_raw, port_names)

        return data

    async def _fetch_endpoint(self, path: str) -> dict:
        async with self._client() as client:
            resp = await client.get(f"{self._base_url}{path}")
            resp.raise_for_status()
            raw = resp.text.strip()
            section = path.lstrip("/!").rstrip("/")
            return _parse_swb(f"{section}:{raw}").get(section, {})

    async def async_set_port_enabled(self, port: int, enabled: bool) -> None:
        """Enable or disable a port by POSTing the modified link object to /link.b.

        Mirrors the SwOS web UI's "Apply All" on the Link tab (POST /link.b,
        Content-Type text/plain). Reads the current link config, flips only the
        port's bit in the `en` mask, and writes the full link object back so all
        other link settings are preserved.
        """
        link = await self._fetch_endpoint("/link.b")
        bit = 1 << (port - 1)
        en = link.get("en", 0)
        link["en"] = (en | bit) if enabled else (en & ~bit)
        body = serialize_link(link).encode("ascii")
        async with self._client() as client:
            resp = await client.post(
                f"{self._base_url}/link.b",
                content=body,
                headers={"Content-Type": "text/plain"},
            )
            resp.raise_for_status()

    async def _fetch_sfp(self) -> dict:
        try:
            return await self._fetch_endpoint("/sfp.b")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (303, 404):
                _LOGGER.debug("SFP endpoint not available")
                return {}
            raise

    async def _fetch_poe(self) -> dict:
        try:
            return await self._fetch_endpoint("/poe.b")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (303, 404):
                _LOGGER.debug("PoE endpoint not available (non-PoE switch)")
                return {}
            raise
        except Exception:
            _LOGGER.debug("PoE endpoint fetch failed", exc_info=True)
            return {}

    def _parse_system_info(self, sys_data: dict) -> SystemInfo:
        hostname = str(sys_data.get("id", "SwOS")).strip()
        model = str(sys_data.get("brd", "")).strip()
        serial = str(sys_data.get("sid", "")).strip()
        firmware = str(sys_data.get("ver", "")).strip()
        mac_raw = str(sys_data.get("mac", "")).strip()
        ip_raw = sys_data.get("ip", 0)
        ip = _ip_from_le(ip_raw) if isinstance(ip_raw, int) and ip_raw else ""
        upt = sys_data.get("upt", 0)
        uptime_sec = upt // 100 if isinstance(upt, int) else 0
        temp = sys_data.get("temp", None)
        board_temp = _signed16(temp) if isinstance(temp, int) and temp > 0 else None

        p1v = sys_data.get("p1v", 0)
        p1c = sys_data.get("p1c", 0)
        p1p = sys_data.get("p1p", 0)
        p2v = sys_data.get("p2v", 0)
        p2c = sys_data.get("p2c", 0)
        p2p = sys_data.get("p2p", 0)
        pcon = sys_data.get("i26", 0)

        return SystemInfo(
            hostname=hostname,
            model=model,
            serial_number=serial,
            firmware=firmware,
            mac=_mac_format(mac_raw),
            ip=ip,
            uptime_seconds=uptime_sec,
            board_temp_c=board_temp,
            psu1_voltage_v=round(p1v / 100, 2) if isinstance(p1v, int) and p1v else 0.0,
            psu1_current_ma=p1c if isinstance(p1c, int) else 0,
            psu1_power_w=round(p1p / 10, 1) if isinstance(p1p, int) and p1p else 0.0,
            psu2_voltage_v=round(p2v / 100, 2) if isinstance(p2v, int) and p2v else 0.0,
            psu2_current_ma=p2c if isinstance(p2c, int) else 0,
            psu2_power_w=round(p2p / 10, 1) if isinstance(p2p, int) and p2p else 0.0,
            power_consumption_w=round(pcon / 10, 1) if isinstance(pcon, int) and pcon else 0.0,
        )

    def _parse_sfp(self, sfp: dict) -> list[SfpSlot]:
        if not sfp:
            return []
        num = 2
        vnd = sfp.get("vnd", [""] * num)
        pnr = sfp.get("pnr", [""] * num)
        ser = sfp.get("ser", [""] * num)
        rev = sfp.get("rev", [""] * num)
        dat = sfp.get("dat", [""] * num)
        typ = sfp.get("typ", [""] * num)
        wln = sfp.get("wln", [0] * num)
        tmp = sfp.get("tmp", [0] * num)
        vcc = sfp.get("vcc", [0] * num)
        tbs = sfp.get("tbs", [0] * num)
        tpw = sfp.get("tpw", [0] * num)
        rpw = sfp.get("rpw", [0] * num)

        slots = []
        for i in range(num):
            vendor = str(vnd[i]).strip() if i < len(vnd) and vnd[i] else ""
            present = bool(vendor)
            port_num = 25 + i

            if not present:
                slots.append(SfpSlot(port=port_num, present=False))
                continue

            # Modules without DDM (e.g. passive DAC cables) report 0xffffff80 (-128)
            # for temperature. Treat that as "no diagnostics" and null all DDM fields
            # rather than surfacing the -128 sentinel and bogus 0 readings.
            temp_raw = _safe_get(tmp, i)
            has_ddm = temp_raw != 0xFFFFFF80
            tx_mw = round(_safe_get(tpw, i) / 10000.0, 3) if has_ddm else 0.0
            rx_mw = round(_safe_get(rpw, i) / 10000.0, 3) if has_ddm else 0.0

            slots.append(SfpSlot(
                port=port_num,
                present=True,
                vendor=vendor,
                part_number=str(pnr[i]).strip() if i < len(pnr) else "",
                serial=str(ser[i]).strip() if i < len(ser) else "",
                revision=str(rev[i]).strip() if i < len(rev) else "",
                date_code=str(dat[i]).strip() if i < len(dat) else "",
                sfp_type=str(typ[i]).strip() if i < len(typ) else "",
                wavelength_nm=_safe_get(wln, i),
                temperature_c=_sfp_temp(temp_raw) if has_ddm else None,
                voltage_v=_sfp_voltage_v(_safe_get(vcc, i)) if has_ddm else None,
                bias_current_ma=_safe_get(tbs, i) if has_ddm else None,
                tx_power_mw=tx_mw,
                tx_power_dbm=_power_dbm(tx_mw),
                rx_power_mw=rx_mw,
                rx_power_dbm=_power_dbm(rx_mw),
            ))
        return slots

    def _parse_port_stats(self, stats: dict, port_names: list, link_mask: int) -> list[PortStats]:
        rb = stats.get("rb", [])
        rbh = stats.get("rbh", [])
        tb = stats.get("tb", [])
        tbh = stats.get("tbh", [])
        rtp = stats.get("rtp", [])
        ttp = stats.get("ttp", [])
        rbp = stats.get("rbp", [])
        tbp = stats.get("tbp", [])
        rmp = stats.get("rmp", [])
        tmp = stats.get("tmp", [])
        rpp = stats.get("rpp", [])
        tpp = stats.get("tpp", [])

        result = []
        for i in range(26):
            name = str(port_names[i]).strip() if i < len(port_names) and port_names[i] else f"Port {i+1}"
            result.append(PortStats(
                port=i + 1,
                name=name,
                link_up=bool(link_mask & (1 << i)),
                rx_bytes=_combine_u64(_safe_get(rb, i), _safe_get(rbh, i)),
                tx_bytes=_combine_u64(_safe_get(tb, i), _safe_get(tbh, i)),
                rx_packets=_safe_get(rtp, i),
                tx_packets=_safe_get(ttp, i),
                rx_broadcast=_safe_get(rbp, i),
                tx_broadcast=_safe_get(tbp, i),
                rx_multicast=_safe_get(rmp, i),
                tx_multicast=_safe_get(tmp, i),
                rx_pause=_safe_get(rpp, i),
                tx_pause=_safe_get(tpp, i),
            ))
        return result

    def _parse_port_errors(self, stats: dict) -> list[PortErrors]:
        rfcs = stats.get("rfcs", [])
        rae = stats.get("rae", [])
        rr = stats.get("rr", [])
        rov = stats.get("rov", [])
        fr = stats.get("fr", [])
        tec = stats.get("tec", [])
        tcl = stats.get("tcl", [])
        tlc = stats.get("tlc", [])

        result = []
        for i in range(26):
            result.append(PortErrors(
                port=i + 1,
                rx_fcs=_safe_get(rfcs, i),
                rx_align=_safe_get(rae, i),
                rx_runts=_safe_get(rr, i),
                rx_oversized=_safe_get(rov, i),
                rx_fragments=_safe_get(fr, i),
                tx_total_errors=_safe_get(tec, i),
                tx_collisions=_safe_get(tcl, i),
                tx_late_collisions=_safe_get(tlc, i),
            ))
        return result

    def _parse_poe(self, poe: dict, port_names: list) -> list[PoePort]:
        pwr = poe.get("pwr", [])
        curr = poe.get("curr", [])
        volt = poe.get("volt", [])
        poes = poe.get("poes", [])

        num_ports = len(pwr)
        result = []
        for i in range(num_ports):
            state_idx = _safe_get(poes, i) if isinstance(poes, list) else 0
            result.append(PoePort(
                port=i + 1,
                state=POE_STATES.get(state_idx),
                current_ma=_safe_get(curr, i),
                voltage_v=round(_safe_get(volt, i) / 10, 1) if _safe_get(volt, i) else 0.0,
                power_w=round(_safe_get(pwr, i) / 10, 1) if _safe_get(pwr, i) else 0.0,
            ))
        return result
