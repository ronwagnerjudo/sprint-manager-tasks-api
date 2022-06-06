# Sprint - Manager Task API

Task API is use to get data from the front-end - the name of the task and the duration of the task. and from the User API - the user token and the user name. 
Task API save the data in his database and passing it to the Calendar API.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install the required packages.

```bash
pip install -r requirements.txt
```

## Get all database tasks data

### Request - GET

`
http://127.0.0.1:3000/all
`

## Add new task

### Request - POST

`
http://127.0.0.1:3000/add
`

## Update existing task

### Request - PUT

`
http://127.0.0.1:3000/update-task
`

## Delete task

### Request - DELETE

`
http://127.0.0.1:3000/delete
`

