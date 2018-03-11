import datetime
import pytz
import urllib
from urllib.parse import urlparse

from common import Page, Ack, DB
from config import Config, Util, Constants

class MyAcks(Page):
    def cur_page_id(self):
        return "my_acks"

    def do_get(self, handler):
        if self.get_user_email(handler) is None:
            self.render_not_logged_in(handler)
            return
        self.render_page(handler)

    def do_post(self, handler):
        if self.get_user_email(handler) is None:
            self.render_not_logged_in(handler)
            return
        content_len = int(handler.headers["content-length"])
        data = handler.rfile.read(content_len)
        data = urllib.parse.parse_qs(data)
        if b'delete-id' in data:
            del_id = data[b'delete-id'][0].decode("utf-8")
            self.delete_ack(del_id)
        if b'delete-eng-update-id' in data:
            del_id = data[b'delete-eng-update-id'][0].decode("utf-8")
            self.delete_eng_update(del_id)
        self.render_page(handler)

    def render_not_logged_in(self, handler):
        handler.send_response(200)
        handler.send_header('Content-type','text/html')
        handler.end_headers()
        self.common_headers(handler.wfile)
        self.menu_bar(handler.wfile, False)
        self.write(handler.wfile, "Please log in.")

    def render_page(self, handler):
        handler.send_response(200)
        handler.send_header('Content-type','text/html')
        handler.end_headers()
        self.common_headers(handler.wfile)
        self.write(handler.wfile, """
        <body>
        <form method=post action=/myacks accept-charset="UTF-8" id="action-form">
            <input type="hidden" name="delete-id" id="delete-id">
            <input type="hidden" name="delete-eng-update-id" id="delete-eng-update-id">
        </form>
        """)
        user_email = self.get_user_email(handler)
        self.menu_bar(handler.wfile, Util.is_superuser(user_email))

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

        now = datetime.datetime.now(pytz.utc)
        self.report_header(
                handler.wfile,
                report,
                generate_links=True,
                msg="My acks for week:",
        )
        self.get_my_acks(handler.wfile, user_email, report)
        self.write(handler.wfile, """
            <p>My suggested eng updates:<br>
            <table border="1">
        """)
        self.render_my_eng_updates(handler.wfile, user_email, report)


    def get_my_acks(self, wfile, email, report):
        conn = Util.get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, msg FROM ack WHERE user_email=%s "+
                "AND inserted_at>%s AND inserted_at<%s",
                (email, report.start, report.end))
        acks = cur.fetchall()
        self.write(wfile, '<table border="1">')
        for ack in acks:
            self.render_ack(wfile, Ack(ack[0], ack[1]))
        self.write(wfile, "</table>")
        cur.close()
        conn.close()

    def render_ack(self, wfile, ack):
        self.write(wfile, """
        <tr>
            <td><pre>%s</pre></td>
            <td>
                <button type="button" onclick="delete_ack('%s')" style="cursor:pointer">
                    <img src="/del.png" width="24">
                </button>
            </td>
        </tr>
        """ % (ack.msg, ack.id))

    def delete_eng_update(self, update_id):
        conn = Util.get_db_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM eng_updates WHERE id=%s", (update_id,))
        conn.commit()
        cur.close()
        conn.close()

    def delete_ack(self, ack_id):
        conn = Util.get_db_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM ack WHERE id=%s", (ack_id,))
        conn.commit()
        cur.close()
        conn.close()

    def head(self):
        return """
        <script>

        var initialSignInCalled = false;

        function page_toggleSignedIn(signedIn) {
            if (initialSignInCalled) {
                location.reload();
            }
            initialSignInCalled = true;
        }

        function delete_ack(id) {
            document.getElementById("delete-id").value = id;
            var form = document.getElementById("action-form");
            form.submit();
        }

        function delete_eng_update(id) {
            document.getElementById("delete-eng-update-id").value = id;
            var form = document.getElementById("action-form");
            form.submit();
        }
        </script>
        """

    def render_my_eng_updates(self, wfile, email, report):
        updates = DB.get_eng_updates(report, email)
        for upd in updates:
            self.write(wfile, """
            <tr>
                <td><pre>%s</pre></td>
                <td>
                    <button type="button" onclick="delete_eng_update('%s')" style="cursor:pointer">
                        <img src="/del.png" width="24">
                    </button>
                </td>
            </tr>
            """ % (upd.msg, upd.id))
