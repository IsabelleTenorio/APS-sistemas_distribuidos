import socket
import json
import time

class AdminClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def ping(self) -> dict: return self._request("PING")
    def status(self, service_id: str | None = None) -> dict:
        cmd = f"STATUS|{service_id}" if service_id else "STATUS"
        return self._request(cmd)
    def summary(self) -> dict: return self._request("SUMMARY")
    def history(self, service_id: str, last_n: int = 20) -> dict: return self._request(f"HISTORY|{service_id}|{last_n}")
    def list_services(self) -> dict: return self._request("LIST")

    def watch(self, interval: int = 5):
        """Gerador que faz polling no servidor via UDP periodicamente."""
        while True:
            summary_resp = self.summary()
            status_resp = self.status()
            
            if summary_resp.get("ok") and status_resp.get("ok"):
                yield {
                    "type": "WATCH_UPDATE",
                    "summary": summary_resp.get("data", {}),
                    "services": status_resp.get("data", {})
                }
            time.sleep(interval)

    def close(self) -> None:
        pass # UDP connectionless, sem socket a fechar

    def _request(self, cmd: str) -> dict:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # Essencial no UDP: previne travamento se pacote se perder
            sock.settimeout(2.0) 
            msg = {"role": "admin", "cmd": cmd}
            
            try:
                sock.sendto(json.dumps(msg).encode(), (self.host, self.port))
                data, _ = sock.recvfrom(65535)
                return json.loads(data.decode("utf-8", errors="replace"))
            except socket.timeout:
                return {"ok": False, "error": "Timeout UDP: Pacote perdido ou servidor offline."}
            except Exception as e:
                return {"ok": False, "error": str(e)}