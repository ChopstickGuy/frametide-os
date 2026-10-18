#!/usr/bin/python3
"""Frametide Bench – reproduzierbarer Leistungstest für Frametide OS.

Misst CPU, Speicher, Kompression, Latenz (auch unter Volllast – entscheidend für
ruckelfreies Spielen), Datenträger, GPU und Startzeit. Ergebnisse landen als JSON in
~/.local/share/frametide-bench/ und lassen sich mit anderen Systemen vergleichen.

  frametide-bench                 alle Tests (ca. 4 Minuten)
  frametide-bench --quick         ohne GPU- und Datenträgertests (ca. 2 Minuten)
  frametide-bench --compare A.json B.json
"""
import argparse
import datetime
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from frametide_i18n import _  # noqa: E402

RESULTS = os.path.join(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
                       "frametide-bench")
NPROC = os.cpu_count() or 1

# Name, Einheit, höher ist besser?
METRICS = {
    "cpu_single": (_("CPU Single-Core"), "Events/s", True),
    "cpu_multi": (_("CPU Multi-Core"), "Events/s", True),
    "cpu_7zip": (_("7-Zip (Kompression/Dekompression)"), "MIPS", True),
    "memory": (_("Speicherbandbreite"), "MiB/s", True),
    "zstd_compress": (_("zstd Kompression"), "MB/s", True),
    "zstd_decompress": (_("zstd Dekompression"), "MB/s", True),
    "latency_idle_avg": (_("Latenz im Leerlauf (Ø)"), "µs", False),
    "latency_idle_p99": (_("Latenz im Leerlauf (99 %)"), "µs", False),
    "latency_load_avg": (_("Latenz unter Volllast (Ø)"), "µs", False),
    "latency_load_p99": (_("Latenz unter Volllast (99 %)"), "µs", False),
    "disk_seq_read": (_("SSD sequentiell lesen"), "MB/s", True),
    "disk_rand_read": (_("SSD 4K zufällig lesen"), "IOPS", True),
    "gpu_vkmark": (_("GPU Vulkan (vkmark)"), "Punkte", True),
    "gpu_glmark2": (_("GPU OpenGL (glmark2)"), "Punkte", True),
    "boot_time": (_("Startzeit"), "s", False),
}


def say(text):
    print(f"» {text}", flush=True)


def run(cmd, timeout=180):
    """stdout und stderr zusammen (manche Werkzeuge schreiben Ergebnisse nach stderr)."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.stdout + proc.stderr
    except (OSError, subprocess.SubprocessError):
        return ""


def have(tool):
    return shutil.which(tool) is not None


# ---------------------------------------------------------------- Tests

def test_sysbench(results):
    if not have("sysbench"):
        return
    say(_("CPU (sysbench)"))
    for key, threads in (("cpu_single", 1), ("cpu_multi", NPROC)):
        out = run(["sysbench", "cpu", f"--threads={threads}", "--time=10", "run"])
        m = re.search(r"events per second:\s*([\d.]+)", out)
        if m:
            results[key] = float(m.group(1))
    out = run(["sysbench", "memory", "--memory-block-size=1M", "--memory-total-size=32G",
               f"--threads={min(NPROC, 4)}", "--time=10", "run"])
    m = re.search(r"([\d.]+) MiB/sec", out)
    if m:
        results["memory"] = float(m.group(1))


def test_7zip(results):
    tool = next((t for t in ("7zz", "7z") if have(t)), None)
    if not tool:
        return
    say(_("7-Zip-Benchmark"))
    out = run([tool, "b", "-mmt" + str(NPROC)])
    m = re.search(r"^Tot:\s+\d+\s+\d+\s+(\d+)", out, re.M)
    if m:
        results["cpu_7zip"] = float(m.group(1))


def test_zstd(results):
    if not have("zstd"):
        return
    say(_("zstd-Kompression"))
    out = run(["zstd", "-b3", "-i5"])
    m = re.search(r"([\d.]+) MB/s,\s*([\d.]+) MB/s", out)
    if m:
        results["zstd_compress"], results["zstd_decompress"] = float(m.group(1)), float(m.group(2))


def wakeup_latency(seconds=15, interval_us=500):
    """Wie pünktlich wacht ein normaler Prozess auf? (Mikrosekunden Verspätung: Ø, 99 %-Wert)

    Entspricht dem, was Spiele, Audio und der Compositor erleben. Ohne root, ohne Echtzeit-Rechte.
    """
    import time
    samples, end = [], time.monotonic() + seconds
    target = interval_us / 1e6
    while time.monotonic() < end:
        t0 = time.perf_counter_ns()
        time.sleep(target)
        samples.append((time.perf_counter_ns() - t0) / 1000 - interval_us)
    samples.sort()
    return round(sum(samples) / len(samples), 1), round(samples[int(len(samples) * 0.99)], 1)


class Cancelled(Exception):
    """Benutzer hat „Stoppen“ gedrückt (SIGTERM) oder Strg+C (SIGINT)."""


def cancel(_signum, _frame):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        os.killpg(os.getpgrp(), signal.SIGTERM)  # laufende Testprogramme (stress-ng, fio, vkmark …) mit beenden
    except OSError:
        pass
    raise Cancelled()


def start_load():
    """Alle Kerne auslasten – mit stress-ng oder notfalls mit Python-Prozessen."""
    if have("stress-ng"):
        return [subprocess.Popen(["stress-ng", "--cpu", str(NPROC), "--timeout", "40s", "-q"])]
    code = "import time\nend=time.time()+40\nwhile time.time()<end: pass"
    return [subprocess.Popen([sys.executable, "-c", code]) for _ in range(NPROC)]


def test_latency(results):
    say(_("Latenz im Leerlauf"))
    results["latency_idle_avg"], results["latency_idle_p99"] = wakeup_latency()
    say(_("Latenz unter Volllast (alle Kerne ausgelastet)"))
    load = start_load()
    try:
        results["latency_load_avg"], results["latency_load_p99"] = wakeup_latency()
    finally:
        for proc in load:
            proc.terminate()
            proc.wait()


def test_disk(results):
    if not have("fio"):
        return
    say(_("Datenträger (fio, 1 GB Testdatei)"))
    with tempfile.TemporaryDirectory(dir=os.path.expanduser("~")) as tmp:
        path = os.path.join(tmp, "fio.bin")
        base = ["fio", "--name=ft", f"--filename={path}", "--size=1G", "--direct=1", "--runtime=10",
                "--time_based", "--ioengine=libaio", "--output-format=json"]
        for key, extra, field in (("disk_seq_read", ["--rw=read", "--bs=1M", "--iodepth=16"], "bw"),
                                  ("disk_rand_read", ["--rw=randread", "--bs=4k", "--iodepth=32"], "iops")):
            try:
                job = json.loads(run(base + extra, timeout=120))["jobs"][0]["read"]
                results[key] = round(job["bw"] / 1024, 1) if field == "bw" else round(job["iops"])
            except (ValueError, KeyError, IndexError):
                pass


def test_gpu(results):
    if not (os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY")):
        say(_("GPU-Tests übersprungen (keine grafische Sitzung)"))
        return
    if have("vkmark"):
        say(_("GPU Vulkan (vkmark)"))
        m = re.search(r"vkmark Score:\s*(\d+)", run(["vkmark", "--present-mode", "immediate"], timeout=300))
        if m:
            results["gpu_vkmark"] = int(m.group(1))
    tool = next((t for t in ("glmark2-wayland", "glmark2") if have(t)), None)
    if tool:
        say(_("GPU OpenGL (glmark2)"))
        m = re.search(r"glmark2 Score:\s*(\d+)", run([tool, "--off-screen"], timeout=300))
        if m:
            results["gpu_glmark2"] = int(m.group(1))


def test_boot(results):
    out = run(["systemd-analyze", "time"])
    m = re.search(r"=\s*(?:(\d+)min\s*)?([\d.]+)s\s*$", out.splitlines()[0] if out else "")
    if m:
        results["boot_time"] = round(int(m.group(1) or 0) * 60 + float(m.group(2)), 2)


# ------------------------------------------------------------- System

def system_info():
    os_release = dict(re.findall(r'^(\w+)="?([^"\n]*)"?$', open("/etc/os-release").read(), re.M))
    cpu = re.search(r"model name\s*:\s*(.+)", open("/proc/cpuinfo").read())
    mem = re.search(r"MemTotal:\s+(\d+)", open("/proc/meminfo").read())
    gpus = [l.split(": ", 1)[1] for l in run(["lspci"]).splitlines() if re.search(r"VGA|3D|Display", l)]
    governor = run(["cat", "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"]).strip()
    return {
        "os": os_release.get("PRETTY_NAME", platform.system()),
        "kernel": platform.release(),
        "cmdline": open("/proc/cmdline").read().strip(),
        "cpu": cpu.group(1) if cpu else platform.processor(),
        "threads": NPROC,
        "memory_gb": round(int(mem.group(1)) / 1024 / 1024, 1) if mem else None,
        "gpus": gpus,
        "cpu_governor": governor,
        "power_profile": run(["powerprofilesctl", "get"]).strip(),
        "mesa": run(["dpkg-query", "-W", "-f=${Version}", "mesa-vulkan-drivers"]).strip(),
        "nvidia": run(["cat", "/sys/module/nvidia/version"]).strip(),
    }


def print_table(results, other=None):
    for key, (name, unit, higher) in METRICS.items():
        if key not in results:
            continue
        line = f"  {name:<36} {results[key]:>12,.1f} {unit}"
        if other and key in other and other[key]:
            diff = (results[key] - other[key]) / other[key] * 100
            better = diff > 0 if higher else diff < 0
            line += f"   {'+' if diff >= 0 else ''}{diff:.1f} % {'✓' if better else '✗' if abs(diff) > 1 else '≈'}"
        print(line)


def main():
    parser = argparse.ArgumentParser(description=_("Frametide Bench – Leistungstest"))
    parser.add_argument("--quick", action="store_true", help=_("ohne GPU- und Datenträgertests"))
    parser.add_argument("--compare", nargs=2, metavar=("NEU.json", "ALT.json"), help=_("zwei Ergebnisse vergleichen"))
    args = parser.parse_args()

    if args.compare:
        new, old = (json.load(open(p)) for p in args.compare)
        print(f"{new['system']['os']} ({new['system']['kernel']})  vs.  {old['system']['os']} ({old['system']['kernel']})\n")
        print_table(new["results"], old["results"])
        return 0

    # Eigene Prozessgruppe (wenn nicht im Terminal): „Stoppen“ beendet so auch alle Testprogramme
    if not sys.stdin.isatty():
        os.setpgrp()
    signal.signal(signal.SIGTERM, cancel)
    signal.signal(signal.SIGINT, cancel)
    results = {}
    tests = [test_sysbench, test_7zip, test_zstd, test_latency, test_boot]
    if not args.quick:
        tests += [test_disk, test_gpu]
    try:
        for test in tests:
            test(results)
    except Cancelled:
        say(_("Benchmark abgebrochen – es wurde nichts gespeichert."))
        return 130
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    report = {"version": 1, "date": datetime.datetime.now().isoformat(timespec="seconds"),
              "system": system_info(), "results": results}
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json")
    with open(path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print()
    print_table(results)
    print()
    say(_("Ergebnis gespeichert: {path}").format(path=path))
    missing = [t for t in ("sysbench", "7z", "stress-ng", "fio", "zstd") if not have(t)]
    if missing:
        say(_("Nicht installiert (Tests übersprungen): {tools}").format(tools=", ".join(missing)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
