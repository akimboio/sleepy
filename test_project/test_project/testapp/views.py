# Create your views here.

# Akimbo imports
from sleepy.base import Base
from sleepy.decorators import Paginate
from sleepy.responses import api_out


class ReturnSimpleListHandler(Base):
    @Paginate("id", keypath="data.stories")
    def GET(self, request, *args, **kwargs):
        return api_out({
            "stories":
            [
                {"id": "a"},
                {"id": "b"},
                {"id": "c"}
                ],
            },
            {
                "actions": {
                    "do_something": "stuff"
                    }
                }
            )

class ReturnComplexListHandler(Base):
    @Paginate("id", keypath="data.stories")
    def GET(self, request, *args, **kwargs):
        """
        Return a lot of stories to test pagination.
        """
        return api_out({
            "stories":
            [{"id": id_}
                for id_
                in range(100)
                ],
            },
            {
                "actions": {
                    "do_something": "stuff"
                    }
                }
            )
