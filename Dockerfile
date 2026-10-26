# 1. Use an official Python runtime as a parent image
FROM python:3.12-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy your dependencies file and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of your application code
COPY . .

# 5. Tell Uvicorn how to run your app
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
# CMD ["python", "app.py"]