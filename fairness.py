"""
Fair Share's fairness rules: pure functions, no saving or networking.

Every finished chore earns its effort points for the person who did it, and costs everyone who was
home that day an equal share of those points. Your balance is what you earned minus your share, so
a positive balance means you have done more than your share. Time away pauses your share instead of
piling it up, and balances are re-centred on zero, so removing someone never leaves the rest of the
house owing points to nobody.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional


@dataclass
class Person:
    id: str
    name: str
    away_until: Optional[str] = None  # ISO date; away up to and including this day

    def is_away(self, day: date) -> bool:
        return bool(self.away_until) and day <= date.fromisoformat(self.away_until)


@dataclass
class Chore:
    id: str
    name: str
    effort: int  # 1 = quick ... 5 = big job


@dataclass
class Completion:
    """One finished chore. Name and effort are copied so history survives later edits."""
    chore_id: str
    chore_name: str
    effort: int
    person_id: str
    day: str
    home: List[str] = field(default_factory=list)  # who shared the cost that day


def record(people: List[Person], chore: Chore, person_id: str, day: date) -> Completion:
    """A completion for `person_id`; whoever did the chore was home, even if marked away."""
    home = [p.id for p in people if not p.is_away(day) or p.id == person_id]
    return Completion(chore.id, chore.name, chore.effort, person_id, day.isoformat(), home)


def balances(people: List[Person], completions: List[Completion]) -> Dict[str, float]:
    """Points earned minus fair share for each current person, re-centred to sum to zero."""
    bal = {p.id: 0.0 for p in people}
    if not bal:
        return {}
    for c in completions:
        if c.person_id in bal:
            bal[c.person_id] += c.effort
        sharers = [i for i in c.home if i in bal]
        for i in sharers:
            bal[i] -= c.effort / len(sharers)
    mean = sum(bal.values()) / len(bal)
    return {i: round(v - mean, 2) for i, v in bal.items()}


def plan(people: List[Person], chores: List[Chore], completions: List[Completion], day: date) -> Dict[str, Optional[str]]:
    """
    Who is up next for each chore. Chores are handed out biggest first to whoever is furthest
    behind, counting each suggestion as if it were done, so one person is not suggested for
    everything at once. Ties go to whoever did that chore least recently, then alphabetically.
    """
    home = [p for p in people if not p.is_away(day)]
    if not home:
        return {c.id: None for c in chores}
    sim = balances(people, completions)
    last_did: Dict[tuple, int] = {}
    for n, c in enumerate(completions):
        last_did[(c.chore_id, c.person_id)] = n
    result: Dict[str, Optional[str]] = {}
    for chore in sorted(chores, key=lambda c: (-c.effort, c.name.lower())):
        pick = min(home, key=lambda p: (round(sim[p.id], 2), last_did.get((chore.id, p.id), -1), p.name.lower()))
        result[chore.id] = pick.id
        for p in home:
            sim[p.id] -= chore.effort / len(home)
        sim[pick.id] += chore.effort
    return result
