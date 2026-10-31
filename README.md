# Server Resource Monitor

A small Python tool that checks **CPU, memory and disk usage** on a Linux server, logs the results, and alerts when a threshold is crossed (optionally to Discord).

Running on a **Google Cloud e2-micro VM (Ubuntu 24.04)**, scheduled with **cron** every 5 minutes.

## Features
- Checks CPU (sampled over 1s), memory and one or more disk paths
- Configurable thresholds via command-line flags
- Logs to file and console with timestamps
- On alert: lists the top 3 processes by memory for faster troubleshooting
- Optional Discord webhook alerts
- Exit code 1 when something is wrong, so other tools can react

## Setup

    sudo apt install -y python3-psutil
    python3 monitor.py

## Usage

    python3 monitor.py                           # defaults: CPU 85%, memory 85%, disk 90%
    python3 monitor.py --cpu 80 --disk 80 --paths / /var
    python3 monitor.py --interval 60             # run continuously every 60s
    python3 monitor.py --webhook "https://discord.com/api/webhooks/..."

## Example output

    2026-10-31 17:50:02 [INFO] CPU            1.0% (threshold 85%) OK
    2026-10-31 17:50:02 [INFO] Memory        43.3% (threshold 85%) OK
    2026-10-31 17:50:02 [INFO] Disk /        11.5% (threshold 90%) OK

## Scheduling with cron

    */5 * * * * /usr/bin/python3 /home/USER/server-resource-monitor/monitor.py --log /home/USER/monitor.log >> /home/USER/cron.log 2>&1

Absolute paths are used because cron runs with a minimal environment. `2>&1` captures errors in the log for debugging.

## What I learned
- Cron runs in UTC on the server and needs absolute paths
- On a 1 GB VM, the monitoring agent itself (Google Ops Agent / OpenTelemetry collector) uses a noticeable share of memory
- Diagnosing an apt lock: find the holding process and wait, instead of deleting the lock file

## Next steps
- Alert cooldown to avoid repeated notifications
- Check whether services are running (systemctl is-active)
- Expose metrics with prometheus_client and graph them in Grafana
- Package with Docker
