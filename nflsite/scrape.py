from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager
from nflsite import db
from nflsite.models import *


def getSource():
    chrome_options = Options()
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--headless')

    url = 'https://www.nfl.com/schedules'
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    driver.get(url)
    source = driver.page_source

    # with open('nflsite/out.html', 'w', encoding='utf-8') as f:
    #     f.write(source)

    driver.quit()
    return source

def getData():
    data = dict()

    # with open('nflsite/out.html') as f:
    #     soup = BeautifulSoup(f.read(), 'lxml')
    soup = BeautifulSoup(getSource(), 'lxml')
    
    year_title = soup.find('h2', class_='nfl-c-content-header__roofline').getText()

    year = int(year_title.split()[0])
    data['year'] = year

    week = year_title.split()[2:]
    week = ' '.join(week)
    data['week'] = week

    games_list = list()

    sections = soup.find_all('section', class_='d3-l-grid--outer d3-l-section-row nfl-o-matchup-group')
    for section in sections:
        day = section.find('h2', class_='d3-o-section-title').getText()
        month = datetime.strptime(day.split()[1], '%B').month
        day = int(day.split()[2][:-2])

        games = section.find_all('div', class_='nfl-c-matchup-strip')

        for game in games:
            game_metadata = dict()

            teams = game.find_all('span', class_='nfl-c-matchup-strip__team-fullname')
            teams = [team.getText().strip() for team in teams]

            game_metadata['teams'] = teams

            records = game.find_all('div', class_='nfl-c-matchup-strip__record')
            records = [record.getText().strip() for record in records]

            game_metadata['records'] = records

            over = game.find('p', class_='nfl-c-matchup-strip__period')
            # over can either be FINAL/OT or a LIVE game 
            if over:
                over = over.getText().strip()
                if 'FINAL' in over:
                    scores = game.find_all('div', class_='nfl-c-matchup-strip__team-score')
                    scores = [score['data-score'] for score in scores]
                    scores = f'{scores[0]}-{scores[1]}'

                    date = datetime(year, month, day)
                    
                    game_metadata['over'] = over
                    game_metadata['scores'] = scores
                # game is live
                else:
                    date = datetime(year, month, day)
                    game_metadata['over'] = None
                    game_metadata['scores'] = None
            else:
                time = game.find('span', class_='nfl-c-matchup-strip__date-time').getText().strip()
                # timezone = game.find('span', class_='nfl-c-matchup-strip__date-timezone').getText().strip()

                time = datetime.strptime(time, '%I:%M %p')
                date = datetime(year, month, day, time.hour, time.minute)

                game_metadata['over'] = None
                game_metadata['scores'] = None            

            game_metadata['date'] = date
            games_list.append(game_metadata)
            #print(date.strftime('%I:%M %p'))

    data['games'] = games_list
    return data

'''
{'teams': ['Chiefs', 'Chargers'], 'records': ['(10-4)', '(8-6)'], 'over': 'FINAL/OT', 'scores': '34-28', 'date': datetime.datetime(2021, 12, 16, 0, 0)}
{'teams': ['Washington', 'Eagles'], 'records': ['(6-7)', '(6-7)'], 'over': None, 'scores': None, 'date': datetime.datetime(2021, 12, 21, 18, 0)}
'''
def dataToDB():
    data = getData()
    bulk = list()
    
    year = data['year']
    week = data['week']

    # keep track of season/week (for picks route)
    curr_season = CurrentSeason.query.get(1)
    # first time setting up
    if not curr_season:
        curr_season = CurrentSeason(year=year, week=week)
        bulk.append(curr_season)

    elif curr_season.week != week:
        # check to see if we need to update the season
        curr_season.year = year
        curr_season.week = week
        db.session.commit()


    all_season = AllSeasons.query.filter_by(year=year, week=week).first()
    if not all_season:
        all_season = AllSeasons(year=year, week=week)
        bulk.append(all_season)

    game_over_ids = list()
    for game in data['games']:

        team1_id = Team.query.filter_by(name=game['teams'][0]).first().id
        team2_id = Team.query.filter_by(name=game['teams'][1]).first().id
        date = game['date']

        # if the game is over add it to team winner
        if game['over']:
            # lookup game in team match for id 
            match_id = TeamMatch.query.filter(db.extract('year', TeamMatch.date) == date.year, 
                                              db.extract('month', TeamMatch.date) == date.month, 
                                              db.extract('day', TeamMatch.date) == date.day, 
                                              TeamMatch.team1_id == team1_id,
                                              TeamMatch.team2_id == team2_id).first()

            # do i need this ? 
            if match_id:
                match_id = match_id.id
            else:
                # no match found, skip
                continue
            
            # using this for user record later down script
            game_over_ids.append(match_id)

            # add to team winner 
            # check to see if game is already in db
            if not TeamWinner.query.filter_by(match_id=match_id).first():
                # add the scores 
                scores = game['scores']

                temp_score = scores.split('-')
                if temp_score[0] > temp_score[1]:
                    winner = team1_id
                elif temp_score[0] < temp_score[1]:
                    winner = team2_id
                else:
                    # in case of tie ?
                    winner = None

                bulk.append(TeamWinner(match_id=match_id, scores=scores, winner=winner))

        else:
            # add to team record 
            # check to see if first team is already in db 
            if not TeamRecord.query.filter_by(team_id=team1_id, year=year, week=week).first():
                bulk.append(TeamRecord(team_id=team1_id, year=year, week=week, record=game['records'][0]))

            # check to see if second is team is already in db 
            if not TeamRecord.query.filter_by(team_id=team2_id, year=year, week=week).first():
                bulk.append(TeamRecord(team_id=team2_id, year=year, week=week, record=game['records'][1]))

            # check to see if game is already in db 
            if not TeamMatch.query.filter_by(team1_id=team1_id, team2_id=team2_id, date=date).first():
                
                bulk.append(TeamMatch(team1_id=team1_id, team2_id=team2_id, date=date, week=week))

    db.session.bulk_save_objects(bulk)
    db.session.commit()

    # only update user records once all games are finished 
    if len(game_over_ids) == len(data['games']):
        updateUserRecord(game_over_ids)


def updateUserRecord(game_over_ids):
    bulk = list()
    users = User.query.all()
    curr_season = CurrentSeason.query.get(1)
    for user in users:
        wins = 0
        losses = 0
        ties = 0

        for match_id in game_over_ids:
            user_pick = UserPick.query.filter_by(user_id=user.id, match_id=match_id).first()
            if user_pick:
                team_winner = TeamWinner.query.filter_by(match_id=match_id).first()

                if user_pick.team_id == team_winner.winner:
                    wins += 1
                # see if winner is not null (null means tie)
                elif team_winner.winner:
                    losses += 1
                else:
                    ties += 1
        
        # get last record and add to new record 
        last_record = UserRecord.query.filter_by(user_id=user.id).order_by(UserRecord.id.desc()).first()
       
        if last_record:
            # making sure a new year hast started yet 
            if last_record.year == curr_season.year:
                split_record = last_record.record.remove('(').remove(')').split('-')
                # seeing if there were any ties 
                if len(split_record) == 2:
                    last_wins = split_record[0]
                    last_losses = split_record[1]
                    last_ties = 0
                else:
                    last_wins = split_record[0]
                    last_losses = split_record[1]
                    last_ties = split_record[2]

                wins += last_wins
                losses += last_losses
                ties += last_ties

        # putting record back together to store
        if ties:
            new_record = f'({wins}-{losses}-{ties})'
        else:
            new_record = f'({wins}-{losses})'

        # i think i can remove this 
        # check to see if we need to udpate record
        # user_record = UserRecord.query.filter_by(user_id=user.id, year=curr_season.year, week=curr_season.week).first()
        # if user_record:
        #     if new_record != user_record.record:
        #         user_record.record = new_record
        # else:
        #     bulk.append(UserRecord(user_id=user.id, year=curr_season.year, week=curr_season.week, record=new_record))

        bulk.append(UserRecord(user_id=user.id, year=curr_season.year, week=curr_season.week, record=new_record))

    db.session.bulk_save_objects(bulk)
    db.session.commit()


if __name__ == '__main__':
    data = getData()
