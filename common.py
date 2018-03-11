from enum import Enum
from http import cookies
import datetime
import urllib

import auth
from config import Util, Constants

class Ack:
    def __init__(self, id, msg):
        self.id = id
        self.msg = msg
        # pre: True if the message is to be considered pre-formatted (i.e. it
        # contains new lines that must be preserved.
        self.pre = '\n' in msg

class EngUpdate:
    def __init__(self, id, msg):
        self.id = id
        self.msg = msg

class PAGE(Enum):
    Ack = 1
    MyAcks = 2

class Page:
    def cur_page_id(self):
        raise Exception("unimplemented cur_page_id")

    def do_get(self, handler):
        raise Exception("unimplemented GET")

    def do_post(self, handler):
        raise Exception("unimplemented POST")

    def write(self, wfile, msg):
        wfile.write(bytes(msg, "utf8"))

    def send_error(self, handler, e):
        handler.send_response(500)
        handler.send_header('Content-type','text/html')
        handler.end_headers()
        handler.wfile.write(bytes(str(e), "utf8"))

    # Pages can override head() if they use common_headers() and want custom
    # code in the <head>.
    def head(self):
        return ""

    def common_headers(self, wfile):
        hdr = """
        <head>
        <link rel="stylesheet" type="text/css" href="site.css">
        <script>
        const cur_page = '%s';
        </script>
        %s
        </head>
        """ % (self.cur_page_id(), self.head())
        self.write(wfile, hdr)

    def get_id_token(self, handler):
        cookiestring = "\n".join(handler.headers.get_all('Cookie',failobj=[]))
        c = cookies.SimpleCookie()
        c.load(cookiestring)
        if 'id-token' not in c:
            return None
        return c['id-token'].value

    def get_user_email(self, handler):
        token = self.get_id_token(handler)
        if token is None:
            return None
        try:
            email = auth.token_to_email(token)
            return email
        except Exception as e:
            print(e)
            return None

    """
    report (Util.ReportWindow):
    generate_links (bool): If set, links for the previous/next weeks will be
                           generated.
    """
    def report_header(self, wfile, report, generate_links, msg="Report for week:"):
        links = ""
        fmt = Constants.datetime_fmt
        if generate_links:
            prev = report.start - datetime.timedelta(days=7)
            next = report.end
            prev_arg = urllib.parse.urlencode({'report_start':prev.strftime(fmt)})
            next_arg = urllib.parse.urlencode({'report_start':next.strftime(fmt)})
            links = """
                &nbsp;
                <a href="?{0}">Previous week</a>
                /
                <a href="?{1}">Next week</a>
            """.format(prev_arg, next_arg)

        self.write(wfile,
            """
            <div>
            {0} {1} -> {2} {3}
            </div>
            <br>
            """.format(
                msg, report.start.strftime(fmt), report.end.strftime(fmt), links)
        )

    def menu_bar(self, wfile, superuser):
        includes = """
            <script src="auth.js"></script>
            <script src="common.js"></script>
            <script src="https://apis.google.com/js/platform.js?onload=initAuth">
            </script>
        """
        self.write(wfile, includes)

        general_report = ""
        if superuser:
            general_report = '<a href="/report" id="report_menu_btn">Report (superuser only)</a>'

        menu = """
        <div id="menu" style="height:30px">
            <div id="signed-out-menu-content">
                <div id="signin-btn"></div>
            </div>
            <div id="signed-in-menu-content">
                <div style="float:left">
                    <a href="/ack" id="ack_menu_btn">Send ACK</a>
                    <a href="/myacks" id="my_acks_menu_btn">My acks</a>
                    {0}
                </div>
                <div style="float:right">
                    <div id="user-name" style="display: inline"></div>
                    <img id="user-photo" style="display: inline" height="32" width="32">
                    <a href="#" id="signout-btn" onclick="signOut();">Sign out</a>
                </div>
            </div>
        </div>
        """.format(general_report)
        self.write(wfile, menu)

class DB:
    def get_eng_updates(report, user_email):
        conn = Util.get_db_conn()
        cur = conn.cursor()
        if user_email is None:
            cur.execute("SELECT id, msg FROM eng_updates WHERE "+
                    "inserted_at>%s AND inserted_at<%s",
                    (report.start, report.end))
        else:
            cur.execute("SELECT id, msg FROM eng_updates WHERE "+
                    "inserted_at>%s AND inserted_at<%s AND user_email=%s",
                    (report.start, report.end, user_email))
        updates_raw = cur.fetchall()
        updates = [EngUpdate(id=upd[0], msg=upd[1]) for upd in updates_raw]
        cur.close()
        conn.close()
        return updates
