import urllib
from urllib.parse import urlparse
import datetime
import pytz
from http import cookies

from common import Page
from config import Config, Util

class Ack(Page):
    def cur_page_id(self):
        return "ack"

    def do_get(self, handler):
        handler.send_response(200)
        handler.send_header('Content-type','text/html')
        handler.end_headers()

        self.common_headers(handler.wfile)
        self.write(handler.wfile, "<body>")
        user_email = self.get_user_email(handler)
        self.menu_bar(handler.wfile, Util.is_superuser(user_email))

        num_acks = self.just_inserted(handler)
        if num_acks != 0:
            self.ack_butterbar(handler.wfile, num_acks)

        now = datetime.datetime.now(pytz.utc)
        adjusted = Util.adjust_ack_ts(now)
        self.report_header(
                handler.wfile,
                Util.report(adjusted, slack=False),
                generate_links=False,
                msg="Sending acks for week:",
        )

        msg = """
            <p1>How did they poke their head above the Roach's high expectations this week?
            <p>
            <form action=/ack method=post accept-charset="UTF-8">
                <fieldset id="fieldset" disabled="true">
                    One ack per line:<br><textarea name=ack rows="10" cols="80"></textarea>
                    <p>
                    Haiku (one multi-line ack):<br><textarea name=haiku rows="4" cols="80"></textarea><br>
                    <input type=submit><br>
                </fieldset>
            </form>
            </body>
        """
        self.write(handler.wfile, msg)

    def do_post(self, handler):
        userID = self.get_user_email(handler)
        if userID is None:
            raise Exception("not logged in")
        # Decode and insert the acks.
        content_len = int(handler.headers["content-length"])
        data = handler.rfile.read(content_len)
        data = urllib.parse.parse_qs(data)
        acks = []
        if b'ack' in data:
            raw_acks = data[b'ack'][0].decode("utf-8")
            acks = self.parse_acks(raw_acks)
        num_acks = len(acks)
        haiku = ""
        if b'haiku' in data:
            haiku = data[b'haiku'][0].decode("utf-8")
            num_acks += 1
        self.insert_acks(userID, acks, haiku)

        handler.send_response(303) # "See-also" code.
        self.set_inserted_cookie(handler, num_acks)
        handler.send_header('Location','/ack')
        handler.end_headers()

    def ack_butterbar(self, wfile, num_acks):
        msg = """
        <script>
            console.log("Clearing just-inserted cookie");
            document.cookie = "just-inserted=;expires=Thu, 01 Jan 1970 00:00:01 GMT;";
        </script>
        """
        msg += '<div id="wrapper"><div id="butterbar">' + str(num_acks) + ' peer ack(s) saved :thumb-up:</div></div>\n'
        self.write(wfile, msg)

    def parse_acks(self, acks):
        return [line.strip() for line in acks.splitlines() if line.strip()]

    def insert_acks(self, user, acks, haiku):
        ack_time = Util.adjust_ack_ts(datetime.datetime.now(pytz.utc))
        conn = Util.get_db_conn()
        cur = conn.cursor()
        for ack in acks:
            cur.execute(
                    "INSERT INTO ack (msg, inserted_at, user_email) VALUES (%s, %s, %s)",
                    (ack, ack_time, user))
        haiku = haiku.rstrip()
        if len(haiku) > 0:
            cur.execute(
                    "INSERT INTO ack (msg, inserted_at, user_email) VALUES (%s, %s, %s)",
                    (haiku, ack_time, user))
        conn.commit()
        cur.close()
        conn.close()

    def head(self):
        return """
        <script>
        function page_toggleSignedIn(signedIn, info) {
            document.getElementById("fieldset").disabled = !signedIn;
        }
        </script>
        """

    def set_inserted_cookie(self, handler, num_acks):
       c = cookies.SimpleCookie()
       c['just-inserted'] = num_acks
       handler.send_header('Set-Cookie',c.output(header=''))

    def just_inserted(self, handler):
        cookiestring = "\n".join(handler.headers.get_all('Cookie',failobj=[]))
        c = cookies.SimpleCookie()
        c.load(cookiestring)
        if 'just-inserted' not in c:
            return 0
        return int(c['just-inserted'].value)
