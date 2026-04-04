FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir vaderSentiment Pillow

COPY core/ core/
COPY parsers/ parsers/
COPY watcher/ watcher/
COPY server/ server/
COPY sprites/ sprites/
COPY __main__.py .

ENV CLAUDE_PROJECTS_PATH=/data/projects

EXPOSE 9400

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9400/health')"

ENTRYPOINT ["python", "__main__.py"]
