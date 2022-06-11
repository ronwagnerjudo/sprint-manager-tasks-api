from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import requests
import os
import logging

logging.basicConfig(level=logging.INFO)

CALENDER_API_URL = os.getenv("CALENDER_API_URL", "http://127.0.0.1:8080")

app = Flask(__name__)

#------------------------------DATEBASE-------------------------------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks-sprint-manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class SprintManager(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True)
    task_name = db.Column(db.String)
    task_time = db.Column(db.Float)


    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

db.create_all()


#--------------------------------APP----------------------------------------
@app.route("/all")
def all_tasks():
    logging.INFO("querying all task in db")
    all_tasks = db.session.query(SprintManager).all()
    return jsonify(tasks=[task.to_dict() for task in all_tasks])


@app.route("/add", methods=["POST"])
def add_tasks():
    user_name = request.form.get("username")
    task_name = request.form.get("task_name")
    task_time = request.form.get("task_time")
    logging.INFO("getting data from the front-end")

    if user_name != "" or task_name != "" or task_time != "":
        add_new_task = SprintManager(
            username = user_name,
            task_name = task_name,
            task_time_start = task_time  
        )
        db.session.add(add_new_task)
        db.session.commit()
        logging.INFO("added new task to the db")

        task_params = {
            "username": user_name,
            "task_name": task_name,
            "task_time_start": task_time
        }

        logging.INFO("init post request")
        requests.post(f"{CALENDER_API_URL}/new_task", json=task_params)
        logging.INFO("sent post request to calendar api")
        return jsonify({"success": "Successfully added new task."}), 200
    else:
        return jsonify(error={"Not valid": "Sorry, you can't leave input empty."}), 404


@app.route("/delete", methods=["DELETE"])
def delete_task():
    task_id = request.form.get("id")
    task_to_delete = SprintManager.query.get(task_id)
    logging.INFO("finding the task by id")
    if task_to_delete:         
        db.session.delete(task_to_delete)
        db.session.commit()
        logging.INFO("task deleted in db")

        task_params = {
        "task_name": task_to_delete['task_name']
        }

        logging.INFO("init delete request")
        requests.delete(f"{CALENDER_API_URL}/delete", json=task_params)
        logging.INFO("sent delete request to calendar api")
        return jsonify({"success": "Successfully deleted task."}), 200
    else:
        logging.INFO("couldn't find the task")
        return jsonify(error={"Not Found": "Sorry a task with that id was not found in the database."}), 404


@app.route("/update-task", methods=["PUT"])
def update_task():
    user_name = request.form.get("username")
    task_name = request.form.get("task_name")
    task_time = request.form.get("task_time")
    logging.INFO("getting data from the front-end")

    task_id = request.form.get("id")
    logging.INFO("querying db to find the task by id")
    task_to_update = SprintManager.query.get(task_id)
    if task_to_update:
        task_to_update.username = user_name
        task_to_update.task_name = task_name
        task_to_update.task_time = task_time
        db.session.commit()
        logging.INFO("updated task in db")

        task_params = {
        "username": user_name,
        "task_name": task_name,
        "task_time_start": task_time
        }

        logging.INFO("init put request")
        requests.put(f"{CALENDER_API_URL}/new_task", json=task_params)
        logging.INFO("sent put request to calendar api")
        return jsonify({"success": "Successfully updated the new task."}), 200
    else:
        logging.INFO("task did not found in db")
        return jsonify(error={"Not Found": "Sorry a task with that id was not found in the database."}), 404


if __name__ =="__main__":
    app.run(debug=True, port=3000)