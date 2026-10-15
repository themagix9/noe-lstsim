FROM python:3.12-slim
LABEL org.opencontainers.image.source="https://github.com/themagix9/noe-lstsim"
LABEL org.opencontainers.image.description="Niederösterreich dispatch simulation prototype"
ENV OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
RUN pip install --no-cache-dir piper-tts==1.3.0 \
    && python -m piper.download_voices --download-dir /opt/voices de_DE-thorsten-high de_DE-mls-medium
WORKDIR /app
COPY app/ /app/
RUN mkdir -p /data && chown -R 10001:10001 /data /app
ENV DATA_DIR=/data PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=2)" || exit 1
CMD ["python", "server.py"]
