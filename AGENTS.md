# PIM-Sim Architecture Constraints: Embodied LLM
This repository houses a closed-loop Processing-In-Memory (PIM) simulator designed for evaluating Language-to-Action (VLA) models in robotic control.

1. **Physical Environment (Python):** Uses MuJoCo for physics. The environment state (images/proprioception) is tokenized and fed into the VLA model. 
2. **Workload & ML (C++/Python):** Executes a Transformer-based VLA model. Trace generation must isolate the autoregressive decode phase, specifically capturing KV cache lookups and weight-streaming memory accesses.
3. **Host Microarchitecture (C++):** Built on gem5 using a RISC-V SoC. Custom RISC-V vector/matrix extensions are mapped to PIM commands to accelerate GEMV operations.
4. **Memory & Interconnect (C++):** Built on Ramulator2 with a chiplet-based UCIe interface. Memory arrays are configured for KV-cache-stationary operations.
5. **Execution Synchronization:** Strictly deterministic. The generation of a single action token in the hardware simulator triggers exactly one control-loop step in the MuJoCo environment.

6. **Telemetry & Profiling (Python):** 
   - The simulator must output a unified JSON report per run, combining gem5 cycle stats, Ramulator2 command-level energy estimates, and MuJoCo physical metrics.
   - Do not rely on external monolithic power models like McPAT. Instead, implement a lightweight analytical energy model in Python that multiplies Ramulator2 event counts by configurable energy coefficients (pJ/op).
   - The final output must render a clean terminal dashboard summarizing TOPS, TOPS/W, latency per token, and total simulated energy in Joules.