from functools import wraps
import uuid

import tornado.ioloop
import tornado.web
import tornado.gen
from tornado.options import define, options

import cjson
import motor

db = motor.MotorClient().client.wish_bottle

define("port", default=8888, help="run on the given port", type=int)


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        if not self.get_cookie("user"):
            self.set_cookie("user", str(uuid.uuid4()))
        return self.get_cookie("user")


class GetHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        offset = self.get_argument("offset")
        offset = int(offset)
        cursor = db.text.find({"_id": {"$gte": offset}}).limit(20)
        self.write("{")
        times = 0
        while (yield cursor.fetch_next):
            if times > 0:
                self.write(",")
            times = times + 1
            self.write(cjson.encode(cursor.next_object()))
        self.write("}")
        self.finish()


class StarHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        id = self.get_argument("id")
        cursor = db.zan.find({"user": self.current_user, "text_id": id})
        print self.current_user
        yield cursor.fetch_next
        record = cursor.next_object()
        if record is None:
            cursor = yield db.zan.insert({
                "user": self.current_user,
                "text_id": id
            })
            self.write("successfully")
        else:
            self.set_status(405)
        self.finish()

class UnstarHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        id = self.get_argument("id")
        cursor = db.zan.find({"user": self.current_user, "text_id": id})
        yield cursor.fetch_next
        record = cursor.next_object()
        if record is None:
            self.set_status(405)
        else:
            yield db.zan.remove({"user": self.current_user, "text_id": id})
            self.write("successfully")
        self.finish()


class PostHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        data = cjson.decode(self.request.body)
        name = data["name"]
        content = data["content"]
        # get _id
        cursor = db.text.find().sort([("_id", -1)]).limit(1)
        yield cursor.fetch_next
        message = cursor.next_object()
        if message is None:
            _id = 0
        else:
            _id = message["_id"] + 1
        # insert
        result = yield db.text.insert({
            "_id": _id,
            "name": name,
            "content": content
        })

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
