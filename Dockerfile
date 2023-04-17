FROM python:3.11-slim-bullseye

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

RUN addgroup --gid 1000 --system app \
    && adduser --uid 1000 --system --no-create-home --shell=/bin/false --disabled-password --group app \
    && mkdir /app \
    && chown -R 1000:1000 /app

COPY --chown=app:app ./rdt_search /app
USER app
WORKDIR /app
RUN mkdir /data && chown -R 1000:1000 /data

CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=8000"]
