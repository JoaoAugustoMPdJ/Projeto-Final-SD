
# Projeto-Final-SD
Discentes: João Augusto Moura Peixoto de Jesus (20211TADSSAJ0004) e Gustavo Vitor Oliveira de Andrade (20221TADSSAJ0003)

## Introdução

Este repositório contém implementações relacionadas a conceitos fundamentais de sistemas distribuídos. Os principais tópicos abordados no projeto incluem arquitetura de sistemas distribuídos, comunicação entre componentes, sincronização de relógios lógicos, detecção de falhas e algoritmos de eleição.

## Estrutura do Projeto

O projeto está dividido em arquivos que representam funcionalidades específicas. Abaixo segue uma explicação de cada uma:

### 1. Fundamentos e Arquitetura

**Modelos utilizados:**
- Cliente-servidor
- Arquitetura multicamadas
- gRPC

Os arquivos principais relacionados:
- cliente.py: script que representa o cliente se comunicando com o servidor.
- docker-compose.yml e dockerfile: configuram os containers Docker simulando múltiplas máquinas.
- proto.proto`: define o serviço gRPC utilizado na comunicação remota.
- proto_pb2.py e proto_pb2_grpc.py: arquivos gerados a partir do .proto para suporte ao gRPC.

### 2. Comunicação entre Componentes

**Tecnologias utilizadas:**
- **Sockets (TCP):** Comunicação de baixo nível entre cliente e servidor.
- **gRPC:** Middleware moderno para chamadas remotas.
- **RMI (Remoto):** Invocação de métodos em objetos remotos.

Scripts relacionados:
- cliente.py
- multi.py: demonstra uso de multicast entre múltiplos servidores.
- proto.proto + seus derivados (proto_pb2.py, proto_pb2_grpc.py)

### 3. Sincronização e Estado Global

**Conceitos abordados:**
- Relógios lógicos de Lamport
- Snapshot de estado global do sistema

Script relacionado:
- algorit.py: implementação dos relógios lógicos.

### 4. Eleição e Detecção de Falhas

**Funcionalidades:**
- Algoritmo de eleição (Bully)
- Heartbeat para detecção de falhas entre nós

Script relacionado:
- eleicao.py: responsável por implementar o algoritmo de eleição entre processos distribuídos.

### 5. Comunicação em Grupo

**Técnica usada:**
- Multicast entre nós participantes

Script:
- multi.py: implementa o envio de mensagens multicast entre servidores e clientes.

## Execução do Projeto

1. **Docker:**  
   Para iniciar os containers, utilize:

   ```bash
   docker-compose up --build
   ```

   Isso criará um ambiente simulado com múltiplos nós do sistema distribuído.

2. **Execução manual:**  
   Você também pode executar os scripts individualmente:
   
   1. docker-compose build --no-cache
   2. docker-compose up
   3. Abra um novo terminal e execute: docker exec -it cliente sh
   4. Ainda no novo terminal: python cliente.py

4. **gRPC:**  
   Para gerar os arquivos gRPC a partir do .proto:

   ```bash
   python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto.proto
   ```

## Requisitos

- Python 3.10+
- Docker e Docker Compose
- Bibliotecas: grpcio, grpcio-tools, socket, threading

## Conclusão

Este projeto integra vários conceitos fundamentais de sistemas distribuídos, oferecendo uma base prática para compreensão de arquiteturas distribuídas, comunicação entre componentes, e gerenciamento de falhas e estados globais. Ele simula um sistema real de múltiplos nós com troca de mensagens e mecanismos de controle de estado.
