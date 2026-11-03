#!/usr/bin/env python3
"""Exploratory: check which state results feeds answer scripted requests, and what they return.

Not part of the scraper system. Prints status, content type, size and the start of each response so we
can see the shape of each feed before designing parsers. Standard library only.

Usage: python3 scrapers/explore/probe_feeds.py [name-substring ...]
"""
import sys
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (compatible; wfp-results-probe/0.1)"

FEEDS = {
    "CA api: us-rep": "https://api.sos.ca.gov/returns/us-rep/district/all",
    "CA api: ballot-measures": "https://api.sos.ca.gov/returns/ballot-measures",
    "PA api: election list": "https://www.electionreturns.pa.gov/api/ElectionReturn/GetAllElections?methodName=GetAllElections",
    "NC: statewide results": "https://er.ncsbe.gov/enr/20261103/data/results_0.txt",
    "UT EV: jurisdiction": "https://electionresults.utah.gov/results/public/api/jurisdictions/Utah",
    "WA EV: jurisdiction": "https://results.votewa.gov/results/public/api/jurisdictions/washington",
    "RI EV: jurisdiction": "https://electionresults.ri.gov/results/public/api/jurisdictions/rhodeisland",
    "GA EV: jurisdiction": "https://results.sos.ga.gov/results/public/api/jurisdictions/Georgia",
    "CO Clarity: elections": "https://results.enr.clarityelections.com/CO/elections.json",
    "SC Clarity: elections": "https://results.enr.clarityelections.com/SC/elections.json",
    "CT: elections": "https://ctemspublic.tgstg.net/ng-app/data/election/ElectionList.json",
    "NM: results media": "https://electionresults.sos.nm.gov/ResultsMedia.aspx",
    "NE: results media": "https://electionresults.nebraska.gov/ResultsMedia.aspx",
    "NY ENR: home": "https://nyenr.elections.ny.gov/",
    "OR: results": "https://results.oregonvotes.gov/",
    "TX: home": "https://results.texas-election.com/",
    "DE: GE2026": "https://elections.delaware.gov/results/enr/GE2026.html",
    "OH: live results": "https://liveresults.ohiosos.gov/",
    "AZ: results": "https://results.arizona.vote/",
}


def probe(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read(200_000)
            return resp.status, resp.headers.get("Content-Type", ""), body, time.monotonic() - start
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read(500), time.monotonic() - start
    except Exception as e:  # noqa: BLE001 - exploratory, report anything
        return None, type(e).__name__, str(e).encode(), time.monotonic() - start


def main():
    wanted = [a.lower() for a in sys.argv[1:]]
    for name, url in FEEDS.items():
        if wanted and not any(w in name.lower() for w in wanted):
            continue
        status, ctype, body, secs = probe(url)
        head = body[:300].decode("utf-8", "replace").replace("\n", " ")
        print(f"== {name}  [{status}] {ctype}  {len(body)}B  {secs:.1f}s\n   {url}\n   {head}\n")


if __name__ == "__main__":
    main()
