import random
import time
import hashlib

from flask import Flask, request

import pymongo
try:
    import simplejson as json
except Exception:
    import json
import requests

from settings import APPID, APPSECRET


app = Flask("ticket_server")

CHARSET="abcdefghijklmnopqrstuvwxyz0123456789"

ticket_collection = pymongo.Connection().wish_bottle.wish_bottle.ticket


@app.route("/get_signature", methods=["POST"])
def get_signature():
    data = json.loads(request.data)
    url = data["url"]
    timestamp = int(time.time())
    appId = APPID
    nonceStr = "".join(random.sample(CHARSET, 10))
    try:
        ticket = ticket_collection.find_one()
        if timestamp - ticket["timestamp"] > 3600:
            raise Exception()
        ticket = ticket["content"]
    except Exception:
        res = requests.get("https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s" % (APPID, APPSECRET))
        data = json.loads(res.content)
        access_token = data["access_token"]
        res = requests.get("https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token=%s&type=jsapi" % access_token)
        data = json.loads(res.content)
        ticket = data["ticket"]
        ticket_collection.drop()
        ticket_collection.insert({"content": ticket, "timestamp": timestamp})

    timestamp = str(timestamp)

    signature = "jsapi_ticket="+ticket+"&noncestr="+nonceStr+"&timestamp="+timestamp+"&url="+url
    
    signature = signature.encode("utf-8")

    signature = hashlib.sha1(signature).hexdigest()

    return json.dumps({
        "timestamp": timestamp,
        "nonceStr": nonceStr,
        "appId": appId,
        "signature": signature
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8015, debug=True)
