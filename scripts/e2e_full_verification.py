import urllib.request
import urllib.error
import json
import sys
import os
import time

sys.path.insert(0, os.path.abspath("."))
import jwt
from backend.config import settings

BASE_URL = "http://localhost:8000"

def get_auth_token():
    payload = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "email": "lead.qa@documind.ai",
        "role": "authenticated",
        "aud": "authenticated",
        "exp": int(time.time()) + 7200
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")

TOKEN = get_auth_token()

def log(phase, message, status="INFO"):
    symbol = "✓" if status == "PASS" else ("✗" if status == "FAIL" else "ℹ")
    print(f"[{symbol}] [{phase}] {message}")

def make_req(endpoint, method="GET", data=None, headers=None, auth=True):
    url = f"{BASE_URL}{endpoint}"
    if headers is None:
        headers = {}
    
    if auth:
        headers["Authorization"] = f"Bearer {TOKEN}"
    
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
        
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            res_body = res.read().decode("utf-8")
            return res.status, json.loads(res_body) if res_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except Exception:
            return e.code, {"raw_error": err_body}
    except Exception as e:
        return 500, {"exception": str(e)}

def run_tests():
    results = {}
    print("\n" + "="*60)
    print("DOCUMIND END-TO-END VERIFICATION SUITE")
    print("="*60 + "\n")
    
    # Test 1: Health
    st, data = make_req("/api/health", auth=False)
    if st == 200 and data.get("status") == "healthy":
        log("Health Check", f"Backend healthy: {data['gemini_model']}, embeddings: {data['embedding_model']}", "PASS")
        results["health"] = True
    else:
        log("Health Check", f"Status: {st}, Body: {data}", "FAIL")
        results["health"] = False
        
    # Test 2: Auth Config
    st, data = make_req("/api/auth/config", auth=False)
    if st == 200 and "supabase_url" in data:
        log("Auth Config", f"Supabase configured: {data['supabase_url']}", "PASS")
        results["auth_config"] = True
    else:
        log("Auth Config", f"Status: {st}, Body: {data}", "FAIL")
        results["auth_config"] = False
        
    # Test 3: Document Catalog
    st, data = make_req("/api/documents")
    if st == 200 and "documents" in data:
        log("Document Catalog", f"Retrieved {len(data['documents'])} workspace documents", "PASS")
        results["documents"] = True
    else:
        log("Document Catalog", f"Status: {st}, Body: {data}", "FAIL")
        results["documents"] = False

    # Test 4: Knowledge Explorer Graph
    t0 = time.time()
    st, data = make_req("/api/explorer/graph")
    graph_time = time.time() - t0
    if st == 200 and "nodes" in data and "links" in data:
        log("Knowledge Explorer", f"Graph loaded in {graph_time:.2f}s with {len(data['nodes'])} nodes, {len(data['links'])} links", "PASS")
        results["explorer_graph"] = True
    else:
        log("Knowledge Explorer", f"Status: {st}, Body: {data}", "FAIL")
        results["explorer_graph"] = False

    # Test 5: Research Studio Source Registry
    st, data = make_req("/api/research/sources/registry")
    if st == 200 and "sources" in data and len(data["sources"]) > 0:
        log("Research Registry", f"Catalog verified: {len(data['sources'])} registered authoritative sources", "PASS")
        results["research_registry"] = True
    else:
        log("Research Registry", f"Status: {st}, Body: {data}", "FAIL")
        results["research_registry"] = False

    # Test 6: Research Studio Live Query & Persisted History
    t0 = time.time()
    st, report = make_req("/api/research/query", method="POST", data={
        "topic": "Claude 3.5 Sonnet vs Gemini 2.5 Pro benchmarks",
        "domain": "ai_ml",
        "depth": "brief"
    })
    query_time = time.time() - t0
    report_id = None
    if st == 200 and "executive_summary" in report:
        report_id = report.get("id")
        log("Research Query", f"Report generated in {query_time:.2f}s with {len(report.get('sources', []))} sources (Report ID: {report_id})", "PASS")
        results["research_query"] = True
    else:
        log("Research Query", f"Status: {st}, Body: {report}", "FAIL")
        results["research_query"] = False

    # Test 7: Research History listing and retrieval
    st, hist = make_req("/api/research/history")
    if st == 200 and "reports" in hist and len(hist["reports"]) > 0:
        log("Research History", f"Verified history persistence: {len(hist['reports'])} dossiers archived", "PASS")
        results["research_history"] = True
    else:
        log("Research History", f"Status: {st}, Body: {hist}", "FAIL")
        results["research_history"] = False

    if report_id:
        st, single_rep = make_req(f"/api/research/{report_id}")
        if st == 200 and single_rep.get("id") == report_id:
            log("Research Report Lookup", f"Direct dossier retrieval verified for ID {report_id}", "PASS")
            results["research_lookup"] = True
        else:
            log("Research Report Lookup", f"Failed retrieval for ID {report_id}: {st}", "FAIL")
            results["research_lookup"] = False

    # Test 8: Action Studio Generation and CRUD
    st, action_art = make_req("/api/action/generate", method="POST", data={
        "artifact_type": "checklist",
        "topic": "AI Safety and Benchmark Compliance Checklist",
        "context": "Ensure frontier models undergo unbiased third-party evaluation and alignment verification."
    })
    artifact_id = None
    if st == 200 and ("sections" in action_art or "tasks" in action_art or "items" in action_art):
        artifact_id = action_art.get("id")
        sections_cnt = len(action_art.get("sections", action_art.get("tasks", [])))
        log("Action Studio Generate", f"Generated deliverable '{action_art.get('title')}' with {sections_cnt} sections/tasks (Artifact ID: {artifact_id})", "PASS")
        results["action_generate"] = True
    else:
        log("Action Studio Generate", f"Status: {st}, Body: {action_art}", "FAIL")
        results["action_generate"] = False

    # Action Studio Listing
    st, art_list = make_req("/api/action/artifacts")
    if st == 200 and "artifacts" in art_list:
        log("Action Studio List", f"Retrieved {len(art_list['artifacts'])} action artifacts", "PASS")
        results["action_list"] = True
    else:
        log("Action Studio List", f"Status: {st}, Body: {art_list}", "FAIL")
        results["action_list"] = False

    # Action Studio Update & Delete
    if artifact_id:
        st, upd = make_req(f"/api/action/artifacts/{artifact_id}", method="PUT", data={
            "title": "AI Safety and Benchmark Compliance Checklist (Verified)",
            "summary": "Verified executive compliance summary."
        })
        log("Action Studio Update", f"HTTP {st} - {upd.get('message', 'Updated')}", "PASS" if st == 200 else "FAIL")
        results["action_update"] = (st == 200)

        st, d_res = make_req(f"/api/action/artifacts/{artifact_id}", method="DELETE")
        log("Action Studio Delete", f"HTTP {st} - {d_res.get('message', 'Deleted')}", "PASS" if st == 200 else "FAIL")
        results["action_delete"] = (st == 200)

    # Test 9: Live Monitor Topics & Logs
    st, topics_data = make_req("/api/monitor/topics")
    if st == 200 and "topics" in topics_data:
        log("Live Monitor Topics", f"Retrieved {len(topics_data['topics'])} surveillance topics", "PASS")
        results["monitor_topics"] = True
    else:
        log("Live Monitor Topics", f"Status: {st}, Body: {topics_data}", "FAIL")
        results["monitor_topics"] = False

    # Create temporary surveillance topic
    st, new_topic = make_req("/api/monitor/topics", method="POST", data={
        "topic": "RBI Monetary Policy Updates 2025",
        "domain": "finance_markets",
        "check_interval": "daily"
    })
    topic_id = None
    if st == 200 and "topic" in new_topic:
        topic_id = new_topic["topic"]["id"]
        log("Live Monitor Create", f"Created topic '{new_topic['topic']['topic']}' (ID: {topic_id})", "PASS")
        results["monitor_create"] = True
    else:
        log("Live Monitor Create", f"Status: {st}, Body: {new_topic}", "FAIL")
        results["monitor_create"] = False

    # Run check sweep
    st, sweep = make_req("/api/monitor/check", method="POST", data={"topic": "RBI Monetary Policy Updates 2025"})
    if st == 200 and ("change_level" in sweep or "headline" in sweep):
        log("Live Monitor Sweep", f"Surveillance sweep executed for '{sweep.get('topic')}' - Change level: {sweep.get('change_level')}", "PASS")
        results["monitor_sweep"] = True
    else:
        log("Live Monitor Sweep", f"Status: {st}, Body: {sweep}", "FAIL")
        results["monitor_sweep"] = False

    # Get monitor logs
    st, logs_data = make_req("/api/monitor/logs")
    if st == 200 and "logs" in logs_data:
        log("Live Monitor Logs", f"Retrieved {len(logs_data['logs'])} surveillance audit entries", "PASS")
        results["monitor_logs"] = True
    else:
        log("Live Monitor Logs", f"Status: {st}, Body: {logs_data}", "FAIL")
        results["monitor_logs"] = False

    # Cleanup topic
    if topic_id:
        st, del_topic = make_req(f"/api/monitor/topics/{topic_id}", method="DELETE")
        log("Live Monitor Cleanup", f"Deleted topic ID {topic_id}: HTTP {st}", "PASS" if st == 200 else "FAIL")

    # Test 10: AI Assistant Orchestrator Latency
    t0 = time.time()
    st, chat_res = make_req("/api/chat/ask", method="POST", data={
        "question": "What are the latest capabilities of frontier LLMs?",
        "history": []
    })
    chat_time = time.time() - t0
    if st == 200 and "answer" in chat_res:
        log("AI Assistant Chat", f"Answered in {chat_time:.2f}s with source type '{chat_res.get('source_type')}'. Answer length: {len(chat_res.get('answer', ''))} chars", "PASS")
        results["chat_orchestrator"] = True
    else:
        log("AI Assistant Chat", f"Status: {st}, Body: {chat_res}", "FAIL")
        results["chat_orchestrator"] = False

    print("\n" + "="*60)
    print("FINAL VERIFICATION SUMMARY:")
    all_passed = all(results.values())
    for k, v in results.items():
        print(f"  {k:22}: {'PASS' if v else 'FAIL'}")
    print(f"OVERALL STATUS: {'ALL CHECKS PASSED (100%)' if all_passed else 'SOME CHECKS FAILED'}")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_tests()
