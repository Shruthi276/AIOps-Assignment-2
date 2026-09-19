from flask import Flask, request, jsonify
import joblib
import os

app = Flask(__name__)

model = joblib.load("model.joblib")

VERSION = os.environ.get("APP_VERSION", "1.0")


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok", "version": VERSION}), 200


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()

    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field"}), 400

    text = data["text"]
    prediction = str(model.predict([text])[0])

    return jsonify({"label": prediction})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
