import json
import urllib
from urllib.parse import urlparse
import datetime
import pytz
from http import cookies

from common import Page, EngUpdate, DB, Auth
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
        user_email = Auth.get_user_email(handler)
        self.menu_bar(handler.wfile, Util.is_superuser(user_email))

        num_acks, bounty = self.just_inserted(handler)
        if num_acks != 0:
            self.ack_butterbar(handler.wfile, '%d peer ack(s) saved :thumb-up:' % (num_acks))
        elif bounty:
            self.ack_butterbar(handler.wfile, 'bounty saved :thumb-up:')

        now = datetime.datetime.now(pytz.utc)
        adjusted = Util.adjust_ack_ts(now)
        self.report_header(
                handler.wfile,
                Util.report(adjusted, slack=False),
                generate_links=False,
                msg="Sending acks for week:",
        )

        self.generate_bounty_pane(handler.wfile)

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

                <fieldset id="fieldset-eng-updates" disabled="true">
                    Engineering updates: <img src="question-mark.png" height="16px" title="Suggest eng updates to Peter. Brag about your PR, your friend's PR, shout about a scary issue.">
                    <br><textarea name=eng-updates rows="4" cols="80"></textarea><br>
                    <input type=submit><br>
                </fieldset>
            </form>
        """
        self.write(handler.wfile, msg)

        self.write(handler.wfile, "<p>Suggested eng updates:<br>")
        userID = Auth.get_user_email(handler)
        if userID is None:
            self.write(handler.wfile, "Not logged in")
        else:
            self.write(handler.wfile, "\n<table>\n")
            now = datetime.datetime.now(pytz.utc)
            report = Util.report(now)
            eng_updates = DB.get_eng_updates(report, None)
            for update in eng_updates:
                self.render_eng_update(handler.wfile, update)
            self.write(handler.wfile, "\n</table>\n")
        self.write(handler.wfile, "\n</body></html>\n")

    def do_post(self, handler):
        userID = Auth.get_user_email(handler)
        if userID is None:
            raise Exception("not logged in")
        # Decode and insert the acks.
        content_len = int(handler.headers["content-length"])
        data = handler.rfile.read(content_len)
        data = urllib.parse.parse_qs(data)

        action = ""
        if b'action' in data:
            action = data[b'action'][0].decode("utf-8")

        num_acks = 0
        bounty = False
        if action == "add_bounty":
            bounty = self.handle_add_bounty(data, userID)
        else:
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

            if b'eng-updates' in data:
                update = data[b'eng-updates'][0].decode("utf-8")
                self.insert_eng_update(userID, update)

        handler.send_response(303) # "See-also" code.
        self.set_inserted_cookie(handler, num_acks, bounty)
        handler.send_header('Location','/ack')
        handler.end_headers()

    def generate_bounty_pane(self, wfile):
        self.write(wfile, '\n<div class="right">\n')
        self.write(wfile, """
        <p>Open bounties:
        <img src="question-mark.png" height="16px" title="Tired of your colleagues working on everything but your pet peeve? Tired of working aimlessly only to delete your code later because nobody gave you a peer ack? Add a bounty / work on a bounty for which the sheriff guarantees an ack upon delivery.">
        <br>
        """)
        self.write(wfile, "\n<table border=1>\n")
        bounties = DB.get_open_bounties()
        for b in bounties:
            self.render_bounty(wfile, b)
        self.write(wfile, "\n</table>\n")

        self.write(wfile, "<p>Closed bounties:<br>")
        self.write(wfile, "\n<table border=1>\n")
        bounties = DB.get_closed_bounties()
        for b in bounties:
            self.render_bounty(wfile, b)
        self.write(wfile, "\n</table>\n")
        form = """
        <form action=/ack method=post accept-charset="UTF-8">
        <fieldset id="fieldset-bounties" disabled="true">
            <textarea name=bounty rows="4" style="width:100%;"></textarea><br>
            <button type="submit" name="action" value="add_bounty">Add bounty</button>
        </fieldset>
        </form>
        """
        self.write(wfile, form)
        self.write(wfile, "</div>")


    def ack_butterbar(self, wfile, text):
        msg = """
        <script>
            console.log("Clearing just-inserted cookie");
            document.cookie = "just-inserted=;expires=Thu, 01 Jan 1970 00:00:01 GMT;";
        </script>
        """
        msg += '<div id="wrapper"><div id="butterbar">%s</div></div>\n' % (text)
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

    def insert_eng_update(self, user, eng_update):
        now = datetime.datetime.now(pytz.utc)
        conn = Util.get_db_conn()
        cur = conn.cursor()
        cur.execute(
                "INSERT INTO eng_updates (msg, inserted_at, user_email) VALUES (%s, %s, %s)",
                (eng_update, now, user))
        conn.commit()
        cur.close()
        conn.close()

    def head(self):
        return """
        <script>
        function page_toggleSignedIn(signedIn, info) {
            document.getElementById("fieldset").disabled = !signedIn;
            document.getElementById("fieldset-eng-updates").disabled = !signedIn;
            document.getElementById("fieldset-bounties").disabled = !signedIn;
        }
        </script>
        """

    def set_inserted_cookie(self, handler, num_acks, bounty):
        c = cookies.SimpleCookie()
        if num_acks:
            c['just-inserted'] = "acks:%d" % (num_acks)
        elif bounty:
            c['just-inserted'] = "bounty:1"
        handler.send_header('Set-Cookie',c.output(header=''))

    def just_inserted(self, handler):
        cookiestring = "\n".join(handler.headers.get_all('Cookie',failobj=[]))
        c = cookies.SimpleCookie()
        c.load(cookiestring)
        acks = 0
        bounty = False
        if 'just-inserted' in c:
            val = c['just-inserted'].value
            if val.startswith("acks:"):
                acks = int(val[5:])
            elif val.startswith("bounty:"):
                bounty = True
        return (acks, bounty)

    def render_eng_update(self, wfile, update):
        self.write(wfile, """
        <tr>
            <td><pre>%s</pre></td>
        </tr>
        """ % (update.msg))

    def render_bounty(self, wfile, bounty):
        author = bounty.author.split('@')[0]
        self.write(wfile, """
        <tr>
            <td>%s</td>
            <td>%s</td>
        </tr>
        """ % (author, bounty.msg))

    def handle_add_bounty(self, data, user):
        msg = ""
        if b'bounty' in data:
            msg = data[b'bounty'][0].decode("utf-8")
        else:
            return False

        created_ts = datetime.datetime.now(pytz.utc)
        updated_ts = created_ts
        conn = Util.get_db_conn()
        cur = conn.cursor()
        cur.execute(
                "INSERT INTO bounties (author, created, updated, msg, active) " +
                "VALUES (%s, %s, %s, %s, %s)",
                (user, created_ts, updated_ts, msg, "true"))
        conn.commit()
        cur.close()
        conn.close()
        return True

def serve_acks(handler, verb):
  user_email = Auth.get_user_email(handler)
  handler.send_response(200)
  handler.send_header('Content-type', 'application/json')
  handler.end_headers()
  now = datetime.datetime.now(pytz.utc)
  report = Util.ReportWindow(now + datetime.timedelta(days=-7), now)
  conn = Util.get_db_conn()
  cur = conn.cursor()
  cur.execute("SELECT msg FROM ack WHERE inserted_at>%s AND inserted_at<%s", (report.start, report.end))
  acks = cur.fetchall()
  handler.wfile.write(bytes(json.dumps({"acks": [ack[0] for ack in acks]}), "utf8"))
  cur.close()
  conn.close()
  return
