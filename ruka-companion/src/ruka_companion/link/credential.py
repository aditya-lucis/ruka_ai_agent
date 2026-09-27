"""RUKA VI: Device Credential & Identity — Challenge-Response & Key Rotation.
Strictly follows RUKA-VI Chapter XIX (baris 95-185).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
from typing import Any


@dataclass
class DeviceCredential:
    """Kredensial lokal perangkat — rahasia 256-bit yang tidak pernah keluar rumah."""

    device_id: str
    owner: str
    secret: str
    generation: int = 1

    def public_fingerprint(self) -> str:
        """Sidik jari publik = SHA-256(secret) — disimpan cloud."""
        return hashlib.sha256(self.secret.encode()).hexdigest()

    def sign(self, data: str) -> str:
        """Tandatangani data dengan HMAC-SHA256(secret)."""
        return hmac.new(
            self.secret.encode(), data.encode(), hashlib.sha256
        ).hexdigest()

    def sign_challenge(self, challenge: str) -> str:
        """Tanda tangani challenge dengan verify_token = HMAC(secret, 'verify:' + device_id)."""
        vt = make_verify_token(self)
        return hmac.new(
            vt.encode(), challenge.encode(), hashlib.sha256
        ).hexdigest()


def make_verify_token(credential: DeviceCredential) -> str:
    """Token verifikasi = HMAC(secret, 'verify:' + device_id) — dibuat sisi
    LOKAL saat registrasi dan dikirim SEKALI ke cloud."""
    return credential.sign(f"verify:{credential.device_id}")


def make_rotation_proof(
    old_credential: DeviceCredential, new_fingerprint: str
) -> str:
    """Bukti rotasi: HMAC(verify_token_lama, 'rotate:' + fp_baru).
    Server hanya menyimpan verify_token = HMAC(secret, 'verify:' + device_id).
    HMAC tak bisa dibalik, maka bukti rotasi dihitung DARI verify_token oleh kedua pihak.
    """
    vt = make_verify_token(old_credential)
    return hmac.new(
        vt.encode(), f"rotate:{new_fingerprint}".encode(), hashlib.sha256
    ).hexdigest()


class DeviceRegistry:
    """Registry verifikasi perangkat di sisi cloud/server (Part XIX)."""

    def __init__(self) -> None:
        self._fingerprints: dict[str, dict[str, Any]] = {}

    def register_with_proof(
        self, credential: DeviceCredential, verify_token: str
    ) -> None:
        """Registrasi + proof-of-possession (token verifikasi khusus)."""
        if credential.device_id in self._fingerprints:
            raise ValueError(f"perangkat {credential.device_id} sudah terdaftar")
        self._fingerprints[credential.device_id] = {
            "fingerprint": credential.public_fingerprint(),
            "verify_token": verify_token,
            "owner": credential.owner,
            "revoked": False,
            "generation": credential.generation,
        }

    def verify_auth(
        self, device_id: str, challenge: str, response: str
    ) -> bool:
        """Verifikasi respons challenge-response."""
        entry = self._fingerprints.get(device_id)
        if entry is None or entry.get("revoked", False):
            return False
        expected = hmac.new(
            entry["verify_token"].encode(),
            challenge.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, response)

    verify_challenge = verify_auth

    def revoke(self, device_id: str) -> None:
        """Cabut perangkat terdaftar."""
        if device_id in self._fingerprints:
            self._fingerprints[device_id]["revoked"] = True

    def rotate(
        self,
        device_id: str,
        new_fingerprint: str,
        proof_by_old_secret: str,
    ) -> bool:
        """Rotasi kunci: new_fingerprint sah bila ditandatangani kunci LAMA."""
        entry = self._fingerprints.get(device_id)
        if entry is None or entry.get("revoked", False):
            return False
        expected = hmac.new(
            entry["verify_token"].encode(),
            f"rotate:{new_fingerprint}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, proof_by_old_secret):
            return False
        entry["fingerprint"] = new_fingerprint
        entry["generation"] = int(entry.get("generation", 1)) + 1
        return True

