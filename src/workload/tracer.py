import torch
import json
import os

class VLATracer:
    def __init__(self, trace_file="trace.json"):
        self.trace_file = trace_file
        self.trace = []
        self.hooks = []

    def register_hooks(self, model: torch.nn.Module):
        for name, module in model.named_modules():
            if isinstance(module, torch.nn.Linear):
                # Using a closure to capture the name
                hook = module.register_forward_hook(
                    lambda mod, inp, out, n=name: self._hook_fn(n, mod, inp, out)
                )
                self.hooks.append(hook)

            # Intercept KV Cache updates in self attention if we could identify them
            # For simplicity, if we find a module named 'k_proj' or 'v_proj', we log
            if 'k_proj' in name or 'v_proj' in name:
                pass

    def _hook_fn(self, name, module, inp, out):
        # Determine if it's a GEMV (autoregressive decode step)
        # Assuming input shape is [batch_size, seq_len, in_features]
        # In decode step, seq_len is typically 1
        input_tensor = inp[0]
        if len(input_tensor.shape) == 3:
            batch_size, seq_len, in_features = input_tensor.shape
        elif len(input_tensor.shape) == 2:
            batch_size, in_features = input_tensor.shape
            seq_len = 1
        else:
            return

        out_features = module.out_features

        is_gemv = (seq_len == 1)
        mac_count = batch_size * seq_len * in_features * out_features

        # Determine if it's a KV cache update
        is_kv_update = False
        if 'k_proj' in name or 'v_proj' in name:
            is_kv_update = True

        if is_gemv or is_kv_update:
            op_data = {
                "layer_name": name,
                "type": "GEMV" if is_gemv else "GEMM",
                "is_kv_update": is_kv_update,
                "input_shape": list(input_tensor.shape),
                "weight_shape": [out_features, in_features],
                "mac_count": mac_count
            }
            self.trace.append(op_data)

    def dump_trace(self):
        with open(self.trace_file, "w") as f:
            json.dump(self.trace, f, indent=4)

    def remove_hooks(self):
        for hook in self.hooks:
            hook.remove()
        self.hooks = []
