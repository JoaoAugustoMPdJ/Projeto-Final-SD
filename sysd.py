import socket
import threading
import time
import random
import struct

# Configurações (modificar conforme necessário)
HOST = 'localhost'  # Mudar para IP real se testar em rede
PORTA_BASE = 5000   # Pode precisar alterar se der erro de porta ocupada

# --------------------------------------------
# Parte 1: Comunicação Básica entre Cliente-Servidor
# --------------------------------------------

class Sensor:
    def __init__(self, id_sensor):
        self.id = id_sensor
        self.porta = PORTA_BASE + id_sensor
        self.clock = 0  # Relógio de Lamport simplificado
        self.coordenador = False
        
    def iniciar(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((HOST, self.porta))
                s.listen()
                print(f"Sensor {self.id} rodando na porta {self.porta}")
                
                while True:
                    conn, addr = s.accept()
                    dados = conn.recv(1024).decode()
                    
                    if dados == "GET_DATA":
                        self.clock += 1
                        temp = random.randint(20, 35)  # Dados simulados
                        resposta = f"Sensor {self.id}: Temp={temp}°C (Clock: {self.clock})"
                        conn.sendall(resposta.encode())
                    
                    conn.close()
        except Exception as e:
            print(f"ERRO no sensor {self.id}: {e}")

# --------------------------------------------
# Parte 2: Algoritmo Bully (Eleição)
# --------------------------------------------

class EleicaoBully:
    def __init__(self, id_no, nos_conhecidos):
        self.id = id_no
        self.nos = nos_conhecidos
        
    def iniciar_eleicao(self):
        print(f"\n[Eleição] Nó {self.id} começando eleição...")
        nos_acima = [n for n in self.nos if n > self.id]
        
        if not nos_acima:
            print(f"[Eleição] Nó {self.id} se declara coordenador!")
            return True
        else:
            for n in nos_acima:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(2)
                        s.connect((HOST, PORTA_BASE + n))
                        s.sendall(b"ELEICAO")
                        resposta = s.recv(1024)
                        if resposta == b"OK":
                            print(f"[Eleição] Nó {n} respondeu. Eleição cancelada.")
                            return False
                except:
                    print(f"[Eleição] Nó {n} não respondeu!")
            
            print(f"[Eleição] Nó {self.id} se declara coordenador!")
            return True

# --------------------------------------------
# Parte 3: Cliente e Menu Interativo
# --------------------------------------------

def menu_principal():
    print("\n" + "="*40)
    print(" SISTEMA DE MONITORAMENTO CLIMÁTICO")
    print("="*40)
    print("1. Consultar sensor")
    print("2. Testar eleição Bully")
    print("3. Sair")
    
    try:
        opcao = input("Escolha: ")
        return int(opcao)
    except:
        return 0

def consultar_sensor():
    try:
        id_sensor = int(input("Número do sensor (1-3): "))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORTA_BASE + id_sensor))
            s.sendall(b"GET_DATA")
            dados = s.recv(1024).decode()
            print(f"\nResposta: {dados}")
    except:
        print("Erro ao consultar sensor!")

# --------------------------------------------
# Main (Ponto de Entrada)
# --------------------------------------------

if __name__ == "__main__":
    print("Iniciando sistema...")
    
    # Inicia sensores em threads separadas
    for i in range(1, 4):
        sensor = Sensor(i)
        threading.Thread(target=sensor.iniciar, daemon=True).start()
        time.sleep(0.1)  # Delay para evitar conflitos
    
    # Menu interativo
    while True:
        op = menu_principal()
        
        if op == 1:
            consultar_sensor()
        elif op == 2:
            no = int(input("Nó que inicia eleição (1-3): "))
            bully = EleicaoBully(no, [1, 2, 3])
            bully.iniciar_eleicao()
        elif op == 3:
            print("Saindo...")
            break
        else:
            print("Opção inválida!")