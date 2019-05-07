import datetime
import pytz
import urllib.parse
from urllib.parse import urlparse

from common import Page, Ack, DB, Auth
from config import Config, Util, Constants

class Report(Page):
    def cur_page_id(self):
        return "report"

    def do_get(self, handler):
        if Auth.get_user_email(handler) is None:
            self.render_not_logged_in(handler)
            return
        self.render_page(handler)

    def render_not_logged_in(self, handler):
        handler.send_response(200)
        handler.send_header('Content-type','text/html')
        handler.end_headers()
        self.common_headers(handler.wfile)
        self.menu_bar(handler.wfile, False)
        self.write(handler.wfile)

    def render_page(self, handler):
        handler.send_response(200)
        handler.send_header('Content-type','text/html')
        handler.end_headers()
        self.common_headers(handler.wfile)
        self.write(handler.wfile, "<body>\n")
        user_email = Auth.get_user_email(handler)
        self.menu_bar(handler.wfile)

        # If there's a report start time specified use that. Otherwise,
        # generate the report according to the current time.
        query_components = urllib.parse.parse_qs(urlparse(handler.path).query)
        if 'report_start' in query_components:
            report_start = datetime.datetime.strptime(
                    query_components['report_start'][0], Constants.datetime_fmt)
            report_start = Config.meeting_timezone.localize(report_start)
            report = Util.report_from_start(report_start)
        else:
            now = datetime.datetime.now(pytz.utc)
            report = Util.report(now)

        self.write(handler.wfile, "Report for the current week:")
        self.get_acks(handler.wfile, report)
        self.render_eng_updates(handler.wfile)
        self.write(handler.wfile, "</body></html>\n")

    def get_acks(self, wfile, report):
        conn = Util.get_db_conn()
        cur = conn.cursor()
        self.report_header(
                wfile,
                report,
                generate_links=True,
                msg="Report for week:",
        )
        cur.execute("SELECT id, msg FROM ack WHERE inserted_at>%s AND inserted_at<%s", 
                (report.start, report.end))
        raw_acks = cur.fetchall()
        acks = [Ack(id=ack[0], msg=ack[1]) for ack in raw_acks]
        # Sort acks by the first word. Assuming that many of them start with
        # the name of a person, those will sort together.
        acks = sorted(acks, key=lambda ack: ack.msg.split()[0])
        self.write(wfile,
            """
            <p>
            Acks:<br>
            {0}
            """.format(self.render_acks(acks))
        )
        cur.close()
        conn.close()

    def render_acks(self, acks):
        s = "<ol>"
        for ack in acks:
            if ack.pre:
                s += "<li><pre>{0}</pre></li>".format(ack.msg)
            else:
                s += "<li>{0}</li>".format(ack.msg)
        s += "</ol>"
        return s

    def render_eng_updates(self, wfile):
        self.write(wfile, "<p>Suggested eng updates:<br>")
        now = datetime.datetime.now(pytz.utc)
        report = Util.report(now)
        updates = DB.get_eng_updates(report, None)
        s = "<ol>"
        for upd in updates:
                s += "<li>{0}</li>".format(upd.msg)
        s += "</ol>"
        self.write(wfile, s)
