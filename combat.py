"""Shared battle rules from Projectv10.pdf, pages 3-4."""

from dataclasses import dataclass
from math import isfinite

RULES_PROFILES = ("brief", "server-v3.2.1")
DEFAULT_RULES_PROFILE = "server-v3.2.1"


def win_probability(attackers, defenders, *, humans=False, rules_profile=DEFAULT_RULES_PROFILE):
    """Include guaranteed victories before applying the random-battle formula.

    The benchmark may pass positive floating-point strength estimates. Actual
    simulated battles require integer populations (see sample_battle).
    """
    if rules_profile not in RULES_PROFILES:
        raise ValueError("Unknown battle rules profile.")
    if not isfinite(attackers) or not isfinite(defenders) or attackers <= 0 or defenders <= 0:
        raise ValueError("Battle populations must be positive and finite.")
    if humans and attackers >= defenders:
        return 1.0
    if not humans:
        if 2 * attackers >= 3 * defenders:
            return 1.0
        if rules_profile == "brief" and 2 * defenders >= 3 * attackers:
            return 0.0
    if attackers <= defenders:
        return attackers / (2 * defenders)
    return attackers / defenders - 0.5


@dataclass(frozen=True)
class BattleResult:
    attacker_won: bool
    survivors: int
    probability: float


def sample_battle(attackers, defenders, rng, *, humans=False, rules_profile=DEFAULT_RULES_PROFILE):
    """Resolve a battle using the caller's random.Random-compatible generator.

    After victory, survivors follow Binomial(attackers [+ humans], P).
    After defeat, surviving defenders follow Binomial(defenders, 1-P).
    A winning side can have zero survivors. Deterministic fights consume no RNG.
    """
    if any(type(n) is not int or n <= 0 for n in (attackers, defenders)):
        raise ValueError("Simulated battle populations must be positive integers.")
    probability = win_probability(attackers, defenders, humans=humans, rules_profile=rules_profile)
    if probability == 1:
        return BattleResult(True, attackers + (defenders if humans else 0), probability)
    if probability == 0:
        return BattleResult(False, defenders, probability)
    attacker_won = rng.random() < probability
    population = attackers + (defenders if humans else 0) if attacker_won else defenders
    survival_probability = probability if attacker_won else 1 - probability
    survivors = sum(rng.random() < survival_probability for _ in range(population))
    return BattleResult(attacker_won, survivors, probability)


def expected_battle(attackers, defenders, *, humans=False, rules_profile=DEFAULT_RULES_PROFILE):
    """Deterministic stand-in for look-ahead: the likelier side wins with its mean survivors.

    Not a server rule. Use it for noise-free playouts; use sample_battle for real games.
    """
    if any(type(n) is not int or n <= 0 for n in (attackers, defenders)):
        raise ValueError("Simulated battle populations must be positive integers.")
    probability = win_probability(attackers, defenders, humans=humans, rules_profile=rules_profile)
    population = attackers + (defenders if humans else 0)
    if probability == 1:
        return BattleResult(True, population, probability)
    if probability >= 0.5:
        return BattleResult(True, round(population * probability), probability)
    return BattleResult(False, round(defenders * (1 - probability)), probability)
