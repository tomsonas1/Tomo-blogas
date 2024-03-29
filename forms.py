from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, EmailField, TextAreaField, URLField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField


class CreatePostForm(FlaskForm):
    title = StringField("Pavadinimas", validators=[DataRequired()])
    subtitle = StringField("Paantraštė", validators=[DataRequired()])
    img_url = URLField("Nuotraukos URL",validators=[URL()])
    body = CKEditorField("Tekstas", validators=[DataRequired()])
    submit = SubmitField("Pateikti")




class RegisterForm(FlaskForm):
    name = StringField("Vardas", validators=[DataRequired()])
    email = EmailField("El. paštas", validators=[DataRequired()])
    password = PasswordField("Slaptažodis", validators=[DataRequired()])
    submit = SubmitField("Užsiregistruoti")

class LoginForm(FlaskForm):
    email = EmailField("El. paštas", validators=[DataRequired()])
    password = PasswordField("Slaptažodis", validators=[DataRequired()])
    submit = SubmitField("Prisijungti")


class CommentForm(FlaskForm):
    comment_text = CKEditorField("Komentaras", validators=[DataRequired()])
    submit = SubmitField("Paskelbti")

class ContactMeForm(FlaskForm):
    name = StringField("Jūsų Vardas", validators=[DataRequired()])
    email = EmailField("El. Paštas", validators=[DataRequired()])
    phone = StringField("Tel. Nr. (neprivaloma)")
    message =TextAreaField("Tekstas", validators=[DataRequired()])
    submit = SubmitField('Siųskite')
