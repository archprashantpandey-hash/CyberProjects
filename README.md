# Vortex CLI
### The Ephemeral & Unstable Environment Orchestrator

Vortex CLI is a prototype environment orchestration tool designed to provide developers with safe, isolated, and temporary Linux environments for experimenting with applications under unstable conditions.

It uses Incus containers to create and manage Linux environments and supports controlled network impairment experiments, event recording, report generation, and basic environment metrics.

The goal is to make failure testing easier to reproduce, observe, and clean up without deliberately disrupting the host environment.

---

## 1. Project Objectives

Software applications should be tested not only under normal conditions, but also under unexpected or degraded conditions.

Vortex aims to provide a repeatable workflow for experimenting with scenarios such as:

- Increased network latency.
- Simulated packet loss.
- Temporary network degradation.
- Recording experiment events and timestamps.
- Reviewing experiment outcomes through readable reports.
- Cleaning up temporary network impairment after an experiment.

Vortex is an educational prototype and a foundation for further development. It is not yet a complete production-grade chaos engineering platform.

---

## 2. Current Features

### Environment Management

Vortex uses Incus to create and manage isolated Linux containers.

Supported operations include:

- Creating environments.
- Listing Vortex-managed environments.
- Inspecting environment information.
- Starting and stopping environments.
- Destroying environments with confirmation.
- Rejecting operations on environments that are not marked as Vortex-managed.

### Network Chaos Experiments

Vortex loads experiment configurations from YAML files and applies supported network impairment settings inside a managed container.

Currently supported scenario parameters include:

- Network latency, from 0 to 5000 milliseconds.
- Packet loss, from 0% to 100%.
- Experiment duration, from 1 to 3600 seconds.

The current implementation uses Linux traffic control (`tc`) with the `netem` queueing discipline.

### Event Recording

Experiment events are stored in JSON Lines format.

Recorded events can include:

- Experiment started.
- Network chaos applied.
- Experiment duration completed.
- Experiment failed.
- Experiment finished.
- Cleanup failed.

Each event includes a timestamp, environment name, event type, and associated details.

### Experiment Reports

Vortex generates readable text reports containing:

- Environment name.
- Scenario name.
- Experiment status.
- Configured network conditions.
- Experiment event timeline.
- Number of recorded events.

The report generator selects the latest experiment in the environment's event log.

### Basic Environment Metrics

The metrics command displays available environment information, including:

- Environment status.
- Timestamp of the query.
- Memory usage when exposed by the current Incus output.

CPU usage and memory peak are not currently available through the implemented metrics parser.

---

## 3. Architecture

Vortex is organized into modules that separate the command-line interface, environment management, chaos controls, scenario validation, and observation.

```text
Vortex CLI
    |
    v
Command-Line Interface
    |
    +---- Environment Management
    |          |
    |          v
    |       Incus Backend
    |          |
    |          v
    |       Linux Container
    |
    +---- Scenario Configuration
    |          |
    |          v
    |       YAML Validation
    |          |
    |          v
    |       Experiment Runner
    |          |
    |          v
    |       Network Chaos Controls
    |          |
    |          v
    |       Linux tc / netem
    |
    +---- Observation
               |
               +---- Event Recorder
               |
               +---- Metrics Collector
               |
               +---- Report Generator
```

### Technology Stack

| Technology | Purpose |
|---|---|
| Python | Main implementation language |
| Typer | Command-line interface |
| Incus | Container lifecycle and isolation |
| YAML | Scenario configuration |
| Linux `tc` / `netem` | Network impairment |
| JSON Lines | Experiment event logs |
| pytest | Automated testing |

---

## 4. Project Structure

```text
Vortex Project/
├── scenarios/
│   └── examples/
│       ├── bad-wifi.yaml
│       └── test-network.yaml
├── reports/
│   ├── <environment>.jsonl
│   └── <environment>-report.txt
├── tests/
│   ├── test_config.py
│   └── test_incus_safety.py
├── vortex/
│   ├── chaos/
│   │   └── network.py
│   ├── core/
│   │   └── incus.py
│   ├── lifecycle/
│   ├── observe/
│   │   ├── metrics.py
│   │   ├── recorder.py
│   │   └── report.py
│   ├── scenarios/
│   │   └── runner.py
│   ├── cli.py
│   └── config.py
├── pyproject.toml
├── requirements.txt
├── install.sh
└── README.md
```

Generated reports and logs appear under `reports/`. The exact repository contents may change as development continues.

---

## 5. Requirements

Before running Vortex, ensure that you have:

- Python 3.10 or newer.
- Incus installed and initialized.
- Permission to use the Incus daemon.
- A working Incus image and storage/network configuration.
- A Linux environment with the necessary container networking support.
- `tc` available inside the target container for network experiments.
- `pytest` installed to run the development tests.

Vortex has been developed and tested in Ubuntu under WSL with Python 3.12 and Incus.

---

## 6. Installation

### Step 1: Open the project directory

Open a terminal in the directory containing `pyproject.toml`.

### Step 2: Create a virtual environment

```bash
python3 -m venv .venv
```

### Step 3: Activate it

```bash
source .venv/bin/activate
```

### Step 4: Install Vortex

```bash
python3 -m pip install -e .
```

### Step 5: Verify the installation

```bash
vortex version
vortex --help
```

The command-line interface should display the available commands.

### Step 6: Verify Incus

```bash
incus version
incus list
```

Incus must be initialized and accessible to the current user before environment management commands will work.

---

## 7. Available Commands

| Command | Purpose |
|---|---|
| `vortex version` | Display the Vortex version |
| `vortex status` | Display the reported backend status |
| `vortex create <name>` | Create