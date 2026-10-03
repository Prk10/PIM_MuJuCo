import json
import os
from rich.console import Console
from rich.table import Table

class TelemetryParser:
    def __init__(self, energy_coeffs_file="energy_coeffs.json", clock_freq_ghz=1.0):
        self.clock_freq_ghz = clock_freq_ghz

        with open(energy_coeffs_file, 'r') as f:
            self.energy_coeffs = json.load(f)

    def parse_gem5_stats(self, stats_file):
        return {"sim_ticks": 1000000}

    def parse_ramulator_logs(self, log_file):
        return {
            "RD": 1000,
            "WR": 500,
            "ACT": 1200,
            "PRE": 1200,
            "PIM_MAC": 500000
        }

    def parse_mujoco_metrics(self, state_file):
        return {"physical_energy_joules": 0.05}

    def calculate_metrics(self, gem5_stats, ramulator_stats, mujoco_stats, trace_file=None):
        time_s = gem5_stats["sim_ticks"] * 1e-12

        total_pim_energy_pj = 0
        for cmd, count in ramulator_stats.items():
            if cmd in self.energy_coeffs:
                total_pim_energy_pj += count * self.energy_coeffs[cmd]

        total_pim_energy_j = total_pim_energy_pj * 1e-12

        total_host_energy_j = 0.01
        total_system_energy_j = total_host_energy_j + total_pim_energy_j

        total_macs = ramulator_stats.get("PIM_MAC", 0)

        if trace_file and os.path.exists(trace_file):
            try:
                with open(trace_file, 'r') as f:
                    trace = json.load(f)
                    total_macs = sum(op.get("mac_count", 0) for op in trace)
            except Exception as e:
                print(f"Warning: Could not parse trace file for MAC count. Using ramulator stats. ({e})")

        ops = total_macs * 2
        tops = (ops / time_s) / 1e12 if time_s > 0 else 0

        power_w = total_system_energy_j / time_s if time_s > 0 else 0
        tops_per_w = tops / power_w if power_w > 0 else 0

        return {
            "total_cycles": gem5_stats["sim_ticks"],
            "latency_s": time_s,
            "total_system_energy_j": total_system_energy_j,
            "tops": tops,
            "tops_per_w": tops_per_w,
            "physical_energy_j": mujoco_stats["physical_energy_joules"]
        }

    def generate_dashboard(self, metrics, output_json="results.json"):
        console = Console()
        table = Table(title="PIM-Sim Telemetry Dashboard")

        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Total Cycles", str(metrics["total_cycles"]))
        table.add_row("Latency per Token (s)", f"{metrics['latency_s']:.6e}")
        table.add_row("Total System Energy (J)", f"{metrics['total_system_energy_j']:.6e}")
        table.add_row("PIM Throughput (TOPS)", f"{metrics['tops']:.4f}")
        table.add_row("PIM Efficiency (TOPS/W)", f"{metrics['tops_per_w']:.4f}")
        table.add_row("MuJoCo Physical Energy (J)", f"{metrics['physical_energy_j']:.4f}")

        console.print(table)

        with open(output_json, 'w') as f:
            json.dump(metrics, f, indent=4)
        print(f"Metrics saved to {output_json}")

if __name__ == "__main__":
    parser = TelemetryParser("src/telemetry/energy_coeffs.json")

    gem5 = parser.parse_gem5_stats("dummy_stats.txt")
    ramulator = parser.parse_ramulator_logs("dummy_ramulator.log")
    mujoco = parser.parse_mujoco_metrics("dummy_mujoco.json")

    metrics = parser.calculate_metrics(gem5, ramulator, mujoco, trace_file="trace.json")
    parser.generate_dashboard(metrics)
