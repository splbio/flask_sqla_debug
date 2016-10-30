"""Tests for the FlaskSqlaDebug module.

Do NOT introduce any dependencies outside of the FlaskSqlaDebug module as this
will be released as a standalone module soon.
"""
import unittest

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import logging
import time
from datetime import datetime

from .. import FlaskSqlaDebug


log = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)


class MockTime(object):
    """Used to patch into FlaskSqlaDebug's time.time() calls."""

    def __init__(self, start_time=0, time_step=0):
        """Init with the start time and time step we will be using."""
        self.curr_time = start_time
        self.time_step = time_step

    def __call__(self):
        """Be a callable so we can be called like time.time().

        We bump the time returned by the time step so that our caller sees time moving
        according to time_step's value, either postive or negative.
        """
        rv = self.curr_time
        # log.debug("returning time: {}".format(rv))
        self.curr_time += self.time_step
        return rv

    def get_time(self):
        """Get the current time without adjusting it."""
        return self.curr_time


class LogCounter(object):
    """Count the number of log messages.

    Used to make sure the logging in the FlaskSqlaDebug does the correct number of logs.
    We use this as a duck-type passed in as a logger object so that we count the number
    of calls to log.debug, log.warn, log... etc.
    """

    def __init__(self, debug=False):
        """Set all the counters to zero."""
        self._reset()
        self.debug = debug

    def _reset(self):
        self.warns = 0
        self.errors = 0
        self.infos = 0
        self.debugs = 0

    def warn(self, *args, **kwargs):
        """Mock log.warn."""
        self.warns += 1
        if self.debug:
            log.warn(*args, **kwargs)

    def error(self, *args, **kwargs):
        """Mock log.error."""
        self.errors += 1
        if self.debug:
            log.error(*args, **kwargs)

    def info(self, *args, **kwargs):
        """Mock log.info."""
        self.infos += 1
        if self.debug:
            log.info(*args, **kwargs)

    def debug(self, *args, **kwargs):
        """Mock log.debug."""
        self.debugs += 1
        if self.debug:
            log.debug(*args, **kwargs)

    def total_calls(self):
        """Return total number of calls to logging mocks."""
        return self.warns + self.errors + self.infos + self.debugs


def get_app():
    """Create a flask object and set it up for testing."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)
    app.db = db
    return app


def _create_user_model(db):

    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True)
        email = db.Column(db.String(120), unique=True)

        def __init__(self, username, email):
            self.username = username
            self.email = email

        def __repr__(self):
            return '<User %r>' % self.username

    return User


class FlaskrTestCase(unittest.TestCase):
    """Tests for the FlaskSqlaDebug object."""

    def setUp(self):
        """Create our flask object and setup for tests.

        We create the FlaskSqlaDebug() object here and wire it up with a mock logger.
        """
        flask_app = get_app()
        self.log_catcher = LogCounter()
        self.app = flask_app
        flask_app.flask_sql_debug = FlaskSqlaDebug(
            app=flask_app, engine=flask_app.db.engine, config=flask_app.config, logger=self.log_catcher
        )
        self.models = dict()
        self.models["User"] = _create_user_model(flask_app.db)
        flask_app.db.create_all()
        flask_app.models = self.models
        self.client = self.app.test_client()

    """
    def tearDown(self):
        pass
        # self.db.drop_all()
    """

    def assertZero(self, val, msg=None):  # noqa: N802
        """Assert val is zero."""
        self.assertEqual(val, 0, msg=msg)

    def assertNotZero(self, val, msg=None):  # noqa: N802
        """Assert value not zero."""
        self.assertNotEqual(val, 0, msg=msg)

    def test_max_queries_log(self):
        """Make sure we get a log when the max queries happen."""
        app = self.app

        with app.test_request_context('/?name=Peter'):
            sql_max_query_count = app.flask_sql_debug.sql_max_query_count

            total_calls = self.log_catcher.total_calls()
            self.assertZero(total_calls)
            log.debug("total_calls %d", total_calls)

            user_model = app.models["User"]
            for x in range(sql_max_query_count - 1):
                user_model.query.get(x)
            total_calls = self.log_catcher.total_calls()
            log.debug("total_calls %d", total_calls)
            self.assertZero(total_calls)

            user_model.query.get(sql_max_query_count)
            total_calls = self.log_catcher.total_calls()
            log.debug("total_calls %d", total_calls)
            self.assertNotZero(total_calls)

    def test_max_queries_exception(self):
        """Make sure that when configured to do so we get an exception when exceeding max queries."""
        app = self.app

        with app.test_request_context('/?name=Peter'):
            # def max_queries():
            # app = current_app
            app.flask_sql_debug.throw_exception = True
            sql_max_query_count = app.flask_sql_debug.sql_max_query_count

            user_model = app.models["User"]
            for x in range(sql_max_query_count - 1):
                user_model.query.get(x)
            with self.assertRaises(Exception):
                log.debug("Expecting exception")
                user_model.query.get(sql_max_query_count)

    def test_max_query_time_log(self):
        """Test that we log when we hit the max queries per request."""
        start_time = time.mktime(datetime(2011, 6, 21).timetuple())
        app = self.app

        return_time = MockTime(start_time)
        app.flask_sql_debug.before_cursor_execute_time = return_time
        app.flask_sql_debug.after_cursor_execute_time = return_time

        with app.test_request_context('/?name=Peter'):
            total_calls = self.log_catcher.total_calls()
            self.assertZero(total_calls)

            max_time = 5.0
            app.flask_sql_debug.sql_max_total_query_seconds = max_time

            user_model = app.models["User"]

            # should be ok... time is frozen right now.
            user_model.query.get(0)
            self.assertZero(self.log_catcher.total_calls())

            total_queries = 0
            return_time.time_step = 1.0
            while return_time.get_time() - start_time < max_time:
                log.debug("Query number: {}".format(total_queries))
                total_queries += 1
                user_model.query.get(0)

            self.assertNotZero(self.log_catcher.total_calls())
            self.assertGreater(total_queries, 2)

    def test_max_query_time_exception(self):
        """Test that throwing an exception works for when we exceed the max query time."""
        start_time = time.mktime(datetime(2011, 6, 21).timetuple())
        app = self.app

        return_time = MockTime(start_time)
        app.flask_sql_debug.before_cursor_execute_time = return_time
        app.flask_sql_debug.after_cursor_execute_time = return_time

        with app.test_request_context('/?name=Peter'):
            app.flask_sql_debug.throw_exception = True

            total_calls = self.log_catcher.total_calls()
            self.assertZero(total_calls)

            max_time = 5.0
            app.flask_sql_debug.sql_max_total_query_seconds = max_time

            user_model = app.models["User"]

            # should be ok... time is frozen right now.
            user_model.query.get(0)
            self.assertZero(self.log_catcher.total_calls())

            total_queries = 0
            return_time.time_step = 1.0
            with self.assertRaises(Exception):
                while return_time.get_time() - start_time < max_time:
                    log.debug("Query number: {}".format(total_queries))
                    total_queries += 1
                    user_model.query.get(0)

    def test_single_query_time_log(self):
        """Test the max time for a single query, make sure we log when exceeded."""
        start_time = time.mktime(datetime(2011, 6, 21).timetuple())
        app = self.app

        return_time = MockTime(start_time)
        app.flask_sql_debug.before_cursor_execute_time = return_time
        app.flask_sql_debug.after_cursor_execute_time = return_time

        with app.test_request_context('/?name=Peter'):

            total_calls = self.log_catcher.total_calls()
            self.assertZero(total_calls)

            max_time = 5.0
            app.flask_sql_debug.sql_max_single_query_seconds = max_time

            user_model = app.models["User"]

            # should be ok... time is almost frozen right now.
            return_time.time_step = 0.01
            user_model.query.get(0)
            self.assertZero(self.log_catcher.total_calls())

            return_time.time_step = float(max_time) + 0.1
            user_model.query.get(0)
            self.assertNotZero(self.log_catcher.total_calls())

    def test_single_query_time_exception(self):
        """Test the max time for a single query, make sure we throw an exception when configured to do so."""
        start_time = time.mktime(datetime(2011, 6, 21).timetuple())
        app = self.app

        return_time = MockTime(start_time)
        app.flask_sql_debug.before_cursor_execute_time = return_time
        app.flask_sql_debug.after_cursor_execute_time = return_time

        with app.test_request_context('/?name=Peter'):
            app.flask_sql_debug.throw_exception = True

            max_time = 5.0
            app.flask_sql_debug.sql_max_single_query_seconds = max_time

            user_model = app.models["User"]

            # should be ok... time is almost frozen right now.
            return_time.time_step = 0.01
            user_model.query.get(0)
            self.assertZero(self.log_catcher.total_calls())

            return_time.time_step = float(max_time) + 0.1
            with self.assertRaises(Exception):
                user_model.query.get(0)


if __name__ == '__main__':
    unittest.main()
