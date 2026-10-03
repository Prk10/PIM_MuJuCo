cmake_minimum_required(VERSION 3.14)
project(PIM_MuJuCo_Bridge LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

include(FetchContent)
FetchContent_Declare(
  pybind11
  GIT_REPOSITORY https://github.com/pybind/pybind11.git
  GIT_TAG        v2.11.1
)
FetchContent_MakeAvailable(pybind11)

pybind11_add_module(sync_bridge src/bridge/sync_bridge.cpp)

# If there were other dependencies like gem5 headers or Ramulator2, they would be linked here
# target_link_libraries(sync_bridge PRIVATE ...)
