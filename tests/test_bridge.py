import pytest
import threading
import time

try:
    import sync_bridge
except ImportError:
    pytest.skip("sync_bridge module not built yet. Skipping test.", allow_module_level=True)

def test_sync_bridge_flow():
    bridge = sync_bridge.SyncBridge()

    def gem5_worker():
        token = [0.1, 0.2, 0.3]
        bridge.signal_gem5_token_generated(token)

        physics_state = bridge.wait_for_physics_state()
        assert len(physics_state) == 2
        assert abs(physics_state[0] - 1.0) < 1e-5
        assert abs(physics_state[1] - 2.0) < 1e-5

    t1 = threading.Thread(target=gem5_worker)
    t1.start()

    received_token = bridge.wait_for_action_token()
    assert len(received_token) == 3
    assert abs(received_token[0] - 0.1) < 1e-5
    assert abs(received_token[1] - 0.2) < 1e-5

    physics_state = [1.0, 2.0]
    bridge.signal_mujoco_step_done(physics_state)

    t1.join()
