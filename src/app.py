# -*- coding:utf-8 -*-
from functools import wraps
import uuid
import time

import tornado.ioloop
import tornado.web
import tornado.gen
from tornado.options import define, options

import json
import motor
import bson

db = motor.MotorClient().wish_bottle.wish_bottle

define("port", default=8888, help="run on the given port", type=int)
# sys.setdefaultencoding("utf8")


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        if not self.get_cookie("user"):
            self.set_cookie("user", str(uuid.uuid4()))
        return self.get_cookie("user")


class GetHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        _type = self.get_argument("type")
        if _type == "time":
            timestamp = self.get_argument("timestamp")
            timestamp = int(timestamp)
            response = []
            cursor = db.text.find(
                {"timestamp": {"$lt": timestamp}}
            ).limit(1000)
            while (yield cursor.fetch_next):
                obj = cursor.next_object()
                obj["_id"] = str(obj["_id"])
                # obj["content"] = obj["content"].decode('unicode-escape')
                # obj["name"] = obj["name"].decode('unicode-escape')
                response.append(obj)
            self.write({"response": response})
            self.finish()
        elif _type == "star":
            response = []
            cursor = db.text.find().sort([("star_count", -1), ("timestamp", -1)]).limit(1000)
            while (yield cursor.fetch_next):
                obj = cursor.next_object()
                obj["_id"] = str(obj["_id"])
                response.append(obj)
            self.write({"response": response})
            self.finish()
        elif _type == "_id":
            _id = self.get_argument("_id")
            cursor = db.text.find({"_id": bson.objectid.ObjectId(_id)})
            yield cursor.fetch_next
            obj = cursor.next_object()
            obj["_id"] = str(obj["_id"])
            self.write({"response": [obj]})
            self.finish()
        elif _type == "count":
            count = yield db.text.count()
            self.write({"response": count})
            self.finish()
        else:
            self.write("no such method")
            self.finish()


class StarHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        print(self.current_user)
        _id = self.get_argument("_id")
        cursor = db.zan.find({"user": self.current_user, "text_id": _id})
        yield cursor.fetch_next
        record = cursor.next_object()
        if record is None:
            yield db.zan.insert({
                "user": self.current_user,
                "text_id": _id
            })
            yield db.text.update(
                {"_id": bson.objectid.ObjectId(_id)},
                {"$inc": {"star_count": 1}}
            )
            self.write("successfully")
        else:
            self.set_status(405)
        self.finish()

class UnstarHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        _id = self.get_argument("_id")
        cursor = db.zan.find({"user": self.current_user, "text_id": _id})
        yield cursor.fetch_next
        record = cursor.next_object()
        if record is None:
            self.set_status(405)
        else:
            yield db.zan.remove({"user": self.current_user, "text_id": _id})
            yield db.text.update(
                {"_id": bson.objectid.ObjectId(_id)}, 
                {"$inc": {"star_count": -1}}
            )
            self.write("successfully")
        self.finish()


class PostHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        data = json.loads(self.request.body.decode("utf8"))
        name = data["name"]
        content = data["content"]
        timestamp = int(time.time()*1000)
        # insert
        result = yield db.text.insert({
            "timestamp": timestamp,
            "name": name,
            "content": content,
            "star_count": 0
        })

        self.write({"_id": result})
        self.finish()


application = tornado.web.Application([
    (r"/post", PostHandler),
    (r"/star", StarHandler),
    (r"/unstar", UnstarHandler),
    (r"/get", GetHandler)
])

if __name__ == "__main__":
    tornado.options.parse_command_line()
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
