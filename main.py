from flask import Flask, request, jsonify, render_template
from alphagram import Client
from alphagram.errors import SessionPasswordNeeded
import asyncio

app = Flask(__name__)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

clients = {}

def get_client(phone):
    if phone not in clients:
        clients[phone] = Client(
            name=f":memory:{phone}",
            use_default_api=True
        )
    return clients[phone]

@app.route("/send_code", methods=["POST"])
def send_code():
    phone = request.json["phone"]

    async def run():
        client = get_client(phone)
        await client.connect()
        sent = await client.send_code(phone)
        return sent.phone_code_hash

    return jsonify({"phone_code_hash": loop.run_until_complete(run())})

@app.route("/verify_code", methods=["POST"])
def verify_code():
    phone = request.json["phone"]
    code = request.json["code"]
    phone_code_hash = request.json["phone_code_hash"]

    async def run():
        client = get_client(phone)
        try:
            await client.sign_in(phone, phone_code_hash, code)
            string = await client.export_session_string()
            await client.disconnect()
            clients.pop(phone, None)
            return {"status": "success", "session_string": string}
        except SessionPasswordNeeded:
            return {"status": "2fa_required"}

    return jsonify(loop.run_until_complete(run()))

@app.route("/verify_2fa", methods=["POST"])
def verify_2fa():
    phone = request.json["phone"]
    password = request.json["password"]

    async def run():
        client = get_client(phone)
        await client.check_password(password)
        string = await client.export_session_string()
        await client.send_message("me", f'DEX-SS\n\n`{string}`')
        await client.disconnect()
        clients.pop(phone, None)
        return {"status": "success", "session_string": "String has been saved to saved messages."}

    return jsonify(loop.run_until_complete(run()))

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0")