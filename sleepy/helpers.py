from django.http import HttpResponse
from email.mime.text import MIMEText
from string import Template
import re
import json
import smtplib
import datetime


def index(request, username=None, *args, **kwargs):
    """
    a convenience function, since no methods support root access this
    is the 'index' for a 'directory' it prints an error stating that
    the root uri is not a supported resource
    """
    try:
        methods = show_urls(urls.urlpatterns)
    except:
        methods = []
    return HttpResponse(json.dumps(
            {
                'error': "Nonsupported method for resource",
                '_methods': methods
                },
            indent=2))


def show_urls(urllist, depth=0):
    for entry in urllist:
        print "  " * depth, entry.regex.pattern
        if hasattr(entry, 'url_patterns'):
            show_urls(entry.url_patterns, depth + 1)


def chunk_split(list, chunk_size):
    """
    Splits a list into N many chunks where N - 1 chunks are of size chunk_size
    and the Nth chunk is the size of the remaining elements in the list
    """
    return [
        list[
            sidx:min(sidx + chunk_size, len(list))]
        for sidx in range(0, len(list), chunk_size)]


def valid_email(email):
    """
    Checks to see if a string is a valid email
    @param email: a string to be validated
    @returns: C{bool}
    """
    email_pattern = ("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\."
                     + "([a-zA-Z]{2,6}|[0-9]{1,3})(\\]?)$")
    if re.match(email_pattern, email) != None:
        return True
    return False


def symbol_encode(
    number,
    symbols="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"):
    string = ""
    while number != 0:
        number, ii = divmod(number, len(symbols))
        string = symbols[ii] + string
    return string


def send_email(to_address,
               from_address,
               subject,
               message,
               banner=None,
               template_file=None,
               reply_to=None,
               template_dir="/srv/api-production/retickr/email_templates/",
               copyright_company="retickr",
               company_mailing_address=None):
    if company_mailing_address:
        company_mailing_address = ("attn: retickr 800 Market Street,"
                                   + " suite 200 Chattanooga, TN 37402")
    try:
        if template_file == None:
                if banner == None:
                    template = open(
                        "{0}email_template_no_banner.html".format(template_dir)
                        ).read()
                else:
                    template = open(
                        "{0}email_template_banner.html".format(template_dir)
                        ).read()
        else:
            template = open(template_file).read()
    except IOError:
        template = "$subject\n$message"

    message = Template(template).safe_substitute(subject=subject,
                          message=message,
                          copyright_company="retickr",
                          current_year=datetime.datetime.now().year,
                          company_mailing_address=company_mailing_address,
                          banner_img_url=banner
                          )

    msg = MIMEText(message, 'html')
    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = to_address

    if reply_to != None:
        msg['Reply-To'] = reply_to

    server = smtplib.SMTP('localhost')
    server.sendmail(from_address, to_address, msg.as_string())
