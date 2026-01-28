from flask import Flask, render_template, request, jsonify, session, redirect, url_for, session, flash
from werkzeug.utils import redirect
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import pandas as pd
import numpy as np
from sklearn import linear_model
from sklearn.utils import shuffle
import pickle


app = Flask(__name__)
app.secret_key = 'rksinha359'  # Replace with a secure secret key

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'bcsp'

mysql = MySQL(app)
  # Use the correct endpoint name

# Define the training function
def train_model():
    # Import dataset with student's data
    data = pd.read_csv("student-mat.csv", sep=";")
    predict = "G3"

    # List the variables we want to use for our predictions in this model
    data = data[[ "G1", "G2", "G3", "studytime", "health", "famrel", "failures", "absences"]]
    data = shuffle(data)

    x = np.array(data.drop(columns=[predict]))
    y = np.array(data[predict])

    # Train the model
    linear = linear_model.LinearRegression()
    linear.fit(x, y)

    # Save the trained model
    with open("studentgrades.pickle", "wb") as f:
        pickle.dump(linear, f)

# Train the model when the Flask app starts
train_model()

# Load the trained model
pickle_in = open("studentgrades.pickle", "rb")
linear = pickle.load(pickle_in)


# Predict route
@app.route('/predict', methods=['GET', 'POST'])
def predict():
    data = request.get_json()
    features = data['features']
    
    # Ensure the number of features for prediction matches the number used during training
    if len(features) != 7:  # Assuming you are using 7 features as per the training
        return jsonify({'error': 'Number of features provided does not match the trained model'}), 400
    
    features_for_prediction = np.array(features).reshape(1, -1)
    
    prediction = linear.predict(features_for_prediction)
    
    return jsonify({'predicted_grade': prediction[0]})


# Store predicted grade route
@app.route('/store_grade', methods=['POST'])
def store_grade():
    if 'loggedin' in session:
        if request.method == 'POST' and 'predicted_grade' in request.form:
            predicted_grade = request.form['predicted_grade']
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('INSERT INTO predicted_grades (user_id, predicted_grade) VALUES (%s, %s)', (session['id'], predicted_grade))
            mysql.connection.commit()
            return 'Predicted grade stored successfully!'
        else:
            return 'Error: Predicted grade not provided in the request!'
    else:
        return 'Error: User not logged in!'


@app.route('/')
def index():
    return  render_template('index.html')
           

@app.route('/login', methods =['GET', 'POST'])
def login():
    mesage = ''
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = % s AND password = % s', (email, password, ))
        user = cursor.fetchone()
        if user:
            session['loggedin'] = True
            session['id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            mesage = 'Logged in successfully !'
            return render_template('home.html')
        else:
            mesage = 'Please enter correct email / password!'
    return render_template('login.html', mesage = mesage)
  
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('email', None)
    return redirect(url_for('index'))

  
@app.route('/register', methods =['GET', 'POST'])
def register():
    mesage = ''
    if request.method == 'POST' and 'name' in request.form and 'password' in request.form and 'email' in request.form :
        userName = request.form['name']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = % s', (email, ))
        user = cursor.fetchone()
        if user:
            mesage = 'Account already exists !'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            mesage = 'Invalid email address !'
        elif not userName or not password or not email:
            mesage = 'Please fill out the form !'
        else:
            cursor.execute('INSERT INTO user VALUES (NULL, % s, % s, % s)', (userName, email, password, ))
            mysql.connection.commit()
            mesage = 'You have successfully registered!'
    elif request.method == 'POST':
        mesage = 'Please fill out the form !'
    return render_template('login.html', mesage = mesage)

@app.route('/contact', methods=['POST', 'GET'])
def contact():
    if request.method == 'POST' and 'name' in request.form and 'email' in request.form and 'message' in request.form :
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
       
        cursor.execute('INSERT INTO contactus VALUES (NULL, % s, % s, %s)', (name, email, message, ))
        mysql.connection.commit()
        mesage = 'thankyou for your valuable time!'
    elif request.method == 'POST':
        mesage = 'Please fill out the form !'
    return render_template('index.html', mesage = mesage)


@app.route('/layout')
def layout():
    if 'loggedin' in session:
        return render_template('layout.html')
    else:
        return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'loggedin' in session:
        return render_template('home.html')
    else:
        return redirect(url_for('login'))

@app.route('/prediction')
def prediction():
    if 'loggedin' in session:
        return render_template('prediction.html')
    else:
        return redirect(url_for('login'))

@app.route('/showgraph')
def showgraph():
    if 'loggedin' in session:
        return render_template('plot.html')
    else:
        return redirect(url_for('login'))
    
@app.route('/profile')
def profile():
    # Check if the user is logged in
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE id = %s', (session['id'],))
        user = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', user=user)
    # User is not logged in redirect to login page
    return redirect(url_for('login'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    message = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM adminlogin WHERE username = %s AND password = %s', (username, password))
        admin = cursor.fetchone()
        if admin:
            session['admin_loggedin'] = True
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            message = 'Logged in successfully!'
            return redirect(url_for('admin_home'))
        else:
            message = 'Please enter correct username / password!'
    return render_template('adminlogin.html', message=message)

# Admin logout route
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_loggedin', None)
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    return redirect(url_for('index'))



@app.route('/adminlay')
def adminlayout():
    if 'admin_loggedin' in session:
        return render_template('adminlay.html')
    else:
        return redirect(url_for('admin_login'))

@app.route('/admin/home')
def admin_home():
    if 'admin_loggedin' in session:
        return render_template('admin.html')
    else:
        return redirect(url_for('admin_login'))

@app.route('/admin/showuser')
def Showuser():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM user")
    data = cur.fetchall()
    cur.close()

    return render_template('showuser.html', user=data)


@app.route('/insert', methods = ['POST'])
def insert():
       if request.method == 'POST' and 'name' in request.form and 'password' in request.form and 'email' in request.form :
        flash("Data Inserted Successfully")
        userName = request.form['name']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = % s', (email, ))
        user = cursor.fetchone()
        if user:
            mesage = 'Account already exists !'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            mesage = 'Invalid email address !'
        elif not userName or not password or not email:
            mesage = 'Please fill out the form !'
        else:
            cursor.execute('INSERT INTO user VALUES (NULL, % s, % s, % s)', (userName, email, password, ))
            mysql.connection.commit()
        return render_template('showuser.html')

@app.route('/delete/<string:id_data>', methods = ['GET'])
def delete(id_data):
    flash("Record Has Been Deleted Successfully")
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM user WHERE id=%s", (id_data,))
    mysql.connection.commit()
    return redirect(url_for('Showuser'))



@app.route('/update', methods= ['POST', 'GET'])
def update():
    if request.method == 'POST':
        id_data = request.form['id']
        userName = request.form['name']
        password = request.form['password']
        email = request.form['email']

        cur = mysql.connection.cursor()
        cur.execute("""
        UPDATE user SET name=%s, email=%s, password=%s
        WHERE id=%s
        """, (userName, email, password, id_data))
        flash("Data Updated Successfully")
        return redirect(url_for('Showuser')) 
    

@app.route('/admin/contactus')
def ticket():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM contactus")
    data = cur.fetchall()
    cur.close()

    return render_template('contactus.html', contactus=data)


if __name__ == "__main__":
    app.run(debug=True)