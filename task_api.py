from flask import Flask, jsonify, request, json
from flask_sqlalchemy import SQLAlchemy
import requests
import os
from flask_cors import CORS
import logging
from functools import wraps
from datetime import datetime



logging.basicConfig(level=logging.INFO)

JWT_SECRET = 'secret'
JWT_ALGORITHM = 'HS256'
CALENDER_API_URL = os.getenv("CALENDER_API_URL", "http://127.0.0.1:8080")
USER_API_URL = os.getenv("USER_API_URL", "http://127.0.0.1:5000")

#--------------------------------APP CONFIG-----------------------------------------
app = Flask(__name__)
app.secret_key = os.urandom(12).hex()
CORS(app,  supports_credentials=True)

#------------------------------DATEBASE-------------------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks-sprint-manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class TasksSprintManager(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    sub = db.Column(db.String)
    task_name = db.Column(db.String(50))
    task_time = db.Column(db.Float)
    google_event_id = db.Column(db.String(100))
    task_start_datetime = db.Column(db.String(50))


    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

db.create_all()

#--------------------------------FUNCTIONS-----------------------------------

def parse_date(string_date):
    """Takes this type of string datetime (%Y-%m-%dT%H:%M:%S), and change it to different type (Mon Dec 31 17:41:00 2018) """
    task_start_time = datetime.strptime(string_date, "%Y-%m-%dT%H:%M:%S")
    formatted_task_start_time = datetime.strftime(task_start_time, "%c")
    return formatted_task_start_time

#-------------------------------DECORATOR------------------------------------
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        logging.info("Searching for jwt")
        if request.cookies.get("jwt"):
            logging.info("JWT found")
            token = request.cookies.get("jwt")

        if not token:
            logging.info("No Token")
            return jsonify({'message' : 'Token is missing!'}), 401

        try: 
            response = requests.get(f"{USER_API_URL}/get-user-details", cookies=request.cookies)
            logging.info("Sent get request to user api")
        except:
            logging.info("Problem with the get-user-details response")
            return jsonify({"message' : 'couldn't get a response"}), 404

        data = response.json()
        current_user = data['user_details']['sub']


        return f(current_user, *args, **kwargs)

    return decorated
#--------------------------------APP----------------------------------------
@app.route('/', methods=["GET"])
def status():
    return {'status': "200"}, 200
    
@app.route("/all")
@token_required
def all_tasks(current_user):
    logging.info("Querying all task in db")
    all_tasks = TasksSprintManager.query.filter_by(sub=current_user).all()
    return jsonify(tasks=[task.to_dict() for task in all_tasks])

@app.route("/add", methods=["GET", "POST"])
@token_required
def add_tasks(current_user):
    user_sub = current_user

    data = json.loads(request.data)
    task_name = data["task_name"]
    task_time = data["task_time"]
    logging.info("Getting data from the front-end")

    if task_name != "" or task_time != "":
        task_params = {
            "task_name": task_name,
            "task_time": task_time
        }

        logging.info("Init post request")
        try:
            response = requests.post(f"{CALENDER_API_URL}/new_task", json=task_params, cookies=request.cookies)
            logging.info("Sent post request to calendar api")
        except:
            logging.info("Problem with the calendar_api/new_task response")
            return jsonify({"message": "Problem with response."})

        if response.status_code == 200:
            logging.info("Getting the id of the event from calendar api")
            response = response.json()
            google_event_id = response["googleEventId"]
            task_start_datetime_string = response["start"]["dateTime"]
            formatted_task_start_time = parse_date(task_start_datetime_string)

            add_new_task = TasksSprintManager(
                sub = user_sub,
                task_name = task_name,
                task_time = task_time,
                google_event_id = google_event_id,
                task_start_datetime = formatted_task_start_time
            )
            db.session.add(add_new_task)
            db.session.commit()
            logging.info("Added new task to the db")
            return jsonify({"success": "Successfully added new task."}), 200
        else:
            logging.info("The response to calendar_api/new_task was not 200.")
            return jsonify({"error": "Couldn't add new task to google calendar"}), response.status_code
    else:
        return jsonify({"Not valid": "Sorry, you can't leave fields empty."}), 404


@app.route("/delete", methods=["DELETE"])
@token_required
def delete_task(current_user):
    data = json.loads(request.data)
    task_id = data["id"]
    task_to_delete = TasksSprintManager.query.filter_by(id=task_id, sub=current_user).first()
    logging.info("Finding the task by id and user sub")
    if task_to_delete:
        logging.info("Found the task by id and user sub")       

        task_params = {
        "googleEventId": task_to_delete.google_event_id
        }

        logging.info("Init delete request")
        try:
            response = requests.delete(f"{CALENDER_API_URL}/delete", json=task_params, cookies=request.cookies)
            logging.info("Sent delete request to calendar api")
        except:
            logging.info("Problem with the calendar_api/delete response")
            return jsonify({"message": "Problem with response."}), response.status_code

        if response.status_code == 200:
            logging.info("Sent delete request to calendar api")
            db.session.delete(task_to_delete)
            db.session.commit()
            logging.info("Task deleted in db")
            return jsonify({"success": "Successfully deleted task."}), 200
        else:
            logging.info("The response to calendar_api/delete was not 200.")
            return jsonify({"error": "Event did not deleted in the google calendar."}), response.status_code
    else:
        logging.info("Couldn't find the task")
        return jsonify({"Not Found": "Sorry a task with that id or sub was not found in the database."}), 404


@app.route("/update-task", methods=["PUT", "PATCH"])
@token_required
def update_task(current_user):
    data = json.loads(request.data)

    task_name = data["task_name"]
    task_time = data["task_time"]
    task_id = data["id"]
    logging.info("Getting data from the front-end")

    logging.info("Querying db to find the task by id and user sub")
    task_to_update = TasksSprintManager.query.filter_by(id=task_id, user_id=current_user).first()
    logging.info("Finding the task by id and user sub")
    if task_to_update:
        logging.info("Found the task by id and user sub")

        task_params = {
        "task_name": task_name,
        "task_time_start": task_time,
        "googleEventId": task_to_update['google_event_id']
        }

        logging.info("Init put request")
        try:
            response = requests.put(f"{CALENDER_API_URL}/update", json=task_params)
            logging.info("Sent put request to calendar api")
        except:
            logging.info("Problem with the calendar_api/update response")
            return jsonify({"message": "Problem with response."})

        if response.status_code == 200:
            logging.info("Sent put request to calendar api")
            task_to_update.task_name = task_name
            task_to_update.task_time = task_time
            db.session.commit()
            logging.info("Updated task in db")
            return jsonify({"success": "Successfully updated the new task."}), 200
        else:
            logging.info("The response to calendar_api/update was not 200.")
            return jsonify({"error": "Event did not updated in the google calendar."}), response.status_code
    else:
        logging.info("Task did not found in db")
        return jsonify(error={"Not Found": "Sorry a task with that id was not found in the database."}), 404


if __name__ =="__main__":
    app.run(host="0.0.0.0",debug=True, port=80)