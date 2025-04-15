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
        """Inicializa o sensor com todas as configurações necessárias"""
        # Configurações básicas
        self.id = sensor_id
        self.hostname = f"sensor{sensor_id}"
        self.is_running = True
        
        # Configuração de portas
        self.data_port = int(os.getenv('DATA_PORT', 5000 + sensor_id))
        self.election_port = int(os.getenv('ELECTION_PORT', 6000 + sensor_id))
        self.grpc_port = int(os.getenv('GRPC_PORT', 50050 + sensor_id))
        
        # Componentes do sistema
        self.clock = LamportClock()
        self.data_lock = threading.Lock()
        self.election_log = []
        self.security = SecurityHandler(sensor_id)
        
        # Configuração da rede
        self.nodes = [
            {'id': 1, 'host': 'sensor1', 'data_port': 5001, 'election_port': 6001, 'status': 'unknown'},
            {'id': 2, 'host': 'sensor2', 'data_port': 5002, 'election_port': 6002, 'status': 'unknown'},
            {'id': 3, 'host': 'sensor3', 'data_port': 5003, 'election_port': 6003, 'status': 'unknown'}
        ]
        
        # Dados do sensor
        self.initialize_sensor_data()
        
        # Módulo de eleição
        self.initialize_election_module()
        
        # Inicia serviços
        self.start_services()

    # === INICIALIZAÇÃO ===
    
    def initialize_sensor_data(self):
        """Inicializa os dados do sensor com valores aleatórios"""
        with self.data_lock:
            self.data = {
                "temperature": round(random.uniform(20, 30), 2),
                "humidity": round(random.uniform(50, 80), 2),
                "pressure": round(random.uniform(980, 1020), 2),
                "last_updated": time.time(),
                "version": 1  # Novo campo para controle de versão
            }

    def initialize_election_module(self):
        """Configura o módulo de eleição distribuída"""
        election_nodes = [{'node_id': n['id'], 'host': n['host'], 'port': n['election_port']} 
                         for n in self.nodes]
        self.coordinator = Coordinator(self.id, self.election_port, election_nodes)

    # === SERVIÇOS PRINCIPAIS ===
    
    def start_services(self):
        """Inicia todos os serviços em threads separadas"""
        services = [
            self.handle_data_requests,    # Servidor de dados
            self.simulate_data_changes,   # Atualização periódica de dados
            self.monitor_nodes,           # Monitoramento da rede
            self.start_election_service,  # Serviço de eleição
            self.start_grpc_service,      # Servidor gRPC
            self.replicate_data_periodically,  # Novo: Replicação de dados
            self.periodic_snapshots       # Novo: Snapshots periódicos
        ]
        
        for service in services:
            threading.Thread(target=service, daemon=True).start()
        
        # Interface do usuário
        threading.Thread(target=self.interactive_menu, daemon=True).start()
        
        self.log(f"Sensor {self.id} iniciado na porta {self.data_port}")

    # === COMUNICAÇÃO E PROCESSAMENTO DE MENSAGENS ===
    
    def handle_data_requests(self):
        """Servidor principal para lidar com requisições de dados"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', self.data_port))
            s.listen(5)
            
            while self.is_running:
                try:
                    s.settimeout(1)
                    conn, addr = s.accept()
                    raw_data = conn.recv(4096).decode()
                    
                    if raw_data:
                        response = self.process_message(raw_data)
                        conn.send(json.dumps(response).encode())
                    conn.close()
                except socket.timeout:
                    continue
                except Exception as e:
                    self.log(f"Erro na conexão: {str(e)}")

    def process_message(self, raw_data):
        """Processa todos os tipos de mensagens recebidas"""
        self.clock.increment()
        
        # Mensagens originais
        if raw_data == "GET_DATA":
            return self.handle_get_data()
        elif raw_data == "HEARTBEAT":
            return {"status": "ALIVE", "timestamp": self.clock.get_time()}
        elif raw_data.startswith("ALERT:"):
            return self.handle_alert(raw_data)
        elif raw_data.startswith("TIMESTAMP:"):
            return self.handle_timestamp(raw_data)
            
        # Novas mensagens
        elif raw_data == "SNAPSHOT":
            return self.take_snapshot()
        elif raw_data.startswith("REPLICATE:"):
            return self.handle_replication(raw_data)
        elif raw_data == "GET_NODES_STATUS":
            return {"nodes": self.nodes}
            
        return {"error": "invalid_request"}

    # === MÉTODOS ORIGINAIS DE PROCESSAMENTO ===
    
    def handle_get_data(self):
        """Responde a requisições GET_DATA"""
        with self.data_lock:
            return {
                "sensor_id": self.id,
                "data": self.data,
                "timestamp": self.clock.get_time(),
                "is_coordinator": self.coordinator.is_current_coordinator(),
                "coordinator": self.coordinator.coordinator
            }

    def handle_alert(self, raw_data):
        """Processa mensagens de alerta"""
        alert = raw_data.split(":", 1)[1]
        self.log(f"ALERTA: {alert}")
        self.election_log.append(f"[{time.ctime()}] Alerta recebido: {alert}")
        return {"status": "alert_received"}

    def handle_timestamp(self, raw_data):
        """Atualiza o clock lógico"""
        received_time = int(raw_data.split(":")[1])
        self.clock.update(received_time)
        return {"status": "timestamp_updated"}

    # === NOVOS MÉTODOS DE PROCESSAMENTO ===
    
    def take_snapshot(self):
        """Captura um snapshot do estado atual"""
        with self.data_lock:
            return {
                'sensor_id': self.id,
                'data': self.data.copy(),
                'timestamp': self.clock.get_time(),
                'version': self.data['version']
            }

    def handle_replication(self, raw_data):
        """Processa dados replicados de outros nós"""
        encrypted_data = raw_data.split(":", 1)[1]
        try:
            decrypted_data = self.security.decrypt(encrypted_data)
            with self.data_lock:
                if decrypted_data.get('version', 0) > self.data['version']:
                    self.data.update(decrypted_data)
                    self.data['last_updated'] = time.time()
                    return {"status": "ACK"}
            return {"status": "NACK"}
        except Exception as e:
            self.log(f"Erro na replicação: {str(e)}")
            return {"status": "ERROR"}

    # === REPLICAÇÃO DE DADOS ===
    
    def replicate_data_periodically(self):
        """Replica dados periodicamente para outros nós"""
        while self.is_running:
            time.sleep(15)
            if self.coordinator.is_current_coordinator():
                with self.data_lock:
                    self.replicate_data(self.data.copy())

    def replicate_data(self, data):
        """Envia dados para outros nós"""
        success_count = 0
        encrypted_data = self.security.encrypt(data)
        
        for node in self.nodes:
            if node['id'] != self.id:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(2)
                        s.connect((node['host'], node['data_port']))
                        s.send(f"REPLICATE:{encrypted_data}".encode())
                        if s.recv(1024).decode() == "ACK":
                            success_count += 1
                            node['status'] = 'online'
                except:
                    node['status'] = 'offline'
        
        return success_count >= len(self.nodes) // 2

    # === MONITORAMENTO E TOLERÂNCIA A FALHAS ===
    
    def monitor_nodes(self):
        """Monitora o status dos nós da rede"""
        while self.is_running:
            time.sleep(10)
            if self.coordinator.is_current_coordinator():
                self.check_nodes_health()
            else:
                self.verify_coordinator()

    def check_nodes_health(self):
        """Verifica a saúde dos nós (como coordenador)"""
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
        """Verifica se o coordenador está respondendo"""
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

    # === INTERFACE DO USUÁRIO ===
    
    def interactive_menu(self):
        """Menu interativo principal"""
        menu_options = {
            "1": ("Visualizar dados deste sensor", self.show_local_data),
            "2": ("Consultar sensor específico", self.query_specific_sensor),
            "3": ("Visualizar todos os sensores", self.show_all_sensors),
            "4": ("Informações de eleição", self.show_election_info),
            "5": ("Forçar nova eleição", self.force_election),
            "6": ("Status da rede", self.show_network_status),
            "7": ("Capturar snapshot global", self.capture_global_snapshot),
            "8": ("Sair", self.stop)
        }
        
        while self.is_running:
            try:
                print("\n=== MENU PRINCIPAL ===")
                for key, (desc, _) in menu_options.items():
                    print(f"{key}. {desc}")
                
                choice = input("\nEscolha uma opção: ").strip()
                
                if choice in menu_options:
                    menu_options[choice][1]()
                    
            except KeyboardInterrupt:
                print("\nUse a opção 8 para sair corretamente.")
            except Exception as e:
                print(f"Erro: {str(e)}")

    # === MÉTODOS AUXILIARES ===
    
    def log(self, message):
        """Registra mensagens de log"""
        print(f"[Sensor {self.id}][T{self.clock.get_time()}] {message}")

    def stop(self):
        """Encerra o sensor corretamente"""
        self.is_running = False
        self.coordinator.stop()
        print(f"\n🛑 Sensor {self.id} encerrado")

if __name__ == "__main__":
    print("\n=== SISTEMA DE SENSORES DISTRIBUÍDOS ===  SISTEMA PARA USO EDUCACIONAL")
    sensor_id = int(os.getenv('NODE_ID', input("ID do sensor (1-3): ").strip()))
    
    if sensor_id not in [1, 2, 3]:
        print("⚠️ ID deve ser 1, 2 ou 3")
        exit(1)
        
    sensor = Sensor(sensor_id)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sensor.stop()