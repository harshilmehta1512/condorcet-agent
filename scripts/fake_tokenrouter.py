"""Local stand-in for TokenRouter's OpenAI-compatible /chat/completions. Zero cost; for wiring tests only.
Behaviours: most models answer JSON; 'qwen-latest' answers chatty text; 'mistral-small-latest' rejects temperature
(forces the reasoning-model retry); 'deepseek-chat' is unknown (404) and must be excluded, not counted."""
import json, re, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.headers.get("Authorization") != "Bearer fake-key":
            return self._send(401, {"error": "bad key"})
        model, prompt = body["model"], body["messages"][0]["content"]
        if model == "deepseek-chat":
            return self._send(404, {"error": f"model {model} not found"})
        if model == "mistral-small-latest" and "temperature" in body:
            return self._send(400, {"error": "temperature not supported for this model"})
        seen = re.findall(r"^\[(E\d+|H\d+)\]", prompt, re.M)
        contra = re.search(r"\[(E\d+)\] C\d+ \(Contradicted", prompt)
        action = "BLOCK" if contra else ("ESCALATE" if "Not enough evidence" in prompt else "APPROVE")
        cited = [contra.group(1)] if contra else seen[:1]
        vote = json.dumps({"action": action, "cited": cited, "why": f"fake judge {model}"})
        text = f"Sure! Here is my answer:\n```json\n{vote}\n```" if model == "qwen-latest" else vote
        self._send(200, {"choices": [{"message": {"role": "assistant", "content": text}}]})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
