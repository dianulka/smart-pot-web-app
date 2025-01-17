

from flask import Flask, render_template, request, redirect,session
from flask_socketio import SocketIO
from mqtt.mqtt_client import MqqtClient
from flask_sqlalchemy import SQLAlchemy
import json
import bcrypt

app = Flask(__name__)
socketio = SocketIO(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
mqtt_client = MqqtClient(socketio, 'diana332m@gmail.com')

db = SQLAlchemy(app)
app.secret_key = 'secret_key'


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
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
    mac_address = db.Column(db.String(20), unique=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100), nullable=False)


# class Measurement(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     board_id = db.Column(db.Integer, db.ForeignKey('board.id'))
#     temperature = db.Column(db.Float, nullable=True)
#     humidity = db.Column(db.Float, nullable=True)
#     illuminance = db.Column(db.Float, nullable=True)
#     date = db.Column(db.DateTime, nullable=False)
#
#     board = db.relationship('Board', backref='environmental_measurements')


with app.app_context():
    # Drop and recreate tables
    db.drop_all()
    db.create_all()

    # Create a sample user
    user = User(name="John Doe", email="john@example.com", password="password123")
    db.session.add(user)
    db.session.commit()

    # Add some boards for the user
    board1 = Board(name="Living Room Pot", mac_address="00:1A:2B:3C:4D:5E", owner_id=user.id)
    board2 = Board(name="Bedroom Pot", mac_address="00:1A:AB:3C:4D:5F", owner_id=user.id)
    db.session.add_all([board1, board2])
    db.session.commit()

    print("Database reset and seeded successfully!")


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
    # Fetch the specific pot (board) by its ID
    board = Board.query.get_or_404(board_id)
    user = User.query.filter_by(id=board.owner_id).first()

    # # Dodanie nowych obiektów Board
    # board3 = Board(name="Living RoomDDDD Pot", mac_address="00:1A:2B:3C:4DX:6G", owner_id=user.id)
    # board4 = Board(name="Bedroom FFFFFMSMSMSPot", mac_address="00:1A:AB:3DDC:4D:6H", owner_id=user.id)
    #
    # db.session.add_all([board3, board4])
    # db.session.commit()  # Zapisanie zmian do bazy danych

    # Pass the board and user data to the template
    return render_template(
        'pot.html',
        user=user,
        board=board
    )

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
