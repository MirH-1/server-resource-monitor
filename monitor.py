#!/usr/bin/env python3
"""Server Resource Monitor: checks CPU, memory and disk against thresholds."""

# ===== PART A: THE TOOLS =====
import argparse, json, logging, socket, sys, time, urllib.request
from datetime import datetime
import psutil                     # reads CPU, memory, disk and running programs


# ===== PART B: THE 3 CHECKS =====
# Each check measures one thing and returns: name, value, limit, and OK yes/no

def check_cpu(t):
    v = psutil.cpu_percent(interval=1)            # CPU % measured over 1 second
    return {"name": "CPU", "value": v, "threshold": t, "ok": v < t}

def check_memory(t):
    v = psutil.virtual_memory().percent           # memory (RAM) % used
    return {"name": "Memory", "value": v, "threshold": t, "ok": v < t}

def check_disks(t, paths):
    out = []
    for p in paths:                               # can check one or more disks
        try:
            v = psutil.disk_usage(p).percent      # disk % used
            out.append({"name": f"Disk {p}", "value": v, "threshold": t, "ok": v < t})
        except FileNotFoundError:                 # if the path doesn't exist, skip it, don't crash
            logging.warning("Path %s does not exist, skipping", p)
    return out


# ===== PART D (helper): WHICH PROGRAMS USE THE MOST MEMORY =====
def top_processes(limit=3):
    procs = []
    for p in psutil.process_iter(["pid", "name", "memory_percent"]):   # go through all running programs
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue                              # program closed or no permission: skip it
    procs.sort(key=lambda p: p["memory_percent"] or 0, reverse=True)   # biggest first
    return procs[:limit]                          # keep the top 3


# ===== PART D (optional): SEND THE ALERT TO DISCORD =====
def send_discord_alert(url, msg):
    data = json.dumps({"content": msg}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": "resource-monitor"})
    try:
        urllib.request.urlopen(req, timeout=10)   # timeout = never wait forever
        logging.info("Alert sent to Discord")
    except Exception as e:
        logging.error("Failed to send alert: %s", e)


# ===== PART D: BUILD THE ALERT MESSAGE =====
def build_alert(problems):
    lines = [f"ALERT on {socket.gethostname()} ({datetime.now():%Y-%m-%d %H:%M:%S})"]   # server name + time
    for r in problems:
        lines.append(f"- {r['name']}: {r['value']:.1f}% (threshold {r['threshold']}%)")   # what is too high
    lines.append("Top processes by memory:")
    for p in top_processes():
        lines.append(f"- {p['name']} (PID {p['pid']}): {p['memory_percent']:.1f}%")      # top 3 programs
    return "\n".join(lines)


# ===== PART C: RUN THE CHECKS AND WRITE TO THE LOG =====
def run_checks(args):
    results = [check_cpu(args.cpu), check_memory(args.mem)] + check_disks(args.disk, args.paths)
    for r in results:
        level = logging.INFO if r["ok"] else logging.WARNING      # OK = INFO line, problem = WARNING line
        logging.log(level, "%-12s %5.1f%% (threshold %d%%) %s",
                    r["name"], r["value"], r["threshold"], "OK" if r["ok"] else "ALERT")
    problems = [r for r in results if not r["ok"]]                 # keep only the checks that failed
    if problems:
        msg = build_alert(problems)
        print(msg)                                                 # show the alert
        if args.webhook:
            send_discord_alert(args.webhook, msg)                  # and send it, if Discord is set up
    return problems


# ===== SETTINGS + START =====
def main():
    ap = argparse.ArgumentParser(description="Simple server resource monitor")
    ap.add_argument("--cpu", type=int, default=85)                 # CPU limit (default 85%)
    ap.add_argument("--mem", type=int, default=85)                 # memory limit (default 85%)
    ap.add_argument("--disk", type=int, default=90)                # disk limit (default 90%)
    ap.add_argument("--paths", nargs="+", default=["/"])           # which disk(s) to check
    ap.add_argument("--interval", type=int, default=0, help="seconds between checks; 0 = run once")
    ap.add_argument("--log", default="monitor.log")                # where to write the log
    ap.add_argument("--webhook", help="Discord webhook URL (optional)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                        handlers=[logging.FileHandler(args.log), logging.StreamHandler()])   # write to file AND screen

    # ===== PART E: EXIT CODE =====
    if args.interval <= 0:                         # normal case (cron): run once
        sys.exit(1 if run_checks(args) else 0)     # 1 = problem found, 0 = all OK

    # (optional) run forever, checking every X seconds
    logging.info("Starting monitor every %ds (Ctrl+C to stop)", args.interval)
    try:
        while True:
            run_checks(args)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logging.info("Monitor stopped")

if __name__ == "__main__":                         # start here when the file is run
    main()
