import os
from flask import Flask, render_template, request, jsonify
import face_recognition

import cv2
import numpy as np
import mysql.connector
import dlib
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = r'C:\Users\admin\PycharmProjects\pythonTask\employeelist\employee_images'


app = Flask(__name__, template_folder='template')
app.secret_key = 'your_secret_key'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def connect():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="details"
    )
    return conn


@app.route('/')
def home():
    return render_template('base.html')


def load_employee_images():
    known_face_encodings = []
    known_face_ids = []

    images_folder = r'C:\Users\admin\PycharmProjects\pythonTask\employeelist\employee_images'

    for filename in os.listdir(images_folder):
        employee_id_str, _ = os.path.splitext(filename)

        try:
            employee_id = int(employee_id_str)
        except ValueError:
            continue

        image_path = os.path.join(images_folder, filename)

        image = face_recognition.load_image_file(image_path)
        face_encodings = face_recognition.face_encodings(image)
        if len(face_encodings) > 0:
            face_encoding = face_encodings[0]
            known_face_encodings.append(face_encoding)
            known_face_ids.append(employee_id)

    return known_face_encodings, known_face_ids


@app.route('/scan_employee', methods=['POST'])
def scan_employee():
    cap = cv2.VideoCapture(0)

    ret, frame = cap.read()

    cv2.imshow('Video', frame)

    if not ret:
        cap.release()
        return "Error: Unable to capture image from the camera."

    cap.release()

    known_face_encodings, known_face_ids = load_employee_images()
    unknown_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_encodings = face_recognition.face_encodings(unknown_image)

    if len(face_encodings) > 0:
        unknown_face_encoding = face_encodings[0]

        matches = face_recognition.compare_faces(known_face_encodings, unknown_face_encoding)

        for i, matched in enumerate(matches):
            if matched:
                matched_employee_id = known_face_ids[i]

                conn = connect()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM employees WHERE employee_id = %s", (matched_employee_id,))
                matched_employee = cursor.fetchone()
                conn.close()

                return render_template('employee_details.html', employee=matched_employee)

        return render_template('no_match.html')
    else:
        return render_template('no_face_detected.html')


@app.route('/scan_employee', methods=['GET'])
def show_scan_employee_page():
    return render_template('scan_employee.html')


@app.route('/employee_list', methods=['GET', 'POST'])
def employee_list():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT employee_post FROM employees")
    employee_posts = cursor.fetchall()

    fields = ['employee_id', 'first_name', 'last_name', 'employee_post', 'salary']
    operations = {
        'employee_id': {'equal': '=', 'not_equal': '!='},
        'first_name': {'equal': '=', 'not_equal': '!='},
        'last_name': {'equal': '=', 'not_equal': '!='},
        'employee_post': {'equal': '=', 'not_equal': '!='},
        'salary': {'equal': '=', 'not_equal': '!=', 'less_than': '<', 'greater_than': '>'}
    }

    field = request.form.get('field', 'employee_id')
    operation = request.form.get('operation', 'equal')

    if request.method == 'POST':
        value = request.form['value']

        if field not in operations or operation not in operations[field]:
            field = 'employee_id'
            operation = 'equal'

        if field == 'salary':
            sql = f"SELECT * FROM employees WHERE salary {operations[field][operation]} %s"
        else:
            sql = f"SELECT * FROM employees WHERE {field} {operations[field][operation]} %s"

        val = (value,)
        cursor.execute(sql, val)
    else:
        cursor.execute("SELECT * FROM employees")

    employees = cursor.fetchall()
    conn.close()
    employees = list({(employee[0], employee[1], employee[2], employee[3], employee[4]) for employee in employees})

    return render_template('employee_list.html', employees=employees, employee_posts=employee_posts, fields=fields,
                           operations=operations, field=field)

#
# @app.route('/scan_employee', methods=['GET'])
# def show_scan_employee_page():
#     return render_template('scan_employee.html')


@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    message = ""
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        employee_post = request.form['employee_post']
        salary = request.form['salary']

        uploaded_img = request.files['img']

        if uploaded_img.filename != '':
            img_filename = secure_filename(uploaded_img.filename)
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], img_filename)
            uploaded_img.save(img_path)
        else:
            img_path = None
        conn = connect()
        cursor = conn.cursor()
        sql = "INSERT INTO employees (first_name, last_name,employee_post,salary,img) VALUES (%s, %s, %s, %s,%s)"
        val = (first_name, last_name, employee_post, salary,img_path)
        cursor.execute(sql, val)
        conn.commit()
        conn.close()
        message = "Employee added successfully!!!!..."
    return render_template('add_employee.html', message=message)


@app.route('/edit_employee/<int:employee_id>', methods=['GET', 'POST'])
def edit_employee(employee_id):
    message = ""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE employee_id = %s", (employee_id,))
    employees = cursor.fetchone()

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        employee_post = request.form['employee_post']
        salary = request.form['salary']

        sql = "UPDATE employees SET first_name = %s, last_name = %s, employee_post = %s, salary = %s WHERE 	" \
              "employee_id = %s"
        val = (first_name, last_name, employee_post, salary, employee_id)
        cursor.execute(sql, val)
        conn.commit()
        conn.close()
        message = "Employee updated successfully!!!!..."
        conn = connect()

        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE employee_id = %s", (employee_id,))
        employees = cursor.fetchone()

    return render_template('edit_employee.html', employees=employees, message=message)


@app.route('/delete_employee/<int:employee_id>', methods=['GET', 'POST'])
def delete_employee(employee_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM employees WHERE employee_id = %s", (employee_id,))
    conn.commit()
    conn.close()

    message = "Employee deleted successfully!!!!..."
    return render_template('delete_employee.html', message=message)


if __name__ == '__main__':
    # known_face_encodings = []
    # known_face_ids = []
    #
    # load_employee_images()
    app.run(debug=True)
