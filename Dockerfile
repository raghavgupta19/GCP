# Use lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Expose port Cloud Run expects
EXPOSE 8080

# Run Gunicorn server
CMD ["gunicorn", "-b", ":8080", "main:app"]
