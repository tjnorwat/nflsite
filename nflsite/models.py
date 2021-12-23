from nflsite import db, login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    image_file = db.Column(db.String(50), nullable=False, default='default.jpg')

    def __repr__(self):
        return f'User("{self.username}", "{self.email}")'


class UserRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    week = db.Column(db.String(30), nullable=False)
    record = db.Column(db.String(10), nullable=False)


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)
    image_file = db.Column(db.String(50), unique=True, nullable=False)


class TeamMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team1_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    team2_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    week = db.Column(db.String(30), nullable=False)


class TeamWinner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('team_match.id'), nullable=False)
    scores = db.Column(db.String(10), nullable=False)
    winner = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)


class UserPick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('team_match.id'), nullable=False)


class TeamRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    week = db.Column(db.String(30), nullable=False)
    record = db.Column(db.String(10), nullable=False)


class CurrentSeason(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    week = db.Column(db.String(30), nullable=False)