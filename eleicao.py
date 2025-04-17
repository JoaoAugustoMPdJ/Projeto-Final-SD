import socket
import threading
import time
import os
from algorit import LamportClock

class Coordinator:
    def __init__(self, node_id, port, all_nodes):
        self.node_id = node_id
        self.port = port
        self.all_nodes = all_nodes  # Lista de dicionários com host e port
        self.clock = LamportClock()
        self.coordinator = None
        self.election_in_progress = False
        self.is_alive = True
        
    def start(self):
        """Inicia os serviços do nó"""
        threading.Thread(target=self.listen_for_messages, daemon=True).start()
        threading.Thread(target=self.monitor_coordinator, daemon=True).start()
        print(f" Nó {self.node_id} iniciado na porta {self.port}")
        
    def monitor_coordinator(self):
        """Verifica periodicamente se o coordenador está ativo"""
        while self.is_alive:
            time.sleep(10)
            if self.coordinator and not self.is_current_coordinator():
                if not self.check_node_status(self.coordinator['host'], self.coordinator['port']):
                    print(f" Coordenador {self.coordinator['node_id']} inativo. Iniciando eleição...")
                    self.start_election()

    def is_current_coordinator(self):
        """Verifica se este nó é o coordenador atual"""
        return self.coordinator and self.coordinator['node_id'] == self.node_id

    def check_node_status(self, host, port):
        """Verifica se um nó está respondendo"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((host, port))
                s.send("PING".encode())
                return s.recv(1024).decode() == "PONG"
        except:
            return False

    def start_election(self):
        """Inicia uma eleição usando o algoritmo Bully"""
        if self.election_in_progress:
            return
            
        self.election_in_progress = True
        print(f" Nó {self.node_id} iniciando eleição...")
        
        # Encontra nós com ID maior
        higher_nodes = [n for n in self.all_nodes if n['node_id'] > self.node_id]
        
        if not higher_nodes:
            # Não há nós superiores, este nó se torna coordenador
            self.declare_victory()
        else:
            # Envia mensagem de ELEICAO para nós superiores
            responses = []
            for node in higher_nodes:
                if self.send_election_message(node['host'], node['port']):
                    responses.append(node)
            
            # Se não receber respostas em 3 segundos, declara vitória
            time.sleep(3)
            if not responses:
                self.declare_victory()
                
        self.election_in_progress = False

    def send_election_message(self, host, port):
        """Envia mensagem de ELEICAO para um nó"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((host, port))
                s.send("ELECTION".encode())
                return s.recv(1024).decode() == "ALIVE"
        except:
            return False

    def declare_victory(self):
        """Declara este nó como o novo coordenador"""
        self.coordinator = {
            'node_id': self.node_id,
            'host': f"sensor{self.node_id}",
            'port': self.port
        }
        print(f" Nó {self.node_id} é o novo coordenador!")
        
        # Notifica todos os nós inferiores
        lower_nodes = [n for n in self.all_nodes if n['node_id'] < self.node_id]
        for node in lower_nodes:
            self.send_coordinator_message(node['host'], node['port'])

    def send_coordinator_message(self, host, port):
        """Envia mensagem de COORDENADOR para um nó"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((host, port))
                s.send(f"COORDINATOR {self.node_id} {self.port}".encode())
        except Exception as e:
            print(f"Erro ao enviar mensagem de coordenador: {str(e)}")

    def listen_for_messages(self):
        """Ouve mensagens de outros nós"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', self.port))
            s.listen()
            print(f" Nó {self.node_id} ouvindo na porta {self.port}")
            
            while self.is_alive:
                try:
                    s.settimeout(1)
                    conn, addr = s.accept()
                    data = conn.recv(1024).decode()
                    
                    if data == "ELECTION":
                        print(f" Nó {self.node_id} recebeu ELEICAO de {addr}")
                        conn.send("ALIVE".encode())
                        if not self.election_in_progress:
                            self.start_election()
                            
                    elif data.startswith("COORDINATOR"):
                        _, node_id, port = data.split()
                        self.coordinator = {
                            'node_id': int(node_id),
                            'host': f"sensor{node_id}",
                            'port': int(port)
                        }
                        print(f"Nó {self.node_id} reconhece novo coordenador: Nó {node_id}")
                        
                    elif data == "PING":
                        conn.send("PONG".encode())
                        
                    conn.close()
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Erro na conexão: {str(e)}")

    def stop(self):
        """Para os serviços do nó"""
        self.is_alive = False

if __name__ == "__main__":
    node_id = int(os.getenv('NODE_ID', 1))
    election_port = int(os.getenv('ELECTION_PORT', 6000 + node_id))
    
    # Configuração dos nós para eleição
    all_nodes = [
        {'node_id': 1, 'host': 'sensor1', 'port': 6001},
        {'node_id': 2, 'host': 'sensor2', 'port': 6002},
        {'node_id': 3, 'host': 'sensor3', 'port': 6003}
    ]
    
    coordinator = Coordinator(node_id, election_port, all_nodes)
    coordinator.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        coordinator.stop()
