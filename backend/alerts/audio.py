"""
Audio Alert System for Trade Signals
Plays sounds when signals arrive and when trades execute
"""
import os
from pathlib import Path


class AudioAlerts:
    def __init__(self):
        self.enabled = True
        self.sounds_dir = Path(__file__).parent.parent.parent / "frontend" / "public" / "sounds"

    def play_signal_alert(self, action: str):
        """Play alert when a new trade signal arrives"""
        if not self.enabled:
            return

        # For server-side audio (optional)
        # The main audio plays in the browser via WebSocket notification
        print(f"AUDIO ALERT: New {action} signal received!")

    def play_execution_alert(self):
        """Play alert when a trade is executed"""
        if not self.enabled:
            return

        print("AUDIO ALERT: Trade executed!")

    def play_tp_hit(self):
        """Play alert when take-profit is hit"""
        if not self.enabled:
            return

        print("AUDIO ALERT: Take profit hit! $$$")

    def play_sl_hit(self):
        """Play alert when stop-loss is triggered"""
        if not self.enabled:
            return

        print("AUDIO ALERT: Stop loss triggered!")
