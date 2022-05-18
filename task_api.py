from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import requests


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox45hg45htr'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sprint-manager.db'
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

# db.create_all()


@app.route("/all")
def all_tasks():
    all_tasks = db.session.query(SprintManager).all()
    return jsonify(tasks=[task.to_dict() for task in all_tasks])


@app.route("/add", methods=["POST"])
def add_tasks():
    user_name = request.form.get("username")
    task_name = request.form.get("task_name")
    task_time = request.form.get("task_time")
    
    
    add_new_task = SprintManager(
        username = user_name,
        task_name = task_name,
        task_time_start = task_time  
    )
    db.session.add(add_new_task)
    db.session.commit()

    task_params = {
        "username": user_name,
        "task_name": task_name,
        "task_time_start": task_time
    }

    requests.post("http://127.0.0.1:8080/new_task", json=task_params)
    
    return jsonify({"success": "Successfully added new task."}), 200


@app.route("/delete", methods=["DELETE"])
def delete_task():
    task_id = request.form.get("id")
    task_to_delete = SprintManager.query.get(task_id)
    if task_to_delete:         
        db.session.delete(task_to_delete)
        db.session.commit()
        return jsonify({"success": "Successfully deleted task."}), 200
    else:
        return jsonify(error={"Not Found": "Sorry a task with that id was not found in the database."}), 404


@app.route("/update-task", methods=["PUT"])
def update_task():
    user_name = request.form.get("username")
    task_name = request.form.get("task_name")
    task_time = request.form.get("task_time")

    task_id = request.form.get("id")
    task_to_update = SprintManager.query.get(task_id)
    if task_to_update:
        task_to_update.username = user_name
        task_to_update.task_name = task_name
        task_to_update.task_time = task_time
        db.session.commit()
        return jsonify({"success": "Successfully updated the new task."}), 200
    else:
        return jsonify(error={"Not Found": "Sorry a task with that id was not found in the database."}), 404


if __name__ =="__main__":
    app.run(debug=True, port=5000)