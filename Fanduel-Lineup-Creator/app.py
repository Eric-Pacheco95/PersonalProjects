from flask import Flask, render_template, url_for, request, redirect
import pandas as pd
from scripts.fanduel_lineup_creator import *

app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def home():

    if request.method == 'POST':

        if request.files:

            try:

                csv = request.files['csv']

                contest_df = format_contest_csv(csv)

                pgs,sgs,sfs,pfs,cs = get_lineup(contest_df)

                optimized_lineup = get_optimized_lineup(pgs,sgs,sfs,pfs,cs)

                return render_template('results.html',
                                    tables=[optimized_lineup.to_html(classes='data')],
                                    titles=['Optimal Lineup'])
            
            except Exception as e:
                return render_template('app_error.html')
    else:

        return render_template('app.html')

@app.route('/instructions')
def instructions():

    return render_template('instructions.html')

if __name__ == '__main__':
    app.run(debug=True)