# Use a lightweight Debian base image
FROM debian:bookworm-slim

# Set the working directory
WORKDIR /usr/src/app

# Install necessary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    git \
    ffmpeg \
    build-essential \
    python3-dev \
    libffi-dev \
    libmp3lame-dev \
    procps \
    bash \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


# Create a virtual environment
RUN python3 -m venv /usr/src/app/venv

# Copy the rest of the application files
COPY . .

# Activate the virtual environment and install dependencies
RUN /usr/src/app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Make start.sh executable
RUN chmod +x start.sh

# Ensure the virtual environment is used by default
ENV PATH="/usr/src/app/venv/bin:$PATH"

# Run the application
CMD ["bash", "start.sh"]
