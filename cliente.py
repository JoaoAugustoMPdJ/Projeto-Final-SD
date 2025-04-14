import socket
import os

def get_sensor_data(sensor_host, sensor_port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((sensor_host, sensor_port))
            s.send("GET_DATA".encode())
            data = s.recv(1024).decode()
            return eval(data)
    except Exception as e:
        print(f"Erro ao conectar ao sensor {sensor_host}:{sensor_port}: {str(e)}")
        return None

def main():
    # Usar nomes dos serviços Docker
    sensors = [
        {"id": 1, "host": "sensor1", "port": 5001},
        {"id": 2, "host": "sensor2", "port": 5002},
        {"id": 3, "host": "sensor3", "port": 5003}
    ]
    
    while True:
        print("\n--- Menu Cliente ---")
        print("1. Consultar dados de um sensor")
        print("2. Consultar todos os sensores")
        print("3. Sair")
        
        choice = input("Escolha: ")
        
        if choice == "1":
            sensor_id = int(input("ID do sensor (1-3): "))
            sensor = next((s for s in sensors if s["id"] == sensor_id), None)
            if sensor:
                data = get_sensor_data(sensor["host"], sensor["port"])
                print(f"Dados do sensor {sensor_id}: {data}")
            else:
                print("ID do sensor inválido!")
                
        elif choice == "2":
            for sensor in sensors:
                data = get_sensor_data(sensor["host"], sensor["port"])
                if data:
                    print(f"Sensor {data['sensor_id']}: {data['data']} (Timestamp: {data['timestamp']})")
                else:
                    print(f"Sensor {sensor['id']} não respondendo")
                    
        elif choice == "3":
            break

if __name__ == "__main__":
    main()