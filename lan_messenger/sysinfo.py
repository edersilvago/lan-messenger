"""Dados simples do computador para exibir no contato (Windows, sem dependências)."""
from __future__ import annotations

import ctypes
import platform
import subprocess


DDR_MAP = {
    "20": "DDR", "21": "DDR2", "24": "DDR3", "26": "DDR4", "34": "DDR5",
}


def _run(args: list[str], timeout: float = 5.0) -> str:
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                           startupinfo=si, creationflags=0x08000000)
        return (p.stdout or "").strip()
    except Exception:
        return ""


def cpu_name() -> str:
    out = _run(["wmic", "cpu", "get", "Name", "/value"])
    for line in out.splitlines():
        if line.lower().startswith("name="):
            return line.split("=", 1)[1].strip()
    return platform.processor() or platform.machine() or "-"


def ram_total_gb() -> str:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
    try:
        st = MEMORYSTATUSEX()
        st.dwLength = ctypes.sizeof(st)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
        return f"{round(st.ullTotalPhys / (1024 ** 3))} GB"
    except Exception:
        return "-"


def ram_type() -> str:
    out = _run(["wmic", "memorychip", "get", "SMBIOSMemoryType", "/value"])
    vals = []
    for line in out.splitlines():
        if line.lower().startswith("smbiosmemorytype="):
            v = line.split("=", 1)[1].strip()
            if v and DDR_MAP.get(v, v) not in vals:
                vals.append(DDR_MAP.get(v, v))
    return "/".join(vals) if vals else "-"


def disk_type() -> str:
    # Get-PhysicalDisk é o mais confiável para SSD/HDD no Windows moderno.
    ps = "Get-PhysicalDisk | Select-Object -ExpandProperty MediaType"
    out = _run(["powershell", "-NoProfile", "-Command", ps], timeout=8.0)
    vals = []
    for line in out.splitlines():
        v = line.strip().upper()
        if v in ("SSD", "HDD") and v not in vals:
            vals.append(v)
    if vals:
        return "/".join(vals)
    out = _run(["wmic", "diskdrive", "get", "MediaType", "/value"])
    up = out.upper()
    if "SSD" in up:
        return "SSD"
    if "HDD" in up or "FIXED" in up:
        return "HDD"
    return "-"


def os_version() -> str:
    """Ex: Windows 10 Pro 22H2 (Build 19045.7725)."""
    caption = ""
    build = ""
    version = ""
    out = _run(["wmic", "os", "get", "Caption,BuildNumber,Version", "/value"])
    for line in out.splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.lower() == "caption":
            caption = v.strip()
        elif k.lower() == "buildnumber":
            build = v.strip()
        elif k.lower() == "version":
            version = v.strip()
    if caption:
        suffix = []
        if version:
            suffix.append(f"Versão {version}")
        if build:
            suffix.append(f"Build {build}")
        return caption + (f" ({', '.join(suffix)})" if suffix else "")
    rel = platform.release()
    ver = platform.version()
    return f"Windows {rel} ({ver})" if rel or ver else "-"


def computer_info() -> dict[str, str]:
    return {"cpu": cpu_name(), "ram": ram_total_gb(),
            "ram_type": ram_type(), "disk": disk_type(),
            "os": os_version()}
