from flask import Flask, json, Response, request, render_template
from werkzeug.utils import secure_filename
from os import path, getcwd
from db import Database
import time
import sqlite3
from face import Face
app = Flask(__name__)

app.config['file_allowed'] = ['image/png','image/jpeg']
app.config['storage'] = path.join(getcwd(),'storage')
app.db = Database()
app.face = Face(app)
userp=""

def success_handle(output,status=200, mimetype='application/json'):
    return Response(output,status=status, mimetype=mimetype)


def error_handle(error_message, status=500, mimetype='application/json'):
    return Response(json.dumps({"error":{"message": error_message}}), status=status,mimetype=mimetype)


def get_user_by_id(user_id):
    user={}
    results = app.db.select('SELECT users.id, users.name, users.created, faces.id, faces.user_id, faces.filename,faces.created FROM users LEFT JOIN faces ON faces.user_id = users.id WHERE users.id = ?',[user_id])

    index = 0


    for row in results:
        print(row)
        face = {
            "id": row[3],
            "user_id": row[4],
            "filename": row[5],
            "created": row[6],
        }
        if index==0:
            user = {
                "id": row[0],
                "name": row[1],
                "created": row[2],
                "faces":  []
            }
        if 3 in row:
            user["faces"].append(face)
            index = index + 1

    if 'id' in user:
        return user
    return None


def delete_user_by_id(user_id):
    app.db.delete('DELETE FROM users WHERE users.id = ?', [user_id])
    # also delete all faces with user id
    app.db.delete('DELETE FROM faces WHERE faces.user_id = ?', [user_id])


#Route for Login Page
@app.route('/')
def login_page():
    return render_template('login.html')


#fetching Login Details
@app.route('/login_code',methods=['POST', 'GET'])
def login_code():
    if request.method == 'POST':
        username = request.form['s1']
        password = request.form['s2']
        app.db.select(("select Email, Password  from registeration where Email='" + username + "' and Password='" + password + "'"))
        return render_template('index.html')#, users=users)
    else:
        return render_template('login.html')


#Route for Home Page
@app.route('/page_home')
def page_home():
    return render_template('index.html')


#registeration page
@app.route('/register')
def register():
    return render_template('register.html')


#registeration database
@app.route('/registration_code', methods=['POST', 'GET'])
def registeration_code():
    if request.method == 'POST':
        s1 = request.form['s1']
        s2 = request.form['s2']
        s3 = request.form['s3']
        s4 = request.form['s4']
        s5 = request.form['s5']
        s6 = request.form['s6']
        s7 = request.form['s7']
        s8 = request.form['s8']
        s9 = request.form['s9']
        s10 = request.form['s10']
        s11 = request.form['s11']
        app.db.insert('INSERT INTO registeration(First_Name,Last_Name,Password,Street_No,Additional_Info,Zipcode,Place,Country,Phone_code,Phone_Number,Email) values(?,?,?,?,?,?,?,?,?,?,?)'
                                  ,[s1, s2, s3 ,s4, s5, s6, s7, s8, s9, s10, s11 ])
        #users = app.db.retrieveUsers()
        return render_template('login.html')#, users=users)
    else:
        return render_template('register.html')


@app.route('/api',methods=['GET'])
def homepage():
    print('Welcome to Home Page')

    output = json.dumps({"api": '1.0'})

    return success_handle(output)


@app.route('/api/train',methods=['POST'])
def train():
    output = json.dumps({"success": True})

    if 'file' not in request.files:
        print("Face Image is required")
        return error_handle("Face Image is Required")
    else:
        print("File Request",request.files)
        file=request.files['file']

        if file.mimetype not in app.config['file_allowed']:
            print("File Extension is not allowed")

            return error_handle("We are only allowed upload file with *.png and *.jpg")
        else:

            #get name in form data
            name = request.form['name']
            print("Information of that face", name)

            print("File is Allowed and will be save in", app.config['storage'])
            filename=secure_filename(file.filename)
            print("now filename is",filename)
            trained_storage = path.join(app.config['storage'], 'trained')
            file.save(path.join(trained_storage, filename))
            #let start file to sAVE IN STORAGE

            ##save to sqllite database.db
            created = int(time.time())
            user_id = app.db.insert('INSERT INTO users(name, created) values(?,?)',[name, created])
            if user_id:

                print("User Saved in DataBase", name, user_id)
                #user have been saved now we add face

                face_id = app.db.insert('INSERT INTO faces(user_id, filename, created) values(?,?,?)',[user_id, filename, created])
                if face_id:
                    print("Face has been saved")
                    global userp
                    userp=user_id
                    face_data = {"id": face_id, "filename": filename,"created": created}
                    return_output = json.dumps({"id": user_id, "name": name, "face": [face_data]})
                    return success_handle(return_output)

                else:
                    print("An error saving Face Image")
                    return error_handle("Error Saving Image File")
            else:
                print("Something Happened")
                return error_handle("An error Inserting new user")

        print("Request is contain image")
    return success_handle(output)

#router for user profile
@app.route('/api/users/<int:user_id>',methods=['GET', 'DELETE'])
def user_profile(user_id):

    if request.method == 'GET':
        user = get_user_by_id(user_id)

        if user:
            return success_handle(json.dumps(user), 200)
        else:
            return error_handle("User Not Found", 404)

    if request.method == 'DELETE':
        delete_user_by_id(user_id)
        return success_handle(json.dumps({"deleted": True}))


#router for recognize unknown face
@app.route('/api/recognize', methods=['POST'])
def recognize():

    if 'file' not in request.files:
        return error_handle("Image is Required")
    else:
        file = request.files['file']
        #file extension validate
        if file.mimetype not in app.config['file_allowed']:
            return error_handle("Extension is not allowed")
        else:
            filename = secure_filename(file.filename)
            unknown_storage = path.join(app.config['storage'], 'unknown')
            file_path = path.join(unknown_storage, filename)
            file.save(file_path)

            user_id = app.face.recognize(filename)
            if user_id:
                user = get_user_by_id(user_id)
                message = {"message": "We found {0} matched with your face image".format(user["name"]),"user": user}

                return success_handle(json.dumps(message))
            else:

                error_handle("Sorry we cannot find any people with your face image, try another image")

    return success_handle(json.dumps({"filename_to_compare_is": filename}))

@app.route('/details')
def details():
    return render_template('details.html',u=userp)



#details entrycode
@app.route('/details_code', methods=['POST', 'GET'])
def details_code():
    #output = json.dumps({"success": True})
    if request.method == 'POST':
        s1 = request.form['fathername']
        s2 = request.form['mothername']
        s3 = request.form['age']
        s4 = request.form['address']
        s5 = request.form['city']
        s6 = request.form['state']
        s7 = request.form['country']
        s8 = request.form['zipcode']
        s9 = request.form['phonenumber']
        global userp
        userp = request.form['userid']

        app.db.insert('INSERT INTO details(user_id, fathers_name, mothers_name, age, address, city, state, country, zipcode, phone_number) values(?,?,?,?,?,?,?,?,?,?)',
                               [userp, s1, s2, s3, s4, s5, s6, s7, s8, s9])
        return render_template('index.html')
    else:
        return error_handle("Error Saving Details")




if __name__ == '__main__':
    app.run(debug=True)
