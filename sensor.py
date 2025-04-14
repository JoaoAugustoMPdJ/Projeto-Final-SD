import socket
import threading
import random
import time
import json
import os
from algorit import LamportClock
from eleicao import Coordinator
from multi import iniciar_grpc

class Sensor:
    def __init__(self, sensor_id):
        self.id = sensor_id
        self.hostname = f"sensor{sensor_id}"
        
        # Portas configuráveis por variáveis de ambiente
        self.data_port = int(os.getenv('DATA_PORT', 5000 + sensor_id))
        self.election_port = int(os.getenv('ELECTION_PORT', 6000 + sensor_id))
        self.grpc_port = int(os.getenv('GRPC_PORT', 50050 + sensor_id))
        
        self.clock = LamportClock()
        self.data_lock = threading.Lock()
        self.is_running = True
        
        # Configuração dos nós
        self.nodes = [
            {'id': 1, 'host': 'sensor1', 'data_port': 5001, 'election_port': 6001},
            {'id': 2, 'host': 'sensor2', 'data_port': 5002, 'election_port': 6002},
            {'id': 3, 'host': 'sensor3', 'data_port': 5003, 'election_port': 6003}
        ]
        
        # Dados climáticos simulados
        with self.data_lock:
            self.data = self.generate_sensor_data()
        
        # Serviço de eleição
        election_nodes = [{'node_id': n['id'], 'host': n['host'], 'port': n['election_port']} for n in self.nodes]
        self.coordinator = Coordinator(self.id, self.election_port, election_nodes)
        
        # Inicia todos os serviços
        self.start_services()

    def generate_sensor_data(self):
        """Gera dados climáticos aleatórios"""
        return {
            "temperature": round(random.uniform(20, 30), 2),
            "humidity": round(random.uniform(50, 80), 2),
            "pressure": round(random.uniform(980, 1020), 2),
            "last_updated": time.time()
        }

    def start_services(self):
        """Inicia todos os serviços do sensor"""
        services = [
            self.handle_data_requests,
            self.simulate_data_changes,
            self.monitor_nodes,
            self.start_election_service,
            self.start_grpc_service
        ]
        
        for service in services:
            threading.Thread(target=service, daemon=True).start()
        
        print(f"Sensor {self.id} iniciado na porta {self.data_port}")

    def start_grpc_service(self):
        """Inicia o servidor gRPC"""
        iniciar_grpc(self)

    def start_election_service(self):
        """Inicia o serviço de eleição"""
        time.sleep(1)  # Espera outros serviços iniciarem
        self.coordinator.start()
        print(f"  Serviço de eleição iniciado na porta {self.election_port}")

    def simulate_data_changes(self):
        """Atualiza dados climáticos periodicamente"""
        while self.is_running:
            time.sleep(5)
            with self.data_lock:
                self.data = self.generate_sensor_data()
            self.log(f"Dados atualizados: {self.data}")

    def handle_data_requests(self):
        """Processa requisições de dados climáticos"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', self.data_port))
            s.listen(5)
            self.log(f" Serviço de dados ativo na porta {self.data_port}")
            
            while self.is_running:
                try:
                    s.settimeout(1)
                    conn, addr = s.accept()
                    raw_data = conn.recv(1024).decode()
                    
                    if not raw_data:
                        conn.close()
                        continue
                        
                    response = self.process_message(raw_data)
                    conn.send(json.dumps(response).encode())
                    conn.close()
                except socket.timeout:
                    continue
                except Exception as e:
                    self.log(f"Erro na conexão: {str(e)}")
                    if 'conn' in locals():
                        conn.close()

    def process_message(self, raw_data):
        """Processa mensagens recebidas"""
        self.clock.increment()
        
        if raw_data.startswith("TIMESTAMP:"):
            received_time = int(raw_data.split(":")[1])
            self.clock.update(received_time)
            return {"status": "timestamp_updated"}
            
        elif raw_data == "GET_DATA":
            with self.data_lock:
                return {
                    "sensor_id": self.id,
                    "data": self.data,
                    "timestamp": self.clock.get_time(),
                    "is_coordinator": self.coordinator.is_current_coordinator(),
                    "coordinator": self.coordinator.coordinator
                }
                
        elif raw_data == "HEARTBEAT":
            return {"status": "ALIVE", "timestamp": self.clock.get_time()}
            
        elif raw_data.startswith("ALERT:"):
            alert = raw_data.split(":", 1)[1]
            self.log(f" ALERTA RECEBIDO: {alert}")
            return {"status": "alert_received"}
            
        return {"error": "invalid_request"}

    def monitor_nodes(self):
        """Monitora outros nós periodicamente"""
        while self.is_running:
            time.sleep(10)
            if self.coordinator.is_current_coordinator():
                self.check_nodes_health()
            else:
                self.verify_coordinator()

    def check_nodes_health(self):
        """Verifica saúde dos nós (apenas coordenador)"""
        active_nodes = []
        for node in self.nodes:
            if node['id'] != self.id:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(2)
                        s.connect((node['host'], node['data_port']))
                        s.send("HEARTBEAT".encode())
                        response = json.loads(s.recv(1024).decode())
                        if response.get("status") == "ALIVE":
                            active_nodes.append(node['id'])
                except Exception as e:
                    self.log(f" Nó {node['id']} não respondeu: {str(e)}")
        
        if len(active_nodes) < len(self.nodes) - 2:
            self.log(" Muitos nós inativos - enviando alerta!")
            self.broadcast_alert("AVISO: Múltiplas falhas detectadas")

    def verify_coordinator(self):
        """Verifica se o coordenador está ativo"""
        if not self.coordinator.coordinator:
            return
            
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                coord = self.coordinator.coordinator
                s.connect((coord['host'], coord['port']))
                s.send("PING".encode())
                if s.recv(1024).decode() != "PONG":
                    raise Exception("Resposta inválida")
        except Exception as e:
            self.log(f" Coordenador não respondeu: {str(e)}")
            self.coordinator.start_election()

    def broadcast_alert(self, message):
        """Envia alertas para todos os nós"""
        for node in self.nodes:
            if node['id'] != self.id:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1)
                        s.connect((node['host'], node['data_port']))
                        s.send(f"ALERT:{message}".encode())
                except:
                    continue

    def log(self, message):
        """Log formatado com timestamp"""
        print(f"[Sensor {self.id}][T{self.clock.get_time()}] {message}")

    def stop(self):
        """Para todos os serviços do sensor"""
        self.is_running = False
        self.coordinator.stop()

if __name__ == "__main__":
    print("\n===  Sistema de Sensores Climáticos Distribuídos ===")
    sensor_id = int(os.getenv('NODE_ID', input("Informe o ID do sensor (1-3): ").strip()))
    
    if sensor_id not in [1, 2, 3]:
        print("ID inválido! Deve ser 1, 2 ou 3")
        exit(1)
        
    sensor = Sensor(sensor_id)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sensor.stop()
        print(f"\n[Sensor {sensor_id}]  Encerrando operação...")