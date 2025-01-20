from flask_sqlalchemy import SQLAlchemy
import bcrypt

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, index=True)
    password = db.Column(db.String(100))
    boards = db.relationship('Board', backref='user', lazy=True)

    def __init__(self, email, password, name):
        self.name = name
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))


class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mac_address = db.Column(db.String(20), unique=True, nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100), nullable=False)

class TemperatureMeasurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey('board.id'), index=True)
    temperature = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String, nullable=False)

    board = db.relationship('Board', backref='TemperatureMeasurement')

class HumidityMeasurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey('board.id'),index=True)
    humidity = db.Column(db.Float, nullable=False)
    date = db.Column(db.String, nullable=False)

    board = db.relationship('Board', backref='HumidityMeasurement')

class IlluminanceMeasurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey('board.id'), index=True)
    illuminance = db.Column(db.Float, nullable=False)
    date = db.Column(db.String, nullable=False)

    board = db.relationship('Board', backref='IlluminanceMeasurement')


# class Measurement(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     board_id = db.Column(db.Integer, db.ForeignKey('board.id'))
#     temperature = db.Column(db.Float, nullable=True)
#     humidity = db.Column(db.Float, nullable=True)
#     illuminance = db.Column(db.Float, nullable=True)
#     date = db.Column(db.DateTime, nullable=False)
#
#     board = db.relationship('Board', backref='measurements')

class MeasurementThresholds(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey('board.id'))
    lower_threshold_temperature = db.Column(db.Float, nullable=True)
    upper_threshold_temperature = db.Column(db.Float, nullable=True)
    lower_threshold_humidity = db.Column(db.Float, nullable=True)
    upper_threshold_humidity = db.Column(db.Float, nullable=True)
    lower_threshold_illuminance = db.Column(db.Float, nullable=True)
    upper_threshold_illuminance = db.Column(db.Float, nullable=True)

    measurement_frequency_temperature = db.Column(db.Float, nullable=True)
    measurement_frequency_humidity = db.Column(db.Float, nullable=True)
    measurement_frequency_illuminance = db.Column(db.Float, nullable=True)
