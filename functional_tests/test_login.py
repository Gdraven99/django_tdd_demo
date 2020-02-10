import os
import poplib
import re
import time
from django.core import mail
from selenium.webdriver.common.keys import Keys
import re

from .base import FunctionalTest

SUBJECT = 'Your login link for NotJoshinYa.com lists'


class LoginTest(FunctionalTest):

    def test_can_get_email_link_to_log_in(self):
        # user browses to notjoshinya.com and notices
        # a login section in the navbar of the site
        # its telling them to enter an email address so they do
        if self.staging_server:
            test_email = 'davidjyopp@gmail.com'
        else:
            test_email = 'example@gmail.com'

        self.browser.get(self.live_server_url)
        self.browser.find_element_by_name('email').send_keys(test_email)
        self.browser.find_element_by_name('email').send_keys(Keys.ENTER)

        # a message appears telling the user that an email has been Sent
        self.wait_for(lambda: self.assertIn(
            'Check your email',
            self.browser.find_element_by_tag_name('body').text
        ))

        # user checks their email and finds a message
        body = self.wait_for_email(test_email, SUBJECT)

        # there is a url link in the Email
        self.assertIn('Use this link to log in', body)
        url_search = re.search(r'http://.+/.+$', body)
        if not url_search:
            self.fail(f'Could not find url in email body:\n{body}')
        url = url_search.group(0)
        self.assertIn(self.live_server_url, url)

        #user clicks the provided link
        self.browser.get(url)

        # user is successfully logged in!
        self.wait_to_be_logged_in(email=test_email)

        #User Logs out
        self.browser.find_element_by_link_text('Log out').click()

        #user is logged out
        self.wait_to_be_logged_out(email=test_email)


    def wait_for_email(self, test_email, subject):
        if not self.staging_server:
            email = mail.outbox[0]
            self.assertIn(test_email, email.to)
            self.assertEqual(email.subject, subject)
            return email.body

        email_id = None
        start = time.time()
        inbox = poplib.POP3_SSL('pop.gmail.com')
        try:
            inbox.user('recent:' + test_email)
            inbox.pass_(os.environ['EMAIL_PASSWORD'])
            while time.time() - start < 60:
                # get latest 10 messages
                count, _ = inbox.stat()
                for i in reversed(range(max(1, count - 10), count + 1)):
                    print('getting msg', i)
                    _, lines, __ = inbox.retr(i)
                    lines = [l.decode('utf8') for l in lines]

                    if f'Subject: {subject}' in lines:

                        email_id = i
                        body = '\n'.join(lines)
                        return body
                time.sleep(5)
        finally:
            if email_id:
                inbox.dele(email_id)
            inbox.quit()
