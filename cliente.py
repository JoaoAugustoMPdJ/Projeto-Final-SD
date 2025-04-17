import socket
import json
import time
import random
from security import SecurityHandler

class Cliente:
    def __init__(self):
        self.sensors = [
            {"id": 1, "host": "sensor1", "port": 5001},
            {"id": 2, "host": "sensor2", "port": 5002},
            {"id": 3, "host": "sensor3", "port": 5003}
        ]
        self.security = SecurityHandler(0, "chave_32_bytes_ultra_secreta_1234567890")
        self.timeout = 2  # Timeout de conexão em segundos

    def send_command(self, sensor, command, data=None):
        """Envia comandos aos sensores com tratamento robusto"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout)
                s.connect((sensor["host"], sensor["port"]))
                
                payload = {"command": command}
                if data:
                    payload.update(data)
                    
                encrypted = self.security.encrypt(json.dumps(payload))
                s.sendall(encrypted.encode())
                
                response = s.recv(4096)
                if response:
                    return json.loads(self.security.decrypt(response.decode()))
        except Exception as e:
            print(f"Erro ao comunicar com sensor {sensor['id']}: {str(e)}")
        return None

    def query_specific_sensor(self):
        """Consulta um sensor específico com interação completa"""
        print("\n=== CONSULTAR SENSOR ESPECÍFICO ===")
        try:
            sensor_id = int(input("Digite o ID do sensor (1-3): "))
            if sensor_id not in [1, 2, 3]:
                print("ID inválido! Deve ser 1, 2 ou 3")
                return
                
            sensor = next(s for s in self.sensors if s["id"] == sensor_id)
            print("\nOpções de consulta:")
            print("1. Dados atuais")
            print("2. Status do coordenador")
            print("3. Informações de eleição")
            
            sub_choice = input("Escolha o tipo de consulta: ")
            
            if sub_choice == "1":
                data = self.send_command(sensor, "GET_DATA")
                self.display_sensor_data(sensor["id"], data)
            elif sub_choice == "2":
                data = self.send_command(sensor, "GET_COORDINATOR")
                self.display_coordinator_info(data)
            elif sub_choice == "3":
                data = self.send_command(sensor, "ELECTION_INFO")
                self.display_election_info(data)
            else:
                print("Opção inválida!")
                
        except ValueError:
            print("Entrada inválida! Digite um número.")

    def show_all_sensors(self):
        """Consulta todos os sensores de forma interativa"""
        print("\n=== CONSULTAR TODOS OS SENSORES ===")
        print("1. Obter dados de todos")
        print("2. Ver coordenadores")
        print("3. Estado da eleição")
        
        choice = input("Escolha o tipo de consulta: ")
        
        for sensor in self.sensors:
            print(f"\n Sensor {sensor['id']}")
            
            if choice == "1":
                data = self.send_command(sensor, "GET_DATA")
                self.display_sensor_data(sensor["id"], data)
            elif choice == "2":
                data = self.send_command(sensor, "GET_COORDINATOR")
                self.display_coordinator_info(data)
            elif choice == "3":
                data = self.send_command(sensor, "ELECTION_INFO")
                self.display_election_info(data)
            else:
                print("Opção inválida!")
                break

    def election_info(self):
        """Mostra informações detalhadas da eleição"""
        print("\n=== INFORMAÇÕES DE ELEIÇÃO ===")
        for sensor in self.sensors:
            data = self.send_command(sensor, "ELECTION_INFO")
            if data:
                print(f"\nSensor {sensor['id']}:")
                print(f"Estado: {data.get('state', 'N/A')}")
                print(f"Coordenador atual: {data.get('coordinator_id', 'N/A')}")
                print(f"Participou da última eleição: {'Sim' if data.get('participated', False) else 'Não'}")

    def force_election(self):
        """Força uma nova eleição com confirmação"""
        print("\n=== FORÇAR NOVA ELEIÇÃO ===")
        confirm = input("Tem certeza que deseja forçar nova eleição? (s/n): ").lower()
        if confirm != 's':
            print("Operação cancelada")
            return
            
        for sensor in self.sensors:
            response = self.send_command(sensor, "START_ELECTION", {"force": True})
            if response and response.get("success"):
                print(f"Eleição iniciada pelo sensor {sensor['id']}")
                return
                
        print("Falha ao iniciar eleição")

    def network_status(self):
        """Mostra status detalhado da rede"""
        print("\n=== STATUS DA REDE ===")
        for sensor in self.sensors:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.connect((sensor["host"], sensor["port"]))
                    status = " ONLINE"
            except:
                status = " OFFLINE"
                
            print(f"Sensor {sensor['id']}: {status}")

    def global_snapshot(self):
        """Captura snapshot consistente de todos os sensores"""
        print("\n=== SNAPSHOT GLOBAL ===")
        for sensor in self.sensors:
            data = self.send_command(sensor, "SNAPSHOT")
            if data:
                print(f"\n📸 Sensor {sensor['id']} - Snapshot:")
                self.display_sensor_data(sensor["id"], data)

    def test_failure_detection(self):
        """Testa o sistema de detecção de falhas"""
        print("\n=== TESTE DE DETECÇÃO DE FALHAS ===")
        coordinator = None
        
        # Encontra o coordenador
        for sensor in self.sensors:
            data = self.send_command(sensor, "GET_COORDINATOR")
            if data and data.get("is_coordinator"):
                coordinator = sensor
                break
                
        if not coordinator:
            print("Nenhum coordenador ativo encontrado!")
            return
            
        print(f"Testando coordenador (Sensor {coordinator['id']})...")
        response = self.send_command(coordinator, "PING")
        
        if response and response.get("status") == "PONG":
            print(" Coordenador respondendo corretamente")
        else:
            print(" Falha na comunicação com o coordenador")

    def display_sensor_data(self, sensor_id, data):
        """Exibe os dados do sensor formatados"""
        if not data:
            print(f"\n🔹 Sensor {sensor_id} -  Offline")
            return
            
        sensor_data = data.get("data", {})

        temp = sensor_data.get('temperature', round(random.uniform(15.0, 35.0), 1))
        humidity = sensor_data.get('humidity', round(random.uniform(30.0, 90.0), 1))
        last_updated = sensor_data.get('last_updated', time.time())

        # Formatação de data segura
        try:
            time_str = time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(last_updated))
        except:
            time_str = "Data inválida"
        
        print(f"\n Sensor {sensor_id}")
        print(f" Temperatura: {temp}°C")
        print(f"Umidade: {humidity}%")
        print(f" Pressão: {sensor_data.get('pressure', 'N/A')} hPa")
        print(f" Atualizado: {time_str}")
        print(f" Versão: {sensor_data.get('version', 'N/A')}")
    
        if data.get('is_coordinator'):
            print(" Este nó é o coordenador")

    def display_coordinator_info(self, data):
        """Exibe informações do coordenador"""
        if not data:
            print("Sem informações do coordenador")
            return
            
        if data.get('is_coordinator'):
            print(" Este nó é o coordenador")
        else:
            print(f"Coordenador atual: Nó {data.get('coordinator_id', 'N/A')}")

    def display_election_info(self, data):
        """Exibe informações de eleição"""
        if not data:
            print("Sem informações de eleição")
            return
            
        print(f"Estado: {data.get('election_state', 'N/A')}")
        print(f"Última eleição: {time.ctime(data.get('election_time', 0))}")

    def _graceful_exit(self):
        """Encerra o cliente de forma controlada"""
        print("\nEncerrando cliente...")
        exit(0)

    def show_menu(self):
        """Exibe o menu completo com todas as opções"""
        menu_options = {
            '1': ('Consultar sensor específico', self.query_specific_sensor),
            '2': ('Consultar todos os sensores', self.show_all_sensors),
            '3': ('Informações de eleição', self.election_info),
            '4': ('Forçar nova eleição', self.force_election),
            '5': ('Status da rede', self.network_status),
            '6': ('Capturar snapshot global', self.global_snapshot),
            '7': ('Testar detecção de falhas', self.test_failure_detection),
            '8': ('Sair', self._graceful_exit)
        }

        while True:
            print("\n" + "="*30 + " MENU PRINCIPAL " + "="*30)
            for opt, (desc, _) in menu_options.items():
                print(f"{opt}. {desc}")
            
            choice = input("\nSelecione uma opção: ").strip()
            if choice in menu_options:
                menu_options[choice][1]()
                input("\nPressione Enter para continuar...")
            else:
                print("Opção inválida. Tente novamente.")

if __name__ == "__main__":
    try:
        print("\n=== SISTEMA DE MONITORAMENTO DE SENSORES ===")
        cliente = Cliente()
        cliente.show_menu()
    except KeyboardInterrupt:
        print("\nOperação interrompida pelo usuário")
    except Exception as e:
        print(f"\nErro fatal: {str(e)}")
        exit(1)
