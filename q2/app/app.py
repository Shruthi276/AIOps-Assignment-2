from flask import Flask, request, jsonify
import joblib
import redis
import os
import hashlib

app = Flask(__name__)

model = joblib.load("model.joblib")


redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_client = redis.Redis(host=redis_host, port=6379, decode_responses=True)


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()

    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field"}), 400

    text = data["text"]

    
    cache_key = "predict:" + hashlib.sha256(text.encode()).hexdigest()

    cached_label = redis_client.get(cache_key)
    if cached_label is not None:
        return jsonify({"label": cached_label, "cached": True})

    prediction = str(model.predict([text])[0])
    redis_client.setex(cache_key, 300, prediction)  

    return jsonify({"label": prediction, "cached": False})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
