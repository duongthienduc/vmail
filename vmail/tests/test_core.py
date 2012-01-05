from nose.tools import raises
from vmail.tests import test

class TestCoreSMTP(test.DaemonUnitTest):

    def test_authenticate(self):
        self.assertTrue(self.client.core.authenticate('dave@example.com', 'daisychain').get())

    def test_authenticate_fails(self):
        self.assertFalse(self.client.core.authenticate('dave@example.com', 'password').get())

    def test_blocking_host(self):
        self.assertNone(self.client.core.block_host('10.20.30.40').get())
        result = self.client.core.check_host('10.20.30.40').get()
        self.assertNotNone(result)
        (action, comment) = result
        self.assertEqual(action, 'DENY_DISCONNECT')

    @raises(Exception)
    def test_blocking_host_already_exists(self):
        self.client.core.block_host('43.52.175.8').get()

    def test_check_host(self):
        result = self.client.core.check_host('97.38.123.17').get()
        (action, comment) = result
        self.assertEqual(action, 'DENY_DISCONNECT')
        self.assertEqual(comment, 'Suspected spam source')

    def test_check_host_unknown(self):
        self.assertNone(self.client.core.check_host('1.2.3.4').get())

    def test_check_whitelist(self):
        self.assertTrue(self.client.core.check_whitelist('dumbledore@hogwarts.com').get())

    def test_check_whitelist_unknown(self):
        self.assertFalse(self.client.core.check_whitelist('snape@hogwarts.com').get())

    def test_get_usage_domain(self):
        self.assertEqual(self.client.core.get_usage('example.com').get(), 20656946)

    @raises(Exception)
    def test_get_usage_domain_unknown(self):
        # TODO: Fix this once vmaild has correct error reporting so the
        # exception type is checked etc.
        self.client.core.get_usage('higglepuddle.com').get()

    def test_get_usage_user(self):
        self.assertEqual(self.client.core.get_usage('testing.com', 'fred').get(), 81998643)

    @raises(Exception)
    def test_get_usage_user_unknown(self):
        # TODO: Fix this once vmaild has correct error reporting so the
        # exception type is checked etc.
        self.client.core.get_usage('higglepuddle.com', 'yankeedoodle').get()

    def test_get_quota_domain(self):
        self.assertEqual(self.client.core.get_quota('example.com').get(),
                         52428800)

    @raises(Exception)
    def test_get_quota_domain_unknown(self):
        # TODO: Fix this once vmaild has correct error reporting so the
        # exception type is checked etc.
        self.client.core.get_quota('higglepuddle.com').get()

    def test_last_login(self):
        self.assertTrue(self.client.core.last_login('dave@example.com', 'imap', '1.2.3.4').get())

    @raises(Exception)
    def test_last_login_unknown(self):
        self.client.core.last_login('yankeedoodle@higglepuddle.com', 'imap', '1.2.3.4').get()

    def test_last_login_mixed_case(self):
        self.assertTrue(self.client.core.last_login('Dave@Example.com', 'imap', '1.2.3.4').get())

class TestCoreManagement(test.DaemonUnitTest):

    def test_delete_forward(self):
        self.assertNone(self.client.core.delete_forward('help@example.com').get())
        try:
            self.client.core.get_forward('help@example.com').get()
        except:
            pass
        else:
            self.fail()

    def test_delete_user(self):
        self.assertNone(self.client.core.delete_user('dave@example.com').get())
        try:
            self.client.core.get_user('dave@example.com').get()
        except:
            try:
                self.client.core.get_vacation('dave@example.com').get()
            except:
                pass
            else:
                self.fail()
        else:
            self.fail()

    @raises(Exception)
    def test_delete_user_unknown(self):
        self.client.core.delete_user('yankeedoodle@higglepuddle.com').get()

    def test_get_forward(self):
        forwards = ['help@example.com']
        self.assertEqual(self.client.core.get_forward('info@example.com').get(), forwards)

    @raises(Exception)
    def test_get_forward_unknown(self):
        self.client.core.get_forward('yankeedoodle@higglepuddle.com').get()

    def test_get_forwards(self):
        forwards = {
            u'help@example.com': [u'dave@example.com'],
            u'info@example.com': [u'help@example.com'],
            u'dave@example.com': [u'webmaster@example.com'],
            u'webmaster@example.com': [u'postmaster@example.com'],
            u'postmaster@example.com': [u'dave@example.com']
        }
        self.assertEqual(self.client.core.get_forwards('example.com').get(),
                         forwards)

    @raises(Exception)
    def test_get_forwards_unknown(self):
        self.client.core.get_forwards('higglepuddle.com').get()

    def test_get_user(self):
        user = self.client.core.get_user('fred@testing.com').get()
        self.assertNotNone(user)
        self.assertTrue(user['enabled'])
        self.assertEqual(user['email'], 'fred@testing.com')

    @raises(Exception)
    def test_get_user_unknown(self):
        self.client.core.get_user('hinkypinky@testing.com').get()

    def test_get_vacation(self):
        vacation = self.client.core.get_vacation('dave@example.com').get()
        self.assertNotNone(vacation)
        self.assertEqual(vacation['email'], 'dave@example.com')

    def test_get_vacation_unicode(self):
        vacation = self.client.core.get_vacation('fred@testing.com').get()
        self.assertNotNone(vacation)
        self.assertEqual(vacation['email'], 'fred@testing.com')

    @raises(Exception)
    def test_get_vacation_missing(self):
        return self.client.core.get_vacation('fred@testing.com'
            ).addCallback(self.fail
            ).addErrback(self.assertIsInstance, Failure)

    @raises(Exception)
    def test_get_vacation_unknown(self):
        return self.client.core.get_vacation('hinkypinky@testing.com'
            ).addCallback(self.fail
            ).addErrback(self.assertIsInstance, Failure)

    def test_save_forward(self):
        source = 'sales@example.com'
        destinations = ['dave@example.com']

        def on_added_forward(source_):
            self.assertEqual(source_, source)
            return self.client.core.get_forward(source_
                ).addCallback(self.assertEqual, destinations
                ).addErrback(self.fail)

        self.client.core.save_forward(1, source, destinations).get()

    @raises(Exception)
    def test_save_forward_unknown(self):
        source = 'yankeedoodle@higglepuddle.com'
        destinations = ['help@higglepuddle.com']

        self.client.core.save_forward(5, source, destinations).get()
