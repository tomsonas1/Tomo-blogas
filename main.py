from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, desc
from flask_ckeditor import CKEditor
from datetime import date, datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm, ContactMeForm
from functools import wraps
import smtplib

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_API')
ckeditor = CKEditor(app)
bootstrap = Bootstrap5(app)

login_manager = LoginManager()
login_manager.init_app(app)
##--------------------------------------Email cofig---------------------------------##
sender_email = os.environ.get('SENDER_EMAIL')
email_password = os.environ.get('EMAIL_PASSWORD')
receiver_email = os.environ.get('RECEIVER_EMAIL')
smtp_server = os.environ.get('SMTP_SERVER')


##-----------------------------End Email Config--------------------------------------##
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


class Base(DeclarativeBase):
    pass


app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_uri", "sqlite:///posts.db")
db = SQLAlchemy(model_class=Base)
db.init_app(app)


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("user.id"))
    author = relationship("User", back_populates="posts")
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(100), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=True)
    comments = relationship("Comment", back_populates="parent_post", order_by="Comment.date.desc()")


class User(db.Model, UserMixin):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class Comment(db.Model):
    __tablename__ = "comment"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("user.id"))
    comment_author = relationship("User", back_populates="comments")
    date: Mapped[str] = mapped_column(String(100), nullable=False)
    post_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")


class ReceivedEmails(db.Model):
    __tablename__ = "emails"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(100), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[str] = mapped_column(String(100), nullable=False)



with app.app_context():
    db.create_all()


##----------------------------------Admin only--------------------------------##

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


def logged_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return abort(403)
        return f(*args, **kwargs)

    return decorated_function


##---------------------------------------User-----------------------------------##
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()
        if user:
            flash("Toks El. paštas jau užregistruotas.")
            return redirect(url_for('login'))
        hash_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            password=hash_salted_password,
            name=form.name.data
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('all_posts'))
    return render_template('register.html', form=form, current_user=current_user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if not user:
            flash("Tokio vartotojo nėra, prašome įvesti teisingą el.paštą.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash("Neteisingas slaptažodis. Pasitikslinkite slaptažodį")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('all_posts'))
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


##---------------------------------------Posts-----------------------------------##
@app.route('/')
def home():
    return render_template('index.html', current_user=current_user)


@app.route('/posts')
def all_posts():
    result = db.session.execute(db.select(BlogPost).order_by(desc(BlogPost.date)))
    posts = result.scalars().all()
    return render_template('posts.html', posts=posts, current_user=current_user)


@app.route('/post/<int:post_id>')
def show_post(post_id, to_comment=False):
    request_post = db.get_or_404(BlogPost, post_id)
    return render_template('post.html', post=request_post, current_user=current_user)


@app.route('/post/<int:post_id>/comment', methods=['GET', 'POST'])
@logged_only
def write_comment(post_id):
    request_post = db.get_or_404(BlogPost, post_id)
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("Norint komentuoti reikia prisiregistruoti")
            return redirect(url_for("login"))
        new_comment = Comment(
            text=comment_form.comment_text.data,
            comment_author=current_user,
            parent_post=request_post,
            date=date.today().strftime("%Y-%m-%d")
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post', post_id=request_post.id))

    return render_template('write-comment.html', post=request_post, current_user=current_user,
                           form=comment_form)


@app.route('/delete/<int:comment_id>/<int:post_id>')
@logged_only
def delete_comment(comment_id, post_id):
    comment_to_delete = db.get_or_404(Comment, comment_id)
    db.session.delete(comment_to_delete)
    db.session.commit()
    return redirect(url_for('show_post', post_id=post_id))


@app.route('/add-post', methods=['GET', 'POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%Y-%m-%d")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('all_posts'))
    return render_template('make-post.html', form=form, current_user=current_user)


@app.route('/edit-post/<int:post_id>', methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data

        db.session.commit()
        return redirect(url_for('show_post', post_id=post.id))
    return render_template('make-post.html', is_edit=True, form=edit_form, current_user=current_user)


@app.route('/delete/<int:post_id>')
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    for comment in post_to_delete.comments:
        db.session.delete(comment)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('all_posts'))


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactMeForm()
    if form.validate_on_submit():
        new_email = ReceivedEmails(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            text=form.message.data,
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.session.add(new_email)
        db.session.commit()
        flash("Jūsų žinutė sįkmingai išsiūsta")
        return redirect(url_for('contact'))
    return render_template('contact.html', form=form)


if __name__ == "__main__":
    app.run(debug=False)
