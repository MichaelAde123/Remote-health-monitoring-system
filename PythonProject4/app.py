from flask import Flask, jsonify
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

# Function to fetch the latest data for a specific patient
def fetch_latest_data(patient_id):
    try:
        # Connect to the MySQL database
        conn = mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="",
            database="project4db",
            port=3306
        )
        cursor = conn.cursor()

        # Fetch the latest data for the patient
        query = """
        SELECT timestamp, heart_rate, respiratory_rate, body_temperature, oxygen_saturation,
               systolic_blood_pressure, diastolic_blood_pressure, derived_hrv, derived_pulse_pressure,
               derived_bmi, derived_map, risk_category
        FROM health_metrics
        WHERE patient_id = %s
        ORDER BY timestamp DESC
        LIMIT 1
        """
        cursor.execute(query, (patient_id,))
        result = cursor.fetchone()

        # Format the data as a dictionary
        if result:
            data = {
                "timestamp": result[0].strftime("%Y-%m-%d %H:%M:%S"),
                "heart_rate": result[1],
                "respiratory_rate": result[2],
                "body_temperature": result[3],
                "oxygen_saturation": result[4],
                "systolic_blood_pressure": result[5],
                "diastolic_blood_pressure": result[6],
                "derived_hrv": result[7],
                "derived_pulse_pressure": result[8],
                "derived_bmi": result[9],
                "derived_map": result[10],
                "risk_category": result[11]
            }
        else:
            data = {}

        return data

    except Error as e:
        print(f"Error: {e}")
        return {}

    finally:
        # Close the cursor and connection
        if conn.is_connected():
            cursor.close()
            conn.close()

# Route to fetch the latest data for a specific patient
@app.route("/data/<int:patient_id>")
def get_data(patient_id):
    data = fetch_latest_data(patient_id)
    return jsonify(data)

# Route to serve the webpage
@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Real-Time Patient Data</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h1>Real-Time Patient Data</h1>
        <canvas id="heartRateChart" width="400" height="200"></canvas>
        <canvas id="respiratoryRateChart" width="400" height="200"></canvas>
        <script src="/static/script.js"></script>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(debug=True)