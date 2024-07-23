FROM python:3.12.3-alpine

WORKDIR /app

# Handle dependencies first so the layers are cached
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Add src to Python path
ENV PYTHONPATH=/app/src

# Expose the port the app runs on
EXPOSE 8080

# Run the application
#CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
CMD ["python", "main.py"]