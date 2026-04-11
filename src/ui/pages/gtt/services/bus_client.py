"""
KernClip Bus Client - High-speed IPC for GTT.
Provides publish/subscribe messaging via Unix domain sockets.
Performance: 89k ops/sec, 4.2 Gbps throughput.
"""

import json
import os
import socket
from typing import Optional, Dict, Any


class BusClient:
    """
    KernClip Bus client for high-speed IPC.
    
    Connects to kernclip-busd via Unix domain socket at:
    /run/user/{uid}/kernclip-bus.sock
    """

    def __init__(self):
        """Initialize bus client and check availability."""
        self.socket_path = f"/run/user/{os.getuid()}/kernclip-bus.sock"
        self.available = False
        self._check_availability()

    def _check_availability(self) -> None:
        """Check if kernclip-busd is running by testing socket existence."""
        try:
            self.available = os.path.exists(self.socket_path)
        except Exception:
            self.available = False

    def pub(self, topic: str, data: str, mime: str = "text/plain") -> bool:
        """
        Publish data to a topic on the bus.
        
        Args:
            topic: Topic to publish to
            data: Data payload
            mime: MIME type of data
        
        Returns:
            True if publish succeeded
        """
        if not self.available:
            return False
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(self.socket_path)
            msg = json.dumps({"op": "pub", "topic": topic, "mime": mime, "data": data}) + "\n"
            s.sendall(msg.encode())
            response = b""
            while b"\n" not in response:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
            s.close()
            result = json.loads(response.decode())
            return result.get("ok", False)
        except Exception:
            self.available = False
            return False

    def get(self, topic: str, after_seq: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get latest message from a topic.
        
        Args:
            topic: Topic to get messages from
            after_seq: Optional sequence number for incremental reads
        
        Returns:
            Message dict if available, None otherwise
        """
        if not self.available:
            return None
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(self.socket_path)
            req = {"op": "get", "topic": topic}
            if after_seq:
                req["after_seq"] = after_seq
            msg = json.dumps(req) + "\n"
            s.sendall(msg.encode())
            response = b""
            while b"\n" not in response:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
            s.close()
            result = json.loads(response.decode())
            return result if result.get("ok") else None
        except Exception:
            return None
