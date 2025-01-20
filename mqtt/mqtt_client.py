import json
import paho.mqtt.client as mqtt
from database import db,Board,User
MQTT_PORT = 1883
MQTT_BROKER = "broker.hivemq.com"
#MQTT_TOPIC = "diana332m@gmail.com"

class MqqtClient:
    def __init__(self, socketio, user_id,app):
        self.app = app
        self.socketio = socketio
        self.user_id = user_id
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.mqtt_client.loop_start()
        self.dynamic_topics = {}
        MQTT_TOPIC = user_id
        self.topic_to_subscribe = ['humidity', 'temperature', 'illuminance']
        self.clients = []


    def add_client(self, user_id):
        self.clients.append(user_id)


    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        print(f"Connected with result code {reason_code}")
        client.subscribe(self.user_id)

        with self.app.app_context():
            # Pobierz wszystkie urządzenia przypisane do użytkownika
            user = User.query.filter_by(email=self.user_id).first()
            if not user:
                print(f"User with email {self.user_id} not found!")
                return

            boards = Board.query.filter_by(owner_id=user.id).all()

            # Subskrybuj tematy dla istniejących urządzeń
            for board in boards:
                board_topic = f"{self.user_id}/{board.mac_address}"
                client.subscribe(board_topic)
                print(f"Subscribed to existing board topic: {board_topic}")

            # Subskrybuj dynamiczne tematy, jeśli istnieją
                for topic in self.topic_to_subscribe:
                    print(f'Subscribed to: {board_topic}/{topic}')
                    to_subscribe = f'{board_topic}/{topic}'
                    client.subscribe(to_subscribe)

    def on_message(self, client, userdata, msg):
        print(f"Received message on topic {msg.topic}: {msg.payload}")
        try:
            message = msg.payload.decode("utf-8")
            data = json.loads(message)

            # Użyj kontekstu aplikacji Flask
            with self.app.app_context():
                if msg.topic in self.dynamic_topics.values():
                    for key, topic in self.dynamic_topics.items():
                        if msg.topic == topic:
                            value = data.get(key)
                            if value is not None:
                                print(f"Received {key.capitalize()}: {value}")
                                self.socketio.emit('update_data', {key: value})

                            else:
                                print(f"{key.capitalize()} data not found in the message!")

                elif msg.topic == self.user_id:
                    mac = data.get("device_mac")

                    if not mac:
                        print("MAC address not found in the message!")
                        return

                    print(f"Received MAC Address: {mac}")

                    user = User.query.filter_by(email=self.user_id).first()

                    if not user:
                        print(f"User with email {self.user_id} not found!")
                        return

                    existing_board = Board.query.filter_by(mac_address=mac).first()
                    if not existing_board:
                        # Jeśli urządzenie nie istnieje, dodaj je
                        new_board = Board(
                            name="Płytka ESP32",
                            mac_address=mac,
                            owner_id=user.id
                        )
                        db.session.add(new_board)
                        db.session.commit()
                        print(f"Added new board for user {user.email} with MAC {mac}")
                    else:
                        # Jeśli urządzenie istnieje, zmień właściciela
                        existing_board.owner_id = user.id
                        db.session.commit()
                        print(f"Updated owner of board with MAC {mac} to user {user.email}")

                    for data_type in self.topic_to_subscribe:
                        if data_type not in self.dynamic_topics:
                            new_topic = f"{self.user_id}/{mac}/{data_type}"
                            self.dynamic_topics[data_type] = new_topic
                            client.subscribe(new_topic)
                            print(f"Subscribed to new topic: {new_topic}")

        except json.JSONDecodeError:
            print("Invalid JSON format received!")
        except Exception as e:
            print(f"An error occurred: {e}")


