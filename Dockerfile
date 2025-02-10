# Use an official Python 3.11 image
FROM python:3.11

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

# Expose Flask port
EXPOSE 5000

# Run both extract_map.py (for data) and app.py (Flask)
CMD ["bash", "-c", "python src/extract_map.py && python src/app.py"]
