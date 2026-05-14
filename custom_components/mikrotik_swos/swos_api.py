"""SwOS API client for MikroTik CSS/CRS switches.

Handles HTTP Digest authentication, .swb format parsing, and
live data endpoint fetching (system info, SFP diagnostics).
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
    return bytes.fromhex(h).decode("ascii", errors="replace") if h else ""


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
    bias_current_ma: int = 0
    tx_power_mw: float = 0.0
    tx_power_dbm: float | None = None
    rx_power_mw: float = 0.0
    rx_power_dbm: float | None = None


@dataclass
class SystemInfo:
    hostname: str = ""
    mac: str = ""
    firmware: str = ""
    model: str = ""
    ip: str = ""


@dataclass
class SwitchData:
    system: SystemInfo = field(default_factory=SystemInfo)
    sfp_slots: list[SfpSlot] = field(default_factory=list)


# ── Conversion helpers ────────────────────────────────────────────────────────


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


# ── IP decode ─────────────────────────────────────────────────────────────────


def _ip_from_le(val: int) -> str:
    b = val.to_bytes(4, "little")
    return f"{b[0]}.{b[1]}.{b[2]}.{b[3]}"


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

    def __init__(self, host: str, username: str, password: str, port: int = 80, verify_ssl: bool = False) -> None:
        scheme = "https" if port == 443 else "http"
        self._base_url = f"{scheme}://{host}:{port}"
        self._auth = httpx.DigestAuth(username, password)
        self._verify_ssl = verify_ssl

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(auth=self._auth, verify=self._verify_ssl, timeout=15.0)

    async def test_connection(self) -> SystemInfo:
        try:
            backup = await self._download_backup()
            return self._parse_system_info(backup)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise SwosAuthError("Authentication failed") from exc
            raise SwosApiError(f"HTTP {exc.response.status_code}") from exc
        except httpx.ConnectError as exc:
            raise SwosConnectionError(f"Cannot connect to {self._base_url}") from exc

    async def fetch_data(self) -> SwitchData:
        data = SwitchData()
        backup = await self._download_backup()
        data.system = self._parse_system_info(backup)
        sfp_raw = await self._fetch_sfp()
        data.sfp_slots = self._parse_sfp(sfp_raw)
        return data

    async def _download_backup(self) -> dict:
        async with self._client() as client:
            last_err: Exception = SwosApiError("No backup URL found")
            for path in _BACKUP_PATHS:
                try:
                    resp = await client.get(f"{self._base_url}{path}")
                    resp.raise_for_status()
                    text = resp.text.strip()
                    if "sys.b" in text and ("vlan.b" in text or "link.b" in text):
                        return _parse_swb(text)
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code in (301, 302, 303, 307, 308, 404):
                        last_err = exc
                        continue
                    raise
            raise last_err

    async def _fetch_sfp(self) -> dict:
        async with self._client() as client:
            try:
                resp = await client.get(f"{self._base_url}/sfp.b")
                resp.raise_for_status()
                raw = resp.text.strip()
                return _parse_swb(f"sfp.b:{raw}").get("sfp.b", {})
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    _LOGGER.debug("SFP endpoint not available on this firmware")
                    return {}
                raise

    def _parse_system_info(self, backup: dict) -> SystemInfo:
        sys_data = backup.get("sys.b", {})
        link_data = backup.get("link.b", {})
        hostname = sys_data.get("id", "SwOS")
        if isinstance(hostname, str) and all(c in "0123456789abcdef" for c in hostname.lower()):
            hostname = _hs_decode(hostname)
        ip_raw = sys_data.get("ip", 0)
        ip = _ip_from_le(ip_raw) if ip_raw else ""
        return SystemInfo(hostname=hostname.strip(), ip=ip)

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

            tx_mw = round((tpw[i] if i < len(tpw) else 0) / 10000.0, 3)
            rx_mw = round((rpw[i] if i < len(rpw) else 0) / 10000.0, 3)

            slots.append(SfpSlot(
                port=port_num,
                present=True,
                vendor=vendor,
                part_number=str(pnr[i]).strip() if i < len(pnr) else "",
                serial=str(ser[i]).strip() if i < len(ser) else "",
                revision=str(rev[i]).strip() if i < len(rev) else "",
                date_code=str(dat[i]).strip() if i < len(dat) else "",
                sfp_type=str(typ[i]).strip() if i < len(typ) else "",
                wavelength_nm=wln[i] if i < len(wln) else 0,
                temperature_c=_sfp_temp(tmp[i] if i < len(tmp) else 0),
                voltage_v=_sfp_voltage_v(vcc[i] if i < len(vcc) else 0),
                bias_current_ma=tbs[i] if i < len(tbs) else 0,
                tx_power_mw=tx_mw,
                tx_power_dbm=_power_dbm(tx_mw),
                rx_power_mw=rx_mw,
                rx_power_dbm=_power_dbm(rx_mw),
            ))
        return slots
