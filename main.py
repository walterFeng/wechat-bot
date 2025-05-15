from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from wxauto import WeChat
import os
import uuid
import tempfile

app = Flask(__name__)
CORS(app)  # 允许跨域
wx = WeChat()  # 初始化微信客户端

@app.route('/sessions', methods=['GET'])
def get_sessions():
    sessions = wx.GetSessionList()
    return jsonify({'sessions': sessions})

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    who = data.get('who')
    msg = data.get('msg')
    if not who or not msg:
        return jsonify({'error': 'Missing `who` or `msg`'}), 400
    wx.SendMsg(msg, who)
    return jsonify({'status': 'message sent'})

@app.route('/send_file', methods=['POST'])
def send_file():
    data = request.json
    who = data.get('who')
    files = data.get('files')  # Expecting a list of file paths
    if not who or not files:
        return jsonify({'error': 'Missing `who` or `files`'}), 400
    wx.SendFiles(filepath=files, who=who)
    return jsonify({'status': 'files sent'})

@app.route('/download_chat', methods=['GET'])
def download_chat():
    msgs = wx.GetAllMessage(savepic=True)
    # 临时保存记录为txt
    temp_dir = tempfile.gettempdir()
    unique_name = f"chat_{uuid.uuid4().hex[:8]}.txt"
    save_path = os.path.join(temp_dir, unique_name)
    with open(save_path, 'w', encoding='utf-8') as f:
        for msg in msgs:
            f.write(str(msg) + '\n')
    return send_file(save_path, as_attachment=True, download_name='chat_record.txt')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8057)

