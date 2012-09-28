# Create your views here.

from sleepy.base import Base
from sleepy.decorators import OnlyNewer
from sleepy.responses import api_out

class ReturnListHandler(Base):
    @OnlyNewer("id")
    def GET(self, request, *args, **kwargs):
        return api_out(
            [
                {"id": "a"},
                {"id": "b"},
                {"id": "c"}
                ],
            {
                "actions": {
                    "do_something": "stuff"
                    }
                }
            )
