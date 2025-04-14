import socket
import threading
import random
import time
import json
from algorit import LamportClock
from eleicao import Coordinator

class Sensor:
    def __init__(self, sensor_id, port):
        self.id = sensor_id
        self.data_port = port
        self.election_port = 5000 + sensor_id
        self.clock = LamportClock()
        self.data_lock = threading.Lock()
        self.nodes = [5001, 5002, 5003]
        self.coordinator = None
        self.known_coordinator = None
        
        # Dados climáticos iniciais
        with self.data_lock:
            self.data = {
                "temperature": round(random.uniform(20, 30), 2),
                "humidity": round(random.uniform(50, 80), 2),
                "pressure": round(random.uniform(980, 1020), 2),
                "last_updated": time.time()
            }
        
        # Inicia serviços
        self.start_services()
        
    def start_services(self):
        """Inicia todos os serviços do sensor"""
        services = [
            self.handle_data_requests,
            self.simulate_data_changes,
            self.monitor_nodes,
            self.start_election_service
        ]
        
        for service in services:
            threading.Thread(target=service, daemon=True).start()
        
    def start_election_service(self):
        """Inicia o serviço de eleição distribuída"""
        time.sleep(1)  # Espera inicialização dos outros serviços
        self.coordinator = Coordinator(self.id, self.election_port, [6001, 6002, 6003])
        self.coordinator.start()
        
    def simulate_data_changes(self):
        """Atualiza dados climáticos periodicamente"""
        while True:
            time.sleep(5)
            with self.data_lock:
                self.data = {
                    "temperature": round(random.uniform(20, 30), 2),
                    "humidity": round(random.uniform(50, 80), 2),
                    "pressure": round(random.uniform(980, 1020), 2),
                    "last_updated": time.time()
                }
            self.log(f"Dados atualizados: {self.data}")
            
    def handle_data_requests(self):
        """Processa requisições de dados climáticos"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('localhost', self.data_port))
            s.listen(5)
            self.log(f"Serviço de dados ativo na porta {self.data_port}")
            
            while True:
                conn, addr = None, None
                try:
                    conn, addr = s.accept()
                    raw_data = conn.recv(1024).decode()
                    
                    if not raw_data:
                        continue
                        
                    # Processa mensagem e atualiza relógio
                    response = self.process_message(raw_data)
                    conn.send(json.dumps(response).encode())
                    
                except Exception as e:
                    self.log(f"Erro na conexão: {str(e)}")
                finally:
                    if conn:
                        conn.close()
    
    def process_message(self, raw_data):
        """Processa mensagens recebidas com sincronização Lamport"""
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
                    "is_coordinator": self.is_current_coordinator(),
                    "coordinator_port": self.get_coordinator_port()
                }
                
        elif raw_data == "HEARTBEAT":
            return {"status": "ALIVE", "timestamp": self.clock.get_time()}
            
        elif raw_data.startswith("ALERT:"):
            alert = raw_data.split(":", 1)[1]
            self.log(f"ALERTA RECEBIDO: {alert}")
            return {"status": "alert_received"}
            
        return {"error": "invalid_request"}
    
    def monitor_nodes(self):
        """Monitora outros nós periodicamente"""
        while True:
            time.sleep(10)
            if self.is_current_coordinator():
                self.check_nodes_health()
            else:
                self.verify_coordinator()
    
    def check_nodes_health(self):
        """Verifica saúde dos nós (apenas coordenador)"""
        active_nodes = []
        for port in self.nodes:
            if port != self.data_port:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(2)
                        s.connect(('localhost', port))
                        s.send("HEARTBEAT".encode())
                        response = json.loads(s.recv(1024).decode())
                        if response.get("status") == "ALIVE":
                            active_nodes.append(port)
                except:
                    self.log(f"Nó {port} não respondeu")
        
        if len(active_nodes) < len(self.nodes) - 2:  # Limite de falhas
            self.log("Muitos nós inativos - enviando alerta!")
            self.broadcast_alert("AVISO: Múltiplas falhas detectadas")
    
    def verify_coordinator(self):
        """Verifica se o coordenador está ativo"""
        if not self.known_coordinator:
            return
            
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect(('localhost', self.known_coordinator))
                s.send("HEARTBEAT".encode())
                s.recv(1024)  # Espera resposta
        except:
            self.log("Coordenador não respondeu - iniciando eleição...")
            self.coordinator.start_election()
    
    def broadcast_alert(self, message):
        """Envia alertas para todos os nós"""
        for port in self.nodes:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.connect(('localhost', port))
                    s.send(f"ALERT:{message}".encode())
            except:
                continue
    
    def is_current_coordinator(self):
        """Verifica se este nó é o coordenador atual"""
        return self.coordinator and self.coordinator.is_current_coordinator()
    
    def get_coordinator_port(self):
        """Retorna a porta do coordenador atual"""
        return self.coordinator.get_current_coordinator() if self.coordinator else None
    
    def log(self, message):
        """Log formatado com timestamp"""
        print(f"[Sensor {self.id}][T{self.clock.get_time()}] {message}")

if __name__ == "__main__":
    print("\n=== Sistema de Sensores Climáticos Distribuídos ===")
    sensor_id = int(input("Informe o ID do sensor (1-3): ").strip())
    
    if sensor_id not in [1, 2, 3]:
        print("ID inválido! Deve ser 1, 2 ou 3")
        exit(1)
        
    sensor = Sensor(sensor_id, 5000 + sensor_id)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[Sensor {sensor_id}] Encerrando operação...")