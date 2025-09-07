# =====================================
# app/whatsapp.py
# =====================================
import os
import requests
from typing import Optional
import logging
import json
import hashlib  # LOG: empreinte du token

logger = logging.getLogger(__name__)

class WhatsAppHandler:
    def __init__(self):
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.business_account_id = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
        
        # NOTE: on ne change pas ta version (v18.0), on la LOG uniquement
        self.base_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}"
        
        if not all([self.access_token, self.phone_number_id]):
            logger.warning("Configuration WhatsApp Cloud API incomplète")
        else:
            # ==== LOGS D'INITIALISATION UTILES ====
            token_preview = self.access_token or ""
            fp = hashlib.sha256(token_preview.encode()).hexdigest()[:10]
            has_ws = (token_preview != token_preview.strip())
            logger.warning(  # WARNING pour être sûr que ça s'affiche
                "[WA:init] base_url=%s | phone_number_id=%s | token_len=%d | token_fp=%s | token_prefix=%s | token_has_ws_edges=%s",
                self.base_url, self.phone_number_id, len(token_preview), fp, token_preview[:3], has_ws
            )
            if has_ws or token_preview.endswith("\n"):
                logger.warning("[WA:init] Le token semble contenir des espaces/retours de ligne en bordure")

            if "v18.0" in self.base_url:
                logger.warning("[WA:init] API version détectée: v18.0 (info)")

    async def send_message(self, to: str, message: str) -> bool:
        """Envoie un message WhatsApp via Cloud API"""
        if not self.access_token:
            logger.error("Token WhatsApp non configuré")
            return False
        
        clean_to = to.replace("whatsapp:", "").replace("+", "")
            
        url = f"{self.base_url}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messaging_product": "whatsapp",
            "to": clean_to,
            "type": "text",
            "text": {"body": message}
        }
        
        # ==== LOG AVANT APPEL ====
        try:
            payload_txt = json.dumps(data, ensure_ascii=False)
        except Exception:
            payload_txt = "<payload non sérialisable>"
        logger.warning("[WA:send] POST %s | to_raw=%s | to_clean=%s | payload=%s", url, to, clean_to, payload_txt)

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)

            # ==== LOG APRÈS APPEL (toujours) ====
            try:
                body_text = response.text
            except Exception:
                body_text = "<no-text>"
            logger.warning("[WA:send] status=%s | ok=%s", response.status_code, response.ok)
            logger.warning("[WA:send] response_body=%s", body_text)

            # Si erreur HTTP, on log déjà le corps exact, puis on raise pour conserver le comportement actuel
            response.raise_for_status()
            
            result = response.json()
            logger.info("Message envoyé - ID: %s", result.get('messages', [{}])[0].get('id', 'unknown'))
            return True
            
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", "unknown")
            text = getattr(e.response, "text", str(e))
            logger.error("[WA:send] HTTPError status=%s body=%s", status, text)
            return False
        except Exception as e:
            logger.error("Erreur envoi WhatsApp (Exception): %s", str(e))
            return False
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Vérifie le webhook WhatsApp lors de la configuration"""
        if mode == "subscribe" and token == self.verify_token:
            logger.info("Webhook WhatsApp vérifié avec succès")
            return challenge
        else:
            logger.warning("Échec vérification webhook WhatsApp")
            return None
    
    def parse_webhook_message(self, webhook_data: dict) -> Optional[dict]:
        """Parse les données du webhook WhatsApp"""
        try:
            # LOG pour distinguer 'messages' vs 'statuses'
            try:
                logger.warning("[WA:webhook] keys=%s", list(webhook_data.keys()))
            except Exception:
                pass

            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            
            messages = value.get("messages")
            if not messages:
                logger.warning("[WA:webhook] pas de 'messages' (probablement un status). value_keys=%s", list(value.keys()))
                return None
                
            message = messages[0]
            
            parsed_data = {
                "message_id": message.get("id"),
                "from": message.get("from"),
                "timestamp": message.get("timestamp"),
                "type": message.get("type"),
                "body": "",
                "media_url": None
            }
            
            if message.get("type") == "text":
                parsed_data["body"] = message.get("text", {}).get("body", "")
            elif message.get("type") == "image":
                parsed_data["media_url"] = message.get("image", {}).get("id")
                parsed_data["body"] = message.get("image", {}).get("caption", "")

            logger.warning("[WA:webhook] parsed from=%s type=%s body_len=%d", parsed_data["from"], parsed_data["type"], len(parsed_data["body"] or ""))

            return parsed_data
            
        except Exception as e:
            logger.error("Erreur parsing webhook: %s", str(e))
            return None
