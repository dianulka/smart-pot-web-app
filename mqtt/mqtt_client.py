import json
import paho.mqtt.client as mqtt

MQTT_PORT = 1883
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "user123"

class MqqtClient:
    def __init__(self, socketio, user_id):
        self.socketio = socketio
        self.user_id = user_id
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.mqtt_client.loop_start()
        self.dynamic_topics = {}

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        print(f"Connected with result code {reason_code}")
        client.subscribe(self.user_id)

    def on_message(self, client, userdata, msg):
        print(f"Received message on topic {msg.topic}: {msg.payload}")
        try:
            message = msg.payload.decode("utf-8")
            data = json.loads(message)

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

                for data_type in ['humidity', 'temperature', 'illuminance']:
                    if data_type not in self.dynamic_topics:
                        new_topic = f"{self.user_id}/{mac}/{data_type}"
                        self.dynamic_topics[data_type] = new_topic
                        client.subscribe(new_topic)
                        print(f"Subscribed to new topic: {new_topic}")

        except json.JSONDecodeError:
            print("Invalid JSON format received!")
        except Exception as e:
            print(f"An error occurred: {e}")
