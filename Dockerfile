FROM python:3.11-slim

WORKDIR /app

# We only use Pillow, which does not require these heavy system dependencies.

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
