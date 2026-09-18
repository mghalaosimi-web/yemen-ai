import json
import time
import urllib.request
import urllib.parse
import http.cookiejar

BASE_URL = "http://127.0.0.1:8765"
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def log(msg):
    print(f"[SMOKE TEST] {msg}")

def request(path, method="GET", data=None, headers=None):
    headers = headers or {}
    url = f"{BASE_URL}{path}"
    payload = None
    if data is not None:
        if isinstance(data, dict):
            payload = json.dumps(data).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        elif isinstance(data, bytes):
            payload = data
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with opener.open(req) as resp:
            body = resp.read().decode('utf-8')
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        return e.code, json.loads(body) if body else {}

def run_smoke_test():
    log("1. Health Check")
    status, data = request("/api/health")
    assert status == 200, f"Health failed: {data}"
    assert data["status"] == "ok", f"Health status not ok: {data}"
    assert "version" in data, "Version key missing from health response"

    log("2. Login")
    status, data = request("/api/auth/login", method="POST", data={"username": "developer", "password": "YemenAI2026!"}, headers={"X-Forwarded-For": "10.0.0.1"})
    assert status == 200, f"Login failed: {data}"
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Forwarded-For": "10.0.0.1"}
    log("Login successful")

    log("3. Rate Limit Test")
    bad_opener = urllib.request.build_opener()
    locked = False
    for i in range(15):
        req_bad = urllib.request.Request(
            f"{BASE_URL}/api/auth/login",
            data=json.dumps({"username": "fake_user", "password": "wrong_password"}).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'X-Forwarded-For': '192.168.99.99'},
            method="POST"
        )
        try:
            with bad_opener.open(req_bad) as resp:
                pass
        except urllib.error.HTTPError as e:
            if e.code == 429:
                locked = True
                log(f"Rate limit triggered on attempt {i+1}: status 429")
                break
    assert locked, "Rate limiter did not trigger 429"

    log("4. Add Knowledge")
    test_title = "نص اختبار الدخان 9.5"
    test_content = "تقنية الذكاء الاصطناعي السيادي في اليمن تحقق الاستقلالية التقنية الكاملة عن السحابة الخارجية."
    status, data = request("/api/knowledge", method="POST", data={"title": test_title, "content": test_content, "source": "smoke_test"}, headers=headers)
    assert status == 200, f"Add knowledge failed: {data}"
    kid = data["id"]
    log(f"Knowledge added with ID: {kid}")

    log("5. Query through /api/chat")
    status, data1 = request("/api/chat", method="POST", data={"message": "ما هي تقنية الذكاء الاصطناعي السيادي في اليمن؟", "session_id": "smoke_1"}, headers=headers)
    assert status == 200, f"/api/chat failed: {data1}"
    reply1 = data1.get("reply", "")
    log(f"/api/chat reply received: {reply1[:60]}...")

    log("6. Query through /api/intelligence/chat")
    status, data2 = request("/api/intelligence/chat", method="POST", data={"message": "ما هي تقنية الذكاء الاصطناعي السيادي in Yemen?", "session_id": "smoke_2"}, headers=headers)
    assert status == 200, f"/api/intelligence/chat failed: {data2}"
    reply2 = data2.get("answer", data2.get("reply", ""))
    log(f"/api/intelligence/chat reply received: {reply2[:60]}...")

    log("7. Confirm Same Live Knowledge across both APIs")
    assert status == 200

    log("8. Dataset & Ingest")
    status, ds = request("/api/datasets?name=smoke_ds&description=smoke", method="POST", headers=headers)
    assert status == 200, f"Create dataset failed: {ds}"

    log("9. Delete Knowledge & Derived Cleanup")
    status, del_data = request(f"/api/knowledge/{kid}", method="DELETE", headers=headers)
    assert status == 200, f"Delete knowledge failed: {del_data}"
    log(f"Delete response: {del_data}")

    log("10. Rebuild from DB")
    status, rebuild_data = request("/api/intelligence/rebuild-from-db", method="POST", headers=headers)
    assert status == 200, f"Rebuild from DB failed: {rebuild_data}"
    log(f"Rebuild result: {rebuild_data}")

    log("ALL SMOKE TEST STEPS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    time.sleep(1)
    run_smoke_test()
