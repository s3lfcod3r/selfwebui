FROM python:3.12-slim
# Oberfläche "Bonsai & Qwen Image Generator": statische Dateien plus config.json aus der Umgebung
RUN useradd -r -u 10001 studio
WORKDIR /app
COPY index.html app.js studio.css tokens.css components.css shield.png server.py ./
COPY fonts ./fonts
USER studio
ENV PORT=8112 STUDIO_API=http://192.168.1.103:8111 STUDIO_BONSAI=http://192.168.1.103:8085
EXPOSE 8112
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8112/config.json',timeout=2)"
CMD ["python", "server.py"]
