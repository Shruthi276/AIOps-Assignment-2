FROM python:3.11-slim AS builder

WORKDIR /build

COPY app/requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.11-slim

WORKDIR /app

ENV APP_VERSION=1.1

COPY app /app
COPY --from=builder /install /usr/local

EXPOSE 5000

CMD ["python", "app.py"]
