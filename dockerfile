FROM python:alpine@sha256:18159b2be11db91f84b8f8f655cd860f805dbd9e49a583ddaac8ab39bf4fe1a7

WORKDIR /app

# Copia todos os arquivos necessários explicitamente
COPY algorit.py .
COPY eleicao.py .
COPY multi.py .
COPY proto.proto .
COPY proto_pb2.py .
COPY proto_pb2_grpc.py .
COPY security.py .
COPY sensor.py .
COPY cliente.py .
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto.proto

# Adicione esta verificação de saúde
HEALTHCHECK --interval=5s --timeout=3s \
  CMD python -c "import socket; s = socket.socket(); s.connect(('localhost', ${DATA_PORT:-5000})) or exit(1)" || exit 1

  # Comando padrão (será sobrescrito pelo docker-compose)
CMD ["python", "cliente.py"]