import psycopg2
import datetime
import pytz
from collections import namedtuple
from enum import Enum

"""
CREATE TABLE ack (
	id INT NOT NULL DEFAULT unique_rowid(),
	msg STRING NULL,
	inserted_at TIMESTAMP WITH TIME ZONE NULL,
	user_email STRING NULL,
	CONSTRAINT "primary" PRIMARY KEY (id ASC),
	FAMILY "primary" (id, msg, inserted_at, user_email)
)
"""

class Config:
    conn_string = "host='localhost' port=26257 dbname='peer_ack' user='root'"
    superusers = []
    weekly_meeting_day_of_week = 1  # Monday is 0
    weekly_meeting_time_of_day = datetime.time(hour=17)
    meeting_timezone = pytz.timezone('US/Eastern')
    # report_slack configures how long after the start of a meeting reports
    # will still look at the previous week.
    report_slack = datetime.timedelta(hours=2)
    # push_window configures a time window around a meeting start time; acks
    # sent during this window get pushed to the end of the window so that
    # they're included in the next week's report.
    push_window = datetime.timedelta(hours=1)
    google_client_id = "431881615412-675868jddpuivt4di8pmqnm7k2bqm2jl.apps.googleusercontent.com"

class Constants:
    datetime_fmt = '%Y-%m-%d %H:%M'
 

class Util:
    def get_db_conn():
        conn = psycopg2.connect(Config.conn_string)
        return conn

    ReportWindow = namedtuple('Report', ['start', 'end'])

    def report_from_start(start):
        return Util.ReportWindow(start, start + datetime.timedelta(days=7))

    # report returns a ReportWindow indicating the time window of the "current
    # report": i.e. the report to be presented at the next team meeting (or the
    # on-going team meeting is we're within the "slack" period since the
    # meeting started.
    #
    # now is the datetime relative to which we're asking. Pass
    # datetime.datetime.now(pytz.utc).
    def report(now, slack=True):
        # We need to look either at the meeting falling in the current week or
        # the meeting falling in the previous week, depending on whether the
        # meeting falling in the current week has passed or not.
        cur_week_meeting_dt = Util.cur_week_meeting(now)

        # adjust the timestamp according to the slack period.
        if slack:
            now = now - Config.report_slack
        # If we're below cur_week_meeting_dt, then that's the report we're
        # interested in; its start is 7 days prior. Otherwise, we're interested
        # in the report that starts at cur_week_meeting_dt.
        if now < cur_week_meeting_dt:
            res = cur_week_meeting_dt - datetime.timedelta(days=7)
        else:
            res = cur_week_meeting_dt
        return Util.report_from_start(res)

    def cur_week_meeting(now):
        # Figure out the datetime of the meeting falling in the current week.
        today = now.date()
        start_cur_week = today - datetime.timedelta(days=today.weekday())
        cur_week_meeting_date = start_cur_week + datetime.timedelta(Config.weekly_meeting_day_of_week)
        # cur_week_meeting_dt is the end of the report falling in the current week.
        return Config.meeting_timezone.localize(
                datetime.datetime.combine(
                    cur_week_meeting_date, Config.weekly_meeting_time_of_day))

    # adjust_ack_ts takes a datetime and returns the datetime that should be
    # used for recording an ack. Normally, the result is equal to the input.
    # However, if the input falls within the push window, it gets pushed.
    def adjust_ack_ts(ts):
        cur_week_meeting_dt = Util.cur_week_meeting(ts)
        push_window_start = cur_week_meeting_dt - Config.push_window
        if ts >= push_window_start and ts < cur_week_meeting_dt:
            return cur_week_meeting_dt + datetime.timedelta(minutes=1)
        return ts

    def is_superuser(email):
        return email in Config.superusers
