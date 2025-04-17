import socket
import threading
import random
import time
import json
import os
from algorit import LamportClock
from eleicao import Coordinator
from multi import iniciar_grpc
from security import SecurityHandler

class Sensor:
    def __init__(self, sensor_id):
        self.id = sensor_id
        self.hostname = f"sensor{sensor_id}"
        self.is_running = True
        
        # Configurações de portas
        self.data_port = int(os.getenv('DATA_PORT', 5000 + sensor_id))
        self.election_port = int(os.getenv('ELECTION_PORT', 6000 + sensor_id))
        self.grpc_port = int(os.getenv('GRPC_PORT', 50050 + sensor_id))
        
        # Componentes do sistema
        self.clock = LamportClock()
        self.data_lock = threading.Lock()
        self.election_log = []
        self.security = SecurityHandler(sensor_id, os.getenv('SECURITY_KEY'))
        
        # Configuração da rede
        self.nodes = [
            {'id': 1, 'host': 'sensor1', 'data_port': 5001, 'election_port': 6001, 'status': 'unknown'},
            {'id': 2, 'host': 'sensor2', 'data_port': 5002, 'election_port': 6002, 'status': 'unknown'},
            {'id': 3, 'host': 'sensor3', 'data_port': 5003, 'election_port': 6003, 'status': 'unknown'}
        ]
        
        # Inicialização dos dados
        self.initialize_sensor_data()
        
        # Módulo de eleição
        self.initialize_election_module()
        
        # Inicia todos os serviços
        self.start_services()

    def initialize_sensor_data(self):
        with self.data_lock:
            self.data = {
                "temperature": round(random.uniform(15.0, 35.0), 1),  # Faixa ampliada
                "humidity": round(random.uniform(30.0, 90.0), 1),     # Valores mais variados
                "pressure": round(random.uniform(970.0, 1030.0), 1),  # Precisão decimal
                "last_updated": time.time(),  # Timestamp atual
                "version": 1
            }

    def initialize_election_module(self):
        election_nodes = [{'node_id': n['id'], 'host': n['host'], 'port': n['election_port']} 
                         for n in self.nodes]
        self.coordinator = Coordinator(self.id, self.election_port, election_nodes)

    def start_services(self):
        services = [
            self.handle_data_requests,
            self.simulate_data_changes,
            self.monitor_nodes,
            self.start_election_service,
            self.start_grpc_service,
            self.replicate_data_periodically
        ]
        
        for service in services:
            threading.Thread(target=service, daemon=True).start()

    def simulate_data_changes(self):
        """Atualiza dados com variações graduais e realistas"""
        while self.is_running:
            time.sleep(random.uniform(4, 6))  # Intervalo entre 4-6 segundos
        
        with self.data_lock:
            # Garante valores iniciais válidos
            current_temp = self.data.get('temperature', 20.0)
            current_humidity = self.data.get('humidity', 50.0)
            current_pressure = self.data.get('pressure', 1013.0)
            
            new_data = {
                "temperature": current_temp + random.uniform(-1.5, 1.5),
                "humidity": current_humidity + random.uniform(-3.0, 3.0),
                "pressure": current_pressure + random.uniform(-2.0, 2.0),
                "last_updated": time.time(),
                "version": self.data['version'] + 1
            }
            
            # Aplica limites físicos
            new_data['temperature'] = max(-10.0, min(45.0, new_data['temperature']))
            new_data['humidity'] = max(0.0, min(100.0, new_data['humidity']))
            new_data['pressure'] = max(950.0, min(1050.0, new_data['pressure']))
            
            # Atualiza com arredondamento
            self.data = {k: round(v, 1) for k, v in new_data.items()}

    def start_grpc_service(self):
        iniciar_grpc(self)

    def start_election_service(self):
        time.sleep(2)
        self.coordinator.start()

    def handle_data_requests(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', self.data_port))
            s.listen(5)
            
            while self.is_running:
                try:
                    s.settimeout(1)
                    conn, addr = s.accept()
                    raw_data = conn.recv(4096).decode().strip()
                    
                    if raw_data:
                        try:
                            decrypted_data = self.security.decrypt(raw_data)
                            response = self.process_message(decrypted_data)
                            encrypted_response = self.security.encrypt(json.dumps(response))
                            conn.send(encrypted_response.encode())
                        except Exception as e:
                            self.log(f"Erro de segurança: {str(e)}")
                            conn.send(json.dumps({"error": "security_error"}).encode())
                    conn.close()
                except socket.timeout:
                    continue
                except Exception as e:
                    self.log(f"Erro na conexão: {str(e)}")

    def process_message(self, raw_data):
        self.clock.increment()
        
        if raw_data == "GET_DATA":
            return self.handle_get_data()
        elif raw_data == "HEALTHCHECK":
            return self.handle_healthcheck()
        elif raw_data == "HEARTBEAT":
            return {"status": "ALIVE", "timestamp": self.clock.get_time()}
        elif raw_data.startswith("ALERT:"):
            return self.handle_alert(raw_data)
        elif raw_data.startswith("TIMESTAMP:"):
            return self.handle_timestamp(raw_data)
        elif raw_data == "SNAPSHOT":
            return self.take_snapshot()
        elif raw_data.startswith("REPLICATE:"):
            return self.handle_replication(raw_data)
        elif raw_data == "START_ELECTION":
            self.coordinator.start_election()
            return {"status": "election_started"}
            
        return {"error": "invalid_request"}

    def handle_healthcheck(self):
        return {
            "status": "ALIVE",
            "timestamp": time.time(),
            "sensor_id": self.id,
            "version": self.data['version']
        }

    def handle_get_data(self):
        with self.data_lock:
          return {
            "sensor_id": self.id,
            "data": {
                "temperature": self.data['temperature'],
                "humidity": self.data['humidity'],
                "pressure": self.data['pressure'],
                "last_updated": self.data['last_updated'],
                "version": self.data['version']
            },
            "timestamp": self.clock.get_time(),
            "is_coordinator": self.coordinator.is_current_coordinator(),
            "coordinator": self.coordinator.coordinator
        }

    def handle_alert(self, raw_data):
        alert = raw_data.split(":", 1)[1]
        self.log(f"ALERTA: {alert}")
        self.election_log.append(f"[{time.ctime()}] Alerta recebido: {alert}")
        return {"status": "alert_received"}

    def handle_timestamp(self, raw_data):
        received_time = int(raw_data.split(":")[1])
        self.clock.update(received_time)
        return {"status": "timestamp_updated"}

    def take_snapshot(self):
        with self.data_lock:
            return {
                'sensor_id': self.id,
                'data': self.data.copy(),
                'timestamp': self.clock.get_time(),
                'version': self.data['version']
            }

    def handle_replication(self, raw_data):
        encrypted_data = raw_data.split(":", 1)[1]
        try:
            decrypted_data = json.loads(self.security.decrypt(encrypted_data))
            
            with self.data_lock:
                if decrypted_data.get('version', 0) > self.data['version']:
                    self.data.update(decrypted_data)
                    self.data['last_updated'] = time.time()
                    return {"status": "ACK"}
            return {"status": "NACK"}
        except Exception as e:
            self.log(f"Erro na replicação: {str(e)}")
            return {"status": "ERROR"}

    def replicate_data_periodically(self):
        while self.is_running:
            time.sleep(15)
            if self.coordinator.is_current_coordinator():
                with self.data_lock:
                    data_to_replicate = self.data.copy()
                
                success = self.replicate_data(data_to_replicate)
                if success:
                    self.log("Dados replicados com sucesso para a maioria dos nós")
                else:
                    self.log("Falha ao replicar dados para a maioria dos nós")

    def replicate_data(self, data):
        success_count = 0
        encrypted_data = self.security.encrypt(json.dumps(data))
        
        for node in self.nodes:
            if node['id'] == self.id:
                continue
                
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2)
                    s.connect((node['host'], node['data_port']))
                    s.send(f"REPLICATE:{encrypted_data}".encode())
                    response = json.loads(s.recv(1024).decode())
                    if response.get("status") == "ACK":
                        success_count += 1
                        node['status'] = 'online'
            except Exception as e:
                node['status'] = 'offline'
                self.log(f"Falha na replicação para nó {node['id']}: {str(e)}")
                
        return success_count >= len(self.nodes) // 2  # Quorum

    def monitor_nodes(self):
        while self.is_running:
            time.sleep(10)
            if self.coordinator.is_current_coordinator():
                self.check_nodes_health()
            else:
                self.verify_coordinator()

    def check_nodes_health(self):
        active_nodes = 0
        for node in self.nodes:
            if node['id'] == self.id:
                active_nodes += 1
                continue
                
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2)
                    s.connect((node['host'], node['data_port']))
                    s.send("HEARTBEAT".encode())
                    if json.loads(s.recv(1024).decode()).get("status") == "ALIVE":
                        active_nodes += 1
                        node['status'] = 'online'
            except:
                node['status'] = 'offline'
                
        if active_nodes < len(self.nodes) - 1:
            self.broadcast_alert("AVISO: Múltiplas falhas detectadas")

    def verify_coordinator(self):
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
            self.log(f"Coordenador inativo: {str(e)}")
            self.coordinator.start_election()

    def broadcast_alert(self, message):
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
        print(f"[Sensor {self.id}][T{self.clock.get_time()}] {message}")

    def stop(self):
        self.is_running = False
        self.coordinator.stop()
        print(f"\n Sensor {self.id} encerrado")

if __name__ == "__main__":
    print("\n=== SISTEMA DE SENSORES DISTRIBUÍDOS ===  SISTEMA PARA USO EDUCACIONAL")
    sensor_id = int(os.getenv('NODE_ID'))
    
    if sensor_id not in [1, 2, 3]:
        print(" ID deve ser 1, 2 ou 3")
        exit(1)
        
    sensor = Sensor(sensor_id)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sensor.stop()
