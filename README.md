# PIM-Sim: Embodied LLM Hardware Simulator

PIM-Sim is a closed-loop Processing-In-Memory (PIM) simulator infrastructure designed for evaluating Vision-Language-Action (VLA) models in robotic control. This tool is built to provide deterministic, hardware-accurate evaluations by separating concerns across the physical environment, machine learning workload, host microarchitecture, and memory systems.

## Architecture

PIM-Sim enforces a strict separation of concerns:

1. **Physics (Python)**: Uses [MuJoCo](https://mujoco.org/) to generate real-time sensory data and execute physical motor commands.
2. **Workload (Python/PyTorch)**: Executes the Transformer-based VLA model. Includes a tracer to intercept autoregressive decoding operations (GEMV) and KV cache updates.
3. **Host Microarchitecture (C++)**: Built on [gem5](https://www.gem5.org/), running a RISC-V SoC configuration that dispatches custom instructions to the memory controller.
4. **Memory (C++)**: Built on [Ramulator2](https://github.com/CMU-SAFARI/ramulator2) using a chiplet-based UCIe interface configured for KV-cache-stationary operations.
5. **Synchronization Bridge**: A pybind11-based module bridging Python and C++ domains deterministically to enforce a "Token-to-Action" simulation loop.
6. **Telemetry & Dashboard**: A Python module extracting metrics and analytical energy statistics to produce a terminal dashboard.

## Directory Structure

```
├── src/
│   ├── bridge/         # pybind11 deterministic execution bridge (C++)
│   ├── host/           # gem5 RISC-V SoC configurations (Python)
│   ├── memory/         # Ramulator2 integration (C++)
│   ├── physics/        # MuJoCo environment integration (Python)
│   ├── telemetry/      # Parser and dashboard using rich (Python)
│   └── workload/       # PyTorch LLM tracing hooks (Python)
├── tests/              # pytest unit tests
├── CMakeLists.txt      # Build configuration for C++ pybind11 modules
├── Dockerfile          # Environment image for running PIM-Sim
└── README.md
```

## Requirements

The provided `Dockerfile` encapsulates all necessary dependencies:
- Python 3.10+
- PyTorch
- MuJoCo
- gem5 build prerequisites (m4, scons, zlib, libprotobuf, etc.)
- pybind11
- pytest, rich, numpy

## Building the Simulator

### Using Docker (Recommended)

1. **Build the Docker Image:**
   ```bash
   docker build -t pim-sim .
   ```

2. **Run the Container:**
   ```bash
   docker run -it pim-sim /bin/bash
   ```

### Local Build

If you prefer building locally on Ubuntu 22.04:

1. **Install Prerequisites:**
   ```bash
   sudo apt-get update && sudo apt-get install -y build-essential cmake git python3.10 python3.10-dev python3-pip
   pip3 install torch torchvision torchaudio mujoco rich pytest numpy pybind11
   ```

2. **Build the C++ pybind11 Bridge:**
   ```bash
   cmake -B build
   cmake --build build
   ```

## Usage and Execution

### 1. Generating a Workload Trace
First, run the tracer to generate an Intermediate Representation (IR) memory trace of your Embodied LLM during the autoregressive decode phase:

```python
import torch
import torch.nn as nn
from src.workload.tracer import VLATracer

# Example dummy model
class VLA_Model(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(128, 256)

    def forward(self, x):
        return self.fc(x)

model = VLA_Model()
tracer = VLATracer(trace_file="trace.json")
tracer.register_hooks(model)

# Run an inference step
dummy_input = torch.randn(1, 1, 128)
model(dummy_input)

# Output trace
tracer.dump_trace()
```

### 2. Running the gem5 Host Simulation
Use the `gem5_config.py` script to simulate the generated trace on the host architecture:

```bash
python3 src/host/gem5_config.py --trace trace.json
```

### 3. Parsing Telemetry and Viewing Dashboard
Once the simulation steps are complete, run the telemetry parser to compute Latency, Energy (Joules), and TOPS/W:

```bash
python3 src/telemetry/telemetry_parser.py
```
This command generates a unified dashboard in your terminal and saves raw metrics to `results.json`.

## External Dependencies Integration

### gem5 & Ramulator2 Integration
Presently, `gem5_config.py` runs a mock environment. To integrate with the full gem5 and Ramulator2 simulators:
1. Clone the gem5 repository into `src/host/gem5/` and build it with RISC-V support.
2. Clone Ramulator2 into `src/memory/ramulator2/` and compile it.
3. Link the Ramulator2 library in the `CMakeLists.txt` and update the C++ endpoints in `src/bridge/` and `src/host/` to route requests dynamically.

### MuJoCo Physics Engine
To fully close the loop, load your robotic XML assets into a MuJoCo `MjModel` inside `src/physics/`. Use the `sync_bridge` generated actions to apply control steps via `mujoco.mj_step()`, retrieve proprioceptive/visual tokens, and feed them back to the PyTorch VLA model.

## Running Tests

To verify that the pybind11 synchronization bridge and telemetry parser work correctly:

```bash
export PYTHONPATH=$(pwd)/build:$(pwd)
python3 -m pytest tests/
```
