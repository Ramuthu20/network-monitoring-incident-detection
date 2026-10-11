# Network Monitoring & Incident Detection System

A Python-based network monitoring application developed on Linux to monitor TCP service availability, measure connection-establishment time, detect service outages, track recovery events, and visualize monitoring data through a live web dashboard.

## Features

* **TCP Connectivity Monitoring:** Periodically checks configured local TCP services.
* **Connection-Time Measurement:** Measures TCP connection-establishment time for successful checks.
* **Incident Detection:** Marks a service as down after three consecutive failed checks.
* **Recovery Tracking:** Records when an unavailable service becomes reachable again.
* **Live Dashboard:** Displays endpoint health, connection-time history, and incident events.
* **Structured Logging:** Stores timestamped monitoring records in JSON Lines format.

## Technologies Used

* Python 3
* Linux / Ubuntu
* TCP/IP and Python sockets
* HTTP, HTML, CSS, and JavaScript
* JSON Lines
* Git and GitHub

## Project Structure

```text
network-monitoring-incident-detection/
├── monitor.py
├── dashboard.py
├── .gitignore
└── README.md
```

* `monitor.py` — Performs connectivity checks, tracks failures, and records incidents and recovery.
* `dashboard.py` — Runs the web dashboard and displays monitoring information.
* `.gitignore` — Excludes virtual environment files, backups, cache files, and local monitoring data.
* `README.md` — Project documentation.

Monitoring logs are generated locally at runtime in `logs/monitoring.jsonl` and are not included in the repository.

## How It Works

1. The monitoring script periodically attempts TCP connections to configured endpoints.
2. Successful checks record connection-establishment time.
3. Three consecutive failed checks trigger an incident.
4. When a previously unavailable service becomes reachable, a recovery event is recorded.
5. Monitoring records are stored in a JSON Lines file.
6. The dashboard reads the monitoring data and displays service status, connection-time history, and incident events.

The current configuration monitors these local endpoints:

| Service          | Address     |   Port |
| ---------------- | ----------- | -----: |
| Test Service 2   | `127.0.0.1` | `9090` |
| Web Service Test | `127.0.0.1` | `8080` |

## Installation and Usage

**Prerequisites:** Linux/Ubuntu and Python 3.

Navigate to the project directory:

```bash
cd ~/network-monitor
```

Activate the existing virtual environment:

```bash
source .venv/bin/activate
```

Start the monitoring script in the first terminal:

```bash
python3 monitor.py
```

Start the dashboard in a second terminal:

```bash
cd ~/network-monitor
source .venv/bin/activate
python3 dashboard.py
```

Open the dashboard in a browser:

http://127.0.0.1:8000

The configured test services must be running on ports `8080` and `9090` for successful connectivity checks.

## Testing

The system can be tested through three scenarios:

1. **Normal operation:** Start both test services and verify their availability on the dashboard.
2. **Incident detection:** Stop one service and verify that an incident is recorded after three consecutive failed checks.
3. **Recovery:** Restart the service and verify that a recovery event is recorded.

The monitoring log can be inspected using:

```bash
tail -n 20 logs/monitoring.jsonl
```

## Limitations

* The current implementation monitors local services rather than an entire network or remote hosts.
* A successful TCP connection does not guarantee that the application itself is functioning correctly.
* Connection-time measurements represent TCP connection establishment, not internet latency or full application response time.
* Incident state is maintained in memory and resets when the monitoring process restarts.
* The current version does not include external alerts, persistent incident storage, or authentication for production use.

## Future Improvements

* Support for remote hosts and configurable endpoints.
* Persistent incident history and availability reports.
* HTTP health checks and application-level validation.
* Email notifications and configurable alert thresholds.
* Automated tests and improved historical analysis.

