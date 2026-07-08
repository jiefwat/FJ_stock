FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8501 \
    STOCK_TS_PROVIDER=sample \
    STOCK_TS_PUBLIC_READONLY=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY data/portfolio ./data/portfolio
RUN python -m pip install --no-cache-dir -e .

EXPOSE 8501
CMD ["python", "-m", "stock_ts.web"]
