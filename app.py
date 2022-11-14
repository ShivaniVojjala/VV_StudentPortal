
from cgitb import reset
from distutils.command.config import config
from distutils.command.upload import upload
from mimetypes import init
from io import BytesIO
from typing_extensions import Self
from flask import Flask,render_template, url_for, redirect,flash,request,send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin , login_user, LoginManager, login_required, logout_user,current_user
from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,SubmitField
from wtforms.validators import InputRequired,Length,ValidationError
import os
from flask_bcrypt import Bcrypt
import string, random, requests
from werkzeug.utils import secure_filename
from azure.storage.blob import BlobServiceClient 
from waitress import serve
from multiprocessing.pool import ThreadPool
from azure.storage.blob import  BlobClient
from azure.storage.blob import ContentSettings, ContainerClient
from threading import Thread
import urllib.request


import pathlib

app = Flask(__name__)

# database related
db = SQLAlchemy(app)

bcrypt = Bcrypt(app)
app.config['SQLALCHEMY_DATABASE_URI']= 'sqlite:///database.db'
app.config['SECRET_KEY']= 'mysecretkey'


# azure related
app.config.from_pyfile('config.py')
account = app.config['ACCOUNT_NAME']   # Azure account name
key = app.config['ACCOUNT_KEY']      # Azure Storage account access key  
connect_str = app.config['CONNECTION_STRING']
container = app.config['CONTAINER'] # Container name
allowed_ext = app.config['ALLOWED_EXTENSIONS'] # List of accepted extensions
max_length = app.config['MAX_CONTENT_LENGTH'] # Maximum size of the uploaded file
# account = app.config['ACCOUNT_NAME'] 
# UPLOAD_FOLDER = app.config['UPLOAD_FOLDER'] 
# upload_folder = '/path/to/the/uploads'   
# app.config['UPLOAD_FOLDER']= upload_folder       
    
# image related 
picfolder = os.path.join('static','images')

app.config['UPLOAD_FOLDER']= picfolder

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"



# login database related
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@login_manager.user_loader
def load_employee(user_id):
    return Employee.query.get(int(user_id))

# different database tables
class User(db.Model, UserMixin):
    id= db.Column(db.Integer, primary_key=True)
    firstname=db.Column(db.String(20),nullable=False)
    lastname=db.Column(db.String(20),nullable=False)
    username= db.Column(db.String(20),nullable=False, unique=True)
    password= db.Column(db.String(80),nullable=False)

class Employee(db.Model, UserMixin):
    id= db.Column(db.Integer, primary_key=True)
    username= db.Column(db.String(20),nullable=False, unique=True)
    password= db.Column(db.String(80),nullable=False)


# forms of database

class SignupForm(FlaskForm):
    firstname = StringField(validators=[InputRequired(),Length(min=4,max=20)], render_kw={"placeholder":"Enter your Firstname"})
    lastname = StringField(validators=[InputRequired(),Length(min=4,max=20)], render_kw={"placeholder":"Enter your Lastname"})
    username = StringField(validators=[InputRequired(),Length(min=4,max=20)], render_kw={"placeholder":"Enter a username"})
    password = PasswordField(validators=[InputRequired(),Length(min=4,max=20)], render_kw={"placeholder":"Enter a password"})

    submit = SubmitField("CREATE")

    def validate_username(self, username):
        existing_user_name = User.query.filter_by(username=username.data).first()
        if existing_user_name:
            raise ValidationError("That username already exists. Please choose a different one." )

    

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(),Length(min=4,max=20)], render_kw={"placeholder":"Enter your username"})
    password = PasswordField(validators=[InputRequired(),Length(min=4,max=20)], render_kw={"placeholder":"Enter your password"})

    submit = SubmitField("Login")

class EmployeeForm(FlaskForm):
    username = StringField(validators=[InputRequired(),Length(min=4,max=20)], render_kw={"placeholder":"Enter your username"})
    password = PasswordField(validators=[InputRequired(),Length(min=4,max=20)], render_kw={"placeholder":"Enter your password"})

    submit = SubmitField("Employee Login")


# azure upload 
class Upload(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    filename = db.Column(db.String(50))
    data = db.Column(db.LargeBinary)



#home 
@app.route('/')
def home():
    pic1= os.path.join(app.config['UPLOAD_FOLDER'], 'logo-blue.jpg')
    pic2= os.path.join(app.config['UPLOAD_FOLDER'], 'logo2.jpg')
    pic3= os.path.join(app.config['UPLOAD_FOLDER'],'university_logo.png')
    
    return render_template('home.html', user_image=pic1,user_image2=pic2,user_image3=pic3)

    

    
# login
@app.route('/login' , methods=['GET','POST'])
def login():
    pic2= os.path.join(app.config['UPLOAD_FOLDER'], 'logo2.jpg')
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if  bcrypt.check_password_hash(user.password,form.password.data):
                 login_user(user)
                 form.username.data=""
                 form.password.data=""
                 return redirect(url_for('dashboard'))

            else:
                 flash("Wrong password.Try again! ")

        else:
            flash("User doesnt exist.Enter correct username")


        
    return render_template('login.html', form=form,user_image2=pic2)


# signup
@app.route('/signup', methods=['GET','POST'])
def signup():
    pic2= os.path.join(app.config['UPLOAD_FOLDER'], 'logo2.jpg')
    form= SignupForm()
    
    if form.validate_on_submit():
       
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(firstname=form.firstname.data,lastname=form.lastname.data,username=form.username.data, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()
 
    # elif form.validate_username():

    #     existing_user_name = User.query.filter_by(username=form.username.data).first()
    #     if existing_user_name:
    #         raise ValidationError("That username already exists. Please choose a different one." )

    form.firstname.data= ""
    form.lastname.data = ""
    form.username.data = ""
    form.password.data = ""

    return render_template('signup.html', form=form,user_image2=pic2)

#  employee login
@app.route('/employee' , methods=['GET','POST'])
def employee():
    pic2= os.path.join(app.config['UPLOAD_FOLDER'], 'logo2.jpg')
    form = EmployeeForm()
    if form.validate_on_submit():
        employee = Employee.query.filter_by(username=form.username.data).first()
        if employee:
            if  Employee.query.filter_by(password=form.password.data).first():
                 login_user(employee)
                 form.username.data=""
                 form.password.data=""
                 return redirect(url_for('dashboard2'))

            else:
                 flash("Wrong password.Try again! ")

        else:
            flash("User doesnt exist.Enter correct username")


        
    return render_template('employe.html', form=form,user_image2=pic2)









# # azure upload


blob_service_client = BlobServiceClient.from_connection_string(connect_str)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in allowed_ext

@app.route('/upload',methods=['POST'])
def upload():
    if request.method == 'POST':
        files = request.files.getlist('file')
        for file in files:
            if file and allowed_file(file.filename):
                filename =  secure_filename(file.filename)
                file.save(filename )
                blob_client = blob_service_client.get_blob_client(container = container, blob = filename)
              
                with open(filename, "rb") as data:
                    
                    

                    try:

                        blob_client.upload_blob(data, overwrite=True)
                        msg = "Upload Done ! "
                    except:
                        pass
                    
    os.remove(filename)
    return render_template("dashboard.html", msg=msg)

 

# # dashboard1
@app.route('/dashboard', methods=['GET','POST'])
# @login_required
def dashboard():
    # pic4= os.path.join(app.config['UPLOAD_FOLDER'],'edu.jpg')
    # if request.method == 'POST':
    #     file = request.files['file']                [to store in sql database]

    #     upload = Upload(filename=file.filename,data=file.read())
    #     db.session.add(upload)
    #     db.session.commit()

    #     return f'Uploaded:{file.filename}'
    return render_template('dashboard.html')
 


# dashboard2
@app.route('/dashboard2', methods=['GET','POST'])
@login_required
def dashboard2():
    return render_template('dashboard2.html')


# logout

@app.route("/logout",methods=['GET','POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))






if __name__ == '__main__':
    app.run(debug=True)

