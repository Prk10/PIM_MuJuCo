#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <mutex>
#include <condition_variable>
#include <iostream>
#include <vector>

namespace py = pybind11;

class SyncBridge {
private:
    std::mutex mtx;
    std::condition_variable cv_gem5;
    std::condition_variable cv_mujoco;

    bool gem5_done = false;
    bool mujoco_done = false;

    // Dummy state representation
    std::vector<float> current_action_token;
    std::vector<float> current_physics_state;

public:
    SyncBridge() {
        std::cout << "SyncBridge Initialized.\n";
    }

    // Called by PyTorch/gem5 side to signal that a token has been generated
    void signal_gem5_token_generated(const std::vector<float>& token) {
        std::unique_lock<std::mutex> lock(mtx);
        current_action_token = token;
        gem5_done = true;
        mujoco_done = false;
        std::cout << "[SyncBridge] gem5 completed token generation. Signaling MuJoCo..." << std::endl;
        cv_mujoco.notify_one();
    }

    // Called by MuJoCo side to wait for the generated token
    std::vector<float> wait_for_action_token() {
        py::gil_scoped_release release;
        std::unique_lock<std::mutex> lock(mtx);
        cv_mujoco.wait(lock, [this]{ return gem5_done; });
        gem5_done = false;
        std::cout << "[SyncBridge] MuJoCo received action token." << std::endl;
        return current_action_token;
    }

    // Called by MuJoCo side to signal physics step is done
    void signal_mujoco_step_done(const std::vector<float>& physics_state) {
        std::unique_lock<std::mutex> lock(mtx);
        current_physics_state = physics_state;
        mujoco_done = true;
        std::cout << "[SyncBridge] MuJoCo completed physics step. Signaling gem5/PyTorch..." << std::endl;
        cv_gem5.notify_one();
    }

    // Called by PyTorch/gem5 side to wait for updated physics state
    std::vector<float> wait_for_physics_state() {
        py::gil_scoped_release release;
        std::unique_lock<std::mutex> lock(mtx);
        cv_gem5.wait(lock, [this]{ return mujoco_done; });
        mujoco_done = false;
        std::cout << "[SyncBridge] PyTorch/gem5 received updated physics state." << std::endl;
        return current_physics_state;
    }
};

PYBIND11_MODULE(sync_bridge, m) {
    m.doc() = "Closed-Loop Synchronization Bridge for PIM-Sim Embodied LLM";

    py::class_<SyncBridge>(m, "SyncBridge")
        .def(py::init<>())
        .def("signal_gem5_token_generated", &SyncBridge::signal_gem5_token_generated)
        .def("wait_for_action_token", &SyncBridge::wait_for_action_token)
        .def("signal_mujoco_step_done", &SyncBridge::signal_mujoco_step_done)
        .def("wait_for_physics_state", &SyncBridge::wait_for_physics_state);
}
