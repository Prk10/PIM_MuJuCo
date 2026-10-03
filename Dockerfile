FROM ubuntu:22.04

# Prevent interactive prompts during apt
ENV DEBIAN_FRONTEND=noninteractive

# Update and install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    python3-pip \
    libgoogle-perftools-dev \
    pkg-config \
    zlib1g-dev \
    libprotobuf-dev \
    protobuf-compiler \
    libprotoc-dev \
    m4 \
    scons \
    && rm -rf /var/lib/apt/lists/*

# Set python3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Install PyTorch, MuJoCo, and other Python dependencies
RUN pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip3 install --no-cache-dir mujoco rich pytest numpy pybind11

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Command to run on startup (e.g., bash)
CMD ["/bin/bash"]
RUN cmake -B build && cmake --build build
