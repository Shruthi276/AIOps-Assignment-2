from flask import Flask, request, jsonify
import joblib

app = Flask(__name__)

model = joblib.load("model.joblib")


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()

    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field"}), 400

    text = data["text"]
    prediction = model.predict([text])[0]

    return jsonify({"label": prediction})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
