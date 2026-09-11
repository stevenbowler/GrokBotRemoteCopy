# Playwright + Chromium for Job 1 (agent86-qa-dev).
# Built on the Linux Docker host during deploy. Image has browsers.
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /job
COPY requirements.txt /job/requirements.txt
RUN pip install --no-cache-dir -r /job/requirements.txt
COPY . /job
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN mkdir -p /out /job/generated
CMD ["python", "/job/run_suite.py"]
