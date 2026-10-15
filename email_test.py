"""Explicit manual-only test email. Never sends vacancy notices."""
import json, os, sys, urllib.request, urllib.error
required=("BREVO_API_KEY","EMAIL_TO","EMAIL_FROM")
missing=[x for x in required if not os.environ.get(x)]
if missing:
    raise SystemExit("Missing GitHub Actions Secrets: "+", ".join(missing))
payload={"sender":{"name":"能登屋監控測試","email":os.environ["EMAIL_FROM"]},
         "to":[{"email":os.environ["EMAIL_TO"]}],
         "subject":"【測試】能登屋監控 Email 通知連線",
         "textContent":"這是手動觸發的寄信測試，不代表能登屋有空房。正式空房通知目前尚未啟用。"}
req=urllib.request.Request("https://api.brevo.com/v3/smtp/email",
   data=json.dumps(payload).encode(),headers={"accept":"application/json","api-key":os.environ["BREVO_API_KEY"],"content-type":"application/json"},method="POST")
try:
    with urllib.request.urlopen(req,timeout=25) as response:
        print("Test email API accepted. HTTP", response.status)
except urllib.error.HTTPError as e:
    print("Test email API rejected, HTTP",e.code,"details:",e.read().decode(errors="replace")[:350])
    sys.exit(1)
