"""
Simple Web Interface for Vietnam Football Chatbot

Run with: python -m chatbot.web_app
Then open: http://localhost:5000
"""

from flask import Flask, render_template_string, request, jsonify
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global chatbot instance
chatbot = None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚽ Vietnam Football Chatbot</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            padding: 30px 0;
        }
        
        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #ff6b6b, #ffd93d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        header p {
            color: #a0a0a0;
            font-size: 1.1em;
        }
        
        .chat-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .chat-messages {
            height: 450px;
            overflow-y: auto;
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .message {
            margin-bottom: 15px;
            display: flex;
            align-items: flex-start;
            animation: fadeIn 0.3s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message.user {
            flex-direction: row-reverse;
        }
        
        .message-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2em;
            flex-shrink: 0;
        }
        
        .message.user .message-avatar {
            background: linear-gradient(135deg, #667eea, #764ba2);
            margin-left: 10px;
        }
        
        .message.bot .message-avatar {
            background: linear-gradient(135deg, #11998e, #38ef7d);
            margin-right: 10px;
        }
        
        .message-content {
            max-width: 70%;
            padding: 12px 18px;
            border-radius: 18px;
            line-height: 1.5;
        }
        
        .message.user .message-content {
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-bottom-right-radius: 5px;
        }
        
        .message.bot .message-content {
            background: rgba(255, 255, 255, 0.1);
            border-bottom-left-radius: 5px;
        }
        
        .input-container {
            display: flex;
            gap: 10px;
        }
        
        #user-input {
            flex: 1;
            padding: 15px 20px;
            border: none;
            border-radius: 25px;
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
            font-size: 1em;
            outline: none;
            transition: all 0.3s ease;
        }
        
        #user-input:focus {
            background: rgba(255, 255, 255, 0.15);
            box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.5);
        }
        
        #user-input::placeholder {
            color: #888;
        }
        
        #send-btn {
            padding: 15px 30px;
            border: none;
            border-radius: 25px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: #fff;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        #send-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        
        #send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .examples {
            margin-top: 20px;
        }
        
        .examples h3 {
            color: #ffd93d;
            margin-bottom: 15px;
            font-size: 1.1em;
        }
        
        .example-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .example-btn {
            padding: 10px 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            background: transparent;
            color: #fff;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }
        
        .example-btn:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: #667eea;
        }
        
        .info-box {
            background: rgba(255, 215, 0, 0.1);
            border: 1px solid rgba(255, 215, 0, 0.3);
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
        }
        
        .info-box h4 {
            color: #ffd93d;
            margin-bottom: 10px;
        }
        
        .info-box ul {
            list-style: none;
            color: #ccc;
        }
        
        .info-box li {
            padding: 5px 0;
            padding-left: 20px;
            position: relative;
        }
        
        .info-box li::before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #38ef7d;
        }
        
        .typing-indicator {
            display: none;
            padding: 10px;
            color: #888;
        }
        
        .typing-indicator.show {
            display: block;
        }
        
        .stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .stat-item {
            text-align: center;
            padding: 15px 25px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
        }
        
        .stat-value {
            font-size: 1.8em;
            font-weight: bold;
            background: linear-gradient(90deg, #38ef7d, #11998e);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .stat-label {
            color: #888;
            font-size: 0.9em;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚽ Vietnam Football Chatbot</h1>
            <p>Hỏi đáp về bóng đá Việt Nam với AI sử dụng đồ thị tri thức</p>
        </header>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-value">95.5%</div>
                <div class="stat-label">Độ chính xác</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">1,060</div>
                <div class="stat-label">Thực thể</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">39,114</div>
                <div class="stat-label">Quan hệ</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">3-hop</div>
                <div class="stat-label">Multi-hop</div>
            </div>
        </div>
        
        <div class="chat-container">
            <div class="chat-messages" id="chat-messages">
                <div class="message bot">
                    <div class="message-avatar">🤖</div>
                    <div class="message-content">
                        Xin chào! Tôi là chatbot chuyên về bóng đá Việt Nam. 
                        Bạn có thể hỏi tôi về cầu thủ, câu lạc bộ, đội tuyển quốc gia, 
                        và các mối quan hệ giữa họ. Hãy thử hỏi tôi nhé! ⚽
                    </div>
                </div>
            </div>
            <div class="typing-indicator" id="typing-indicator">
                🤖 Đang suy nghĩ...
            </div>
            <div class="input-container">
                <input type="text" id="user-input" placeholder="Nhập câu hỏi của bạn..." autocomplete="off">
                <button id="send-btn">Gửi</button>
            </div>
        </div>
        
        <div class="examples">
            <h3>💡 Câu hỏi mẫu:</h3>
            <div class="example-buttons">
                <button class="example-btn" onclick="askExample(this)">Quang Hải chơi cho CLB nào?</button>
                <button class="example-btn" onclick="askExample(this)">Công Phượng sinh ra ở đâu?</button>
                <button class="example-btn" onclick="askExample(this)">Ai là đồng đội của Văn Toàn ở HAGL?</button>
                <button class="example-btn" onclick="askExample(this)">Quang Hải và Văn Hậu có chơi cùng CLB không?</button>
                <button class="example-btn" onclick="askExample(this)">Tiến Linh từng khoác áo đội tuyển Việt Nam chưa?</button>
                <button class="example-btn" onclick="askExample(this)">HLV Park Hang-seo dẫn dắt đội nào?</button>
            </div>
        </div>
        
        <div class="info-box">
            <h4>📋 Các loại câu hỏi hỗ trợ:</h4>
            <ul>
                <li><strong>Đúng/Sai:</strong> "Quang Hải chơi cho Hà Nội FC, đúng hay sai?"</li>
                <li><strong>Có/Không:</strong> "Công Phượng có từng chơi cho HAGL không?"</li>
                <li><strong>Thông tin:</strong> "Văn Lâm sinh ra ở đâu?"</li>
                <li><strong>Multi-hop (2 bước):</strong> "Quang Hải và Văn Hậu có chơi cùng CLB không?"</li>
                <li><strong>Multi-hop (3 bước):</strong> "Ai chơi cho CLB ở cùng tỉnh với Công Phượng?"</li>
            </ul>
        </div>
    </div>
    
    <script>
        const chatMessages = document.getElementById('chat-messages');
        const userInput = document.getElementById('user-input');
        const sendBtn = document.getElementById('send-btn');
        const typingIndicator = document.getElementById('typing-indicator');
        
        function addMessage(content, isUser) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user' : 'bot'}`;
            messageDiv.innerHTML = `
                <div class="message-avatar">${isUser ? '👤' : '🤖'}</div>
                <div class="message-content">${content}</div>
            `;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        async function sendMessage() {
            const message = userInput.value.trim();
            if (!message) return;
            
            // Add user message
            addMessage(message, true);
            userInput.value = '';
            sendBtn.disabled = true;
            typingIndicator.classList.add('show');
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                addMessage(data.response, false);
            } catch (error) {
                addMessage('Xin lỗi, có lỗi xảy ra. Vui lòng thử lại!', false);
            }
            
            typingIndicator.classList.remove('show');
            sendBtn.disabled = false;
            userInput.focus();
        }
        
        function askExample(btn) {
            userInput.value = btn.textContent;
            sendMessage();
        }
        
        sendBtn.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
        
        userInput.focus();
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    global chatbot
    
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'response': 'Vui lòng nhập câu hỏi!'})
    
    try:
        # Use chatbot to get response
        response = chatbot.chat(user_message)
        return jsonify({'response': response})
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({'response': f'Xin lỗi, có lỗi xảy ra: {str(e)}'})


def main():
    global chatbot
    
    print("="*60)
    print("⚽ VIETNAM FOOTBALL CHATBOT - WEB INTERFACE")
    print("="*60)
    
    # Initialize chatbot
    print("\n🚀 Đang khởi tạo HybridChatbot...")
    from .chatbot import HybridChatbot
    
    chatbot = HybridChatbot()
    if not chatbot.initialize():
        print("❌ Không thể khởi tạo chatbot!")
        return
    
    print("✅ Chatbot đã sẵn sàng!")
    print("\n" + "="*60)
    print("🌐 Mở trình duyệt và truy cập: http://localhost:5000")
    print("📝 Nhấn Ctrl+C để dừng server")
    print("="*60 + "\n")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    main()
