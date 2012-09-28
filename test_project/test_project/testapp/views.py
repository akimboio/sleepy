# Create your views here.

from sleepy.base import Base
from sleepy.decorators import OnlyNewer
from sleepy.responses import api_out

class ReturnListHandler(Base):
    @OnlyNewer(lambda x: x)
    def GET(self, request, *args, **kwargs):
        return api_out(["a", "b", "c"])
