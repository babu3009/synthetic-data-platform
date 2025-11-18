"""Generate creative, memorable names for requests."""
import random
from typing import List

# Adjectives that describe data or generation
ADJECTIVES: List[str] = [
    "swift", "bright", "clever", "dynamic", "elegant", "flowing", "golden",
    "heroic", "infinite", "jovial", "keen", "lively", "mystic", "noble",
    "optimal", "pristine", "quantum", "radiant", "stellar", "turbo",
    "ultimate", "vivid", "wise", "xenial", "zealous", "agile", "bold",
    "cosmic", "daring", "epic", "fleet", "grand", "happy", "ideal",
    "jolly", "kind", "loyal", "magic", "neat", "omega", "proud",
    "quick", "rapid", "smart", "tidy", "unique", "vast", "warm"
]

# Nouns related to data, science, or nature
NOUNS: List[str] = [
    "atlas", "beacon", "catalyst", "dataset", "eclipse", "falcon", "galaxy",
    "horizon", "insight", "journey", "keystone", "lightning", "matrix", "nexus",
    "oracle", "phoenix", "quasar", "reactor", "spectrum", "titan",
    "universe", "vertex", "wave", "xenon", "zenith", "archive", "byte",
    "crystal", "delta", "engine", "forge", "grid", "helix", "ion",
    "jade", "kernel", "laser", "meteor", "node", "orbit", "pulse",
    "quest", "river", "spark", "stream", "torch", "unit", "vault", "wind"
]


def generate_request_alias() -> str:
    """
    Generate a creative, memorable alias for a request.
    
    Returns a combination like "swift-phoenix" or "cosmic-galaxy".
    """
    adjective = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    return f"{adjective}-{noun}"


def generate_unique_alias(existing_aliases: List[str], max_attempts: int = 10) -> str:
    """
    Generate a unique alias that doesn't exist in the provided list.
    
    Args:
        existing_aliases: List of already used aliases
        max_attempts: Maximum number of generation attempts
    
    Returns:
        A unique alias, or a UUID-suffixed alias if uniqueness cannot be achieved
    """
    for _ in range(max_attempts):
        alias = generate_request_alias()
        if alias not in existing_aliases:
            return alias
    
    # Fallback: append a random number
    import uuid
    return f"{generate_request_alias()}-{str(uuid.uuid4())[:8]}"
