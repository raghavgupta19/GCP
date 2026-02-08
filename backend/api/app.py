from flask import Flask, request, jsonify
from flask_cors import CORS
from backend.services.storage import write_to_bucket


app = Flask(__name__)
CORS(app)  # allow frontend (8080) to talk to backend (3000)

@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data received"}), 400

    try:
        write_to_bucket(data)
        return jsonify({"status": "saved"}), 200
    except Exception as e:
        # Log real error to server
        print("ERROR:", e)
        return jsonify({"error": "internal error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)

