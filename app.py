from flask import Flask, request
from flask_cors import CORS
import mysql.connector
import bcrypt
import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

app = Flask(__name__)
CORS(app)


# =========================
# MySQL Database Connection
# =========================

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", 3306))
    )


# =========================
# Basic Backend Test
# =========================

@app.route("/")
def home():
    return {
        "message": "Ride Sharing System Backend is running"
    }


# =========================
# Database Connection Test
# =========================

@app.route("/db-test")
def db_test():
    try:
        connection = get_db_connection()

        if connection.is_connected():
            connection.close()

            return {
                "status": "success",
                "message": "MySQL database connected successfully"
            }

    except mysql.connector.Error as error:
        return {
            "status": "error",
            "message": str(error)
        }, 500


# =========================
# Student Registration
# =========================

@app.route("/register", methods=["POST"])
def register():

    data = request.get_json()

    if not data:
        return {
            "status": "error",
            "message": "No registration data received"
        }, 400

    full_name = data.get("full_name")
    email = data.get("email")
    phone = data.get("phone")
    student_id = data.get("student_id")
    password = data.get("password")
    role = data.get("role")

    if not all([full_name, email, student_id, password, role]):
        return {
            "status": "error",
            "message": "Please fill all required fields"
        }, 400

    if role not in ["passenger", "driver"]:
        return {
            "status": "error",
            "message": "Role must be passenger or driver"
        }, 400

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE email = %s OR student_id = %s
            """,
            (email, student_id)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()
            connection.close()

            return {
                "status": "error",
                "message": "Email or Student ID already registered"
            }, 409

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        cursor.execute(
            """
            INSERT INTO users
            (
                full_name,
                email,
                phone,
                student_id,
                password,
                role
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                full_name,
                email,
                phone,
                student_id,
                hashed_password,
                role
            )
        )

        connection.commit()

        cursor.close()
        connection.close()

        return {
            "status": "success",
            "message": "Student registered successfully"
        }, 201

    except mysql.connector.Error as error:

        return {
            "status": "error",
            "message": str(error)
        }, 500


# =========================
# Student Login
# =========================

@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()

    if not data:
        return {
            "status": "error",
            "message": "No login data received"
        }, 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return {
            "status": "error",
            "message": "Email and password are required"
        }, 400

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                full_name,
                email,
                phone,
                student_id,
                password,
                role
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if not user:
            return {
                "status": "error",
                "message": "Invalid email or password"
            }, 401

        password_is_correct = bcrypt.checkpw(
            password.encode("utf-8"),
            user["password"].encode("utf-8")
        )

        if not password_is_correct:
            return {
                "status": "error",
                "message": "Invalid email or password"
            }, 401

        return {
            "status": "success",
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "full_name": user["full_name"],
                "email": user["email"],
                "phone": user["phone"],
                "student_id": user["student_id"],
                "role": user["role"]
            }
        }, 200

    except mysql.connector.Error as error:

        return {
            "status": "error",
            "message": str(error)
        }, 500


# =========================
# Create / Offer a Ride
# =========================

@app.route("/rides", methods=["POST"])
def create_ride():

    data = request.get_json()

    if not data:
        return {
            "status": "error",
            "message": "No ride data received"
        }, 400

    driver_id = data.get("driver_id")
    start_location = data.get("start_location")
    destination = data.get("destination")
    ride_date = data.get("ride_date")
    ride_time = data.get("ride_time")
    available_seats = data.get("available_seats")
    price = data.get("price", 0)
    description = data.get("description", "")

    if not all([
        driver_id,
        start_location,
        destination,
        ride_date,
        ride_time,
        available_seats
    ]):
        return {
            "status": "error",
            "message": "Please fill all required ride details"
        }, 400

    try:
        driver_id = int(driver_id)
        available_seats = int(available_seats)
        price = float(price)

    except (ValueError, TypeError):

        return {
            "status": "error",
            "message": "Invalid driver ID, seats or price"
        }, 400

    if available_seats <= 0:
        return {
            "status": "error",
            "message": "Available seats must be greater than 0"
        }, 400

    if price < 0:
        return {
            "status": "error",
            "message": "Price cannot be negative"
        }, 400

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE id = %s
            AND role = 'driver'
            """,
            (driver_id,)
        )

        driver = cursor.fetchone()

        if not driver:

            cursor.close()
            connection.close()

            return {
                "status": "error",
                "message": "Driver account not found"
            }, 404

        cursor.execute(
            """
            INSERT INTO rides
            (
                driver_id,
                start_location,
                destination,
                ride_date,
                ride_time,
                available_seats,
                price,
                description
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                driver_id,
                start_location,
                destination,
                ride_date,
                ride_time,
                available_seats,
                price,
                description
            )
        )

        connection.commit()

        ride_id = cursor.lastrowid

        cursor.close()
        connection.close()

        return {
            "status": "success",
            "message": "Ride offered successfully",
            "ride_id": ride_id
        }, 201

    except mysql.connector.Error as error:

        return {
            "status": "error",
            "message": str(error)
        }, 500


# =========================
# Get Available Rides
# =========================

@app.route("/rides", methods=["GET"])
def get_rides():

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                rides.id,
                rides.driver_id,
                users.full_name AS driver_name,
                users.email AS driver_email,
                rides.start_location,
                rides.destination,
                rides.ride_date,
                rides.ride_time,
                rides.available_seats,
                rides.price,
                rides.description,
                rides.status
            FROM rides
            INNER JOIN users
                ON rides.driver_id = users.id
            WHERE rides.status = 'active'
            ORDER BY rides.ride_date ASC, rides.ride_time ASC
            """
        )

        rides = cursor.fetchall()

        cursor.close()
        connection.close()

        for ride in rides:

            if ride["ride_date"] is not None:
                ride["ride_date"] = ride["ride_date"].isoformat()

            if ride["ride_time"] is not None:
                ride["ride_time"] = str(ride["ride_time"])

        return {
            "status": "success",
            "rides": rides
        }, 200

    except mysql.connector.Error as error:

        return {
            "status": "error",
            "message": str(error)
        }, 500


# =========================
# Request / Join a Ride
# =========================

@app.route("/ride-requests", methods=["POST"])
def request_ride():

    data = request.get_json()

    if not data:
        return {
            "status": "error",
            "message": "No ride request data received"
        }, 400

    ride_id = data.get("ride_id")
    passenger_id = data.get("passenger_id")

    if not ride_id or not passenger_id:
        return {
            "status": "error",
            "message": "Ride ID and passenger ID are required"
        }, 400

    try:
        ride_id = int(ride_id)
        passenger_id = int(passenger_id)

    except (ValueError, TypeError):

        return {
            "status": "error",
            "message": "Invalid ride ID or passenger ID"
        }, 400

    try:

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, role
            FROM users
            WHERE id = %s
            """,
            (passenger_id,)
        )

        passenger = cursor.fetchone()

        if not passenger:

            cursor.close()
            connection.close()

            return {
                "status": "error",
                "message": "Passenger account not found"
            }, 404

        cursor.execute(
            """
            SELECT
                id,
                driver_id,
                available_seats
            FROM rides
            WHERE id = %s
            AND status = 'active'
            """,
            (ride_id,)
        )

        ride = cursor.fetchone()

        if not ride:

            cursor.close()
            connection.close()

            return {
                "status": "error",
                "message": "Ride not found or no longer available"
            }, 404

        if ride[1] == passenger_id:

            cursor.close()
            connection.close()

            return {
                "status": "error",
                "message": "You cannot request your own ride"
            }, 400

        if ride[2] <= 0:

            cursor.close()
            connection.close()

            return {
                "status": "error",
                "message": "No seats available"
            }, 400

        cursor.execute(
            """
            SELECT id
            FROM ride_requests
            WHERE ride_id = %s
            AND passenger_id = %s
            AND status = 'pending'
            """,
            (ride_id, passenger_id)
        )

        existing_request = cursor.fetchone()

        if existing_request:

            cursor.close()
            connection.close()

            return {
                "status": "error",
                "message": "You have already requested this ride"
            }, 409

        cursor.execute(
            """
            INSERT INTO ride_requests
            (
                ride_id,
                passenger_id,
                status
            )
            VALUES (%s, %s, 'pending')
            """,
            (
                ride_id,
                passenger_id
            )
        )

        connection.commit()

        request_id = cursor.lastrowid

        cursor.close()
        connection.close()

        return {
            "status": "success",
            "message": "Ride request sent successfully",
            "request_id": request_id
        }, 201

    except mysql.connector.Error as error:

        return {
            "status": "error",
            "message": str(error)
        }, 500


# =========================
# Get Ride Requests for Driver
# =========================

@app.route("/ride-requests/driver/<int:driver_id>", methods=["GET"])
def get_driver_requests(driver_id):

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE id = %s
            AND role = 'driver'
            """,
            (driver_id,)
        )

        driver = cursor.fetchone()

        if not driver:

            cursor.close()
            connection.close()

            return {
                "status": "error",
                "message": "Driver account not found"
            }, 404

        cursor.execute(
            """
            SELECT
                ride_requests.id AS request_id,
                ride_requests.ride_id,
                ride_requests.passenger_id,
                users.full_name AS passenger_name,
                users.email AS passenger_email,
                users.phone AS passenger_phone,
                users.student_id AS passenger_student_id,
                rides.start_location,
                rides.destination,
                rides.ride_date,
                rides.ride_time,
                rides.price,
                ride_requests.status,
                ride_requests.requested_at
            FROM ride_requests
            INNER JOIN rides
                ON ride_requests.ride_id = rides.id
            INNER JOIN users
                ON ride_requests.passenger_id = users.id
            WHERE rides.driver_id = %s
            ORDER BY ride_requests.requested_at DESC
            """,
            (driver_id,)
        )

        requests = cursor.fetchall()

        cursor.close()
        connection.close()

        for ride_request in requests:

            if ride_request["ride_date"] is not None:
                ride_request["ride_date"] = (
                    ride_request["ride_date"].isoformat()
                )

            if ride_request["ride_time"] is not None:
                ride_request["ride_time"] = str(
                    ride_request["ride_time"]
                )

            if ride_request["requested_at"] is not None:
                ride_request["requested_at"] = (
                    ride_request["requested_at"].isoformat()
                )

            if ride_request["price"] is not None:
                ride_request["price"] = str(
                    ride_request["price"]
                )

        return {
            "status": "success",
            "requests": requests
        }, 200

    except mysql.connector.Error as error:

        return {
            "status": "error",
            "message": str(error)
        }, 500


# =========================
# Get Ride Requests for Passenger
# =========================

@app.route("/ride-requests/passenger/<int:passenger_id>", methods=["GET"])
def get_passenger_requests(passenger_id):

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Check that the user is a passenger
        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE id = %s
            AND role = 'passenger'
            """,
            (passenger_id,)
        )

        passenger = cursor.fetchone()

        if not passenger:

            cursor.close()
            connection.close()

            return {
                "status": "error",
                "message": "Passenger account not found"
            }, 404

        # Get all requests made by this passenger
        cursor.execute(
            """
            SELECT
                ride_requests.id AS request_id,
                ride_requests.ride_id,
                rides.driver_id,
                users.full_name AS driver_name,
                users.email AS driver_email,
                users.phone AS driver_phone,
                users.student_id AS driver_student_id,
                rides.start_location,
                rides.destination,
                rides.ride_date,
                rides.ride_time,
                rides.available_seats,
                rides.price,
                rides.description,
                rides.status AS ride_status,
                ride_requests.status AS request_status,
                ride_requests.requested_at
            FROM ride_requests
            INNER JOIN rides
                ON ride_requests.ride_id = rides.id
            INNER JOIN users
                ON rides.driver_id = users.id
            WHERE ride_requests.passenger_id = %s
            ORDER BY ride_requests.requested_at DESC
            """,
            (passenger_id,)
        )

        requests = cursor.fetchall()

        cursor.close()
        connection.close()

        # Convert MySQL date/time values into JSON-safe strings
        for ride_request in requests:

            if ride_request["ride_date"] is not None:
                ride_request["ride_date"] = (
                    ride_request["ride_date"].isoformat()
                )

            if ride_request["ride_time"] is not None:
                ride_request["ride_time"] = str(
                    ride_request["ride_time"]
                )

            if ride_request["requested_at"] is not None:
                ride_request["requested_at"] = (
                    ride_request["requested_at"].isoformat()
                )

            if ride_request["price"] is not None:
                ride_request["price"] = str(
                    ride_request["price"]
                )

        return {
            "status": "success",
            "requests": requests
        }, 200

    except mysql.connector.Error as error:

        return {
            "status": "error",
            "message": str(error)
        }, 500


# =========================
# Accept Ride Request
# =========================

@app.route("/ride-requests/<int:request_id>/accept", methods=["PUT"])
def accept_ride_request(request_id):

    data = request.get_json()

    if not data:
        return {
            "status": "error",
            "message": "Driver ID is required"
        }, 400

    driver_id = data.get("driver_id")

    if not driver_id:

        return {
            "status": "error",
            "message": "Driver ID is required"
        }, 400

    try:
        driver_id = int(driver_id)

    except (ValueError, TypeError):

        return {
            "status": "error",
            "message": "Invalid driver ID"
        }, 400

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                ride_requests.id AS request_id,
                ride_requests.ride_id,
                ride_requests.status,
                rides.driver_id,
                rides.available_seats
            FROM ride_requests
            INNER JOIN rides
                ON ride_requests.ride_id = rides.id
            WHERE ride_requests.id = %s
            AND rides.driver_id = %s
            """,
            (request_id, driver_id)
        )

        ride_request = cursor.fetchone()

        if not ride_request:

            cursor.close()
            connection.close()

            return {
                "status": "error",
                "message": "Ride request not found"
            }, 404

        if ride_request["status"] != "pending":

            cursor.close()
            connection.close()

            return {
                "status": "error",
                "message": "This request has already been processed"
            }, 409

        if ride_request["available_seats"] <= 0:

            cursor.close()
            connection.close()

            return {
                "status": "error",
                "message": "No seats available"
            }, 400

        cursor.execute(
            """
            UPDATE ride_requests
            SET status = 'accepted'
            WHERE id = %s
            """,
            (request_id,)
        )

        cursor.execute(
            """
            UPDATE rides
            SET available_seats = available_seats - 1
            WHERE id = %s
            """,
            (ride_request["ride_id"],)
        )

        connection.commit()

        cursor.close()
        connection.close()

        return {
            "status": "success",
            "message": "Ride request accepted successfully"
        }, 200

    except mysql.connector.Error as error:

        connection.rollback()

        cursor.close()
        connection.close()

        return {
            "status": "error",
            "message": str(error)
        }, 500


# =========================
# Reject Ride Request
# =========================

@app.route("/ride-requests/<int:request_id>/reject", methods=["PUT"])
def reject_ride_request(request_id):

    data = request.get_json()

    if not data:
        return {
            "status": "error",
            "message": "Driver ID is required"
        }, 400

    driver_id = data.get("driver_id")

    if not driver_id:

        return {
            "status": "error",
            "message": "Driver ID is required"
        }, 400

    try:
        driver_id = int(driver_id)

    except (ValueError, TypeError):

        return {
            "status": "error",
            "message": "Invalid driver ID"
        }, 400

    try:

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                ride_requests.id,
                ride_requests.status
            FROM ride_requests
            INNER JOIN rides
                ON ride_requests.ride_id = rides.id
            WHERE ride_requests.id = %s
            AND rides.driver_id = %s
            """,
            (request_id, driver_id)
        )

        ride_request = cursor.fetchone()

        if not ride_request:

            cursor.close()
            connection.close()

            return {
                "status": "error",
                "message": "Ride request not found"
            }, 404

        if ride_request["status"] != "pending":

            cursor.close()
            connection.close()

            return {
                "status": "error",
                "message": "This request has already been processed"
            }, 409

        cursor.execute(
            """
            UPDATE ride_requests
            SET status = 'rejected'
            WHERE id = %s
            """,
            (request_id,)
        )

        connection.commit()

        cursor.close()
        connection.close()

        return {
            "status": "success",
            "message": "Ride request rejected successfully"
        }, 200

    except mysql.connector.Error as error:

        connection.rollback()

        cursor.close()
        connection.close()

        return {
            "status": "error",
            "message": str(error)
        }, 500


# =========================
# Start Flask Server
# =========================

if __name__ == "__main__":
    app.run(debug=True)