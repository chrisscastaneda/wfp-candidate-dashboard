"""Results Caster (<county>.resultscaster.com), a JavaScript app over a JSON API. Erie County uses it, and the plan
lists Onondaga as another. Calls, in order:

  api/resultscasts/current                      -> elections: {slug, title, electionDate: {year, month, day}}
  api/resultscasts/<slug>/shell                 -> groups ("Election Day", "Early Voting", "Absentee") and
                                                   contests: {contestAltTallyKey, title, area, voteFor, choices:
                                                   [{choiceAltTallyKey, name, affiliations: [{altAffiliationKey,
                                                   abbreviation}]}]}
  api/resultscasts/<slug>/results/<group>       -> per contest: progress/progressTotal (districts reported) and votes
                                                   per choice and per party line

A contest's votes are the sum of its groups. Candidates on several lines ("DEM", "WOR") are one choice with
per-line votes in `party_lines`. Election slugs are made up per election (Erie's Nov 3 one is "testgen"), so the
source finds the election by date.
"""
from urllib.parse import quote

from .. import config, names
from ..model import Choice, Contest, Reporting
from ..source import NotPublished, Source

# Results Caster's line abbreviations, mapped to the codes the rest of the package uses.
_PARTY = {"WOR": "WFP", "NON": None}


def find_election(listing: dict) -> str:
    wanted = config.ELECTION_DATE
    found = [i for i in listing.get("Items") or []
             if (i["electionDate"].get("year"), i["electionDate"].get("month"), i["electionDate"].get("day"))
             == (wanted.year, wanted.month, wanted.day)]
    if not found:
        raise NotPublished(f"no {wanted} election listed")
    # Prefer one not titled as a test, in case the county posts a replacement.
    found.sort(key=lambda i: "test" in (i.get("title") or "").lower())
    return found[0]["slug"]


def parse(shell: dict, results: dict[str, dict], *, source_id: str, state: str, county: str,
          updated: str | None = None) -> list[Contest]:
    """`results` maps each group ("Election Day", ...) to its results payload."""
    tallies: dict[str, dict] = {}   # contest key -> {"choices": {choice key: [votes, {line key: votes}]}, ...}
    for group, payload in results.items():
        for item in (payload.get("election") or {}).get("contests") or []:
            tally = tallies.setdefault(item["key"], {"choices": {}, "progress": None, "total": None})
            if group == "Election Day" or tally["total"] is None:
                tally["progress"], tally["total"] = item.get("progress"), item.get("progressTotal")
            for choice in item.get("choices") or []:
                votes, lines = tally["choices"].setdefault(choice["key"], [0, {}])
                tally["choices"][choice["key"]][0] = votes + (choice.get("votes") or 0)
                for line in choice.get("affiliations") or []:
                    lines[line["key"]] = lines.get(line["key"], 0) + (line.get("votes") or 0)
    contests = []
    for item in shell.get("contests") or []:
        title = (item.get("title") or "").strip()
        tally = tallies.get(item["contestAltTallyKey"], {"choices": {}, "progress": None, "total": None})
        choices = []
        for choice in item.get("choices") or []:
            if choice.get("isWriteIn") or choice["name"].lower() == "write-in":
                continue
            votes, by_line = tally["choices"].get(choice["choiceAltTallyKey"], [0, {}])
            lines = {}
            for line in choice.get("affiliations") or []:
                code = _PARTY.get(line.get("abbreviation"), line.get("abbreviation"))
                if code:
                    lines[code] = lines.get(code, 0) + by_line.get(line["altAffiliationKey"], 0)
            party = next(iter(lines), None)
            choices.append(Choice(choice["name"].strip(), votes, party, choice_id=choice["choiceAltTallyKey"],
                                  party_lines=lines or None))
        kind = names.office_type(title)
        contest = Contest(
            source=source_id, contest_id=item["contestAltTallyKey"], state=state, title=title, office_type=kind,
            district=names.district(title), jurisdiction=f"{county} County", vote_for=item.get("voteFor") or 1,
            # The county's share of state and federal races; its own races and town races are complete.
            scope="partial" if kind not in ("local", "measure", "judicial") or "supreme" in title.lower()
            else "complete",
            reporting=Reporting(tally["progress"], tally["total"],
                                text=f"{tally['progress'] or 0} of {tally['total']} districts reported"
                                if tally["total"] else None),
            feed_updated_at=updated, choices=choices)
        contest.fill_percentages()
        contests.append(contest)
    return contests


class ResultsCasterSource(Source):
    platform = "Results Caster"
    level = "county"

    def __init__(self, id, state, county, subdomain, site_name, tiers=(4,)):
        self.id, self.state, self.county, self.tiers = id, state, county, frozenset(tiers)
        self.title = f"{county} County (Results Caster)"
        self.site_name, self.base = site_name, f"https://{subdomain}.resultscaster.com"
        self.url = self.base + "/"

    def pull(self, fetch):
        api = f"{self.base}/api/resultscasts/"
        slug = find_election(fetch.get(api + "current"))
        shell = fetch.get(api + f"{slug}/shell")
        status = fetch.get(api + f"{slug}/status")
        results = {group: fetch.get(api + f"{slug}/results/{quote(group)}")
                   for group in shell.get("groups") or ["Election Day"]}
        contests = parse(shell, results, source_id=self.id, state=self.state, county=self.county,
                         updated=status.get("uploadedDTTM"))
        for contest in contests:
            contest.url = f"{self.base}/r/{slug}"
        return contests
