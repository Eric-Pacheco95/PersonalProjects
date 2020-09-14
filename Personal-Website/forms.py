from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired


class ContactForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired('Please provide name')])
    email = StringField("Email", validators=[DataRequired('Please provide email')])
    message = TextAreaField("Message", validators=[DataRequired('Please provide message')])
    submit = SubmitField("Send")
