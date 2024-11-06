# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /src

# Install necessary system dependencies
RUN apt-get update
RUN apt-get -y install python3-pip python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0

# Copy the requirements file into the container
COPY ./services/v1/requirements.txt /src/services/v1/requirements.txt

# Create and activate a virtual environment, then install Python dependencies
RUN python3 -m venv services/v1/.venv && \
    . services/v1/.venv/bin/activate && \
    pip install --no-cache-dir -r /src/services/v1/requirements.txt

# Copy the application code into the container
COPY ./ /src

# Set environment variables to use the virtual environment
ENV PATH="/src/services/v1/.venv/bin:$PATH"

# Run FastAPI server using uvicorn when the container launches
CMD ["uvicorn", "services.v1.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]