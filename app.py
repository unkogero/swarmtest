from flask import Flask
import socket
import os

app = Flask(__name__)

@app.route('/')
def hello():
    hostname = socket.gethostname()
    return f'''
    <html>
        <head><title>Docker Swarm Test</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px; background-color: #e3f2fd;">
            <h1 style="color: #c62828;">Docker Swarm 動作確認 v3.0</h1>
            <h2>コンテナ名: {hostname}</h2>
            <p style="font-size: 20px; color: #d32f2f;">🚀 ローリングアップデート第2弾！</p>
        </body>
    </html>
    '''

@app.route('/health')
def health():
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
