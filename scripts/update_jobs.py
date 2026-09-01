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
DREAMWORK = "https://raw.githubusercontent.com/dreamworkhq/Open-Tech-Internships-2027/main/data/listings.json"
SPEEDY_SWE = "https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main/README.md"
SPEEDY_AI = "https://raw.githubusercontent.com/speedyapply/2027-AI-College-Jobs/main/README.md"
FAANG_TRACKER = "https://raw.githubusercontent.com/Emjumaev/FAANG-2027-Internships-Tracker/main/README.md"
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


def eligible_title(title):
    lower = title.lower()
    wrong_term = any(k in lower for k in ("fall 2026", "summer 2026", "spring 2027", "winter 2027", "2026 start"))
    wrong_degree = any(k in lower for k in ("undergraduate only", "undergraduate internship", " - undergraduate", ", bs,", "ph.d", "phd"))
    relevant = any(k in lower for k in ("software", "developer", "frontend", "front-end", "backend", "full stack", "full-stack", "machine learning", "artificial intelligence", " ai ", "data scien", "data engineer", "nlp", "computer vision", "ml intern"))
    return relevant and not wrong_term and not wrong_degree


def season_for(title):
    lower = title.lower()
    if "fall" in lower:
        return "Fall 2027"
    if "summer" in lower:
        return "Summer 2027"
    return "2027 · season unspecified"


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
    advanced_degree = any(k in title for k in ("master", "graduate", "advanced degree", ", ms,", " ms intern"))
    if job["area"] == "Machine learning" or advanced_degree:
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
        if eligible_title(title):
            jobs.append({"company": company, "title": title, "location": location or "Location not listed", "season": "Summer 2027", "age": age, "url": direct, "source": "Simplify + Pitt CSC"})
    return jobs


def applyguy_jobs(payload):
    jobs = []
    for item in json.loads(payload).get("jobs", []):
        season = item.get("season", "")
        if season not in ("Summer 2027", "Fall 2027", "2027"):
            continue
        title = item.get("title", "")
        if not eligible_title(title):
            continue
        if item.get("category") != "Software Engineering" and not any(k in title.lower() for k in ("machine learning", "data scien", "artificial intelligence")):
            continue
        jobs.append({"company": item.get("company", "Unknown"), "title": title, "location": item.get("location", "Location not listed"), "season": "Fall 2027" if season == "Fall 2027" else "Summer 2027", "age": item.get("age", ""), "url": item.get("listingUrl") or item.get("url"), "source": "ApplyGuy"})
    return jobs


def speedy_jobs(markdown, source):
    jobs = []
    for line in markdown.splitlines():
        if not line.startswith("| <a href="):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        company, title, location, application, age = text(cells[0]), text(cells[1]), text(cells[2]), cells[4], text(cells[5])
        links = re.findall(r'href="([^"]+)"', application, flags=re.I)
        if "2027" not in title or not eligible_title(title) or not links:
            continue
        jobs.append({"company": company, "title": title, "location": location or "Location not listed", "season": season_for(title), "age": age, "url": clean_url(links[-1]), "source": source})
    return jobs


def dreamwork_jobs(payload):
    jobs = []
    for item in json.loads(payload).get("listings", []):
        title = item.get("title", "")
        if "2027" not in title or not eligible_title(title):
            continue
        first_seen = item.get("firstIndexedAt") or item.get("postedAt") or ""
        age = ""
        try:
            days = (datetime.now(timezone.utc) - datetime.fromisoformat(first_seen.replace("Z", "+00:00"))).days
            age = f"{max(days, 0)}d"
        except ValueError:
            pass
        location = item.get("location") or "Location not listed"
        if item.get("remoteType") == "remote" and "remote" not in location.lower():
            location = f"Remote · {location}"
        jobs.append({"company": item.get("company", "Unknown"), "title": title, "location": location, "season": season_for(title), "age": age, "url": clean_url(item.get("url", "")), "source": "Dreamwork direct-career index"})
    return jobs


def faang_jobs(markdown):
    jobs, company = [], ""
    for line in markdown.splitlines():
        if line.startswith("## "):
            company = text(line[3:])
            continue
        match = re.match(r"\| \[([^]]+)\]\((https?://[^)]+)\).*?\| ([^|]+) \| ([^|]+) \| ([^|]+) \|", line)
        if not match or not company:
            continue
        title, url, category, location, posted = match.groups()
        title = re.sub(r"\s*🆕\s*$", "", title).strip()
        if "2027" not in title or not eligible_title(title):
            continue
        age = ""
        try:
            days = (datetime.now(timezone.utc) - datetime.strptime(posted.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)).days
            age = f"{max(days, 0)}d"
        except ValueError:
            pass
        jobs.append({"company": company, "title": title, "location": location.strip(), "season": season_for(title), "age": age, "url": clean_url(url), "source": "FAANG direct-career APIs"})
    return jobs


def dedupe_key(job):
    parts = urlsplit(job["url"])
    google_id = re.search(r"/results/(\d+)", parts.path)
    if google_id:
        return f"google-{google_id.group(1)}"
    path = re.sub(r"/(en-us|en_US|fr-ca|externalcareersite)/", "/", parts.path, flags=re.I)
    path = re.sub(r"/application/?$", "", path, flags=re.I)
    return f"{parts.netloc.lower()}{path.lower()}".rstrip("/")


def main():
    feeds = [
        simplify_jobs(fetch(SIMPLIFY)),
        applyguy_jobs(fetch(APPLYGUY)),
        speedy_jobs(fetch(SPEEDY_SWE), "SpeedyApply SWE"),
        speedy_jobs(fetch(SPEEDY_AI), "SpeedyApply AI/ML"),
        dreamwork_jobs(fetch(DREAMWORK)),
        faang_jobs(fetch(FAANG_TRACKER)),
    ]
    candidates = [job for feed in feeds for job in feed]
    unique = {}
    for job in candidates:
        if not job.get("url", "").startswith("http"):
            continue
        key = dedupe_key(job)
        job["area"] = area(job["title"])
        job["keywords"] = keywords(job["title"])
        job["fitScore"], job["fitReasons"] = score(job)
        if key in unique:
            existing = unique[key]
            sources = set(existing["source"].split(" + ")) | set(job["source"].split(" + "))
            preferred = job if job["fitScore"] > existing["fitScore"] else existing
            preferred["source"] = " + ".join(sorted(sources))
            unique[key] = preferred
        else:
            unique[key] = job
    jobs = sorted(unique.values(), key=lambda j: (-j["fitScore"], j["company"], j["title"]))[:500]
    for job in jobs:
        identity = f'{job["company"]}|{job["title"]}|{job["location"]}'.encode("utf-8")
        job["id"] = int(hashlib.sha256(identity).hexdigest()[:8], 16)
    source_counts = {"Simplify + Pitt CSC": len(feeds[0]), "ApplyGuy": len(feeds[1]), "SpeedyApply SWE": len(feeds[2]), "SpeedyApply AI/ML": len(feeds[3]), "Dreamwork": len(feeds[4]), "FAANG APIs": len(feeds[5])}
    output = {"updatedAt": datetime.now(timezone.utc).isoformat(), "count": len(jobs), "sourceCounts": source_counts, "jobs": jobs}
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(jobs)} deduplicated roles to {OUTPUT}")


if __name__ == "__main__":
    main()
