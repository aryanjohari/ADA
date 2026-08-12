"""Typed host vitals snapshot — metal probes only, no LLM.

Stable core schema (version 1) + open `extras` for Pi quirks.
Never invent disk free or throttle bits; probe failures go in probe_errors.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from ada import __version__
from ada.io.paths import DEFAULT_ADA_DATA_ROOT, get_data_root

# Urgent disk thresholds (M00 §6.3 helpers)
ROOT_LOW_BYTES = 1 * 1024**3  # 1 GiB
ADA_DATA_LOW_BYTES = 5 * 1024**3  # 5 GiB

# Raspberry Pi throttled flag bits (vcgencmd get_throttled)
_THROTTLE_BITS = {
    "under_voltage_now": 0,
    "freq_capped_now": 1,
    "throttled_now": 2,
    "soft_temp_limit_now": 3,
    "under_voltage_sticky": 16,
    "freq_capped_sticky": 17,
    "throttled_sticky": 18,
    "soft_temp_limit_sticky": 19,
}


class ProbeError(BaseModel):
    probe: str
    message: str


class HostInfo(BaseModel):
    hostname: str
    boot_id: str | None = None


class TimeInfo(BaseModel):
    timezone: str
    utc_offset: str
    ntp_synchronized: bool | None = None


class LoadInfo(BaseModel):
    load1: float
    load5: float
    load15: float


class MemoryInfo(BaseModel):
    mem_total_bytes: int
    mem_available_bytes: int
    swap_total_bytes: int
    swap_used_bytes: int


class ThrottledBits(BaseModel):
    under_voltage_now: bool = False
    freq_capped_now: bool = False
    throttled_now: bool = False
    soft_temp_limit_now: bool = False
    under_voltage_sticky: bool = False
    freq_capped_sticky: bool = False
    throttled_sticky: bool = False
    soft_temp_limit_sticky: bool = False


class ThermalInfo(BaseModel):
    temp_c: float | None = None
    temp_source: str | None = None
    throttled_hex: str | None = None
    throttled_bits: ThrottledBits | None = None
    under_voltage_now: bool = False


class DiskInfo(BaseModel):
    mount: str
    label: str
    fstype: str | None = None
    total_bytes: int
    used_bytes: int
    avail_bytes: int
    used_pct: float


class MountsInfo(BaseModel):
    ada_data_ok: bool
    ada_data_source: str | None = None


class NetIface(BaseModel):
    name: str
    operstate: str
    ipv4: list[str] = Field(default_factory=list)


class NetInfo(BaseModel):
    ifaces: list[NetIface] = Field(default_factory=list)


class VitalsSnapshot(BaseModel):
    """Versioned vitals document; unknown extras keys are allowed."""

    model_config = ConfigDict(extra="ignore")

    schema_version: int = 1
    ts: str
    host: HostInfo
    time: TimeInfo
    load: LoadInfo
    memory: MemoryInfo
    thermal: ThermalInfo
    disks: list[DiskInfo]
    mounts: MountsInfo
    net: NetInfo
    probe_errors: list[ProbeError] = Field(default_factory=list)
    extras: dict[str, Any] = Field(default_factory=dict)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_throttled_hex(hex_str: str) -> ThrottledBits:
    """Decode vcgencmd get_throttled hex into convenience flags."""
    cleaned = hex_str.strip().lower()
    if cleaned.startswith("throttled="):
        cleaned = cleaned.split("=", 1)[1]
    value = int(cleaned, 16)
    flags = {name: bool(value & (1 << bit)) for name, bit in _THROTTLE_BITS.items()}
    return ThrottledBits(**flags)


def parse_meminfo(text: str) -> dict[str, int]:
    """Parse /proc/meminfo into kB values keyed by field name."""
    out: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        parts = rest.split()
        if not parts:
            continue
        try:
            out[key] = int(parts[0])
        except ValueError:
            continue
    return out


def memory_from_meminfo(parsed: dict[str, int]) -> MemoryInfo:
    """Prefer MemAvailable over MemFree — MemFree is not usable memory."""
    total_kb = parsed.get("MemTotal", 0)
    # Fall back only if Available truly missing (ancient kernels).
    avail_kb = parsed.get("MemAvailable", parsed.get("MemFree", 0))
    swap_total_kb = parsed.get("SwapTotal", 0)
    swap_free_kb = parsed.get("SwapFree", 0)
    return MemoryInfo(
        mem_total_bytes=total_kb * 1024,
        mem_available_bytes=avail_kb * 1024,
        swap_total_bytes=swap_total_kb * 1024,
        swap_used_bytes=max(0, (swap_total_kb - swap_free_kb) * 1024),
    )


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _run(cmd: list[str], timeout: float = 2.0) -> str:
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"exit {result.returncode}")
    return result.stdout.strip()


def _probe_boot_id(errors: list[ProbeError]) -> str | None:
    try:
        return _read_text(Path("/proc/sys/kernel/random/boot_id"))
    except OSError as exc:
        errors.append(ProbeError(probe="boot_id", message=str(exc)))
        return None


def _probe_load(errors: list[ProbeError]) -> LoadInfo:
    try:
        parts = _read_text(Path("/proc/loadavg")).split()
        return LoadInfo(load1=float(parts[0]), load5=float(parts[1]), load15=float(parts[2]))
    except (OSError, IndexError, ValueError) as exc:
        errors.append(ProbeError(probe="loadavg", message=str(exc)))
        return LoadInfo(load1=0.0, load5=0.0, load15=0.0)


def _probe_memory(errors: list[ProbeError]) -> MemoryInfo:
    try:
        parsed = parse_meminfo(Path("/proc/meminfo").read_text(encoding="utf-8"))
        return memory_from_meminfo(parsed)
    except OSError as exc:
        errors.append(ProbeError(probe="meminfo", message=str(exc)))
        return MemoryInfo(
            mem_total_bytes=0,
            mem_available_bytes=0,
            swap_total_bytes=0,
            swap_used_bytes=0,
        )


def _probe_time(errors: list[ProbeError]) -> TimeInfo:
    tz_name = "UTC"
    try:
        link = Path("/etc/localtime").resolve()
        # e.g. /usr/share/zoneinfo/Pacific/Auckland
        parts = link.parts
        if "zoneinfo" in parts:
            idx = parts.index("zoneinfo")
            tz_name = "/".join(parts[idx + 1 :])
        elif Path("/etc/timezone").is_file():
            tz_name = _read_text(Path("/etc/timezone"))
    except OSError as exc:
        errors.append(ProbeError(probe="timezone", message=str(exc)))

    try:
        zi = ZoneInfo(tz_name)
    except Exception:
        zi = ZoneInfo("UTC")
        tz_name = "UTC"

    now = datetime.now(zi)
    offset = now.strftime("%z")
    utc_offset = f"{offset[:3]}:{offset[3:]}" if offset else "+00:00"

    ntp: bool | None = None
    try:
        out = _run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"])
        ntp = out.strip().lower() in {"yes", "true", "1"}
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        errors.append(ProbeError(probe="timedatectl", message=str(exc)))

    return TimeInfo(timezone=tz_name, utc_offset=utc_offset, ntp_synchronized=ntp)


def _probe_thermal(errors: list[ProbeError]) -> ThermalInfo:
    temp_c: float | None = None
    temp_source: str | None = None
    throttled_hex: str | None = None
    bits: ThrottledBits | None = None

    try:
        out = _run(["vcgencmd", "measure_temp"])
        # temp=47.7'C
        m = re.search(r"temp=([0-9.]+)", out)
        if m:
            temp_c = float(m.group(1))
            temp_source = "vcgencmd"
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
        errors.append(ProbeError(probe="vcgencmd_temp", message=str(exc)))

    if temp_c is None:
        try:
            millideg = int(_read_text(Path("/sys/class/thermal/thermal_zone0/temp")))
            temp_c = millideg / 1000.0
            temp_source = "thermal_zone0"
        except (OSError, ValueError) as exc:
            errors.append(ProbeError(probe="thermal_zone0", message=str(exc)))

    try:
        out = _run(["vcgencmd", "get_throttled"])
        m = re.search(r"(0x[0-9a-fA-F]+)", out)
        if m:
            throttled_hex = m.group(1).lower()
            bits = parse_throttled_hex(throttled_hex)
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
        errors.append(ProbeError(probe="vcgencmd_throttled", message=str(exc)))

    under = bool(bits.under_voltage_now) if bits else False
    return ThermalInfo(
        temp_c=temp_c,
        temp_source=temp_source,
        throttled_hex=throttled_hex,
        throttled_bits=bits,
        under_voltage_now=under,
    )


def _fstype_for(mount: str) -> str | None:
    try:
        for line in Path("/proc/mounts").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[1] == mount:
                return parts[2]
    except OSError:
        pass
    return None


def _disk_for(mount: str, label: str, errors: list[ProbeError]) -> DiskInfo | None:
    try:
        st = os.statvfs(mount)
    except OSError as exc:
        errors.append(ProbeError(probe=f"statvfs:{mount}", message=str(exc)))
        return None
    total = st.f_frsize * st.f_blocks
    avail = st.f_frsize * st.f_bavail
    used = total - (st.f_frsize * st.f_bfree)
    used_pct = (used / total * 100.0) if total else 0.0
    return DiskInfo(
        mount=mount,
        label=label,
        fstype=_fstype_for(mount),
        total_bytes=total,
        used_bytes=used,
        avail_bytes=avail,
        used_pct=round(used_pct, 2),
    )


def _probe_mounts(ada_root: Path, errors: list[ProbeError]) -> tuple[MountsInfo, list[DiskInfo]]:
    disks: list[DiskInfo] = []
    root_disk = _disk_for("/", "rootfs", errors)
    if root_disk:
        disks.append(root_disk)

    ada_ok = False
    source: str | None = None
    mount_str = str(ada_root)
    try:
        for line in Path("/proc/mounts").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == mount_str:
                ada_ok = True
                source = parts[0]
                break
    except OSError as exc:
        errors.append(ProbeError(probe="proc_mounts", message=str(exc)))

    # Sandbox override: directory exists counts as ok for vitals mounts field
    # when ADA_DATA_ROOT is set and root is not the production path.
    if not ada_ok and ada_root.is_dir() and os.environ.get("ADA_DATA_ROOT"):
        if ada_root.resolve() != Path(DEFAULT_ADA_DATA_ROOT).resolve():
            ada_ok = True
            source = "ADA_DATA_ROOT"

    if ada_root.is_dir():
        ada_disk = _disk_for(mount_str, "ada-data", errors)
        if ada_disk:
            disks.append(ada_disk)

    return MountsInfo(ada_data_ok=ada_ok, ada_data_source=source), disks


def _ipv4_for_iface(name: str) -> list[str]:
    try:
        out = _run(["ip", "-br", "addr", "show", "dev", name])
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        return []
    # Example: wlan0 UP 192.168.7.134/22 fe80::1/64
    addrs: list[str] = []
    parts = out.split()
    for token in parts[2:]:
        if ":" in token and "." not in token.split("/")[0]:
            continue  # skip IPv6 for v0 summary
        if "." in token:
            addrs.append(token)
    return addrs


def _probe_net(errors: list[ProbeError]) -> NetInfo:
    ifaces: list[NetIface] = []
    sys_net = Path("/sys/class/net")
    try:
        names = sorted(p.name for p in sys_net.iterdir() if p.name != "lo")
    except OSError as exc:
        errors.append(ProbeError(probe="sys_net", message=str(exc)))
        return NetInfo(ifaces=[])

    for name in names:
        try:
            oper = _read_text(sys_net / name / "operstate").upper()
        except OSError:
            oper = "UNKNOWN"
        ifaces.append(NetIface(name=name, operstate=oper, ipv4=_ipv4_for_iface(name)))
    return NetInfo(ifaces=ifaces)


def _probe_extras(errors: list[ProbeError]) -> dict[str, Any]:
    extras: dict[str, Any] = {"agent_version": __version__}

    try:
        out = _run(["vcgencmd", "measure_clock", "arm"])
        m = re.search(r"frequency\(0\)=(\d+)", out) or re.search(r"=(\d+)", out)
        if m:
            extras["arm_clock_hz"] = int(m.group(1))
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
        errors.append(ProbeError(probe="arm_clock", message=str(exc)))

    for key in ("arm", "gpu"):
        try:
            out = _run(["vcgencmd", "get_mem", key])
            m = re.search(r"(\d+)M", out)
            if m:
                extras[f"firmware_mem_{key}_m"] = int(m.group(1))
        except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
            errors.append(ProbeError(probe=f"firmware_mem_{key}", message=str(exc)))

    try:
        swaps = Path("/proc/swaps").read_text(encoding="utf-8")
        extras["zram_swap"] = "zram" in swaps
    except OSError as exc:
        errors.append(ProbeError(probe="swaps", message=str(exc)))

    try:
        mid = _read_text(Path("/etc/machine-id"))
        extras["machine_id"] = mid[:12] + "…" if len(mid) > 12 else mid
    except OSError:
        pass

    try:
        ip4 = _run(["tailscale", "ip", "-4"])
        if ip4:
            extras["tailscale_ipv4"] = ip4.splitlines()[0].strip()
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        pass

    return extras


def collect_vitals(*, ada_root: Path | None = None) -> VitalsSnapshot:
    """Collect a typed vitals snapshot from this host."""
    errors: list[ProbeError] = []
    root = ada_root if ada_root is not None else get_data_root()

    hostname = socket.gethostname()
    boot_id = _probe_boot_id(errors)
    mounts, disks = _probe_mounts(root, errors)

    return VitalsSnapshot(
        ts=utc_now_iso(),
        host=HostInfo(hostname=hostname, boot_id=boot_id),
        time=_probe_time(errors),
        load=_probe_load(errors),
        memory=_probe_memory(errors),
        thermal=_probe_thermal(errors),
        disks=disks,
        mounts=mounts,
        net=_probe_net(errors),
        probe_errors=errors,
        extras=_probe_extras(errors),
    )


def urgent_faults(snap: VitalsSnapshot) -> list[str]:
    """Compute urgent body faults from a snapshot (for doctor/status)."""
    faults: list[str] = []
    if not snap.mounts.ada_data_ok:
        faults.append("ada_data_ok=false")
    for disk in snap.disks:
        if disk.label == "rootfs" and disk.avail_bytes < ROOT_LOW_BYTES:
            faults.append(f"root avail low ({disk.avail_bytes} bytes)")
        if disk.label == "ada-data" and disk.avail_bytes < ADA_DATA_LOW_BYTES:
            faults.append(f"ada-data avail low ({disk.avail_bytes} bytes)")
    bits = snap.thermal.throttled_bits
    if bits and (bits.under_voltage_now or bits.freq_capped_now or bits.throttled_now):
        faults.append(f"throttled_now ({snap.thermal.throttled_hex})")
    return faults
