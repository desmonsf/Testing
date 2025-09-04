# =====================================
# app/scheduler.py
# =====================================
from datetime import datetime, time
import pytz
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class SleepScheduler:
    def __init__(self):
        self.timezone = pytz.timezone('Europe/Paris')
        self.sleep_start = time(0, 0)   # Minuit
        self.sleep_end = time(8, 0)     # 8h du matin
        
    def is_sleep_time(self) -> bool:
        """Vérifie si c'est l'heure de veille (00h-8h)"""
        now = datetime.now(self.timezone).time()
        return self.sleep_start <= now < self.sleep_end
    
    def is_wake_up_time(self) -> bool:
        """Vérifie si c'est l'heure de réveil (8h)"""
        now = datetime.now(self.timezone).time()
        return now.hour == 8 and now.minute < 5  # 5 min de marge
    
    def check_availability(self):
        """Middleware pour vérifier si le service est disponible"""
        if self.is_sleep_time():
            logger.info("Service en veille nocturne (00h-8h)")
            raise HTTPException(
                status_code=503, 
                detail="Service en pause nocturne. Actif de 8h à minuit."
            )
    
    def get_wake_up_message(self) -> str:
        """Message quand le bot se réveille"""
        return """☀️ **Bonjour !** 

Je suis de retour pour t'aider avec tes factures !
Période d'activité : 8h - 00h

Que puis-je faire pour toi aujourd'hui ? 💪"""
    
    def get_sleep_message(self) -> str:
        """Message automatique pendant la veille"""
        return """🌙 **Bonne nuit !**

Je suis en pause jusqu'à 8h demain matin.

En attendant, tu peux :
• Préparer tes factures à envoyer
• Noter tes questions pour demain
• Te reposer aussi ! 😴

À demain ! 👋"""
