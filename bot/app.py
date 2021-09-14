from flask import Flask, request, abort, Response

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

from util.ncu import NCUCalendar

import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("CHANNEL_ACCESS_TOKEN", None))
handler = WebhookHandler(os.environ.get("CHANNEL_SECRET", None))
webhook_url = os.environ.get("WEBHOOK_URL", None)


@app.route("/download")
def download():
    if request.args.get("id") is not None:
        filename = f'{request.args.get("id")}.ics'
        for f in os.scandir("schedule"):
            if filename == f.name:
                with open(f'schedule/{f.name}') as f:
                    return Response(f.read(),
                                    status=200,
                                    content_type="text/calendar",
                                    headers={'Content-Disposition': 'attachment'})
        return Response("403", status=403)
    else:
        return Response("403", status=403)


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.split("\n")
    command = text[0]
    print(text)
    if event.source.user_id != "Udeadbeefdeadbeefdeadbeefdeadbeef":
        if command == "login":
            try:
                user = NCUCalendar(username=text[1], password=text[2], announce_time=int(text[3]))
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text=f'Open this link at the outside of your Line app: {webhook_url}/download?id={user.get_calendar()}')
                )
            except IndexError as e:
                print(e)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="Params: username, password, announce_time")
                )
            except ValueError as e:
                print(e)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="Error")
                )
        elif command == "demo":
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f'Open this link at the outside of your Line app: {webhook_url}/download?id=demo_ae0fbbd60b5ee9e496840db3e7dd7d81')
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="unknown command")
            )


if __name__ == "__main__":
    app.run()
