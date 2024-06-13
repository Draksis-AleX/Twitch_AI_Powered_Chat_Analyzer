
FROM python:3.9-slim

WORKDIR /app

# Installa i pacchetti necessari all'applicazione
RUN apt-get update && apt-get install -y \
    gcc \
    libc-dev \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copia i file di requisiti e installa le dipendenze
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto del codice dell'applicazione nel container
COPY . .

EXPOSE 5000

CMD python web_interface.py

