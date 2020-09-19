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
from sklearn.preprocessing import MinMaxScaler
from pulp import *

#Load label encoders, player_slugs_names, team abbreviations and team full names from saved joblib objects
player_label_encoder = joblib.load('joblib_objects/player_label_encoder')
team_label_encoder = joblib.load('joblib_objects/team_label_encoder')
player_slugs_names = joblib.load('joblib_objects/player_slugs_names')
team_abbreviations_full_name_dict = joblib.load('joblib_objects/team_abbreviations_full_name_dict')

#Reversed dictionary of player_slugs_names - slugs as keys, values as player names
player_slugs_then_names = {value:key for key,value in player_slugs_names.items()}

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


#Function to format contest csv 
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

    #Make empty dictionary to hold features
    historic_features = {}

    #Get past 7 games
    df_past_7_games = df.iloc[-7:]

    #Add past 7 games basic stats averages and store in historic_features
    for feature in past_7_features:
        historic_features[f'{feature}_last_7'] = [df_past_7_games[feature].mean()]
    
    #Add all-time games basic stats averages and store in historic_features
    for feature in past_7_features:
        historic_features[f'{feature}_average'] = [df[feature].mean()]

    #Create dataframe that contains all new averages
    historic_features_df = pd.DataFrame(historic_features)

    return historic_features_df

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
        most_recent_game = get_historic_features(df)
        most_recent_game_date = df.iloc[-1]['date']

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

        #Concatenate 3 dataframes into one then produce values as list
        prediction_series = pd.concat([location_opponent_id_df.iloc[0], analytics.iloc[0], most_recent_game.iloc[0]])
        prediction_df = pd.DataFrame(prediction_series.to_dict(),index=[0])
        prediction_testing_array = prediction_df.values
        
        #Load MinMaxScaler based on slug and transform values 
        scaler = joblib.load(f'scalers/{slug}_scaler')

        prediction_testing_array = scaler.transform(prediction_testing_array)

        #Get prediction by loading model based on slug and using prediction_testing_array to produce prediction
        player_xgb_model = joblib.load(f'models/{slug}_model.dat')
        prediction = player_xgb_model.predict(prediction_testing_array)

        return prediction
    
    else:
        pass

#Function to get all predictions for players in contest over 3500 salary
def get_predictions(contest_df):

    #Create empty dataframe to hold all projections
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

            if salary > 3500:

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
            
            else:
                pass
        
        except Exception as e:
            print(e)

    #Create top value df
    sorted_predictions_df = predictions_df.sort_values('pts_spread', ascending=False)

    #Create top value list for each position
    pgs = predictions_df.loc[predictions_df['position'] == 'PG'].sort_values('pts_spread', ascending=False).iloc[:6].values
    sgs = predictions_df.loc[predictions_df['position'] == 'SG'].sort_values('pts_spread', ascending=False).iloc[:6].values
    sfs = predictions_df.loc[predictions_df['position'] == 'SF'].sort_values('pts_spread', ascending=False).iloc[:6].values
    pfs = predictions_df.loc[predictions_df['position'] == 'PF'].sort_values('pts_spread', ascending=False).iloc[:6].values
    cs = predictions_df.loc[predictions_df['position'] =='C'].sort_values('pts_spread',ascending=False).iloc[:4].values

    return pgs,sgs,sfs,pfs,cs

#Function to get optimized lineup
def get_optimized_lineup(pgs,sgs,sfs,pfs,cs):

    #Make empty dictionaries that will hold salary and points info for each player
    salaries = {}
    points = {}

    #Fill salaries and points dictionaries with player info
    for position in [pgs,sgs,sfs,pfs,cs]:
        
        player_salaries = {}
        player_points = {}
        position_dictionary_key = position[0][3]
        
        for player in position:
            
            player_salaries[player[0]] = player[4]
            player_points[player[0]] = player[2]
            
        salaries[position_dictionary_key] = player_salaries
        points[position_dictionary_key] = player_points

    #Set lineup constraints
    pos_num_available = {
        "PG": 2,
        "SG": 2,
        "SF": 2,
        "PF": 2,
        "C": 1
    }

    #Salary cap constraints
    SALARY_CAP = 60000
    MINIMUM_SALARY_USE = 59000

    #Binary variable to determine if player is included or excluded in lineup
    _vars = {k: LpVariable.dict(k, v, cat="Binary") for k, v in points.items()}

    #Set problem as maximize 
    prob = LpProblem("Fantasy", LpMaximize)
    rewards = []
    costs = []
    position_constraints = []
    
    #Insert problem constraints into LpProblem object
    for k, v in _vars.items():
        costs += lpSum([salaries[k][i] * _vars[k][i] for i in v])
        rewards += lpSum([points[k][i] * _vars[k][i] for i in v])
        prob += lpSum([_vars[k][i] for i in v]) == pos_num_available[k]
    
    prob += lpSum(rewards)
    prob += lpSum(costs) <= SALARY_CAP
    prob += lpSum(costs) >= MINIMUM_SALARY_USE

    #Solve problem
    prob.solve()

    #Create empty dataframe top hold optimal lineup
    optimized_lineup_df = pd.DataFrame(columns=['Player','Salary','Position'])
    
    #Fill optimized_lineup_df with optimized lineup
    for v in prob.variables():
    
        score = str(prob.objective)
        constraints = [str(const) for const in prob.constraints.values()]
        score = score.replace(v.name, str(v.varValue))
        constraints = [const.replace(v.name, str(v.varValue)) for const in constraints]
        
        if v.varValue != 0:
            v_str_split = str(v).split('_')
            slug = v_str_split[1]
            position = v_str_split[0]
            
            player = player_slugs_then_names[slug]
            salary = salaries[position][slug]
            
            new_row = {
                'Player':player,
                'Salary':salary,
                'Position':position
            }
            
            optimized_lineup_df = optimized_lineup_df.append(new_row,ignore_index=True)
    
    return optimized_lineup_df
            