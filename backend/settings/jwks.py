import dataclasses as dc
import hashlib
import json
from typing import Any, Self

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def _kid_from_public_pem(public_pem: str) -> str:
    hash = hashlib.sha256(public_pem.encode('utf-8')).hexdigest()
    return hash[:16]


@dc.dataclass(frozen=True, slots=True)
class JsonWebKey:
    kid: str
    private_key: str
    public_key: str

    @classmethod
    def generate(
        cls,
        *,
        key_size: int = 2048,
        public_exponent: int = 65537,
        kid: str | None = None,
    ) -> Self:
        priv = rsa.generate_private_key(
            public_exponent=public_exponent,
            key_size=key_size,
        )

        priv_pem = priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode('utf-8')

        pub_pem = (
            priv
            .public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode('utf-8')
        )

        k = kid or _kid_from_public_pem(pub_pem)
        return cls(kid=k, private_key=priv_pem, public_key=pub_pem)

    def as_dict(self) -> dict[str, Any]:
        return {
            'kid': self.kid,
            'alg': 'RS256',
            'kty': 'RSA',
            'use': 'sig',
            'private_key_pem': self.private_key,
            'public_key_pem': self.public_key,
        }

    def dumps(self) -> str:
        return json.dumps(self.as_dict(), indent=2, sort_keys=True)

    def export(self, filename: str) -> None:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.dumps())

    @classmethod
    def from_file(cls, filename: str) -> Self:
        with open(filename, encoding='utf-8') as f:
            data = json.load(f)

        return cls(
            kid=data['kid'],
            private_key=data['private_key_pem'],
            public_key=data['public_key_pem'],
        )
