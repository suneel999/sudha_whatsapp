import os
import requests

t = os.environ["WA_TEST_TOKEN"].strip()
h = {"Authorization": f"Bearer {t}"}
r = requests.get(
    "https://graph.facebook.com/v21.0/debug_token",
    params={"input_token": t, "access_token": t},
    timeout=30,
)
print(r.status_code)
print(r.text[:2000])
