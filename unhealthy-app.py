from flask import Flask
import time
import os

app = Flask(__name__)
start_time = time.time()

@app.route('/')
def hello():
    return f'Running for {int(time.time() - start_time)} seconds'

@app.route('/health')
def health():
    # 30秒後にヘルスチェック失敗
    uptime = time.time() - start_time
    if uptime > 30:
        return 'UNHEALTHY', 500
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
