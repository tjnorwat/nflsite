import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_apscheduler import APScheduler

# set configuration values
class Config:
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "America/Chicago"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pV4HlTJ7IFIk2LZp8EQGuPhvEjpKuunm'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config.from_object(Config())
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


# initialize scheduler
scheduler = APScheduler()
# if you don't wanna use a config, you can set options here:
# scheduler.api_enabled = True
scheduler.init_app(app)
scheduler.start()


from nflsite import routes

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

# getting schedule data and adding to db
from nflsite.scrape import dataToDB
from nflsite.models import TeamMatch

@scheduler.task('interval', id='db_1', hours=6)
def scheduleData():
    dataToDB()

match = TeamMatch.query.get(1)
if not match:
    dataToDB()