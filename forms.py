from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, EmailField, validators, PasswordField, TextAreaField
from wtforms.validators import DataRequired, URL, EqualTo, Length, Regexp, Email
#from flask_ckeditor import CKEditorField
from flask_bootstrap import Bootstrap5



class RegisterForm(FlaskForm):
    email = EmailField("Email: ", validators=[DataRequired(), validators.Email()])
    password = PasswordField("Password (at least 8 characters long): ", validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters long."),
])

    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message="Passwords must match.")
    ])

    username = StringField("Username: ", validators=[DataRequired()])
    submit = SubmitField("Register")



class LoginForm(FlaskForm):
    email = EmailField("Email: ", validators=[DataRequired()])
    password = PasswordField("Password: ", validators=[DataRequired()])
    submit = SubmitField("Log in")
