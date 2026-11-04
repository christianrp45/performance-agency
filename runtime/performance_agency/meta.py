"""Cliente mínimo da API de Marketing da Meta (Graph API), só com as operações da lista fechada.

Em modo simulação (padrão) nada é enviado: devolve a requisição que seria feita, sem o token.
"""
import hashlib
import hmac
import json
import urllib.error
import urllib.parse
import urllib.request


class MetaError(RuntimeError):
    pass


class MetaClient:
    def __init__(self, access_token: str, api_version: str = "v26.0", app_secret: str = "", dry_run: bool = True,
                 opener=None):
        if not dry_run and not access_token:
            raise MetaError("META_ACCESS_TOKEN ausente em agencia/.env.")
        self._token = access_token
        self._secret = app_secret
        self.base = f"https://graph.facebook.com/{api_version}"
        self.dry_run = dry_run
        self._open = opener or urllib.request.urlopen

    def _auth(self) -> dict:
        auth = {"access_token": self._token}
        if self._secret:  # appsecret_proof: protege o token se ele vazar
            auth["appsecret_proof"] = hmac.new(self._secret.encode(), self._token.encode(), hashlib.sha256).hexdigest()
        return auth

    def _call(self, method: str, path: str, params: dict) -> dict:
        body = {k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v)) for k, v in params.items()}
        if self.dry_run:
            return {"dry_run": True, "method": method, "url": f"{self.base}/{path}", "params": body}
        data = dict(body, **self._auth())
        if method == "GET":
            req = urllib.request.Request(f"{self.base}/{path}?{urllib.parse.urlencode(data)}")
        else:
            req = urllib.request.Request(f"{self.base}/{path}", data=urllib.parse.urlencode(data).encode(), method=method)
        try:
            with self._open(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read().decode("utf-8")).get("error", {})
            except Exception:
                err = {}
            raise MetaError(f"Meta {e.code}: {err.get('message', 'erro')} (code {err.get('code')})") from None

    # ---- leitura (não precisa de aprovação) ----
    def insights(self, ad_account_id: str, date_preset: str = "last_7d", level: str = "ad") -> dict:
        fields = "campaign_name,adset_name,ad_name,spend,impressions,reach,frequency,cpm,ctr,actions,cost_per_action_type"
        if self.dry_run:
            return {"dry_run": True, "data": []}
        return self._call("GET", f"act_{ad_account_id}/insights",
                          {"fields": fields, "date_preset": date_preset, "level": level, "limit": 200})

    def get(self, object_id: str, fields: str) -> dict:
        return self._call("GET", object_id, {"fields": fields})

    # ---- escrita (só via executor, depois do portão LICET) ----
    def create_campaign_paused(self, ad_account_id: str, name: str, objective: str = "OUTCOME_ENGAGEMENT") -> dict:
        return self._call("POST", f"act_{ad_account_id}/campaigns",
                          {"name": name, "objective": objective, "status": "PAUSED", "special_ad_categories": []})

    def create_adset(self, ad_account_id: str, campaign_id: str, name: str, page_id: str,
                     daily_budget_cents: int, targeting: dict, status: str = "PAUSED",
                     destination_type: str = "MESSAGING_INSTAGRAM_DIRECT_MESSENGER_WHATSAPP") -> dict:
        """Criado dentro de uma campanha PAUSADA, nada entrega até a campanha ser ativada."""
        return self._call("POST", f"act_{ad_account_id}/adsets", {
            "name": name, "campaign_id": campaign_id, "status": status,
            "billing_event": "IMPRESSIONS", "optimization_goal": "CONVERSATIONS",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP", "destination_type": destination_type,
            "daily_budget": int(daily_budget_cents), "promoted_object": {"page_id": page_id},
            "targeting": targeting,
        })

    def set_daily_budget(self, adset_id: str, daily_budget_cents: int) -> dict:
        return self._call("POST", adset_id, {"daily_budget": int(daily_budget_cents)})

    def set_status(self, object_id: str, status: str) -> dict:
        if status not in ("PAUSED", "ACTIVE"):
            raise MetaError("Status permitido: PAUSED ou ACTIVE (apagar não é permitido).")
        return self._call("POST", object_id, {"status": status})
