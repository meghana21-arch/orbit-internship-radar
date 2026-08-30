#!/usr/bin/env python3
"""Build the public job feed from maintained, free internship datasets."""
import html
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

SIMPLIFY = "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/README.md"
APPLYGUY = "https://raw.githubusercontent.com/ApplyGuy/2027-Internships/main/data/internships.json"
OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "jobs.json"


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Orbit-Internship-Radar/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def text(value):
    value = re.sub(r"<br\s*/?>", ", ", value, flags=re.I)
    value = re.sub(r"<summary>.*?</summary>", "", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip(" ,")


def clean_url(value):
    parts = urlsplit(html.unescape(value))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def area(title):
    lower = title.lower()
    if any(k in lower for k in ("machine learning", "artificial intelligence", " ai ", "data scientist", "nlp", "computer vision")):
        return "Machine learning"
    if any(k in lower for k in ("front end", "front-end", "frontend", "ui engineer")):
        return "Frontend"
    if any(k in lower for k in ("back end", "back-end", "backend", "infrastructure", "distributed", "platform")):
        return "Backend"
    if any(k in lower for k in ("full stack", "full-stack", "fullstack")):
        return "Full stack"
    return "Generic SDE"


def keywords(title):
    vocabulary = ["Python", "Java", "C++", "Go", "React", "TypeScript", "JavaScript", "Cloud", "AI", "ML", "Data", "Infrastructure", "Distributed systems", "Security", "Mobile", "Robotics"]
    lower = title.lower()
    found = [word for word in vocabulary if word.lower().replace("distributed systems", "distributed") in lower]
    defaults = {"Machine learning": ["Python", "ML"], "Frontend": ["React", "TypeScript"], "Backend": ["APIs", "Systems"], "Full stack": ["Frontend", "Backend"], "Generic SDE": ["Software engineering"]}
    return (found + defaults[area(title)])[:4]


def score(job):
    value = 72
    reasons = ["Matches a graduate-level software internship search"]
    title = job["title"].lower()
    if job["area"] == "Machine learning" or any(k in title for k in ("master", "graduate", "advanced degree")):
        value += 10
        reasons.append("Strong fit for a master's candidate")
    if job["area"] in ("Backend", "Full stack", "Generic SDE"):
        value += 6
        reasons.append("Three years of engineering experience can differentiate you")
    if "remote" in job["location"].lower() or any(k in job["location"] for k in ("FL", "Florida")):
        value += 5
        reasons.append("Location is Florida or remote-friendly")
    if job.get("age", "").endswith("d"):
        try:
            if int(job["age"][:-1]) <= 7:
                value += 5
                reasons.append("Recently posted")
        except ValueError:
            pass
    return min(value, 98), reasons[:3]


def simplify_jobs(markdown):
    jobs, company = [], ""
    for row in re.findall(r"<tr>(.*?)</tr>", markdown, flags=re.I | re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.I | re.S)
        if len(cells) < 5:
            continue
        candidate = text(cells[0])
        if candidate and candidate != "↳":
            company = candidate
        title, location, age = text(cells[1]), text(cells[2]), text(cells[4])
        links = re.findall(r'href="([^"]+)"', cells[3], flags=re.I)
        direct = next((clean_url(link) for link in links if "simplify.jobs" not in link), "")
        if not company or not title or not direct:
            continue
        relevant = any(k in title.lower() for k in ("software", "developer", "frontend", "backend", "full stack", "full-stack", "machine learning", "artificial intelligence", "data scien", "data engineer", "nlp", "computer vision"))
        undergraduate_only = any(k in title.lower() for k in ("undergraduate only", "undergraduate internship", " - undergraduate"))
        if relevant and not undergraduate_only:
            jobs.append({"company": company, "title": title, "location": location or "Location not listed", "season": "Summer 2027", "age": age, "url": direct, "source": "Simplify + Pitt CSC"})
    return jobs


def applyguy_jobs(payload):
    jobs = []
    for item in json.loads(payload).get("jobs", []):
        season = item.get("season", "")
        if season not in ("Summer 2027", "Fall 2027", "2027"):
            continue
        title = item.get("title", "")
        if item.get("category") != "Software Engineering" and not any(k in title.lower() for k in ("machine learning", "data scien", "artificial intelligence")):
            continue
        jobs.append({"company": item.get("company", "Unknown"), "title": title, "location": item.get("location", "Location not listed"), "season": "Fall 2027" if season == "Fall 2027" else "Summer 2027", "age": item.get("age", ""), "url": item.get("listingUrl") or item.get("url"), "source": "ApplyGuy"})
    return jobs


def main():
    candidates = simplify_jobs(fetch(SIMPLIFY)) + applyguy_jobs(fetch(APPLYGUY))
    unique = {}
    for job in candidates:
        key = re.sub(r"\W+", "", (job["company"] + job["title"] + job["location"]).lower())
        job["area"] = area(job["title"])
        job["keywords"] = keywords(job["title"])
        job["fitScore"], job["fitReasons"] = score(job)
        unique[key] = job
    jobs = sorted(unique.values(), key=lambda j: (-j["fitScore"], j["company"], j["title"]))[:150]
    for job in jobs:
        identity = f'{job["company"]}|{job["title"]}|{job["location"]}'.encode("utf-8")
        job["id"] = int(hashlib.sha256(identity).hexdigest()[:8], 16)
    output = {"updatedAt": datetime.now(timezone.utc).isoformat(), "count": len(jobs), "jobs": jobs}
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(jobs)} deduplicated roles to {OUTPUT}")


if __name__ == "__main__":
    main()
