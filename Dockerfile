# Build com Podman:  podman build -t slm-rag-api:latest .
FROM python:3.12-slim

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

# OpenShift (SCC restricted-v2) roda com um UID ALEATÓRIO pertencente ao grupo 0.
# Tornar os arquivos graváveis pelo grupo root faz o app funcionar com qualquer UID.
RUN chgrp -R 0 /app && chmod -R g=u /app

EXPOSE 8000
# UID não-root apenas como default (o OpenShift atribui outro UID em runtime).
USER 1001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
