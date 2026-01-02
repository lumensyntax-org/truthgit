"""
TruthGit Hashing - Sistema de Content-Addressing

Similar a Git, todo objeto se identifica por el hash SHA-256 de su contenido.
Esto garantiza:
- Integridad: corrupción es detectable
- Deduplicación: mismo contenido = mismo hash
- Verificación: el hash ES la dirección
"""

import hashlib
import json
from typing import Any


def canonical_serialize(obj: dict[str, Any]) -> str:
    """
    Serializar objeto de forma canónica para hashing consistente.

    - Keys ordenadas alfabéticamente
    - Sin espacios extra
    - Unicode normalizado
    - Determinístico
    """
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def content_hash(content: str | dict[str, Any], prefix: str = "") -> str:
    """
    Calcular hash SHA-256 del contenido.

    Args:
        content: String o dict a hashear
        prefix: Prefijo opcional (e.g., "claim", "axiom")

    Returns:
        Hash hexadecimal de 64 caracteres

    Example:
        >>> content_hash({"type": "claim", "content": "Hello"})
        'a7f3b2c1d4e5f6...'
    """
    if isinstance(content, dict):
        serialized = canonical_serialize(content)
    else:
        serialized = str(content)

    if prefix:
        serialized = f"{prefix}\0{serialized}"

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def verify_hash(content: str | dict[str, Any], expected_hash: str, prefix: str = "") -> bool:
    """
    Verificar que el contenido produce el hash esperado.

    Args:
        content: Contenido a verificar
        expected_hash: Hash esperado
        prefix: Prefijo usado en el hash original

    Returns:
        True si el hash coincide
    """
    actual_hash = content_hash(content, prefix)
    return actual_hash == expected_hash


def short_hash(full_hash: str, length: int = 8) -> str:
    """
    Obtener versión corta del hash (para display).

    Example:
        >>> short_hash("a7f3b2c1d4e5f6789...")
        'a7f3b2c1'
    """
    return full_hash[:length]


def hash_to_path(hash_value: str) -> tuple[str, str]:
    """
    Convertir hash a estructura de directorio (como Git).

    Los primeros 2 caracteres son el directorio,
    el resto es el nombre del archivo.

    Example:
        >>> hash_to_path("a7f3b2c1d4e5f6789...")
        ('a7', 'f3b2c1d4e5f6789...')
    """
    return hash_value[:2], hash_value[2:]


def path_to_hash(directory: str, filename: str) -> str:
    """
    Reconstruir hash desde path.

    Example:
        >>> path_to_hash('a7', 'f3b2c1d4e5f6789...')
        'a7f3b2c1d4e5f6789...'
    """
    return directory + filename


class HashVerificationError(Exception):
    """Error cuando un hash no coincide con su contenido."""

    def __init__(self, expected: str, actual: str, object_type: str = "object"):
        self.expected = expected
        self.actual = actual
        self.object_type = object_type
        super().__init__(
            f"Hash mismatch for {object_type}: "
            f"expected {short_hash(expected)}, got {short_hash(actual)}"
        )


# === Tests ===


def _test_hashing():
    """Pruebas del sistema de hashing."""

    # Test 1: Mismo contenido = mismo hash
    content = {"type": "claim", "content": "Test claim"}
    hash1 = content_hash(content)
    hash2 = content_hash(content)
    assert hash1 == hash2, "Same content should produce same hash"

    # Test 2: Diferente contenido = diferente hash
    content2 = {"type": "claim", "content": "Different claim"}
    hash3 = content_hash(content2)
    assert hash1 != hash3, "Different content should produce different hash"

    # Test 3: Orden de keys no importa (canonical)
    content_a = {"b": 2, "a": 1}
    content_b = {"a": 1, "b": 2}
    assert content_hash(content_a) == content_hash(content_b), "Key order shouldn't matter"

    # Test 4: Verificación
    assert verify_hash(content, hash1), "Verification should pass"
    assert not verify_hash(content2, hash1), "Verification should fail for different content"

    # Test 5: Path conversion
    test_hash = "a7f3b2c1d4e5f6789abcdef"
    dir_part, file_part = hash_to_path(test_hash)
    assert dir_part == "a7"
    assert file_part == "f3b2c1d4e5f6789abcdef"
    assert path_to_hash(dir_part, file_part) == test_hash

    print("✅ All hashing tests passed")


if __name__ == "__main__":
    _test_hashing()
