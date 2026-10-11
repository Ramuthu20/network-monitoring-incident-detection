import socket
import time
import json
import os
from datetime import datetime, timezone

TARGETS = [
    {"name": "Test Service 2", "host": "127.0.0.1", "port": 9090},
    {"name": "Web Service Test", "host": "127.0.0.1", "port": 8080},
]

INTERVAL = 5
FAILURE_THRESHOLD = 3

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "monitoring.jsonl")

# Runtime state resets when the monitor restarts.
previous = {}
consecutive_failures = {}
incident_start = {}

def check_target(target):
    start = time.perf_counter()
    try:
        with socket.create_connection(
            (target["host"], target["port"]), timeout=2
        ):
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {"status": "UP", "latency_ms": latency, "error": None}
    except OSError as exc:
        return {"status": "DOWN", "latency_ms": None, "error": str(exc)}

def record(event):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

print("Network Monitoring & Incident Detection System")
print(f"Checking TCP connectivity every {INTERVAL} seconds.")
print(f"A service is marked DOWN after {FAILURE_THRESHOLD} consecutive failures.")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        for target in TARGETS:
            name = target["name"]
            result = check_target(target)
            now = datetime.now(timezone.utc).isoformat()
            raw_status = result["status"]

            consecutive_failures.setdefault(name, 0)

            if raw_status == "DOWN":
                consecutive_failures[name] += 1
            else:
                consecutive_failures[name] = 0

            old_status = previous.get(name)

            if old_status is None:
                # Avoid declaring an initial outage until the threshold is met.
                if raw_status == "UP":
                    status = "UP"
                    event_type = "BASELINE"
                    previous[name] = "UP"
                elif consecutive_failures[name] >= FAILURE_THRESHOLD:
                    status = "DOWN"
                    event_type = "INCIDENT"
                    previous[name] = "DOWN"
                    incident_start[name] = now
                else:
                    status = "CHECKING"
                    event_type = "CHECK"
            elif old_status == "UP" and consecutive_failures[name] >= FAILURE_THRESHOLD:
                status = "DOWN"
                event_type = "INCIDENT"
                previous[name] = "DOWN"
                incident_start[name] = now
            elif old_status == "DOWN" and raw_status == "UP":
                status = "UP"
                event_type = "RECOVERY"
                previous[name] = "UP"
            else:
                status = old_status
                event_type = "CHECK"

            event = {
                "timestamp": now,
                "name": name,
                "host": target["host"],
                "port": target["port"],
                **result,
                "status": status,
                "event": event_type,
                "consecutive_failures": consecutive_failures[name],
            }

            if name in incident_start and status == "DOWN":
                event["incident_start"] = incident_start[name]
            elif event_type == "RECOVERY":
                event["incident_start"] = incident_start.pop(name, None)

            record(event)

            latency_text = (
                f"{result['latency_ms']} ms"
                if result["latency_ms"] is not None
                else result["error"]
            )
            print(
                f"[{now}] {event_type}: {name} {status} "
                f"(raw check: {raw_status}, failures: "
                f"{consecutive_failures[name]}) | {latency_text}"
            )

        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\nMonitoring stopped.")
