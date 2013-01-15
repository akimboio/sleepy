# Universe imports

# Akimbo imports
from sleepy.base import Base
from sleepy.responses import api_out


class ReturnComplexListHandler(Base):
    def GET(self, request, *args, **kwargs):
        """
        Return a lot of stories to test pagination.
        """
        return api_out(
            {
                "stories":
                [
                    {
                        "id": id_,
                        "update_time": str(id_)
                    }
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


class CORSTest(Base):
    def GET(self, request, *args, **kwargs):
        return api_out({ "does it work?": "yes" })
