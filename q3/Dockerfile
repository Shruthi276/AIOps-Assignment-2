FROM python:3.11-slim
WORKDIR /app
COPY validator.py .
COPY shards/ /data/
ENTRYPOINT ["python3", "validator.py"]
