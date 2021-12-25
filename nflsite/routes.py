import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request
from nflsite import app, db, bcrypt
from nflsite.forms import RegistrationForm, LoginForm, UpdateAccountForm
from nflsite.models import User, UserRecord, Team, TeamMatch, TeamWinner, UserPick, TeamRecord, CurrentSeason
from flask_login import login_user, current_user, logout_user, login_required

from nflsite.scrape import dataToDB, getSource


@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')


@app.route("/about")
def about():
    return render_template('about.html')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'error')
    return render_template('login.html', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', image_file=image_file, form=form)


@app.route("/picks", methods=['GET', 'POST'])
@login_required
def picks():
    curr_season = CurrentSeason.query.get(1)
    matches = TeamMatch.query.filter(db.extract('year', TeamMatch.date) == curr_season.year, 
                                     TeamMatch.week == curr_season.week).all()

    if request.method == 'GET':
        
        match_data = {'season' : curr_season}
        data_list = list()
        for match in matches:
            team1 = Team.query.get(match.team1_id)
            team2 = Team.query.get(match.team2_id)

            # add if game is over or not , datetime 
            d_dict = {
                'team1_id' : team1.id,
                'team1_name' : team1.name,
                'team1_image' : 'team_logo/' + team1.image_file,
                'team2_id' : team2.id,
                'team2_name' : team2.name,
                'team2_image' : 'team_logo/' + team2.image_file,
                'match_id' : match.id,
                'match_date' : match.date                
            }

            user_pick = UserPick.query.filter_by(user_id=current_user.id, match_id=match.id).first()
            # if the user has already picked their team, show them 
            if user_pick:
                d_dict['user_pick'] = user_pick.team_id
            else:
                d_dict['user_pick'] = None

            data_list.append(d_dict)
        
        match_data['data'] = data_list
        return render_template('picks.jinja', matches=match_data)

    elif request.method == 'POST':
        # print(request.values)

        bulk = list()
        for match in matches:
            
            # choosing which matches to vote for are optional
            team_id = request.form.get(f'matchid_{match.id}')
            if team_id:
                user_id = current_user.id
                match_id = match.id
                # check to see if user already voted for a match
                # if user has already picked a match, update it
                has_picked = UserPick.query.filter_by(user_id=user_id, match_id=match_id).first()
                if has_picked:
                    # if user has changed their pick, update it
                    if has_picked.team_id != team_id: 
                        has_picked.team_id = team_id
                else:
                    bulk.append(UserPick(user_id=user_id, team_id=team_id, match_id=match_id))

        db.session.bulk_save_objects(bulk)
        db.session.commit()

        flash('Your picks have been saved!', 'success')
        return redirect(url_for('picks'))


@app.route('/test_db', methods=['GET'])
def test_db():
    #getSource()
    dataToDB()
    
    return 'HELLO'

