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
    <title>Vietnam Football Chatbot</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
            background: #f7f7f8;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        /* Header */
        .header {
            background: white;
            border-bottom: 1px solid #e5e5e5;
            padding: 12px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .header h1 {
            font-size: 16px;
            font-weight: 600;
            color: #202123;
        }
        
        .header-info {
            font-size: 13px;
            color: #6e6e80;
        }
        
        /* Main container */
        .container {
            flex: 1;
            display: flex;
            flex-direction: column;
            max-width: 800px;
            width: 100%;
            margin: 0 auto;
            overflow: hidden;
        }
        
        /* Messages area */
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .messages::-webkit-scrollbar {
            width: 8px;
        }
        
        .messages::-webkit-scrollbar-track {
            background: transparent;
        }
        
        .messages::-webkit-scrollbar-thumb {
            background: #d1d1d6;
            border-radius: 4px;
        }
        
        .messages::-webkit-scrollbar-thumb:hover {
            background: #b1b1b6;
        }
        
        /* Message styles */
        .message {
            display: flex;
            gap: 12px;
            max-width: 100%;
        }
        
        .message.user {
            flex-direction: row-reverse;
        }
        
        .message-content {
            padding: 12px 16px;
            border-radius: 18px;
            max-width: 70%;
            line-height: 1.5;
            font-size: 15px;
        }
        
        .message.user .message-content {
            background: #2b2b2b;
            color: white;
        }
        
        .message.bot .message-content {
            background: white;
            color: #202123;
            border: 1px solid #e5e5e5;
        }
        
        /* Input area */
        .input-area {
            background: white;
            border-top: 1px solid #e5e5e5;
            padding: 20px;
        }
        
        .input-container {
            max-width: 800px;
            margin: 0 auto;
            position: relative;
        }
        
        .input-wrapper {
            display: flex;
            background: white;
            border: 1px solid #d1d1d6;
            border-radius: 12px;
            padding: 8px 12px;
            transition: border-color 0.2s;
        }
        
        .input-wrapper:focus-within {
            border-color: #2b2b2b;
        }
        
        #user-input {
            flex: 1;
            border: none;
            outline: none;
            font-size: 15px;
            font-family: inherit;
            color: #202123;
            background: transparent;
            resize: none;
            max-height: 200px;
            min-height: 24px;
            line-height: 24px;
        }
        
        #user-input::placeholder {
            color: #8e8ea0;
        }
        
        #send-btn {
            background: transparent;
            border: none;
            cursor: pointer;
            padding: 4px 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: opacity 0.2s;
        }
        
        #send-btn:disabled {
            opacity: 0.3;
            cursor: not-allowed;
        }
        
        #send-btn:not(:disabled):hover {
            opacity: 0.8;
        }
        
        /* Send button icon */
        .send-icon {
            width: 24px;
            height: 24px;
            fill: #202123;
        }
        
        #send-btn:disabled .send-icon {
            fill: #8e8ea0;
        }
        
        /* Empty state */
        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            padding: 40px 20px;
            text-align: center;
        }
        
        .empty-state h2 {
            font-size: 32px;
            font-weight: 600;
            color: #202123;
            margin-bottom: 8px;
        }
        
        .empty-state p {
            font-size: 16px;
            color: #6e6e80;
        }
        
        /* Typing indicator */
        .typing-indicator {
            display: none;
            padding: 12px 16px;
            background: white;
            border: 1px solid #e5e5e5;
            border-radius: 18px;
            width: fit-content;
        }
        
        .typing-indicator.show {
            display: flex;
            gap: 4px;
        }
        
        .typing-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #8e8ea0;
            animation: typing 1.4s infinite;
        }
        
        .typing-dot:nth-child(2) {
            animation-delay: 0.2s;
        }
        
        .typing-dot:nth-child(3) {
            animation-delay: 0.4s;
        }
        
        @keyframes typing {
            0%, 60%, 100% {
                opacity: 0.3;
            }
            30% {
                opacity: 1;
            }
        }
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
    <!-- Header -->
    <div class="header">
        <h1>Vietnam Football Chatbot</h1>
    </div>
    
    <!-- Main container -->
    <div class="container">
        <!-- Messages area -->
        <div class="messages" id="messages">
            <!-- Empty state (hidden after first message) -->
            <div class="empty-state" id="empty-state">
                <h2>Vietnam Football Chatbot</h2>
                <p>Hỏi tôi về cầu thủ, câu lạc bộ, và đội tuyển bóng đá Việt Nam</p>
            </div>
        </div>
        
        <!-- Input area -->
        <div class="input-area">
            <div class="input-container">
                <div class="input-wrapper">
                    <textarea 
                        id="user-input" 
                        placeholder="Gửi tin nhắn..." 
                        rows="1"
                        autocomplete="off"
                    ></textarea>
                    <button id="send-btn" disabled>
                        <svg class="send-icon" viewBox="0 0 24 24">
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const chatMessages = document.getElementById('messages');
        const userInput = document.getElementById('user-input');
        const sendBtn = document.getElementById('send-btn');
        const emptyState = document.getElementById('empty-state');
        
        // Auto-resize textarea and enable/disable send button
        userInput.addEventListener('input', () => {
            userInput.style.height = 'auto';
            userInput.style.height = Math.min(userInput.scrollHeight, 200) + 'px';
            sendBtn.disabled = !userInput.value.trim();
        });
        
        function addMessage(content, isUser) {
            // Hide empty state after first message
            if (emptyState) {
                emptyState.style.display = 'none';
            }
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user' : 'bot'}`;
            messageDiv.innerHTML = `
                <div class="message-content">${content}</div>
            `;
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function addTypingIndicator() {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message bot';
            typingDiv.id = 'typing-indicator';
            typingDiv.innerHTML = `
                <div class="message-content">
                    <span style="opacity: 0.5">Đang trả lời...</span>
                </div>
            `;
            chatMessages.appendChild(typingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function removeTypingIndicator() {
            const typing = document.getElementById('typing-indicator');
            if (typing) {
                typing.remove();
            }
        }
        
        async function sendMessage() {
            const message = userInput.value.trim();
            if (!message) return;
            
            // Add user message
            addMessage(message, true);
            userInput.value = '';
            userInput.style.height = 'auto'; // Reset height
            sendBtn.disabled = true;
            
            // Show typing indicator
            addTypingIndicator();
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                
                // Remove typing indicator and add response
                removeTypingIndicator();
                addMessage(data.response, false);
            } catch (error) {
                removeTypingIndicator();
                addMessage('Xin lỗi, có lỗi xảy ra. Vui lòng thử lại!', false);
            }
            
            sendBtn.disabled = false;
            userInput.focus();
        }
        
        // Handle Enter and Shift+Enter
        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        sendBtn.addEventListener('click', sendMessage);
        
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
