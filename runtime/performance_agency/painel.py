"""Painel local da Performance Agency.

    python -m performance_agency.painel "<pasta do cliente>" [--porta 8780] [--demo]

Abre um painel em http://127.0.0.1:<porta> para acompanhar a campanha, ler o impacto de cada proposta,
confirmar/autorizar com nome, executar, gerar relatório e ver o histórico.

Segurança: escuta só em 127.0.0.1; toda ação exige o cabeçalho X-Painel-Token (gerado a cada execução e
entregue só à página), o que impede outros sites de acionarem o painel; nenhum segredo (.env) é lido pela tela.
--demo trabalha numa cópia temporária com IDs fictícios e sempre em simulação.
"""
import argparse
import csv
import json
import secrets
import shutil
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config, executor, proposals, report

STATIC = Path(__file__).with_name("painel.html")
SAFE_CONFIG = ("name", "ad_account_id", "page_id", "instagram_user_id", "currency", "dry_run", "spend_approval",
               "limits", "min_trust_level", "require_ledger_integrity")


def make_demo(folder: Path) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="painel-demo-"))
    (tmp / "agencia").mkdir()
    data = json.loads((folder / "agencia" / "config.json").read_text(encoding="utf-8"))
    data.update(ad_account_id="000000", page_id="000000", instagram_user_id="000000", dry_run=True,
                name=f"{data.get('name', 'Cliente')} (DEMONSTRAÇÃO)")
    (tmp / "agencia" / "config.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    for spec in (folder / "agencia").glob("*.json"):
        if spec.name != "config.json":
            shutil.copy2(spec, tmp / "agencia" / spec.name)
    for sub in ("criativos", "dados"):
        if (folder / sub).exists():
            shutil.copytree(folder / sub, tmp / sub)
    return tmp


def planilha_resumo(folder: Path) -> dict:
    path = folder / "dados" / "planilha-conversas.csv"
    etapas, valor = {}, 0.0
    if path.exists():
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                e = (row.get("etapa") or "sem etapa").strip().lower()
                etapas[e] = etapas.get(e, 0) + 1
                if e == "venda":
                    try:
                        valor += float((row.get("valor") or "0").replace(",", ""))
                    except ValueError:
                        pass
    total = sum(etapas.values())
    return {"existe": path.exists(), "conversas": total, "etapas": etapas, "vendas": etapas.get("venda", 0),
            "faturamento": valor}


def audit_tail(cfg, n=60) -> list:
    if not cfg.audit_log.exists():
        return []
    lines = cfg.audit_log.read_text(encoding="utf-8").splitlines()[-n:]
    out = []
    for line in reversed(lines):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        d.pop("result", None)  # resposta bruta da API não vai para a tela
        out.append(d)
    return out


def latest_report(folder: Path) -> dict:
    files = sorted((folder / "relatorios").glob("*.md")) if (folder / "relatorios").exists() else []
    if not files:
        return {}
    return {"nome": files[-1].name, "texto": files[-1].read_text(encoding="utf-8")}


def state(folder: Path) -> dict:
    cfg = config.load(folder)
    cfg_view = {k: getattr(cfg, k) for k in SAFE_CONFIG}
    props = []
    for p in proposals.list_all(cfg):
        props.append({"id": p.id, "status": p.status, "risk": p.risk, "impact": p.impact, "summary": p.summary,
                      "reason": p.reason, "rollback": p.rollback, "created_at": p.created_at, "expires_at": p.expires_at,
                      "approval": {k: v for k, v in p.approval.items() if k in ("method", "by", "confirmed_at",
                                                                                 "verified_at", "ledger_id", "trust_level")},
                      "executed": bool(p.execution), "dry_run_last": p.execution.get("dry_run") if p.execution else None,
                      "licet": {"action": p.licet_action(), "agent_id": cfg.agent_id, "target": p.licet_target(cfg)}})
    specs = sorted(s.name for s in cfg.agency_dir.glob("*.json") if s.name != "config.json")
    return {"config": cfg_view, "proposals": list(reversed(props)), "audit": audit_tail(cfg),
            "planilha": planilha_resumo(folder), "relatorio": latest_report(folder), "specs": specs,
            "missing": [k for k in ("ad_account_id", "page_id", "instagram_user_id") if not getattr(cfg, k)],
            "agora": time.time()}


def make_handler(folder: Path, token: str, demo: bool, port: int = 8780):
    page = STATIC.read_text(encoding="utf-8").replace("__TOKEN__", token).replace("__DEMO__", "true" if demo else "false")

    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _host_ok(self):  # bloqueia DNS rebinding: só aceita o próprio endereço local
            return self.headers.get("Host", "") in allowed_hosts

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False))

        def do_GET(self):
            if not self._host_ok():
                return self._json(403, {"erro": "host não permitido"})
            if self.path in ("/", "/index.html"):
                return self._send(200, page, "text/html; charset=utf-8")
            if self.path == "/api/estado":
                if self.headers.get("X-Painel-Token") != token:
                    return self._json(403, {"erro": "token inválido"})
                try:
                    return self._json(200, state(folder))
                except Exception as e:
                    return self._json(500, {"erro": f"{type(e).__name__}: {e}"})
            return self._json(404, {"erro": "não encontrado"})

        def do_POST(self):
            if not self._host_ok():
                return self._json(403, {"erro": "host não permitido"})
            if self.headers.get("X-Painel-Token") != token or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self._json(403, {"erro": "requisição recusada"})
            try:
                body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 65536)) or b"{}")
            except ValueError:
                return self._json(400, {"erro": "JSON inválido"})
            cfg = config.load(folder)
            try:
                if self.path == "/api/confirmar":
                    p = executor.confirm(cfg, body["id"], body.get("frase", ""), body.get("nome", ""))
                    return self._json(200, {"ok": True, "msg": f"{p.id} autorizada por {p.approval.get('by')}."})
                if self.path == "/api/executar":
                    p, _ = executor.execute(cfg, body["id"])
                    sim = p.execution.get("dry_run")
                    return self._json(200, {"ok": True, "msg": f"{p.id}: {'simulado (nada enviado à Meta)' if sim else 'executado na Meta'}."})
                if self.path == "/api/relatorio":
                    meta = None if cfg.dry_run else executor.client_for(cfg)
                    path = report.write(cfg, meta)
                    return self._json(200, {"ok": True, "msg": f"Relatório gravado: {path.name}"})
                if self.path == "/api/propor":
                    name = Path(body.get("spec", "")).name
                    spec_path = cfg.agency_dir / name
                    if not name.endswith(".json") or name == "config.json" or not spec_path.exists():
                        return self._json(400, {"erro": "plano não encontrado"})
                    spec = json.loads(spec_path.read_text(encoding="utf-8"))
                    op = "meta.ads.create" if "object_id" in spec["params"] and "ads" in spec["params"] else "meta.launch.create_paused"
                    p = proposals.create(cfg, op, spec["params"], spec["summary"], spec["reason"], spec.get("rollback", ""))
                    return self._json(200, {"ok": True, "msg": f"Proposta {p.id} criada."})
                return self._json(404, {"erro": "não encontrado"})
            except (proposals.PolicyError, executor.ExecutionRefused, KeyError, FileNotFoundError, ValueError) as e:
                return self._json(422, {"ok": False, "erro": str(e)})
            except Exception as e:  # erro inesperado (ex.: Meta) — mostra sem derrubar o painel
                return self._json(500, {"ok": False, "erro": f"{type(e).__name__}: {e}"})

    return Handler


def main(argv=None):
    ap = argparse.ArgumentParser(description="Painel local da Performance Agency")
    ap.add_argument("pasta")
    ap.add_argument("--porta", type=int, default=8780)
    ap.add_argument("--demo", action="store_true", help="cópia temporária com IDs fictícios, sempre em simulação")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    folder = Path(a.pasta)
    if a.demo:
        folder = make_demo(folder)
        print(f"Demonstração em {folder}")
    config.load(folder)  # falha cedo se não houver config
    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", a.porta), make_handler(folder, token, a.demo, a.porta))
    print(f"Painel em http://127.0.0.1:{a.porta}  (Ctrl+C para fechar)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
