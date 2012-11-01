"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

# Universe imports
import json

# Third party imports
from django.test import TestCase, Client


class SimpleTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_no_get_variable(self):
        response = self.client.get(
            "/simple_test_list")
        response = json.loads(response.content)

        expected_output = [{"id": "a"}, {"id":"b"}, {"id":"c"}]

        assert response["data"]["stories"] == expected_output, (
            "Expected: '{0}', received: '{1}'".format(
                expected_output,
                response["data"]["stories"]))

    def test_if_range_get_variable(self):
        response = self.client.get(
            "/simple_test_list",
            {"_if_range": "b"})
        response = json.loads(response.content)

        expected_output = [{"id":"a"}]

        assert response["data"]["stories"] == expected_output, (
            "Expected: '{0}', received: '{1}'".format(
                expected_output,
                response["data"]["stories"]))


    def test_if_range_header(self):
        response = self.client.get(
            "/simple_test_list",
            **{"If-Range":"b"})
        response = json.loads(response.content)

        expected_output = [{"id":"a"}]

        assert response["data"]["stories"] == expected_output, (
            "Expected: '{0}', received: '{1}'".format(
                expected_output,
                response["data"]["stories"]))


class PaginationTestWithDefaultArgs(TestCase):
    """
    Note: for the purposes of this test,
    we assume the default offset is 0 and
    the default num_stories is 25.
    """
    test_server_domain = "http://testserver"

    def setUp(self):
        self.client = Client()

    def test_older_action_with_default_args(self):
        response = self.client.get(
            "/complex_test_list")
        response = json.loads(response.content)

        # Verify expected output
        expected_output = [
            {"id": idx}
            for idx
            in range(25)]

        assert response["data"]["stories"] == expected_output, (
            "Expected: '{0}', received: '{1}'".format(
                expected_output,
                response["data"]["stories"]))

        # Verify that the older link gives the next page of data
        actions = response["actions"]

        older_api_call = actions["older"]["endpoint"]

        # Remove the parts that reference a domain
        api_path = older_api_call.replace(
            self.test_server_domain, "")

        response2 = self.client.get(
            api_path
            )
        response2 = json.loads(response2.content)

        expected_output2 = [
            {"id": idx}
            for idx
            in range(25, 50)]

        assert response2["data"]["stories"] == expected_output2, (
            "Expected: '{0}', received: '{1}'".format(
                expected_output2,
                response2["data"]["stories"]))


class PaginationTestWithOffset(TestCase):
    test_server_domain = "http://testserver"

    def setUp(self):
        response = self.client.get(
            "/complex_test_list",
            {
                "offset": 30
            })
        response = json.loads(response.content)

        # Verify expected output
        expected_output = [
            {"id": idx}
            for idx
            in range(30, 55)]

        assert response["data"]["stories"] == expected_output, (
            "Expected: '{0}', received: '{1}'".format(
                expected_output,
                response["data"]["stories"]))

        self.actions = response['actions']

    def test_older_action_with_offset(self):
        """
        """
        # Verify that the older link gives the next page of data
        older_api_call = self.actions["older"]["endpoint"]

        # Remove the parts that reference a domain
        api_path = older_api_call.replace(
            self.test_server_domain, "")

        response = self.client.get(
            api_path
            )
        response = json.loads(response.content)

        expected_output = [
            {"id": idx}
            for idx
            in range(55, 80)]

        assert response["data"]["stories"] == expected_output, (
            "Expected: '{0}', received: '{1}'".format(
                expected_output,
                response["data"]["stories"]))

    def test_newer_action_with_offset(self):
        # Verify that the older link gives the next page of data
        newer_api_call = self.actions["newer"]["endpoint"]

        # Remove the parts that reference a domain
        api_path = newer_api_call.replace(
            self.test_server_domain, "")

        response = self.client.get(
            api_path
            )
        response = json.loads(response.content)

        expected_output = [
            {"id": idx}
            for idx
            in range(5, 30)]

        assert response["data"]["stories"] == expected_output, (
            "Expected: '{0}', received: '{1}'".format(
                expected_output,
                response["data"]["stories"]))


class PaginationTestWithOffsetAndIfRange(TestCase):
    test_server_domain = "http://testserver"

    def setUp(self):
        response = self.client.get(
            "/complex_test_list",
            {
                "offset": 30,
                "_if_range": 10,
                "_get_older": True,
            })
        response = json.loads(response.content)

        # Verify expected output
        expected_output = [
            {"id": idx}
            for idx
            in range(40, 65)]

        assert response["data"]["stories"] == expected_output, (
            "Expected: '{0}', received: '{1}'".format(
                expected_output,
                response["data"]["stories"]))

        self.actions = response['actions']

    def test_older_action_with_offset_and_if_range(self):
        """
        """
        # Verify that the older link gives the next page of data
        older_api_call = self.actions["older"]["endpoint"]

        # Remove the parts that reference a domain
        api_path = older_api_call.replace(
            self.test_server_domain, "")

        response = self.client.get(
            api_path
            )
        response = json.loads(response.content)

        expected_output = [
            {"id": idx}
            for idx
            in range(65, 90)]

        assert response["data"]["stories"] == expected_output, (
            "Expected: '{0}', received: '{1}'".format(
                expected_output,
                response["data"]["stories"]))

        self.actions = response['actions']

    def test_newer_action_with_offset_and_if_range(self):
        # Verify that the older link gives the next page of data
        older_api_call = self.actions["newer"]["endpoint"]

        # Remove the parts that reference a domain
        api_path = older_api_call.replace(
            self.test_server_domain, "")

        response = self.client.get(
            api_path
            )
        response = json.loads(response.content)

        expected_output = [
            {"id": idx}
            for idx
            in range(5, 10)]

        assert response["data"]["stories"] == expected_output, (
            "Expected: '{0}', received: '{1}'".format(
                expected_output,
                response["data"]["stories"]))

        self.actions = response['actions']
