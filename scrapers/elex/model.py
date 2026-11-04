"""The normalized result model. Every source converts its feed into these types; nothing above a source sees a
raw feed. Field meanings are documented in docs/election-results-scraper-plan.md ("The normalized result model").
"""
from dataclasses import asdict, dataclass, field

# Source statuses. Only OK and NOT_MODIFIED carry fresh contests; the others keep the previous ones current.
OK = "ok"
NOT_MODIFIED = "not_modified"
NOT_PUBLISHED = "not_published"
BLOCKED = "blocked"
ERROR = "error"
SKIPPED = "skipped"  # --watch only: the source's min_interval hasn't passed
HEALTHY = {OK, NOT_MODIFIED, NOT_PUBLISHED, SKIPPED}


@dataclass
class Choice:
    name: str
    votes: int = 0
    party: str | None = None
    pct: float | None = None
    choice_id: str | None = None
    party_lines: dict | None = None

    def __post_init__(self):
        if self.choice_id is None:
            self.choice_id = self.name


@dataclass
class Reporting:
    units_reporting: int | None = None
    units_total: int | None = None
    pct: float | None = None
    text: str | None = None
    as_percent: bool = True         # False when units aren't a share of the count (counties that posted anything)

    def __post_init__(self):
        if not self.as_percent:
            self.pct = None
        elif self.pct is None and self.units_total:
            self.pct = round(100 * (self.units_reporting or 0) / self.units_total, 1)


@dataclass
class Contest:
    source: str
    contest_id: str
    state: str                      # two-letter code
    title: str
    office_type: str                # see names.office_type
    district: str | None = None     # district number, or the measure number/letter for measures
    jurisdiction: str | None = None
    scope: str = "complete"         # "partial" when the source reports only one county's share
    vote_for: int = 1
    final: bool = False
    reporting: Reporting = field(default_factory=Reporting)
    feed_updated_at: str | None = None
    choices: list[Choice] = field(default_factory=list)
    url: str | None = None          # a page for this contest's election, when better than the source's url
    uncontested: bool = False       # one candidate on the ballot; sources often post no count for these

    @property
    def total_votes(self) -> int:
        return sum(c.votes for c in self.choices)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Contest":
        d = dict(d)
        d["reporting"] = Reporting(**d.get("reporting") or {})
        d["choices"] = [Choice(**c) for c in d.get("choices", [])]
        return cls(**d)

    def fill_percentages(self):
        """Compute choice percentages from votes when the feed doesn't give them."""
        total = self.total_votes
        for c in self.choices:
            if c.pct is None:
                c.pct = round(100 * c.votes / total, 2) if total else 0.0


@dataclass
class SourceResult:
    source: str
    status: str
    contests: list[Contest] = field(default_factory=list)
    message: str = ""
    fetched_at: str | None = None
    seconds: float = 0.0
    requests: list[dict] = field(default_factory=list)
    changed: bool = False
