FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /code

COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./main.py /code/main.py
COPY ./models.py /code/models.py
COPY ./receipt_processor.py /code/receipt_processor.py

RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /code
USER appuser

EXPOSE ${PORT}

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"] 