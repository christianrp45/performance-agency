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

    # ---- criativos e anúncios de mensagem (Messenger + Instagram + WhatsApp) ----
    def _post_file(self, path: str, field_name: str, file_path, fields: dict) -> dict:
        """Upload multipart (vídeo). Em simulação, só descreve o envio."""
        from pathlib import Path
        file_path = Path(file_path)
        if self.dry_run:
            return {"dry_run": True, "method": "POST", "url": f"{self.base}/{path}",
                    "upload": {"field": field_name, "file": file_path.name, "bytes": file_path.stat().st_size}}
        boundary = "----performance-agency-" + hashlib.sha256(file_path.name.encode()).hexdigest()[:16]
        parts = []
        for k, v in dict(fields, **self._auth()).items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field_name}"; '
                     f'filename="{file_path.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode())
        parts.append(file_path.read_bytes())
        parts.append(f"\r\n--{boundary}--\r\n".encode())
        req = urllib.request.Request(f"{self.base}/{path}", data=b"".join(parts), method="POST",
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with self._open(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read().decode("utf-8")).get("error", {})
            except Exception:
                err = {}
            raise MetaError(f"Meta {e.code}: {err.get('message', 'erro')} (code {err.get('code')})") from None

    def upload_image(self, ad_account_id: str, file_path) -> str:
        """Devolve o image_hash."""
        import base64
        from pathlib import Path
        data = Path(file_path).read_bytes()
        res = self._call("POST", f"act_{ad_account_id}/adimages", {"bytes": base64.b64encode(data).decode()})
        if self.dry_run:
            return "dryrun_hash_" + hashlib.sha256(data).hexdigest()[:12]
        images = res.get("images", {})
        first = next(iter(images.values()), {})
        if not first.get("hash"):
            raise MetaError(f"Upload de imagem sem hash: {res}")
        return first["hash"]

    def upload_video(self, ad_account_id: str, file_path, name: str) -> str:
        """Devolve o video_id."""
        res = self._post_file(f"act_{ad_account_id}/advideos", "source", file_path, {"name": name})
        if self.dry_run:
            return "dryrun_video_" + hashlib.sha256(str(file_path).encode()).hexdigest()[:12]
        if not res.get("id"):
            raise MetaError(f"Upload de vídeo sem id: {res}")
        return res["id"]

    MULTIDESTINATION_CTAS = [
        {"type": "MESSAGE_PAGE", "value": {"app_destination": "MESSENGER", "link": "https://fb.com/messenger_doc/"}},
        {"type": "WHATSAPP_MESSAGE", "value": {"app_destination": "WHATSAPP", "link": "https://api.whatsapp.com/send"}},
        {"type": "INSTAGRAM_MESSAGE", "value": {"app_destination": "INSTAGRAM_DIRECT", "link": "https://www.instagram.com"}},
    ]

    def create_message_creative(self, ad_account_id: str, page_id: str, instagram_user_id: str, name: str,
                                primary_text: str, headline: str, welcome_message: str,
                                image_hash: str = "", video_id: str = "") -> dict:
        """Criativo de anúncio que abre conversa (multidestino). Imagem: image_hash. Vídeo: video_id + capa."""
        cta = {"type": "MESSAGE_PAGE", "value": {"app_destination": "MESSENGER"}}
        if video_id:
            story = {"page_id": page_id, "instagram_user_id": instagram_user_id,
                     "video_data": {"video_id": video_id, "image_hash": image_hash, "title": headline,
                                    "message": primary_text, "page_welcome_message": welcome_message,
                                    "call_to_action": cta}}
        else:
            story = {"page_id": page_id, "instagram_user_id": instagram_user_id,
                     "link_data": {"name": headline, "message": primary_text, "image_hash": image_hash,
                                   "link": "https://fb.com/messenger_doc/", "page_welcome_message": welcome_message,
                                   "call_to_action": cta}}
        return self._call("POST", f"act_{ad_account_id}/adcreatives", {
            "name": name, "object_story_spec": story,
            "asset_feed_spec": {"optimization_type": "DOF_MESSAGING_DESTINATION",
                                "call_to_actions": self.MULTIDESTINATION_CTAS},
        })

    def create_ad(self, ad_account_id: str, adset_id: str, name: str, creative_id: str, status: str = "ACTIVE") -> dict:
        """Anúncio dentro do conjunto. Só entrega se a campanha estiver ativa."""
        return self._call("POST", f"act_{ad_account_id}/ads",
                          {"name": name, "adset_id": adset_id, "creative": {"creative_id": creative_id}, "status": status})

    def set_daily_budget(self, adset_id: str, daily_budget_cents: int) -> dict:
        return self._call("POST", adset_id, {"daily_budget": int(daily_budget_cents)})

    def set_status(self, object_id: str, status: str) -> dict:
        if status not in ("PAUSED", "ACTIVE"):
            raise MetaError("Status permitido: PAUSED ou ACTIVE (apagar não é permitido).")
        return self._call("POST", object_id, {"status": status})
