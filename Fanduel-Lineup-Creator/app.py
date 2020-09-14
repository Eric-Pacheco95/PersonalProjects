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
                pgs,sgs,sfs,pfs,cs = get_lineup(csv)

                return render_template('results.html',
                                    tables=[
                                        pgs.to_html(classes='data'),
                                        sgs.to_html(classes='data'),
                                        sfs.to_html(classes='data'),
                                        pfs.to_html(classes='data'),
                                        cs.to_html(classes='data')
                                    ],
                                    titles=['PGs','SGs','SFs','PFs','Cs'])
            
            except Exception as e:
                return render_template('app_error.html')
    else:

        return render_template('app.html')

@app.route('/instructions')
def instructions():

    return render_template('instructions.html')

if __name__ == '__main__':
    app.run(debug=True)