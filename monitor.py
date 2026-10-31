#!/usr/bin/env python3
"""Server Resource Monitor: checks CPU, memory and disk against thresholds."""
import argparse, json, logging, socket, sys, time, urllib.request
from datetime import datetime
import psutil

def check_cpu(t):
    v = psutil.cpu_percent(interval=1)
    return {"name": "CPU", "value": v, "threshold": t, "ok": v < t}

def check_memory(t):
    v = psutil.virtual_memory().percent
    return {"name": "Memory", "value": v, "threshold": t, "ok": v < t}

def check_disks(t, paths):
    out = []
    for p in paths:
        try:
            v = psutil.disk_usage(p).percent
            out.append({"name": f"Disk {p}", "value": v, "threshold": t, "ok": v < t})
        except FileNotFoundError:
            logging.warning("Path %s does not exist, skipping", p)
    return out

def top_processes(limit=3):
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_percent"]):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procs.sort(key=lambda p: p["memory_percent"] or 0, reverse=True)
    return procs[:limit]

def send_discord_alert(url, msg):
    data = json.dumps({"content": msg}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": "resource-monitor"})
    try:
        urllib.request.urlopen(req, timeout=10)
        logging.info("Alert sent to Discord")
    except Exception as e:
        logging.error("Failed to send alert: %s", e)

def build_alert(problems):
    lines = [f"ALERT on {socket.gethostname()} ({datetime.now():%Y-%m-%d %H:%M:%S})"]
    for r in problems:
        lines.append(f"- {r['name']}: {r['value']:.1f}% (threshold {r['threshold']}%)")
    lines.append("Top processes by memory:")
    for p in top_processes():
        lines.append(f"- {p['name']} (PID {p['pid']}): {p['memory_percent']:.1f}%")
    return "\n".join(lines)

def run_checks(args):
    results = [check_cpu(args.cpu), check_memory(args.mem)] + check_disks(args.disk, args.paths)
    for r in results:
        level = logging.INFO if r["ok"] else logging.WARNING
        logging.log(level, "%-12s %5.1f%% (threshold %d%%) %s", r["name"], r["value"], r["threshold"], "OK" if r["ok"] else "ALERT")
    problems = [r for r in results if not r["ok"]]
    if problems:
        msg = build_alert(problems)
        print(msg)
        if args.webhook:
            send_discord_alert(args.webhook, msg)
    return problems

def main():
    ap = argparse.ArgumentParser(description="Simple server resource monitor")
    ap.add_argument("--cpu", type=int, default=85)
    ap.add_argument("--mem", type=int, default=85)
    ap.add_argument("--disk", type=int, default=90)
    ap.add_argument("--paths", nargs="+", default=["/"])
    ap.add_argument("--interval", type=int, default=0, help="seconds between checks; 0 = run once")
    ap.add_argument("--log", default="monitor.log")
    ap.add_argument("--webhook", help="Discord webhook URL (optional)")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                        handlers=[logging.FileHandler(args.log), logging.StreamHandler()])
    if args.interval <= 0:
        sys.exit(1 if run_checks(args) else 0)
    logging.info("Starting monitor every %ds (Ctrl+C to stop)", args.interval)
    try:
        while True:
            run_checks(args)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logging.info("Monitor stopped")

if __name__ == "__main__":
    main()
