# Vortex CLI
### The Ephemeral & Unstable Environment Orchestrator

Vortex CLI is a Linux environment orchestration tool designed to provide developers with safe, isolated, and temporary environments for testing applications under failure scenarios and unstable conditions.

It uses Incus containers to create and manage isolated Linux environments and supports controlled network impairment, CPU and memory restrictions, application health checks, experiment recording, report generation, and automatic restoration of temporary changes.

**Project objective:**

To provide developers with a safe, isolated, and temporary environment to test applications against failure scenarios and unstable conditions.

---

## 1. Project Objectives

Applications should be tested not only under normal conditions but also under unexpected and degraded conditions.

Vortex provides a repeatable workflow for experimenting with:

- Increased network latency.
- Simulated packet loss.
- CPU resource restrictions.
- Memory resource restrictions.
- Application health checks under unstable conditions.
- Experiment event recording and timelines.
- Verification of temporary changes.
- Restoration of original environment settings.
- Automatic expiration and cleanup of temporary environments.

---

## 2. Features

### Environment Management

Vortex uses Incus to create and manage isolated Linux containers.

Supported operations:

- Create Debian Linux environments.
- List Vortex-managed environments.
- Inspect environment information.
- Start and stop environments.
- Destroy managed environments.
- Assign time-to-live (TTL) values.
- Detect expired environments.
- Clean up expired environments.

### Network Chaos Engineering

Vortex uses Linux traffic control (`tc`) and the `netem` queueing discipline to simulate network degradation.

Supported parameters:

| Parameter | Supported range |
|---|---|
| Latency | 0–5000 milliseconds |
| Packet loss | 0–100% |

The system captures the original network configuration, applies the requested impairment, verifies the resulting configuration, and attempts restoration after the experiment.

### CPU and Memory Resource Restrictions

Vortex can temporarily restrict container resources through Incus configuration.

Supported parameters:

| Parameter | Supported range |
|---|---|
| CPU restriction | 1–100% |
| Memory limit | 64 MiB–4 GiB |

The resource engine:

- Captures original resource settings.
- Applies CPU and memory restrictions.
- Verifies the effective configuration.
- Restores previous settings after the experiment.
- Verifies resource restoration.

### Application Health Checks

Scenario files can define commands to execute inside the target container.

Each check supports:

- A descriptive name.
- A command and its arguments.
- An execution timeout.
- An expected exit code.
- Captured standard output and error output.

This allows the experiment to verify whether basic application or system operations continue working under unstable conditions.

### Experiment Recording

Vortex records experiment events in JSON Lines format.

Events can include:

- Experiment started.
- Network impairment applied and verified.
- Resource restrictions verified.
- Application checks completed.
- Experiment duration completed.
- Network cleanup verified.
- Resource cleanup verified.
- Experiment finished or failed.

### Experiment Reports

Vortex generates readable text reports containing:

- Environment and scenario information.
- Experiment status.
- Configured network conditions.
- Application health-check results.
- Execution times and exit codes.
- Experiment event timeline.
- Total recorded events.
- Failed application checks.

### TTL and Automatic Cleanup

Vortex supports environment lifetimes using TTL values such as:

- `30m` — 30 minutes.
- `2h` — 2 hours.
- `1d` — 1 day.

Expired environments can be identified and removed using the cleanup command.

### Concurrent Operation Protection

Vortex uses operation locks to prevent conflicting operations against the same managed environment during critical lifecycle and experiment operations.

---

## 3. Architecture

Vortex separates its command-line interface, container management, chaos controls, lifecycle operations, and experiment observation.

```text
                         VORTEX CLI
                             |
              +--------------+--------------+
              |              |              |
        Environment      Scenario       Lifecycle
        Management     Configuration    Management
              |              |              |
            Incus        YAML Loader      TTL / Locks
              |              |
       Linux Container   Experiment Runner
                             |
              +--------------+--------------+
              |                             |
        Network Chaos                 Resource Chaos
              |                             |
          tc / netem                  Incus Limits
              |                             |
              +--------------+--------------+
                             |
                    Application Checks
                             |
                      Observation
                             |
              +--------------+--------------+
              |              |              |
          Recorder        Metrics         Reports
```

### Technology Stack

| Technology | Purpose |
|---|---|
| Python | Main implementation language |
| Typer | Command-line interface |
| Rich | Terminal interface and presentation |
| Incus | Container management and isolation |
| PyYAML | Scenario configuration |
| Linux `tc` / `netem` | Network impairment |
| JSON Lines | Experiment event recording |
| pytest | Automated testing |

---

## 4. Project Structure

```text
Vortex Project/
├── scenarios/
│   └── examples/
│       ├── application-resilience.yaml
│       ├── bad-wifi.yaml
│       ├── resource-resilience.yaml
│       └── test-network.yaml
│
├── reports/
│   ├── <environment>.jsonl
│   └── <environment>-report.txt
│
├── tests/
│   ├── test_cleanup.py
│   ├── test_config.py
│   ├── test_incus_safety.py
│   ├── test_locks.py
│   ├── test_network.py
│   ├── test_report.py
│   ├── test_resource_config.py
│   ├── test_resources.py
│   ├── test_runner.py
│   ├── test_ttl.py
│   └── test_workload.py
│
├── vortex/
│   ├── chaos/
│   │   ├── network.py
│   │   └── resources.py
│   │
│   ├── core/
│   │   └── incus.py
│   │
│   ├── lifecycle/
│   │   ├── cleanup.py
│   │   ├── locks.py
│   │   └── ttl.py
│   │
│   ├── observe/
│   │   ├── metrics.py
│   │   ├── recorder.py
│   │   └── report.py
│   │
│   ├── scenarios/
│   │   ├── runner.py
│   │   └── workload.py
│   │
│   ├── cli.py
│   ├── config.py
│   └── ui.py
│
├── pyproject.toml
├── requirements.txt
├── install.sh
└── README.md
```

Generated experiment logs and reports are stored under `reports/`.

---

## 5. Requirements

Before running Vortex, ensure that you have:

- Python 3.10 or newer.
- Incus installed and initialized.
- Permission to access the Incus daemon.
- A working Incus storage pool and network.
- Linux container networking support.
- `tc` available inside the target container for network experiments.

Vortex has been developed and tested in Ubuntu under WSL2 with Python 3.12 and Incus.

---

## 6. Installation

### Prerequisites

Before installing Vortex, ensure that you have:

- Ubuntu or another supported Linux environment.
- Python 3.10 or newer.
- Incus installed and initialized.
- Permission to access the Incus daemon.

### Step 1: Open the project directory

Open a terminal in the Vortex project directory containing `install.sh` and `pyproject.toml`.

### Step 2: Run the installer

```bash
bash install.sh
```

The installation script:

- Checks the Python version.
- Creates a virtual environment if one does not already exist.
- Activates the project virtual environment.
- Installs Vortex and its dependencies.
- Checks whether the Incus CLI is available.

### Step 3: Activate the virtual environment

```bash
source .venv/bin/activate
```

The installer activates the environment only within its own process, so this step is required in your terminal.

### Step 4: Verify the installation

```bash
vortex version
vortex --help
vortex status
```

### Step 5: Verify Incus

```bash
incus version
incus list
```

Incus must be initialized and accessible before Vortex can create and manage environments.

### Alternative: Manual installation

The project can also be installed manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## 7. Available Commands

| Command | Purpose |
|---|---|
| `vortex version` | Display the Vortex version |
| `vortex status` | Display backend and feature status |
| `vortex create <name>` | Create a temporary Linux environment |
| `vortex create <name> --ttl 30m` | Create an environment with a lifetime |
| `vortex list` | List managed environments |
| `vortex inspect <name>` | Display environment details |
| `vortex start <name>` | Start a stopped environment |
| `vortex stop <name>` | Stop a running environment |
| `vortex destroy <name>` | Delete an environment with confirmation |
| `vortex destroy <name> --yes` | Delete without confirmation |
| `vortex cleanup` | Remove expired environments |
| `vortex cleanup --dry-run` | Preview expired environments |
| `vortex run <scenario> <environment>` | Execute a failure experiment |
| `vortex report <environment>` | Generate an experiment report |
| `vortex metrics <environment>` | Display environment metrics |

For command-specific options and arguments, use:

```bash
vortex --help
vortex create --help
vortex run --help
vortex cleanup --help
```

---

## 8. Experiment Scenarios

Vortex uses YAML files to define experiment scenarios.

A scenario can specify:

- Network conditions.
- CPU and memory restrictions.
- Experiment duration.
- Application health checks.

### Example: Resource Resilience

```yaml
name: resource-resilience
description: Verify workload stability under CPU, memory, and network constraints

network:
  latency_ms: 100
  packet_loss_percent: 2

resources:
  cpu_percent: 25
  memory_limit: "768MiB"

duration_seconds: 10

checks:
  - name: container-identity
    command:
      - /usr/bin/id
      - -u
    timeout_seconds: 3
    expected_exit_code: 0

  - name: operating-system-check
    command:
      - /usr/bin/test
      - -r
      - /etc/os-release
    timeout_seconds: 3
    expected_exit_code: 0
```

### Running an experiment

Create an environment:

```bash
vortex create resource-lab --ttl 1h
```

Execute the scenario:

```bash
vortex run scenarios/examples/resource-resilience.yaml resource-lab
```

Generate a report:

```bash
vortex report resource-lab
```

Inspect the environment:

```bash
vortex inspect resource-lab
```

Clean up expired environments:

```bash
vortex cleanup
```

---

## 9. Safety and Reliability

Vortex incorporates several mechanisms intended to keep experiments isolated and reversible.

### Environment Ownership

Lifecycle and experiment operations validate that the target environment is Vortex-managed.

### Baseline Configuration

Original network and resource configurations are captured before temporary changes are applied.

### Verification

Vortex checks whether requested configurations were applied successfully.

### Restoration

Temporary network and resource modifications are restored after the experiment. Restoration is verified before successful completion is reported.

### Failure Handling

The experiment runner attempts cleanup when an experiment fails, including failures during application checks.

### Operation Locks

Locks help prevent conflicting concurrent operations on the same environment.

### TTL Protection

Expired environments are rejected by applicable operations and can be removed through the cleanup mechanism.

---

## 10. Testing

Run the automated test suite:

```bash
python3 -m pytest tests/ -q
```

Check Python compilation:

```bash
python3 -m compileall -q vortex tests
```

The test suite covers configuration validation, environment safety, network chaos, resource restrictions, workload checks, reporting, TTL, cleanup, operation locks, and experiment execution.

---

## 11. Limitations

Vortex is an educational prototype and a foundation for further development, not a complete production-grade chaos engineering platform.

Current limitations include:

- Metrics depend on information exposed by Incus.
- CPU usage and memory peak are not currently available through the implemented metrics parser.
- Experiments require an accessible Incus daemon.
- Network experiments depend on Linux traffic-control support inside the target environment.
- TTL expiration and cleanup depend on the cleanup mechanism being invoked; Vortex is not a continuously running background scheduler.
- The project has not been validated as a production orchestration system.

---

## 12. Project Purpose

Vortex demonstrates how isolated Linux environments, controlled failure injection, experiment verification, event recording, and automated cleanup can be combined into a command-line failure-testing workflow.

The project aims to make experimentation with unstable application conditions safer, more reproducible, and easier to understand.