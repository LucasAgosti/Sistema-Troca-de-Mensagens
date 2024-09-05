# -----------------------------------------------------------------------------
# Copyright 2024 Lucas Fernandes
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# -----------------------------------------------------------------------------

import socket
import threading
import pickle
import pika
import time
import argparse

class ChatServer:
    def __init__(self, host, port, max_clients=10):
        """
        Inicializa o servidor de chat.
        - host: IP onde o servidor vai rodar.
        - port: Porta onde o servidor escutará as conexões.
        - max_clients: Número máximo de clientes permitidos.
        """
        self.host = host
        self.port = port
        self.max_clients = max_clients
        self.clients = {}  # Dicionário para conexões de clientes e seus nomes
        self.client_status = {}  # Status online/offline dos clientes
        self.contacts = {}  # Lista de contatos de cada cliente
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.lock = threading.Lock()

        # Conecta ao RabbitMQ para gerenciamento de mensagens offline no broker
        self.connect_rabbitmq()

    def connect_rabbitmq(self):
        """Conecta ao RabbitMQ, com tentativa de reconexão em caso de falha."""
        try:
            self.rabbitmq_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            self.rabbitmq_channel = self.rabbitmq_connection.channel()
            print("Conexão com RabbitMQ estabelecida.")
        except Exception as e:
            print(f"Erro ao conectar ao RabbitMQ: {e}. Tentando novamente em 5 segundos...")
            time.sleep(5)
            self.connect_rabbitmq()

    def start(self):
        """Inicia o servidor e aguarda conexões de clientes."""
        print(f"Servidor iniciado em {self.host}:{self.port}")
        try:
            self.accept_connections()
        except Exception as e:
            print(f"Erro no servidor: {e}")
        finally:
            self.shutdown()

    def accept_connections(self):
        """Aceita conexões de clientes continuamente."""
        print("Aguardando conexões...")
        while True:
            try:
                client, addr = self.server_socket.accept()
                threading.Thread(target=self.register_client, args=(client,), daemon=True).start()
            except Exception as e:
                print(f"Erro ao aceitar conexões: {e}")
                break

    def register_client(self, client):
        """
        Registra um cliente no servidor e cria uma fila de mensagens no RabbitMQ.
        - client: Socket do cliente conectado.
        """
        try:
            username = pickle.loads(client.recv(4096))
            with self.lock:
                if username in self.clients.values():
                    client.send(pickle.dumps("Nome de usuário já em uso. Tente outro."))
                    client.close()
                    return
                self.clients[client] = username
                self.client_status[username] = True  # O cliente começa online
                self.contacts[username] = []  # Inicializa lista de contatos do cliente

                # Criação de uma fila no RabbitMQ para o cliente
                self.rabbitmq_channel.queue_declare(queue=username, durable=True)
            print(f"Usuário {username} conectado e fila de mensagens criada.")
            self.update_user_list(client)
            self.handle_client(client)
        except Exception as e:
            print(f"Erro ao registrar cliente: {e}")
            client.close()

    def handle_client(self, client):
        """
        Lida com as ações do cliente, como envio de mensagens ou atualizações de status.
        """
        try:
            while True:
                data = client.recv(4096)
                if not data:
                    break
                action_data = pickle.loads(data)
                print(f"Ação recebida de {self.clients[client]}: {action_data}")
                self.handle_action(action_data, client)
        except Exception as e:
            print(f"Erro ao gerenciar cliente {self.clients[client]}: {e}")
        finally:
            with self.lock:
                username = self.clients.pop(client, None)
                self.client_status.pop(username, None)
                if username:
                    print(f"Usuário {username} desconectado.")
            client.close()
            self.update_user_list(client)

    def handle_action(self, action_data, client):
        """
        Executa ações baseadas nos dados recebidos do cliente.
        - action_data: Dicionário com dados de ação do cliente.
        """
        if action_data['action'] == 'send_private_message':
            target_user = action_data['target_user']
            message = action_data['message']

            # Verificação se o destinatário está na lista de contatos de quem envia a mensagem
            username = self.clients[client]
            if target_user not in self.contacts[username]:
                client.send(pickle.dumps(
                    f"Erro: Você não pode enviar mensagens para {target_user}, pois ele não está na sua lista de contatos."))
                print(f"{username} tentou enviar mensagem para {target_user}, que não está na lista de contatos.")
                return

            # Verifica se o destinatário está online
            if self.client_status.get(target_user, False):
                # Se o destinatário estiver online, envia a mensagem diretamente para ele
                self.send_private_message(client, message, target_user)
            else:
                # Se estiver offline, envia a mensagem para a fila RabbitMQ
                self.send_message_to_queue(client, target_user, message)

        elif action_data['action'] == 'add_contact':
            contact = action_data['contact']
            self.add_contact(client, contact)

        elif action_data['action'] == 'remove_contact':
            contact = action_data['contact']
            self.remove_contact(client, contact)

        elif action_data['action'] == 'status_update':
            with self.lock:
                self.client_status[self.clients[client]] = action_data['status']
            print(f"{self.clients[client]} mudou para {'online' if action_data['status'] else 'offline'}")

            # Se o cliente ficar online, busca mensagens offline no broker do RabbitMQ
            if action_data['status']:
                threading.Thread(target=self.retrieve_offline_messages, args=(self.clients[client],)).start()

    def retrieve_offline_messages(self, username):
        """
        Busca as mensagens offline da fila RabbitMQ e as envia ao cliente.
        """
        try:
            if self.rabbitmq_connection.is_closed:
                print("Conexão com RabbitMQ perdida. Tentando reconectar...")
                self.connect_rabbitmq()

            messages = []
            while True:
                method_frame, properties, body = self.rabbitmq_channel.basic_get(queue=username, auto_ack=False)
                if method_frame:
                    messages.append(body.decode())
                    self.rabbitmq_channel.basic_ack(method_frame.delivery_tag)
                else:
                    break

            if messages:
                print(f"Entregando {len(messages)} mensagens offline para {username}")
                self.send_offline_messages_to_client(username, messages)

        except Exception as e:
            print(f"Erro ao consumir mensagens offline para {username}: {e}")
            self.connect_rabbitmq()

    def send_offline_messages_to_client(self, username, messages):
        """
        Envia todas as mensagens offline para o cliente quando ele voltar online.
        """
        target_client = next((c for c, u in self.clients.items() if u == username), None)
        if target_client:
            try:
                target_client.send(pickle.dumps(messages))
                print(f"Mensagens offline entregues a {username}.")
            except Exception as e:
                print(f"Erro ao enviar mensagens offline para {username}: {e}")

    def add_contact(self, client, contact):
        """
        Adiciona um contato à lista de contatos do cliente.
        """
        username = self.clients[client]

        if contact == username:
            client.send(pickle.dumps("Você não pode adicionar a si mesmo como contato."))
            print(f"{username} tentou se adicionar como contato.")
            return

        if contact in self.client_status:
            if contact not in self.contacts[username]:
                self.contacts[username].append(contact)
                self.update_user_list(client)
                client.send(pickle.dumps(f"Contato {contact} adicionado."))
                print(f"Contato {contact} adicionado para {username}.")
            else:
                client.send(pickle.dumps(f"Contato {contact} já está na lista."))
        else:
            client.send(pickle.dumps(f"Contato {contact} não existe."))

    def remove_contact(self, client, contact):
        """
        Remove um contato da lista de contatos do cliente.
        """
        username = self.clients[client]
        if contact in self.contacts[username]:
            self.contacts[username].remove(contact)
            self.update_user_list(client)
            client.send(pickle.dumps(f"Contato {contact} removido."))
            print(f"Contato {contact} removido de {username}.")
        else:
            client.send(pickle.dumps(f"Contato {contact} não está na lista."))

    def send_private_message(self, client, message, target_user):
        """
        Envia mensagem diretamente para um cliente, caso esteja online.
        """
        username = self.clients[client]

        if target_user not in self.contacts[username]:
            client.send(pickle.dumps(
                f"Erro: Você não pode enviar mensagens para {target_user}, pois ele não está na sua lista de contatos."))
            print(f"{username} tentou enviar mensagem para {target_user}, que não está na lista de contatos.")
            return

        target_client = next((c for c, u in self.clients.items() if u == target_user), None)
        if target_client:
            try:
                target_client.send(pickle.dumps(f"{self.clients[client]} (privado): {message}"))
                client.send(pickle.dumps(f"Você para ({target_user}): {message}"))
            except Exception as e:
                print(f"Erro ao enviar mensagem para {target_user}: {e}")
        else:
            print(f"Usuário {target_user} não encontrado online.")

    def send_message_to_queue(self, client, target_user, message):
        """
        Envia mensagem para a fila do destinatário no RabbitMQ e confirma ao remetente.
        """
        try:
            if self.rabbitmq_connection.is_closed:
                print("Conexão com RabbitMQ perdida. Tentando reconectar...")
                self.connect_rabbitmq()

            self.rabbitmq_channel.basic_publish(
                exchange='',
                routing_key=target_user,
                body=message,
                properties=pika.BasicProperties(delivery_mode=2)  # Persistência da mensagem
            )
            print(f"Mensagem para {target_user} armazenada na fila RabbitMQ.")
            client.send(pickle.dumps(f"Você (privado): {message}"))

        except Exception as e:
            print(f"Erro ao enviar mensagem para a fila do RabbitMQ: {e}")
            self.connect_rabbitmq()

    def update_user_list(self, client):
        """Atualiza a lista de contatos de um cliente."""
        username = self.clients[client]
        user_list = self.contacts[username]
        client.send(pickle.dumps({'action': 'update_user_list', 'user_list': user_list}))

    def shutdown(self):
        """Encerra o servidor e desconecta todos os clientes."""
        print("Encerrando o servidor...")
        with self.lock:
            for client in self.clients.keys():
                client.close()
            self.server_socket.close()
            self.rabbitmq_connection.close()


if __name__ == '__main__':
    # Definição dos argumentos de linha de comando para IP e Porta
    parser = argparse.ArgumentParser(description="Servidor de Chat com RabbitMQ")
    parser.add_argument('--host', type=str, default='0.0.0.0', help='IP para o servidor escutar (padrão: 0.0.0.0)')
    parser.add_argument('--port', type=int, required=True, help='Porta para o servidor escutar')
    args = parser.parse_args()

    server = ChatServer(host=args.host, port=args.port)
    server.start()
