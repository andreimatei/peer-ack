import datetime
import json
import pytz

from common import Auth
from config import Util

def serve(handler, verb):
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
