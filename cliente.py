import socket

def get_sensor_data(sensor_port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', sensor_port))
            s.send("GET_DATA".encode())
            data = s.recv(1024).decode()
            return eval(data)
    except:
        return None

def main():
    sensor_ports = [5001, 5002, 5003]  # Portas dos sensores
    
    while True:
        print("\n--- Menu Cliente ---")
        print("1. Consultar dados de um sensor")
        print("2. Consultar todos os sensores")
        print("3. Sair")
        
        choice = input("Escolha: ")
        
        if choice == "1":
            sensor_id = int(input("ID do sensor (1-3): "))
            data = get_sensor_data(5000 + sensor_id)
            print(f"Dados do sensor {sensor_id}: {data}")
            
        elif choice == "2":
            for port in sensor_ports:
                data = get_sensor_data(port)
                if data:
                    print(f"Sensor {data['sensor_id']}: {data['data']} (Timestamp: {data['timestamp']})")
                else:
                    print(f"Sensor na porta {port} não respondendo")
                    
        elif choice == "3":
            break

if __name__ == "__main__":
    main()