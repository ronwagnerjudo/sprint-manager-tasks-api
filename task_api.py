from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import requests
import os
import logging
from functools import wraps
from datetime import datetime



logging.basicConfig(level=logging.INFO)

JWT_SECRET = 'secret'
JWT_ALGORITHM = 'HS256'
CALENDER_API_URL = os.getenv("CALENDER_API_URL", "http://127.0.0.1:8080")

#--------------------------------APP CONFIG-----------------------------------------
app = Flask(__name__)
app.secret_key = os.urandom(12).hex()

#------------------------------DATEBASE-------------------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks-sprint-manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class TasksSprintManager(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    sub = db.Column(db.String, unique=True)
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

        if 'jwt' in request.cookies.get("jwt"):
            token = request.cookies['jwt']

        if not token:
            return jsonify({'message' : 'Token is missing!'}), 401

        try: 
            response = requests.get("https://127.0.0.1:5000/get-credentials")
            data = response.json()
            current_user = TasksSprintManager.query.filter_by(sub=data['sub']).first()
        except:
            return jsonify({'message' : 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated
#--------------------------------APP----------------------------------------
@app.route("/all")
@token_required
def all_tasks(current_user):
    logging.INFO("querying all task in db")
    all_tasks = TasksSprintManager.query.filter_by(sub=current_user.sub).all()
    return jsonify(tasks=[task.to_dict() for task in all_tasks])


@app.route("/add", methods=["GET", "POST"])
@token_required
def add_tasks(current_user):
    user_sub = current_user.sub
    task_name = request.form.get("task_name")
    task_time = request.form.get("task_time")
    logging.INFO("getting data from the front-end")

    if task_name != "" or task_time != "":
        task_params = {
            "task_name": task_name,
            "task_time_start": task_time
        }

        logging.INFO("init post request")
        requests.post(f"{CALENDER_API_URL}/new_task", json=task_params)
        logging.INFO("sent post request to calendar api")

        get_response = requests.get("https://127.0.0.1:8080/new_task", timeout=3)
        logging.INFO("getting the id of the event from calendar api")
        response = get_response.json()
        google_event_id = response["googleEventId"]
        task_start_datetime_string = response["eventStartDate"]
        formatted_task_start_time = parse_date(task_start_datetime_string)

        add_new_task = TasksSprintManager(
            username = user_sub,
            task_name = task_name,
            task_time_start = task_time,
            google_event_id = google_event_id,
            task_start_datetime = formatted_task_start_time
        )
        db.session.add(add_new_task)
        db.session.commit()
        logging.INFO("added new task to the db")

  
        return jsonify({"success": "Successfully added new task."}), 200
    else:
        return jsonify(error={"Not valid": "Sorry, you can't leave input empty."}), 404


@app.route("/delete", methods=["DELETE"])
@token_required
def delete_task(current_user):
    task_id = request.form.get("id")
    task_to_delete = TasksSprintManager.query.filter_by(id=task_id, user_id=current_user.sub).first()
    logging.INFO("finding the task by id")
    if task_to_delete:         
        db.session.delete(task_to_delete)
        db.session.commit()
        logging.INFO("task deleted in db")

        task_params = {
        "task_name": task_to_delete['task_name'],
        "googleEventId": task_to_delete['google_event_id']
        }

        logging.INFO("init delete request")
        requests.delete(f"{CALENDER_API_URL}/delete", json=task_params)
        logging.INFO("sent delete request to calendar api")
        return jsonify({"success": "Successfully deleted task."}), 200
    else:
        logging.INFO("couldn't find the task")
        return jsonify(error={"Not Found": "Sorry a task with that id was not found in the database."}), 404


@app.route("/update-task", methods=["PUT", "PATCH"])
@token_required
def update_task(current_user):
    task_name = request.form.get("task_name")
    task_time = request.form.get("task_time")
    logging.INFO("getting data from the front-end")

    task_id = request.form.get("id")
    logging.INFO("querying db to find the task by id")
    task_to_update = TasksSprintManager.query.filter_by(id=task_id, user_id=current_user.sub).first()
    if task_to_update:
        task_to_update.task_name = task_name
        task_to_update.task_time = task_time
        db.session.commit()
        logging.INFO("updated task in db")

        task_params = {
        "task_name": task_name,
        "task_time_start": task_time,
        "googleEventId": task_to_update['google_event_id']
        }

        logging.INFO("init put request")
        requests.put(f"{CALENDER_API_URL}/new_task", json=task_params)
        logging.INFO("sent put request to calendar api")
        return jsonify({"success": "Successfully updated the new task."}), 200
    else:
        logging.INFO("task did not found in db")
        return jsonify(error={"Not Found": "Sorry a task with that id was not found in the database."}), 404


if __name__ =="__main__":
    app.run(debug=True, port=3030, ssl_context='adhoc')