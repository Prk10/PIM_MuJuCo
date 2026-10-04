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

## Detailed External Dependencies Integration

### 1. Integrating MuJoCo (Physics Engine)
The MuJoCo integration operates within the `src/physics/` domain. This is where the physical simulation steps are executed and where the loop connects back to the PyTorch model.

**How to integrate and feed data:**
1. **Model Loading:** Load your robotic asset (e.g., a UR5 arm or humanoid) using `mujoco.MjModel.from_xml_path()`.
2. **Synchronization Bridge Loop:**
   Inside your main Python control script, import the compiled `sync_bridge` extension.
   ```python
   import sync_bridge
   import mujoco

   bridge = sync_bridge.SyncBridge()
   model = mujoco.MjModel.from_xml_path("robot.xml")
   data = mujoco.MjData(model)

   while simulation_running:
       # 1. Wait for the VLA model (simulated via gem5) to output an action token
       action_token = bridge.wait_for_action_token()

       # 2. Decode the token into physical commands (e.g., joint torques)
       data.ctrl[:] = decode_token_to_torques(action_token)

       # 3. Step the MuJoCo physics engine exactly once
       mujoco.mj_step(model, data)

       # 4. Collect proprioceptive/sensory data (qpos, qvel, camera pixels)
       proprioceptive_state = data.qpos.tolist() + data.qvel.tolist()
       # (Optionally render camera frames here)

       # 5. Send the updated physics state back to the PyTorch VLA model to generate the next token
       bridge.signal_mujoco_step_done(proprioceptive_state)
   ```

### 2. Integrating Ramulator2 (Memory System)
The Ramulator2 integration operates within the `src/memory/` and `src/host/` domains. It is responsible for simulating the PIM (Processing-In-Memory) operations.

**How to integrate and route memory requests:**
1. **Build Ramulator2:** Clone the Ramulator2 repository into `src/memory/ramulator2/` and compile it as a shared library.
2. **Link via CMake:** Update `CMakeLists.txt` to link the `libramulator2.so` against your host C++ components.
3. **Route Requests in gem5:**
   In `src/host/gem5_config.py`, the trace (generated by `VLATracer`) represents memory access patterns.
   When using full gem5, you configure a custom memory controller endpoint (e.g., `Ramulator2_Endpoint`) in your Python config.
   ```python
   # In src/host/gem5_config.py (when full gem5 is linked)
   system.mem_ctrl = m5.objects.Ramulator2Controller()
   system.mem_ctrl.config_file = "ramulator2_config.yaml"
   ```
4. **Custom Instructions (PIM):**
   The IR trace captures GEMV MAC counts. Inside your custom gem5 memory controller C++ code, when a read/write matches a specific address range dedicated to PIM, you translate these operations into Ramulator2 requests.
   - For a standard memory access: Route an `ACT`, `RD`/`WR`, `PRE` sequence to Ramulator2.
   - For a PIM operation (MAC): Map the GEMV trace counts to a custom PIM command defined in your Ramulator2 configuration (e.g., `PIM_MAC`), calculating the latency and energy accurately based on the KV-cache stationary setup.

## Running Tests

To verify that the pybind11 synchronization bridge and telemetry parser work correctly:

```bash
export PYTHONPATH=$(pwd)/build:$(pwd)
python3 -m pytest tests/
```
