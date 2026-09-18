import pandas as pd
import joblib

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB


df = pd.read_csv("spam_dataset.csv")

X = df["text"]
y = df["label"]

model = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("classifier", MultinomialNB())
])

model.fit(X, y)

joblib.dump(model, "model.joblib")

print("Model trained successfully!")
print(f"Training samples: {len(df)}")
print("Model saved as model.joblib")

test_messages = [
    "WIN a FREE iPhone now! Click here: win-now.co/claim",
    "Hey, are we still meeting for lunch tomorrow?",
]

predictions = model.predict(test_messages)

for message, prediction in zip(test_messages, predictions):
    print(f"\nMessage: {message}")
    print(f"Prediction: {prediction}")
