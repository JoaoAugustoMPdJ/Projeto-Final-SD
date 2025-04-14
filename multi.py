# grpc_handler.py - Adicione este arquivo novo
import grpc
from concurrent import futures
import time
import proto_pb2 as pb2
import proto_pb2_grpc as pb2_grpc

class SensorGRPC(pb2_grpc.SensorServiceServicer):
    def __init__(self, sensor):
        self.sensor = sensor  # Recebe seu sensor original

    def GetData(self, request, context):
        return pb2.DadosSensor(
            id=self.sensor.id,
            temperatura=self.sensor.temperatura,
            umidade=self.sensor.umidade,
            timestamp=self.sensor.relogio_lamport
        )

def iniciar_grpc(sensor):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_SensorServiceServicer_to_server(SensorGRPC(sensor), server)
    server.add_insecure_port(f'[::]:{50051 + sensor.id}')  # Porta única por sensor
    server.start()
    
    print(f"Servidor gRPC do sensor {sensor.id} rodando na porta {50051 + sensor.id}")
    try:
        while True:
            time.sleep(3600)  # Mantém o servidor ativo
    except KeyboardInterrupt:
        server.stop(0)