from flask import Flask, render_template, request
from forms import ContactForm
from flask_mail import Mail, Message
import os

app = Flask(__name__)
app.secret_key = '4@#vdfg^&13asdfs#'

mail_settings = {
    "MAIL_SERVER": 'smtp-mail.outlook.com',
    "MAIL_PORT": 587,
    "MAIL_USE_TLS": 1,
    "MAIL_USERNAME": os.environ['HOTMAIL_USER'],
    "MAIL_PASSWORD": os.environ['HOTMAIL_PASSWORD'],
}

app.config.update(mail_settings)
mail = Mail(app)

@app.route('/')
def Intro():

    return render_template('intro.html')

@app.route('/Home')
def Home():

    return render_template('home.html')


@app.route('/Resume')
def Resume():

    return render_template('resume.html')


@app.route('/Projects')
def Projects():

    return render_template('projects.html')

@app.route('/Contact', methods=['GET','POST'])
def Contact():
    form = ContactForm()

    if request.method == 'POST' and form.validate():
        msg = Message(body=form.message.data,
                        subject=f'Hello this is {form.name.data}!',
                        sender=os.environ['HOTMAIL_USER'],
                        recipients=['pacheco.eric.anthony@gmail.com'])
        mail.send(msg)

        return render_template('contact_message.html', form=form)

    elif request.method == 'GET':
        return render_template('contact.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)