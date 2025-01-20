import json
import paho.mqtt.client as mqtt
from datetime import datetime

from database import db,Board,User,IlluminanceMeasurement,HumidityMeasurement,TemperatureMeasurement

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883

class MqttClient:
    def __init__(self, app,socketio):
        self.topic_to_subscribe_from_db = []
        self.topics = ['humidity', 'temperature', 'illuminance']
        self.app = app

        self.new_clients = []

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.mqtt_client.loop_start()

        self.socketio = socketio

        with self.app.app_context():
            users = User.query.all()
            for user in users:
                boards = Board.query.filter_by(owner_id=user.id)
                if not (boards.count() == 0):
                    for board in boards:
                        topic = f"{user.email}/{board.mac_address}"
                        #self.topic_to_subscribe_from_db.append(topic)
                        print(topic + " was appended to list topics_to_subscribe_from_db, init")
                        for t in self.topics:
                            t1 = f"{topic}/{t}"
                            self.topic_to_subscribe_from_db.append(t1)

        print(self.topic_to_subscribe_from_db)


    def emit_update(self, board_id, data_type, value, timestamp):
        self.socketio.emit('new_measurement', {
            "board_id": board_id,
            "type": data_type,
            "value": value,
            "timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })

    def add_client(self, email):
        self.new_clients.append(email)
        self.mqtt_client.subscribe(email)
        print(f"Added client: {email}")


    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        print(f"Connected with result code {reason_code}")
        print(len(self.topic_to_subscribe_from_db))
        for topic in self.topic_to_subscribe_from_db:
            client.subscribe(topic)
            print(f"on_connect, subscribed to: {topic}")

    def on_message(self, client, userdata, msg):
        print(f"Received message on topic {msg.topic}: {msg.payload}")

        try:
            message = msg.payload.decode("utf-8")
            data = json.loads(message)

            # przesyłanie - użytkownik zarejestrowany already, płytka w bazie, jest relacja między nimi
            # topic: diana332m@gmail.com/A1-B2-C3-D5-E6-F7/illuminance
            # payload: illuminance: 200, unit: lx, date: 19.01.2025 14:39:20
            if msg.topic in self.topic_to_subscribe_from_db:
                user_email, mac, data_type = msg.topic.split('/')
                with self.app.app_context():
                    user = User.query.filter_by(email=user_email).first()
                    board = Board.query.filter_by(mac_address = mac).first()

                    value = data.get(data_type)
                    timestamp = data.get("timestamp")
                    #timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    print(f"Value: {value}")
                    if data_type == 'illuminance':
                        illuminance_measurement = IlluminanceMeasurement(
                            board_id = board.id,
                            illuminance = value,
                            date = timestamp
                        )
                        db.session.add(illuminance_measurement)
                        db.session.commit()
                        print('Illuminance measurement saved')
                        self.emit_update(board.id, 'illuminance', value, timestamp)


                    elif data_type == 'temperature':
                        temperature_measurement = TemperatureMeasurement(
                            board_id = board.id,
                            temperature = value,
                            date = timestamp
                        )
                        db.session.add(temperature_measurement)
                        db.session.commit()
                        print('Temperature measurement saved')

                        self.emit_update(board.id, 'temperature', value, timestamp)

                    elif data_type == 'humidity':
                        humidity_measurement = HumidityMeasurement(
                            board_id = board.id,
                            humidity = value,
                            date = timestamp
                        )
                        db.session.add(humidity_measurement)
                        db.session.commit()
                        print('Humidity measurement saved')
                        self.emit_update(board.id, 'humidity', value, timestamp)
                    else:
                        print("Data not found in message")

            # nowy użytkownik zarejestrowany, płytka w bazie lub nie, ale nie ma relacji między nimi
            # topic: diana332m@gmail.com
            # payload: mac_topic : A1-B2-C3-D5-E6-F7
            elif msg.topic in self.new_clients:
                new_user_email = msg.topic
                mac = data.get("device_mac")
                if not mac:
                    print("MAC address not found in the message!")
                    return

                print(f"Received MAC address: {mac}")

                with self.app.app_context():
                    user = User.query.filter_by(email=new_user_email).first()
                    existing_board = Board.query.filter_by(mac_address=mac).first()

                    if existing_board is None:
                        new_board = Board(
                            mac_address=mac,
                            owner_id=user.id,
                            name = f"Smart Pot: {mac}"
                        )
                        db.session.add(new_board)
                        db.session.commit()
                        print(f"Added new board for user {user.email} with MAC {mac}")

                    else:
                        # The device has already been registered to database. Need to change the owner
                        previous_owner = User.query.filter_by(id = existing_board.owner_id).first()
                        existing_board.owner_id = user.id
                        db.session.commit()
                        print(f"Updated owner of board with MAC {mac} to user {user.email}")

                        # for topic in self.topic_to_subscribe_from_db:
                        for data_type in self.topics:
                            to_unsubscribe = f"{previous_owner.email}/{mac}/{data_type}"
                            print("To unsubscribe : " + to_unsubscribe)
                            client.unsubscribe(to_unsubscribe)
                            self.topic_to_subscribe_from_db.remove(to_unsubscribe)

                for topic in self.topics:
                    to_subscribe = f"{new_user_email}/{mac}/{topic}"
                    client.subscribe(to_subscribe)
                    self.topic_to_subscribe_from_db.append(to_subscribe)
                    print(f"Subscribed to {to_subscribe}")

                self.new_clients.remove(new_user_email)
                print(self.topic_to_subscribe_from_db)

            #TODO jakiś już zarejestrowany użytkownik odkupuje płytkę
            # elif msg.topic in

            else:
                print(f"User with email {msg.topic} not found! Register user with this email")
                print(self.topic_to_subscribe_from_db)
                return

        except json.JSONDecodeError:
            print("Invalid JSON format received!")
        except Exception as e:
            print(f"An error occurred: {e}")




