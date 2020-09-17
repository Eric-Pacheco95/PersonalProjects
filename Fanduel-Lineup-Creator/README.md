# Fanduel lineup creator

## Background

Fanduel is an online sports fantasy betting website, where users can place wagers on their favourite sports such as NBA basketball. The focus of this project is to produce winning contest entries for fanduel NBA contests. The steps to producing a winning lineup include:

* Collecting and storing relevant NBA data for each NBA player
* Feature engineering more variables which helps to create better player models
* Create models for each individual NBA player which can predict a player's fantasy output
* Using individual player models, and past NBA player data, predict player fantasy output for each player in fanduel contest
* Optimize lineup based on predicted player fantasy outputs to maximize value of contest lineup

These were the objectives of the project, and I have created a web app to test the results - https://fanduel-lineup-creator.herokuapp.com/

The rest of this readme will explain the project in detail.\

## NBA Fanduel

Fanduel's betting platform has been gaining popularity significantly, and a main cause of this can be attributed to Fanduel's revolutionary approach to fantasy. In the past the traditional fantasy sports format included players joining a fantasy league where players would draft their team at the beginning of the fantasy year. Players have the ability to add, drop, and trade players throughout the season. 

Fanduel changes this format by introducing daily fantasy contests. Each daily contest on NBA fanduel has a game slate which represents how many games a player is betting on. Each NBA player playing during the game slate is assigned a salary. This salary is representative of how many projected fantasy points that player is expected to produce that night. To finish a lineup the player must choose 2 points guards, 2 shooting guards, 2 small forwards, 2 power forwards and one center, and the total combined salary of the players must be below 60,000. The focus is for the player's lineup to produce the most fantasy points with the given salaries for each NBA player.

The scoring format for Fanduel follows a NBA player's stats for a game:

![Scoring Format](static/images/scoring_system_FD.png)

Daily NBA fantasy allows players to bet on a single night of NBA games, compared to being committed to a whole season of NBA games with the traditional fantasy format. 

## Problem Statement

The steps to producing a winning contest lineup are the same as outlined in the background section:

* Collecting and storing relevant NBA data for each NBA player
* Feature engineering more variables which helps to create better player models
* Create models for each individual NBA player which can predict a player's fantasy output
* Using individual player models, and past NBA player data, predict player fantasy output for each player in fanduel contest
* Optimize lineup based on predicted player fantasy outputs to maximize value of contest lineup


## Data Collection and Storing

All NBA player data was collected and stored using this [jupyter notebook](https://github.com/Eric-Pacheco95/PersonalProjects/blob/master/Fanduel-Lineup-Creator/notebooks/player_stats.ipynb)

To collect NBA player data the [basketball reference web scraper library](https://jaebradley.github.io/basketball_reference_web_scraper/) was used. This library contains all NBA data collected from https://www.basketball-reference.com/

After all the data was collected and formatted, each players data was uploaded to a AWS Redshift database as a table.

NBA team advanced data was also collected from basketball reference, however the data was available to be downloaded as a csv. Each year from 2016-2020 was collected.

![Advanced Stats](static/images/advanced_stats.png)
