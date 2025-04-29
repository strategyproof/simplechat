# lambda/index.py
import json
import os
import urllib.request
import urllib.error

# グローバル変数としてクライアントを初期化（初期値）
bedrock_client = None

# モデルID
MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")

def lambda_handler(event, context):
    try:
        # FastAPIエンドポイント
        FASTAPI_URL = os.environ.get("FASTAPI_URL", "https://2cba-34-32-198-202.ngrok-free.app/predict")

        print("Received event:", json.dumps(event))

        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")

        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])

        print("Processing message:", message)
        print("Calling FastAPI endpoint:", FASTAPI_URL)

        # FastAPI用のリクエストペイロード
        request_payload = {
            "message": message,
            "conversationHistory": conversation_history
        }
        req = urllib.request.Request(
            FASTAPI_URL,
            data=json.dumps(request_payload).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as res:
                response_body = json.loads(res.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            print("HTTPError from FastAPI:", error_body)
            raise Exception(f"FastAPI error: {e.code} {error_body}")

        print("FastAPI response:", json.dumps(response_body, ensure_ascii=False))

        # FastAPIの返却形式に応じて応答を取得
        assistant_response = response_body.get('response')
        if not assistant_response:
            raise Exception("No response content from FastAPI")

        # アシスタントの応答を会話履歴に追加
        conversation_history.append({
            "role": "assistant",
            "content": assistant_response
        })

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": conversation_history
            })
        }

    except Exception as error:
        print("Error:", str(error))
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
