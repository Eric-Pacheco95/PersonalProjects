from sqlalchemy import *
from sqlalchemy.orm import Session
from sqlalchemy import Table, Column, String, MetaData, Integer, Float
import os
import pandas as pd
import datetime as datetime
from basketball_reference_web_scraper import client
import joblib

#Get db user and password from environment variables
user = os.environ['RDS_NBA_DATABASE_USER']
password = os.environ['RDS_NBA_DATABASE_PASSWORD']

#Create connections to both db_scraped_data and db_cleaned_data
db_scraped_data = create_engine(f'postgresql://{user}:{password}@fanduel-lineup-prediction-scraped-data.cvzkizpca2fx.us-east-1.rds.amazonaws.com')
db_cleaned_data = create_engine(f'postgresql://{user}:{password}@fanduel-lineup-prediction-cleaned-data.cvzkizpca2fx.us-east-1.rds.amazonaws.com')

#Load Advanced Analytics
advanced_analytics_table = pd.read_csv('cleaned_data/advanced_analytics/advanced_analytics_total.csv', index_col=0)
advanced_analytics_columns = advanced_analytics_table.columns
advanced_analytics_columns[2:]

#Function to get yesterday's boxscores and create player dataframe
def get_boxscores_yesterday():

    #Load player and team label encoders
    player_label_encoder = joblib.load('joblib_objects/player_label_encoder')
    team_label_encoder = joblib.load('joblib_objects/team_label_encoder')

    #Define column names from box scores
    columns_names = [
        'slug', 'name', 'location', 'opponent', 'seconds_played',
        'made_field_goals', 'attempted_field_goals',
        'made_three_point_field_goals', 'attempted_three_point_field_goals',
        'made_free_throws', 'attempted_free_throws', 'offensive_rebounds',
        'defensive_rebounds', 'assists', 'steals', 'blocks', 'turnovers',
        'game_score'
    ]

    #Empty Dataframe to store player keys and respective dataframes containing box scores
    player_dataframes = {}

    #Get yesterdays date
    today_date = datetime.datetime.today() - datetime.timedelta(days=1)
    today_date = datetime.datetime.strptime(f"{today_date.year}-{today_date.month}-{today_date.day}", "%Y-%m-%d")

    #Get box scores for yesterday
    box_scores = client.player_box_scores(day=today_date.day, month=today_date.month,year=today_date.year)

    #Loop through each box score and add stat line to respective player's dataframes in player_dataframes
    for player in box_scores:
        if player not in list(player_dataframes.keys()):

            player_columns_names = ['date','slug','name','player_id','positions','FD_pts_scored','location','opponent','opponent_id','points_scored','seconds_played','made_field_goals','attempted_field_goals','made_three_point_field_goals',
                    'attempted_three_point_field_goals','made_free_throws','attempted_free_throws','offensive_rebounds','defensive_rebounds',
                    'assists','steals','blocks','turnovers','game_score']

            player_dataframes[player['slug']] = pd.DataFrame(columns=player_columns_names)
        else:
            pass

        #Create dataframe from player boxscore, filter for only needed columns, then convert back to dictionary format
        player_box_score = pd.DataFrame([player])
        player_box_score = player_box_score[columns_names].to_dict('index')[0]

        #Add date to row
        player_box_score['date'] = today_date

        #Format Team Name
        player_box_score['opponent'] = str(player_box_score['opponent']).split('.')[1]

        #Add player ID
        player_id = player_label_encoder.transform([player['slug']])
        player_box_score['player_id'] = player_id[0]

        #Add opponent ID
        opponent_id = team_label_encoder.transform([str(player_box_score['opponent'])])
        player_box_score['opponent_id'] = opponent_id[0]

        #Add points scored
        points_scored = (player['made_field_goals'] * 2) + player['made_three_point_field_goals'] + player['made_free_throws']
        player_box_score['points_scored'] = points_scored

        #Add fanduel points scored
        fd_pts_scored = (points_scored + ( (player['offensive_rebounds']+player['defensive_rebounds']) * 1.2 ) + (player['assists']*1.5) +
                        (player['steals']*3) + (player['blocks']*3) - player['turnovers'])
        player_box_score['FD_pts_scored'] = fd_pts_scored

        #Format Location
        player_box_score['location'] = str(player_box_score['location'])

        #Add boxscore to player_dataframes based on dictionary key ('slug')
        player_dataframes[player['slug']] = player_dataframes[player['slug']].append(player_box_score, ignore_index=True)

    return player_dataframes

#Get nba season dates for 4 nba seasons (2016-2020)
nba_season_start_end_dates = {'2016-2017':[datetime.datetime(2016,10,25),datetime.datetime(2017,4,12)],
                             '2017-2018':[datetime.datetime(2017,10,17),datetime.datetime(2018,4,11)],
                             '2018-2019':[datetime.datetime(2018,10,16),datetime.datetime(2019,4,10)],
                             '2019-2020':[datetime.datetime(2019,10,22),datetime.datetime(2020,8,14)]}

nba_2016_to_2017_dates = [nba_season_start_end_dates['2016-2017'][0] + datetime.timedelta(days=x) for x in range((nba_season_start_end_dates['2016-2017'][1]-nba_season_start_end_dates['2016-2017'][0]).days+1)]
nba_2017_to_2018_dates = [nba_season_start_end_dates['2017-2018'][0] + datetime.timedelta(days=x) for x in range((nba_season_start_end_dates['2017-2018'][1]-nba_season_start_end_dates['2017-2018'][0]).days+1)]
nba_2018_to_2019_dates = [nba_season_start_end_dates['2018-2019'][0] + datetime.timedelta(days=x) for x in range((nba_season_start_end_dates['2018-2019'][1]-nba_season_start_end_dates['2018-2019'][0]).days+1)]
nba_2019_to_2020_dates = [nba_season_start_end_dates['2019-2020'][0] + datetime.timedelta(days=x) for x in range((nba_season_start_end_dates['2019-2020'][1]-nba_season_start_end_dates['2019-2020'][0]).days+1)]

#Function that gets the season period a date falls under
def get_season_year(x):
    if x in nba_2016_to_2017_dates:
        return 2016
    elif x in nba_2017_to_2018_dates:
        return 2017
    elif x in nba_2018_to_2019_dates:
        return 2018
    else:
        return 2019

#Function to retrieve the corresponding advanced analytics based on opponent id and year
def get_advanced_analytics(x):
    analytics = advanced_analytics_table.loc[
        (x['year'] == advanced_analytics_table['year']) &
        (x['opponent_id'] == advanced_analytics_table['Team_ID']),
        advanced_analytics_columns[2:]]

    return analytics

#Gets formatted new row which takes the last entry and adds relevent column data
def get_new_row(df):

    #Get last row of dataframe
    new_row = df.iloc[-1:]

    #Add new column which has the number of rest days
    new_row['rest'] = df.loc[
        -1:, :]['date'] - df.iloc[-2]['date'] - datetime.timedelta(days=1)

    #Add binary columns (1 or 0 based on condition)
    new_row['no_rest'] = new_row['rest'].apply(
        lambda x: 1 if (x == datetime.timedelta(days=0)) else 0)
    new_row['1_day_rest'] = new_row['rest'].apply(
        lambda x: 1 if (x == datetime.timedelta(days=1)) else 0)
    new_row['2_day_rest'] = new_row['rest'].apply(
        lambda x: 1 if (x == datetime.timedelta(days=2)) else 0)
    new_row['3_day_rest'] = new_row['rest'].apply(
        lambda x: 1 if (x == datetime.timedelta(days=3)) else 0)
    new_row['4_day_rest'] = new_row['rest'].apply(
        lambda x: 1 if (x == datetime.timedelta(days=4)) else 0)
    new_row['5_day_rest'] = new_row['rest'].apply(
        lambda x: 1 if (x == datetime.timedelta(days=5)) else 0)
    new_row['5_plus_day_rest'] = new_row['rest'].apply(
        lambda x: 1 if (x > datetime.timedelta(days=5)) else 0)

    #Get the season the game was played in
    year = new_row['date'].apply(get_season_year).values[0]

    #Add advanced analytics columns and define them as empty for now
    for column in advanced_analytics_columns[2:]:
        new_row[column] = ''

    #Get corresponding advanced analytics and fill empty columns with respective data
    analytics = advanced_analytics_table.loc[
        (year == advanced_analytics_table['year']) &
        (new_row['opponent_id'].values[0] ==
         advanced_analytics_table['Team_ID']), advanced_analytics_columns[2:]]
    new_row.iloc[0, 32:] = analytics.iloc[0].to_list()

    return new_row

#Adds new boxscores to db_scraped_data if the dates for the boxscores do not already exist
def add_boxscores_to_scraped_database(player_dataframes):

    counter = 0

    for player in player_dataframes.keys():

        db_df_scraped = pd.read_sql_table(player, db_scraped_data, index_col='index')

        date = player_dataframes[player]['date'].to_list()[0]

        if date not in db_df_scraped['date'].to_list():

            player_dataframes[player].to_sql(player, db_scraped_data, if_exists='append')
            counter += 1
        
        else:
            pass
    
    return counter

#Adds new cleaned boxscores to db_cleaned_data if the dates do not already exists in db
def add_boxscores_to_cleaned_database(player_dataframes):

    for player in player_dataframes.keys():

        db_df_scraped = pd.read_sql_table(player,db_scraped_data, index_col='index')
        db_df_scraped = db_df_scraped.reset_index(drop=True)

        db_df_cleaned = pd.read_sql_table(player,db_cleaned_data, index_col='index')

        new_row = get_new_row(db_df_scraped)

        date = new_row['date'].to_list()[0]

        if date not in db_df_cleaned['date'].to_list():

            new_row.to_sql(player, db_cleaned_data, if_exists='append')

        else:
            pass

#Cumulative function which will add boxscores to db_scraped_data and then the formatted boxscores to db_cleaned_data
def run_all_functions():

    player_dataframes = get_boxscores_yesterday()
    counter = add_boxscores_to_scraped_database(player_dataframes)
    add_boxscores_to_cleaned_database(player_dataframes)

    update_logs_df = pd.read_csv('update/logs/update_logs.csv',index_col=0)
    update_logs_df.append({'Date':datetime.datetime.today(), 'Number_Players_Updated': counter})
    update_logs_df.to_csv('update/logs/update_logs.csv')
    
run_all_functions()