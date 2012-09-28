"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase, Client

class SimpleTest(TestCase):
    def setUp(self):
        self.client = Client()

    def no_get_variable_test(self):
        response = self.client.get("/test_list")
        response = json.loads(response.content)
        assert response["data"] == ["a", "b", "c"], response["data"]

    def if_range_get_variable_test(self):
        response = self.client.get("/test_list", {"_if_range": "b"})
        response = json.loads(response.conten)
        assert response["data"] == ["a"], response["data"]

    def if_range_header_test(self):
        response = self.client.get("/test_list", If_Range="b")
        response = json.loads(response.conten)
        assert response["data"] == ["a"], response["data"]


        
