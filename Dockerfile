# Use the NVIDIA CUDA image as a base
FROM nvidia/cuda:11.8.0-base-ubuntu22.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python and necessary libraries
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev

# Create a directory for the app
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the working directory
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python3", "__main__.py"]
