from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime

from nflsite import db
from nflsite.models import *


url = 'https://www.nfl.com/schedules/2021/REG15/'


def getSource():
    chrome_options = Options()
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--headless')

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    source = driver.page_source

    with open('nflsite/out.html', 'w', encoding='utf-8') as f:
        f.write(source)

    driver.quit()

def getData():
    data = dict()

    with open('nflsite/week15_before.html') as f:
        soup = BeautifulSoup(f.read(), 'lxml')
    
    year_title = soup.find('h2', class_='nfl-c-content-header__roofline').getText()

    year = int(year_title.split()[0])

    week = year_title.split()[2:]
    week = ' '.join(week)
    data['week'] = week

    games_list = list()

    # keep track of season/week (for picks route)
    curr_season = CurrentSeason.query.get(1)
    # first time setting up
    if not curr_season:
        curr_season = CurrentSeason(year=year, week=week)
        db.session.add(curr_season)
        db.session.commit()

    elif curr_season.week != week:
        # check to see if we need to update the season
        curr_season.year = year
        curr_season.week = week
        db.session.commit()


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
            
            if over:
                over = over.getText().strip()
                scores = game.find_all('div', class_='nfl-c-matchup-strip__team-score')
                scores = [score['data-score'] for score in scores]
                scores = f'{scores[0]}-{scores[1]}'

                date = datetime(year, month, day)
                
                game_metadata['over'] = over
                game_metadata['scores'] = scores
            
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

    week = data['week']
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
                                              TeamMatch.team1_id==team1_id,
                                              TeamMatch.team2_id==team2_id).first()

            if match_id:
                match_id = match_id.id
            else:
                # no match found, skip
                continue

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
                    winner = team1_id

                bulk.append(TeamWinner(match_id=match_id, scores=scores, winner=winner))

        # add to team match
        else:
            # check to see if game is already in db 
            if not TeamMatch.query.filter_by(team1_id=team1_id, team2_id=team2_id, date=date).first():
                bulk.append(TeamMatch(team1_id=team1_id, team2_id=team2_id, date=date, week=week))

    db.session.bulk_save_objects(bulk)
    db.session.commit()


if __name__ == '__main__':
    data = getData()
