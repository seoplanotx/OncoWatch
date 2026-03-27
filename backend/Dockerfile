FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
COPY app ./app
COPY scripts ./scripts

RUN pip install --no-cache-dir -e .

EXPOSE 17845

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "17845"]
