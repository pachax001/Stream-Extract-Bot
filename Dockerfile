# Use a lightweight base image
FROM alpine:latest

# Set the working directory
WORKDIR /usr/src/app

# Install necessary packages and build dependencies
RUN apk --no-cache add \
    python3 \
    py3-pip \
    git \
    ffmpeg \
    build-base \
    python3-dev \
    libffi-dev \
    bash

# Create a virtual environment
RUN python3 -m venv /usr/src/app/venv

# Activate the virtual environment and install dependencies
RUN /usr/src/app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Make start.sh executable
RUN chmod +x start.sh

# Ensure the virtual environment is used by default
ENV PATH="/usr/src/app/venv/bin:$PATH"

# Run the application
CMD ["bash", "start.sh"]
