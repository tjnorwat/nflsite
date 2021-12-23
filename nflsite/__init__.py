import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pV4HlTJ7IFIk2LZp8EQGuPhvEjpKuunm'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'



from nflsite import routes


# how work ? ?
# setting up db for first time use
from nflsite import db
if not os.path.exists('database.db'): 
    db.create_all()


# more setup 
# setting up team table 
from nflsite.models import Team
rows = Team.query.first()
if not rows:
    bulk = list()
    teams_logo = os.listdir('nflsite/static/team_logo')
    teams = [team.split('.')[0] for team in teams_logo]
    for team in teams:
        bulk.append(Team(name=team, image_file=team + '.png'))
    db.session.bulk_save_objects(bulk)
    db.session.commit()
