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

## Instalação

### 1. Clonar o Repositório

git clone https://github.com/LucasAgosti/Sistema-Troca-de-Mensagens.git
cd Sistema-Troca-de-Mensagens (ou local do arquivo)

### 2. Configurar o RabbitMQ

brew install rabbitmq
brew services start rabbitmq

(para Windows ou Linux, use sudo-apt get ou via browser)

Para verificar se o RabbitMQ está rodando, 
abra o painel de controle web em http://localhost:15672 (usuário: guest, senha: guest).

### 3. Instalar as Dependências Python e executar servidor

pip install pika
python server.py

### 4. Execute cada instância do cliente

python client.py
(para cada instância)

## Uso

- Entrar no Sistema: Quando o cliente é iniciado, o usuário deve inserir um nome de usuário.
- Adicionar Contato: O usuário pode adicionar um contato à sua lista clicando em "Adicionar Contato".
- Remover Contato: O usuário pode remover contatos da sua lista clicando em "Remover Contato".
- Enviar Mensagens: Se o contato estiver na lista, o usuário pode selecionar o contato na lista e enviar mensagens.
- Estado Online/Offline: O usuário pode alternar entre os estados de online e offline. Se o usuário ficar offline, ele receberá as mensagens pendentes ao retornar.
- Mensagens Offline: Quando um usuário está offline, as mensagens são armazenadas no RabbitMQ e entregues automaticamente quando o usuário retorna online.

## Problemas Conhecidos
- Conflitos de Merge: Caso um merge entre branches não seja concluído, use o comando git merge --abort para reiniciar o processo.
- Erros de Conexão: Certifique-se de que o RabbitMQ esteja rodando e configurado corretamente antes de executar o servidor e clientes.
