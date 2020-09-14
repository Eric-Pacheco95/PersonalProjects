import pandas as pd
from datetime import datetime
from basketball_reference_web_scraper import client
import joblib
import unicodedata
import numpy as np
import xgboost as xgb
import datetime
from sqlalchemy import *
from sqlalchemy.orm import Session
from sqlalchemy import Table, Column, String, MetaData, Integer, Float
import os

#Load label encoders, player_slugs_names, team abbreviations and team full names from saved joblib objects
player_label_encoder = joblib.load('joblib_objects/player_label_encoder')
team_label_encoder = joblib.load('joblib_objects/team_label_encoder')
player_slugs_names = joblib.load('joblib_objects/player_slugs_names')
team_abbreviations_full_name_dict = joblib.load('joblib_objects/team_abbreviations_full_name_dict')

#Create connections to db_cleaned_data
user = os.environ['RDS_NBA_DATABASE_USER']
password = os.environ['RDS_NBA_DATABASE_PASSWORD']

db_cleaned_data = create_engine(f'postgresql://{user}:{password}@fanduel-lineup-prediction-cleaned-data.cvzkizpca2fx.us-east-1.rds.amazonaws.com')

#Load Advanced Analytics

advanced_analytics_table = pd.read_csv('cleaned_data/advanced_analytics/advanced_analytics_total.csv',index_col=0)
advanced_analytics_columns = advanced_analytics_table.columns

#Define features
base_features = [
    'FD_pts_scored', 'location', 'opponent_id', 'points_scored',
    'seconds_played', 'made_field_goals', 'attempted_field_goals',
    'made_three_point_field_goals', 'attempted_three_point_field_goals',
    'made_free_throws', 'attempted_free_throws', 'offensive_rebounds',
    'defensive_rebounds', 'assists', 'steals', 'blocks', 'turnovers',
    'game_score', 'rest', 'no_rest', '1_day_rest', '2_day_rest', '3_day_rest',
    '4_day_rest', '5_day_rest', '5_plus_day_rest', 'Simple_Rating_System',
    'Offensive_Rating', 'Defensive_Rating', 'Net_Rating', 'Pace',
    'Free_Throw_Rate', '3_Pt_Rate', 'Turnover_Percentage',
    'Offensive_Rebound_Percentage', 'Opponent_EFG',
    'Opponent_Turnover_Percentage', 'Opponent_Defensive_Rebound_Percentage'
]

past_7_features = [
    'points_scored', 'seconds_played', 'made_field_goals',
    'attempted_field_goals', 'made_three_point_field_goals',
    'attempted_three_point_field_goals', 'made_free_throws',
    'attempted_free_throws', 'offensive_rebounds', 'defensive_rebounds',
    'assists', 'steals', 'blocks', 'turnovers', 'game_score'
]

#Function to remove accents and symbols from strings
def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def format_contest_csv(csv_file):

    #Load csv
    contest_df = pd.read_csv(csv_file, index_col=0)
    contest_df = contest_df.rename(columns={'Id': 'FD_player_ID'})
    contest_df = contest_df.loc[contest_df['Injury Indicator'] != 'O', :]

    #Filter columns, format nickname and add player slugs based on nickname
    contest_df = contest_df[['FD_player_ID','Position','Nickname','FPPG','Salary','Game','Opponent']]
    contest_df['Nickname'] = contest_df['Nickname'].apply(lambda x: x.replace('.',''))
    contest_df['Nickname'] = contest_df['Nickname'].apply(lambda x: f"{x.split(' ')[0]} {x.split(' ')[1]}")
    contest_df['slug'] = contest_df['Nickname'].apply(lambda x: player_slugs_names[x])

    # Add binary location column (0 for home, 1 for away)
    contest_df['location'] = ''
    for i in range(len(contest_df)):
        home_team = contest_df['Game'].iloc[i].split('@')[1]
        if contest_df['Opponent'].iloc[i] == home_team:
            location = 1
        else:
            location = 0

        contest_df['location'].iloc[i] = location

    #Convert opponent abbreviation to full team name formatted for team label encoder
    contest_df['Opponent'] = contest_df['Opponent'].apply(lambda x: team_abbreviations_full_name_dict[x])

    #Create two columns with opponent id and player id
    contest_df['Opponent_ID'] = contest_df['Opponent'].apply(lambda x: team_label_encoder.transform([x])[0])
    contest_df['player_ID'] = contest_df['slug'].apply(lambda x: player_label_encoder.transform([x])[0])

    return contest_df

#Function to retrieve model features dataframe for player which includes past week averages and total averages
def get_historic_features(df):

    for feature in past_7_features:
        df[f'{feature}_last_7'] = df[feature].rolling(window=7).mean()

        for i in range(len(df)):
            if i < 7:
                df[f'{feature}_last_7'].iloc[i] = df[feature].iloc[0:(
                    i + 1)].rolling(i + 1).mean().mean()
            else:
                pass

    df_totals = df[past_7_features]

    for feature in past_7_features:
        df_totals[f'{feature}_average'] = ''
        for i in range(len(df_totals)):
            df_totals[f'{feature}_average'].iloc[i] = df_totals[feature].iloc[
                0:i + 1].mean()
        else:
            pass

    df_totals_columns = [f'{feature}_average' for feature in past_7_features]

    df_totals = df_totals[df_totals_columns]

    df_model_features = df
    df_model_features = df_model_features.reset_index()

    df_totals = df_totals.reset_index()

    df_model_features = pd.merge(df_model_features, df_totals, on='index')
    df_model_features = df_model_features.drop('index', axis=1)
    df_model_features = df_model_features.drop('rest', axis=1)
    df_model_features = df_model_features.drop(past_7_features, axis=1)

    return df_model_features

def predict_player_fdpoints(slug, location, opponent_id):

    #Load player csv data
    df = pd.read_sql_table(slug, db_cleaned_data, index_col='index')
    df = df.reset_index(drop=True)

    if len(df) > 5:

        #Define required features from historic data
        X_features = [
            'points_scored_last_7', 'seconds_played_last_7',
            'made_field_goals_last_7', 'attempted_field_goals_last_7',
            'made_three_point_field_goals_last_7',
            'attempted_three_point_field_goals_last_7', 'made_free_throws_last_7',
            'attempted_free_throws_last_7', 'offensive_rebounds_last_7',
            'defensive_rebounds_last_7', 'assists_last_7', 'steals_last_7',
            'blocks_last_7', 'turnovers_last_7', 'game_score_last_7',
            'points_scored_average', 'seconds_played_average',
            'made_field_goals_average', 'attempted_field_goals_average',
            'made_three_point_field_goals_average',
            'attempted_three_point_field_goals_average',
            'made_free_throws_average', 'attempted_free_throws_average',
            'offensive_rebounds_average', 'defensive_rebounds_average',
            'assists_average', 'steals_average', 'blocks_average',
            'turnovers_average', 'game_score_average'
        ]

        #Use get_historic_features function to get historic data and retrieve most recent game with only X features columns
        most_recent_game = get_historic_features(df).iloc[-1]
        most_recent_game_date = most_recent_game['date']
        most_recent_game = most_recent_game[X_features]

        #Get days of rest by calculting from most recent game date
        current_date = datetime.datetime.now()
        days_rest = (current_date - most_recent_game_date).days - 1

        #Create dataframe starting with location and opponent ID
        location_opponent_id_df = pd.DataFrame({
            'location': [location],
            'Opponent_ID': [opponent_id]
        })

        #Add rest columns
        location_opponent_id_df['no_rest'] = 1 if days_rest == 0 else 0
        location_opponent_id_df['1_day_rest'] = 1 if days_rest == 1 else 0
        location_opponent_id_df['2_day_rest'] = 1 if days_rest == 2 else 0
        location_opponent_id_df['3_day_rest'] = 1 if days_rest == 3 else 0
        location_opponent_id_df['4_day_rest'] = 1 if days_rest == 4 else 0
        location_opponent_id_df['5_day_rest'] = 1 if days_rest == 5 else 0
        location_opponent_id_df['5_plus_day_rest'] = 1 if days_rest > 5 else 0

        #Get advanced analytics from opponent ID
        opponent_id = location_opponent_id_df['Opponent_ID'].iloc[0]
        analytics = advanced_analytics_table.loc[
            (advanced_analytics_table['year'] == 2019) &
            (advanced_analytics_table['Team_ID'] == opponent_id),
            advanced_analytics_columns[2:]]
        analytics = analytics[[
            'Simple_Rating_System', 'Offensive_Rating', 'Defensive_Rating',
            'Net_Rating', 'Pace', 'Free_Throw_Rate', '3_Pt_Rate',
            'Turnover_Percentage', 'Offensive_Rebound_Percentage', 'Opponent_EFG',
            'Opponent_Turnover_Percentage', 'Opponent_Defensive_Rebound_Percentage'
        ]]

        prediction_df = pd.concat([location_opponent_id_df.iloc[0], analytics.iloc[0], most_recent_game], axis=0)
        prediction_testing_array = pd.DataFrame(prediction_df).transpose().values

        player_xgb_model = joblib.load(f'models/{slug}_model.dat')
        prediction = player_xgb_model.predict(prediction_testing_array)

        return prediction
    
    else:
        pass

def predict_full_lineup(csv_file):

    #Load formatted contest csv into pandas dataframe
    contest_df = format_contest_csv(csv_file)

    predictions_df = pd.DataFrame(columns=['slug','pts_spread','position','salary'])
    for slug in contest_df:
        #Predict fd_pts and compare to projection based on fd listed salary
        fd_pts_prediction = predict_player_fdpoints(contest_df['slug'])
        player_position = contest_df['Position']
        pts_projection = (contest_df['Salary'] / 1000) * 5
        pts_spread = (fd_pts_prediction - pts_projection) / 10

        #Add row to predictions_df
        predictions_df.append({'slug':contest_df['slug'], 'pts_spread':pts_spread,
                                'position':player_position, 'salary':contest_df['Salary']},ignore_index=True)

        #Create top value df
        sorted_predictions_df = predictions_df.sort_values('pts_spread',ascending=True)

        #Create top value dfs for each position
        sorted_predictions_pg_df = predictions_df.loc[predictions_df['position'] == 'PG'].sort_values('pts_spread',ascending=True).iloc[:5]
        sorted_predictions_sg_df = predictions_df.loc[predictions_df['position'] == 'SG'].sort_values('pts_spread',ascending=True).iloc[:5]
        sorted_predictions_sf_df = predictions_df.loc[predictions_df['position'] == 'SF'].sort_values('pts_spread',ascending=True).iloc[:5]
        sorted_predictions_pf_df = predictions_df.loc[predictions_df['position'] == 'PF'].sort_values('pts_spread',ascending=True).iloc[:5]
        sorted_predictions_c_df = predictions_df.loc[predictions_df['position'] == 'C'].sort_values('pts_spread', ascending=True).iloc[:5]

        # List of FD positions.
        FD_POSITION_LIST = ['PG', 'SG', 'PF', 'SF', 'C']
        salaries = predictions_df['Salary'].to_numpy()
        values = predictions_df['pts_spread'].to_numpy()

def get_lineup(csv_file):

    contest_df = format_contest_csv(csv_file)

    predictions_df = pd.DataFrame(columns=[
        'slug', 'projected_fd_pts',
        'pts_spread', 'position', 'salary'
    ])

    for i in range(len(contest_df)):

        try:

            #Define parameters for player
            slug = contest_df.iloc[i]['slug']
            location = contest_df.iloc[i]['location']
            position = contest_df.iloc[i]['Position']
            salary = contest_df.iloc[i]['Salary']
            opponent_id = contest_df.iloc[i]['Opponent_ID']

            #Predict player projection and get pts_spread
            prediction = predict_player_fdpoints(slug, location, opponent_id)[0]
            pts_projection = (salary / 1000) * 5
            pts_spread = (prediction - pts_projection) / 10

            #Add new row to predictions
            predictions_df = predictions_df.append(
                {
                    'slug': slug,
                    'projected_fd_pts': prediction,
                    'pts_spread': pts_spread,
                    'position': position,
                    'salary': salary
                },
                ignore_index=True)
        
        except Exception as e:
            print(e)

    #Create top value df
    sorted_predictions_df = predictions_df.sort_values('pts_spread', ascending=False)

    #Create top value dfs for each position
    pgs = predictions_df.loc[predictions_df['position'] == 'PG'].sort_values('pts_spread', ascending=False).iloc[:6]
    sgs = predictions_df.loc[predictions_df['position'] == 'SG'].sort_values('pts_spread', ascending=False).iloc[:6]
    sfs = predictions_df.loc[predictions_df['position'] == 'SF'].sort_values('pts_spread', ascending=False).iloc[:6]
    pfs = predictions_df.loc[predictions_df['position'] == 'PF'].sort_values('pts_spread', ascending=False).iloc[:6]
    cs = predictions_df.loc[predictions_df['position'] =='C'].sort_values('pts_spread',ascending=False).iloc[:4]

    return pgs,sgs,sfs,pfs,cs