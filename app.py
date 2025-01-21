

from flask import Flask, render_template, request, redirect, session, jsonify
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from database import db, User, Board, MeasurementThresholds, HumidityMeasurement,TemperatureMeasurement,IlluminanceMeasurement
import bcrypt
from mqtt_client2 import MqttClient
from flask import request, redirect, url_for, flash
import json
app = Flask(__name__)
socketio = SocketIO(app,cors_allowed_origins="*")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'


app.secret_key = 'secret_key'
db.init_app(app)


# with app.app_context():
#     # Drop and recreate tables
#     db.drop_all()
#     db.create_all()
#
#     # Create a sample user
#     user = User(name="user1", email="user1@wp.com", password="password123")
#     db.session.add(user)
#     db.session.commit()
#
#     # Add some boards for the user
#     board1 = Board(name="Living Room Pot", mac_address="00:1A:2B:3C:4D:5E", owner_id=user.id)
#     board2 = Board(name="Bedroom Pot", mac_address="00:1A:AB:3C:4D:5F", owner_id=user.id)
#     db.session.add_all([board1, board2])
#     db.session.commit()
#
#     print("Database reset and seeded successfully!")

mqtt_client = MqttClient(app, socketio)
@app.route('/dashboard')
def index():
    if 'email' in session:
        user = User.query.filter_by(email=session['email']).first()
        boards = Board.query.filter_by(owner_id=user.id).all()
        return render_template('dashboard.html', user=user, boards=boards)

    return redirect('/login')



@app.route('/register',methods=['GET','POST'])
def register():
    if request.method == 'POST':
        # handle request
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        new_user = User(name=name,email=email,password=password)
        db.session.add(new_user)
        db.session.commit()
        mqtt_client.add_client(email)
        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['email'] = user.email

            return redirect('/dashboard')
        else:
            return render_template('login.html', error='Invalid user')


    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('email',None)
    return redirect('/login')


@app.route('/pot/<int:board_id>')
def pot_detail(board_id):
    board = Board.query.get_or_404(board_id)
    user = User.query.filter_by(id=board.owner_id).first()

    return render_template(
        'pot.html',
        user=user,
        board=board
    )

@app.route('/configure/<int:board_id>')
def configure(board_id):
    board = Board.query.get_or_404(board_id)
    user = User.query.filter_by(id=board.owner_id).first()

    thresholds = MeasurementThresholds.query.filter_by(board_id=board_id).first()
    if not thresholds:
        thresholds = MeasurementThresholds(
            board_id=board_id,
            lower_threshold_temperature=15.0,
            upper_threshold_temperature=30.0,
            lower_threshold_humidity=30.0,
            upper_threshold_humidity=70.0,
            lower_threshold_illuminance=25.0,
            upper_threshold_illuminance=150.0,
            measurement_frequency_temperature = 20000,
            measurement_frequency_humidity = 10000,
            measurement_frequency_illuminance = 6000
        )
        db.session.add(thresholds)
        db.session.commit()

    return render_template(
        'configuration.html',
        user=user,
        board=board,
        thresholds=thresholds
    )

@app.route('/save_thresholds/<int:board_id>', methods=['POST'])
def save_thresholds(board_id):
    board = Board.query.get_or_404(board_id)

    # Fetch the existing thresholds or create new ones
    thresholds = MeasurementThresholds.query.filter_by(board_id=board_id).first()
    if not thresholds:
        thresholds = MeasurementThresholds(board_id=board_id)

    try:
        # Update thresholds from form data
        thresholds.lower_threshold_temperature = float(request.form['lower_temperature'])
        thresholds.upper_threshold_temperature = float(request.form['upper_temperature'])
        thresholds.lower_threshold_humidity = float(request.form['lower_humidity'])
        thresholds.upper_threshold_humidity = float(request.form['upper_humidity'])
        thresholds.lower_threshold_illuminance = float(request.form['lower_illuminance'])
        thresholds.upper_threshold_illuminance = float(request.form['upper_illuminance'])

        thresholds.measurement_frequency_temperature = float(request.form['measurement_frequency_temperature'])
        thresholds.measurement_frequency_humidity = float(request.form['measurement_frequency_humidity'])
        thresholds.measurement_frequency_illuminance = float(request.form['measurement_frequency_illuminance'])

        db.session.add(thresholds)
        db.session.commit()

        config_data = {
            # "lower_threshold_temperature": thresholds.lower_threshold_temperature,
            # "upper_threshold_temperature": thresholds.upper_threshold_temperature,
            # "lower_threshold_humidity": thresholds.lower_threshold_humidity,
            # "upper_threshold_humidity": thresholds.upper_threshold_humidity,
            # "lower_threshold_illuminance": thresholds.lower_threshold_illuminance,
            # "upper_threshold_illuminance": thresholds.upper_threshold_illuminance,
            "measurement_frequency_temperature": thresholds.measurement_frequency_temperature,
            "measurement_frequency_humidity": thresholds.measurement_frequency_humidity,
            "measurement_frequency_illuminance": thresholds.measurement_frequency_illuminance
        }


        topic = f"{board.user.email}/{board.mac_address}/configuration"

        mqtt_client.mqtt_client.publish(topic, json.dumps(config_data))
        print(f"Published configuration to {topic}")

        flash('Thresholds successfully updated and sent to the device!', 'success')
        return redirect(url_for('configure', board_id=board_id))

    except ValueError as e:
        flash(f'Invalid input: {e}', 'error')
        return redirect(url_for('configure', board_id=board_id))

@app.route('/api/measurements/<int:board_id>', methods=['GET'])
def get_measurements(board_id):
    try:
        temperature_data = TemperatureMeasurement.query.filter_by(board_id=board_id).order_by(
            TemperatureMeasurement.date.desc()).limit(30).all()
        humidity_data = HumidityMeasurement.query.filter_by(board_id=board_id).order_by(
            HumidityMeasurement.date.desc()).limit(30).all()
        illuminance_data = IlluminanceMeasurement.query.filter_by(board_id=board_id).order_by(
            IlluminanceMeasurement.date.desc()).limit(30).all()

        data = {
            "temperature": [{"value": t.temperature, "timestamp": t.date.isoformat(' ','auto')} for t in
                            reversed(temperature_data)],
            "humidity": [{"value": h.humidity, "timestamp": h.date.isoformat(' ','auto')} for h in reversed(humidity_data)],
            "illuminance": [{"value": i.illuminance, "timestamp": i.date.isoformat(' ','auto')} for i in
                            reversed(illuminance_data)],
        }

        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/delete/<int:board_id>', methods=['GET', 'POST'])
def delete_board(board_id):
    board = Board.query.get_or_404(board_id)
    user = User.query.filter_by(id=board.owner_id).first()
    if request.method == 'POST':
        try:
            TemperatureMeasurement.query.filter_by(board_id=board_id).delete()
            HumidityMeasurement.query.filter_by(board_id=board_id).delete()
            IlluminanceMeasurement.query.filter_by(board_id=board_id).delete()

            MeasurementThresholds.query.filter_by(board_id=board_id).delete()

            for topic in mqtt_client.topics:
                mqtt_client.topic_to_subscribe_from_db.remove(f"{user.email}/{board.mac_address}/{topic}")
                mqtt_client.mqtt_client.unsubscribe(f"{user.email}/{board.mac_address}/{topic}")
            print(f"Po usunięciu doniczki o mac {board.mac_address }topice do subskrybowania: {mqtt_client.topic_to_subscribe_from_db} ")
            print(f"Po usunięciu doniczki o mac {board.mac_address} kleinci maile subskrybowania; {mqtt_client.users_emails}")
            # Delete the board itself
            db.session.delete(board)
            db.session.commit()


            flash(f"The board '{board.name}' was successfully deleted.", 'success')
            return redirect('/dashboard')
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while deleting the board: {str(e)}", 'error')
            return redirect('/dashboard')

    return render_template('delete.html', board=board)


if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
