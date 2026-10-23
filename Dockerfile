FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 GRADIO_ANALYTICS_ENABLED=False GRADIO_SERVER_NAME=0.0.0.0 GRADIO_SERVER_PORT=7860
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY requirements.txt pyproject.toml ./
COPY src ./src
COPY app ./app
COPY configs ./configs
COPY gradio_app.py ./
RUN python -m pip install --no-cache-dir -r requirements.txt && python -m pip install --no-cache-dir --no-deps .
RUN useradd --create-home --uid 10001 demo && mkdir -p /tmp/gradio && chown -R demo:demo /tmp/gradio /workspace
USER demo
EXPOSE 7860
CMD ["python","-m","app.hosted"]
