// 微信小程序调用示例代码

// 方式1：使用分块接口模拟打字效果
async function chatWithTypingEffect(prompt) {
    try {
        wx.showLoading({ title: 'AI思考中...' });
        
        const res = await wx.request({
            url: 'https://your-domain.com/api/chat/miniprogram',
            method: 'POST',
            data: { prompt: prompt },
            header: { 'Content-Type': 'application/json' }
        });
        
        wx.hideLoading();
        
        if (res.data.code === 200) {
            const { chunks, chunk_delay } = res.data.data;
            let currentText = '';
            
            // 模拟打字效果
            for (let i = 0; i < chunks.length; i++) {
                currentText += chunks[i];
                
                // 更新UI显示
                this.setData({
                    currentAnswer: currentText
                });
                
                // 延迟显示下一块
                await new Promise(resolve => setTimeout(resolve, chunk_delay));
            }
            
            // 打字完成，添加到消息列表
            this.setData({
                messages: [...this.data.messages, {
                    role: 'assistant',
                    content: currentText,
                    timestamp: Date.now()
                }],
                currentAnswer: ''
            });
            
        } else {
            throw new Error(res.data.data.error);
        }
        
    } catch (error) {
        wx.hideLoading();
        wx.showToast({
            title: '请求失败',
            icon: 'error',
            duration: 2000
        });
        console.error('聊天请求失败:', error);
    }
}

// 方式2：使用简化接口直接显示
async function chatSimple(prompt) {
    try {
        wx.showLoading({ title: 'AI思考中...' });
        
        const res = await wx.request({
            url: 'https://your-domain.com/api/chat/simple',
            method: 'POST',
            data: { prompt: prompt },
            header: { 'Content-Type': 'application/json' }
        });
        
        wx.hideLoading();
        
        if (res.data.code === 200) {
            const answer = res.data.data.answer;
            
            // 直接显示完整回答
            this.setData({
                messages: [...this.data.messages, {
                    role: 'assistant',
                    content: answer,
                    timestamp: res.data.data.timestamp
                }]
            });
            
        } else {
            throw new Error(res.data.data.error);
        }
        
    } catch (error) {
        wx.hideLoading();
        wx.showToast({
            title: '请求失败',
            icon: 'error',
            duration: 2000
        });
        console.error('聊天请求失败:', error);
    }
}

// 方式3：支持多轮对话
async function chatWithHistory(prompt, messages) {
    try {
        wx.showLoading({ title: 'AI思考中...' });
        
        const res = await wx.request({
            url: 'https://your-domain.com/api/chat/simple',
            method: 'POST',
            data: { 
                messages: messages.map(msg => ({
                    role: msg.role,
                    content: msg.content
                }))
            },
            header: { 'Content-Type': 'application/json' }
        });
        
        wx.hideLoading();
        
        if (res.data.code === 200) {
            const answer = res.data.data.answer;
            
            // 添加AI回答到消息历史
            const newMessages = [...messages, {
                role: 'assistant',
                content: answer,
                timestamp: res.data.data.timestamp
            }];
            
            this.setData({
                messages: newMessages
            });
            
            return newMessages;
            
        } else {
            throw new Error(res.data.data.error);
        }
        
    } catch (error) {
        wx.hideLoading();
        wx.showToast({
            title: '请求失败',
            icon: 'error',
            duration: 2000
        });
        console.error('聊天请求失败:', error);
        return messages; // 返回原消息列表
    }
}

// 小程序页面完整示例
Page({
    data: {
        messages: [],
        inputText: '',
        currentAnswer: '',
        isLoading: false
    },

    // 输入框内容变化
    onInputChange(e) {
        this.setData({
            inputText: e.detail.value
        });
    },

    // 发送消息
    async sendMessage() {
        const { inputText, messages } = this.data;
        
        if (!inputText.trim()) {
            wx.showToast({
                title: '请输入消息',
                icon: 'none'
            });
            return;
        }

        // 添加用户消息
        const newMessages = [...messages, {
            role: 'user',
            content: inputText.trim(),
            timestamp: Date.now()
        }];

        this.setData({
            messages: newMessages,
            inputText: '',
            isLoading: true
        });

        // 调用聊天接口
        await this.chatWithHistory(inputText.trim(), newMessages);
        
        this.setData({
            isLoading: false
        });
    },

    // 聊天方法
    async chatWithHistory(prompt, messages) {
        try {
            const res = await wx.request({
                url: 'https://your-domain.com/api/chat/simple',
                method: 'POST',
                data: { 
                    messages: messages.map(msg => ({
                        role: msg.role,
                        content: msg.content
                    }))
                },
                header: { 'Content-Type': 'application/json' }
            });
            
            if (res.data.code === 200) {
                const answer = res.data.data.answer;
                
                this.setData({
                    messages: [...messages, {
                        role: 'assistant',
                        content: answer,
                        timestamp: res.data.data.timestamp
                    }]
                });
                
            } else {
                throw new Error(res.data.data.error);
            }
            
        } catch (error) {
            wx.showToast({
                title: '请求失败',
                icon: 'error',
                duration: 2000
            });
            console.error('聊天请求失败:', error);
        }
    },

    // 清空对话
    clearChat() {
        wx.showModal({
            title: '确认清空',
            content: '确定要清空所有对话记录吗？',
            success: (res) => {
                if (res.confirm) {
                    this.setData({
                        messages: []
                    });
                }
            }
        });
    }
});

// 小程序配置文件 app.json
const appConfig = {
    "pages": [
        "pages/chat/chat"
    ],
    "window": {
        "navigationBarTitleText": "AI聊天助手",
        "navigationBarBackgroundColor": "#ffffff",
        "navigationBarTextStyle": "black"
    },
    "networkTimeout": {
        "request": 30000,
        "downloadFile": 30000
    },
    "permission": {
        "scope.userLocation": {
            "desc": "你的位置信息将用于小程序位置接口的效果展示"
        }
    }
};

module.exports = {
    chatWithTypingEffect,
    chatSimple,
    chatWithHistory,
    appConfig
};
