import os
from google import genai

# 從環境變數讀取 Key
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ 找不到 API Key，請檢查環境變數設定！")
else:
    # 這裡很關鍵：我們明確指定使用 'gemini' 模式，這會強迫它走 AI Studio 的 API 路徑
    client = genai.Client(api_key=api_key)
    
    try:
        # 測試提問
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents="你好，我正在用 Jetson Orin Nano 跟你打招呼！"
        )
        
        print("-" * 30)
        print(response.text)
        print("-" * 30)
        
    except Exception as e:
        print(f"❌ 發生錯誤：{e}")
        # 如果還是失敗，嘗試印出所有可用模型，看看你的 Key 權限
        print("\n嘗試列出可用模型：")
        for m in client.models.list():
            print(f"- {m.name}")
