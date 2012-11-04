"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

# Universe imports
import json
import urlparse

# Third party imports
from django.test import TestCase, Client

from datadiff.tools import assert_equal


class PaginationTestWithDefaultArgs(TestCase):
    """
    Note: for the purposes of this test,
    we assume the default offset is 0 and
    the default num_stories is 25.
    """
    test_server_domain = "http://testserver"

    def setUp(self):
        self.client = Client()

        response = self.client.get(
            "/complex_test_list")
        response = json.loads(response.content)

        self.actions = response['data']['actions']

    def test_older_action_with_default_args(self):
        # Verify that the older link gives the next page of data
        older_api_call = self.actions["older"]["endpoint"]

        # Remove the parts that reference a domain
        parse_obj = urlparse.urlparse(older_api_call)

        actual_query_dict = dict([
            param_pair.split('=')
            for param_pair
            in parse_obj.query.split('&')])

        expected_query_dict = {
            "ref_time": "0",
            "get_older": "True",
            "offset": "25",
            "num_stories": "25",
        }

        assert_equal(
            expected_query_dict,
            actual_query_dict,
            "\n\n\tExpected: {0}, \n\n\tReceived: {1}".format(
                expected_query_dict, actual_query_dict))

    def test_newer_action_with_default_args(self):
        # Verify that the older link gives the next page of data
        newer_api_call = self.actions["newer"]["endpoint"]

        # Remove the parts that reference a domain
        parse_obj = urlparse.urlparse(newer_api_call)

        actual_query_dict = dict([
            param_pair.split('=')
            for param_pair
            in parse_obj.query.split('&')])

        expected_query_dict = {
            "ref_time": "0",
            "get_older": "False",
            "offset": "0",
            "num_stories": "25",
        }

        assert_equal(
            expected_query_dict,
            actual_query_dict,
            "\n\n\tExpected: {0}, \n\n\tReceived: {1}".format(
                expected_query_dict, actual_query_dict))


class PaginationTestWithOffset(TestCase):
    test_server_domain = "http://testserver"

    def setUp(self):
        self.client = Client()

        response = self.client.get(
            "/complex_test_list",
            {
                "offset":50
                })
        response = json.loads(response.content)

        self.actions = response['data']['actions']

    def test_older_action_with_offset(self):
        """
        """
        older_api_call = self.actions["older"]["endpoint"]

        # Remove the parts that reference a domain
        parse_obj = urlparse.urlparse(older_api_call)

        actual_query_dict = dict([
            param_pair.split('=')
            for param_pair
            in parse_obj.query.split('&')])

        expected_query_dict = {
            "ref_time": "0",
            "get_older": "True",
            "offset": "75",
            "num_stories": "25",
        }

        assert_equal(
            expected_query_dict,
            actual_query_dict,
            "\n\n\tExpected: {0}, \n\n\tReceived: {1}".format(
                expected_query_dict, actual_query_dict))

    def test_newer_action_with_offset(self):
        newer_api_call = self.actions["newer"]["endpoint"]

        # Remove the parts that reference a domain
        parse_obj = urlparse.urlparse(newer_api_call)

        actual_query_dict = dict([
            param_pair.split('=')
            for param_pair
            in parse_obj.query.split('&')])

        expected_query_dict = {
            "ref_time": "0",
            "get_older": "False",
            "offset": "25",
            "num_stories": "25",
        }

        assert_equal(
            expected_query_dict,
            actual_query_dict,
            "\n\n\tExpected: {0}, \n\n\tReceived: {1}".format(
                expected_query_dict, actual_query_dict))


class PaginationTestWithOffsetAndRefTime(TestCase):
    test_server_domain = "http://testserver"

    def setUp(self):
        self.client = Client()

        response = self.client.get(
            "/complex_test_list",
            {
                "offset":50,
                "ref_time":30,
            })
        response = json.loads(response.content)

        self.actions = response['data']['actions']

    def test_older_action_with_offset_and_if_range(self):
        """
        """
        older_api_call = self.actions["older"]["endpoint"]

        # Remove the parts that reference a domain
        parse_obj = urlparse.urlparse(older_api_call)

        actual_query_dict = dict([
            param_pair.split('=')
            for param_pair
            in parse_obj.query.split('&')])

        expected_query_dict = {
            "ref_time": "30",
            "get_older": "True",
            "offset": "75",
            "num_stories": "25",
        }

        assert_equal(
            expected_query_dict,
            actual_query_dict,
            "\n\n\tExpected: {0}, \n\n\tReceived: {1}".format(
                expected_query_dict, actual_query_dict))

    def test_newer_action_with_offset_and_if_range(self):
        newer_api_call = self.actions["newer"]["endpoint"]

        # Remove the parts that reference a domain
        parse_obj = urlparse.urlparse(newer_api_call)

        actual_query_dict = dict([
            param_pair.split('=')
            for param_pair
            in parse_obj.query.split('&')])

        expected_query_dict = {
            "ref_time": "30",
            "get_older": "False",
            "offset": "25",
            "num_stories": "25",
        }

        assert_equal(
            expected_query_dict,
            actual_query_dict,
            "\n\n\tExpected: {0}, \n\n\tReceived: {1}".format(
                expected_query_dict, actual_query_dict))
