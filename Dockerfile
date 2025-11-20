# Use a base Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot code
COPY img.py .

# Command to run the bot when the container starts
CMD ["python", "img.py"]
