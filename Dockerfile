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

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Make start.sh executable
RUN chmod +x start.sh

# Run the application
CMD ["bash", "start.sh"]
