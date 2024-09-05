# Sistema-Troca-de-Mensagens
 
# Sistema de Chat com Suporte a Mensagens Offline

Este projeto implementa um sistema de chat baseado em sockets com suporte a armazenamento de mensagens offline utilizando RabbitMQ como broker de mensagens. O sistema foi desenvolvido como parte de um projeto maior e implementa várias funcionalidades, como adicionar e remover contatos, gerenciamento de filas de mensagens, e troca de mensagens privadas.

## Funcionalidades

1. **Troca de Mensagens em Tempo Real**: Usuários podem se comunicar em tempo real se ambos estiverem online.
2. **Mensagens Offline**: Quando um usuário está offline, as mensagens são armazenadas no RabbitMQ e entregues quando o usuário se reconecta.
3. **Adicionar e Remover Contatos**: Usuários podem adicionar e remover outros usuários da sua lista de contatos.
4. **Estado Online/Offline**: Usuários podem alternar entre o estado online e offline.
5. **Gerenciamento de Filas**: Para cada usuário, é criada uma fila no RabbitMQ para armazenar mensagens enquanto estão offline.

## Arquitetura

- **Server**: Gerencia as conexões dos usuários e suas mensagens, garantindo que as mensagens offline sejam armazenadas corretamente no RabbitMQ.
- **Client**: Interface gráfica feita em `Tkinter` para permitir que os usuários troquem mensagens e gerenciem suas listas de contatos.
- **RabbitMQ**: Responsável por armazenar mensagens quando o destinatário estiver offline.

## Requisitos

- Python 3.x
- RabbitMQ
- Bibliotecas Python:
  - `socket`
  - `threading`
  - `pickle`
  - `pika` (RabbitMQ)

