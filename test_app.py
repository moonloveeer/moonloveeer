from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World! This is a test server.'

if __name__ == '__main__':
    print("Starting test server on http://localhost:5005")
    app.run(host='0.0.0.0', port=5005, debug=True)
