import socket
import threading
import time
from algorit import LamportClock

class Coordinator:
    def __init__(self, node_id, port, all_ports):
        self.node_id = node_id
        self.port = port
        self.all_ports = all_ports  # Lista de portas de todos os nós
        self.clock = LamportClock()
        self.coordinator = None
        self.election_in_progress = False
        
    def start(self):
        """Inicia os serviços do nó"""
        threading.Thread(target=self.listen_for_messages).start()
        threading.Thread(target=self.monitor_coordinator).start()
        
    def monitor_coordinator(self):
        """Verifica periodicamente se o coordenador está ativo"""
        while True:
            time.sleep(10)  # Verifica a cada 10 segundos
            if self.coordinator and self.coordinator != self.port:
                if not self.is_node_alive(self.coordinator):
                    print(f"Coordinator {self.coordinator} parece estar inativo. Iniciando eleição...")
                    self.start_election()

    def is_node_alive(self, port):
        """Verifica se um nó está respondendo"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect(('localhost', port))
                s.send("PING".encode())
                return True
        except:
            return False

    def start_election(self):
        """Inicia uma eleição usando o algoritmo Bully"""
        if self.election_in_progress:
            return
            
        self.election_in_progress = True
        print(f"Nó {self.node_id} iniciando eleição...")
        
        higher_nodes = [p for p in self.all_ports if p > self.port]
        
        if not higher_nodes:
            # Não há nós superiores, este nó se torna coordenador
            self.declare_victory()
        else:
            # Envia mensagem de ELEICAO para nós superiores
            responses = []
            for port in higher_nodes:
                if self.send_election_message(port):
                    responses.append(port)
            
            # Se não receber respostas em 3 segundos, declara vitória
            time.sleep(3)
            if not responses:
                self.declare_victory()
                
        self.election_in_progress = False

    def send_election_message(self, port):
        """Envia mensagem de ELEICAO para um nó"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect(('localhost', port))
                s.send("ELECTION".encode())
                return True
        except:
            return False

    def declare_victory(self):
        """Declara este nó como o novo coordenador"""
        self.coordinator = self.port
        print(f"🎉 Nó {self.node_id} é o novo coordenador!")
        
        # Notifica todos os nós inferiores
        lower_nodes = [p for p in self.all_ports if p < self.port]
        for port in lower_nodes:
            self.send_coordinator_message(port)

    def send_coordinator_message(self, port):
        """Envia mensagem de COORDENADOR para um nó"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('localhost', port))
                s.send(f"COORDINATOR {self.port}".encode())
        except:
            pass

    def listen_for_messages(self):
        """Ouve mensagens de outros nós"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', self.port))
            s.listen()
            print(f"Nó {self.node_id} ouvindo na porta {self.port}")
            
            while True:
                conn, addr = s.accept()
                data = conn.recv(1024).decode()
                
                if data == "ELECTION":
                    print(f"Nó {self.node_id} recebeu mensagem de ELEICAO")
                    # Responde imediatamente para evitar que o remetente se declare coordenador
                    conn.send("ALIVE".encode())
                    # Inicia sua própria eleição se o remetente tem ID menor
                    self.start_election()
                    
                elif data.startswith("COORDINATOR"):
                    new_coord_port = int(data.split()[1])
                    self.coordinator = new_coord_port
                    print(f"Nó {self.node_id} reconhece novo coordenador na porta {new_coord_port}")
                    
                elif data == "PING":
                    conn.send("PONG".encode())
                    
                conn.close()

if __name__ == "__main__":
    node_id = int(input("ID do nó (1-3): "))
    port = 5000 + node_id  # Portas 6001, 6002, 6003 para eleição
    all_ports = [6001, 6002, 6003]  # Portas de todos os nós
    
    node = Coordinator(node_id, port, all_ports)
    node.start()
    
    # Inicia uma eleição se este for o nó de maior ID
    if node_id == 3:
        time.sleep(2)
        node.start_election()