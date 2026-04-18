from flask import Flask
import os

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health():
    return "Flask works!", 200
