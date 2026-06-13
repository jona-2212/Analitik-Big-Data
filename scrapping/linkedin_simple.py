import csv
import html
import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, List
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

OUTPUT_FIELDS = [
    "job_title",
    "company_name",
    "location",
    "job_type",
    "experience_level",
    "education_req",
    "salary_range",
    "job_requirements",
    "job_responsibilities",
    "posted_date",
    "source_platform",
]

COMPLETENESS_FIELDS = [
    "job_title",
    "company_name",
    "location",
    "job_type",
    "experience_level",
    "education_req",
    "salary_range",
    "job_requirements",
    "job_responsibilities",
    "posted_date",
]


@dataclass
class Job:
    job_title: str
    company_name: str
    location: str
    job_type: str
    experience_level: str
    education_req: str
    salary_range: str
    job_requirements: str
    job_responsibilities: str
    posted_date: str
    source_platform: str
    job_url: str = ""


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def normalize_bullets(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    parts = [normalize_space(p) for p in re.split(r"\n+|\s*\|\s*|•", text)]
    ban = {"show more", "show less", "requirements", "requirements:", "job description", "job description:"}
    out, seen = [], set()
    for p in parts:
        p = re.sub(r"^[\-•●*\d\.)\(\s]+", "", p).strip(" -|")
        if not p:
            continue
        low = p.lower()
        if low in ban:
            continue
        if low in seen:
            continue
        seen.add(low)
        out.append(p)
    return " | ".join(out)


def infer_education(text: str) -> str:
    t = (text or "").lower()
    labels = []
    checks = [
        ("sma", "SMA"), ("smk", "SMK"), ("diploma", "Diploma"), ("d3", "D3"),
        ("s1", "S1"), ("bachelor", "Bachelor"), ("s2", "S2"), ("master", "Master")
    ]
    for key, lbl in checks:
        if key in t and lbl not in labels:
            labels.append(lbl)
    return ", ".join(labels)


def infer_salary(text: str) -> str:
    m = re.findall(r"(?:rp|idr)\s?[\d\.,]+(?:\s?[kKmM])?", normalize_space(text), flags=re.I)
    if not m:
        return ""
    return m[0] if len(m) == 1 else f"{m[0]} - {m[1]}"


def normalize_posted_date(text: str) -> str:
    txt = (text or "").strip().lower()
    if not txt:
        return ""
    today = date.today()
    if any(x in txt for x in ["today", "hari ini", "just now", "baru saja"]):
        return today.isoformat()
    m = re.search(r"(\d+)\s*(day|week|month|hari|minggu|bulan)", txt)
    if not m:
        return ""
    num = int(m.group(1))
    unit = m.group(2)
    if unit in ["day", "hari"]:
        return (today - timedelta(days=num)).isoformat()
    if unit in ["week", "minggu"]:
        return (today - timedelta(weeks=num)).isoformat()
    return (today - timedelta(days=30 * num)).isoformat()


def with_start(url: str, page: int, page_size: int = 25) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs["start"] = [str((page - 1) * page_size)]
    return urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))


def split_desc_sections(desc_html: str) -> tuple[str, str]:
    txt = html.unescape(desc_html or "")
    txt = re.sub(r"<br\s*/?>", "\n", txt, flags=re.I)
    txt = re.sub(r"</(p|li|div|h2|h3|h4)>", "\n", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    lines = [normalize_space(x) for x in re.split(r"\n+", txt) if normalize_space(x)]
    if not lines:
        return "", ""

    req_kw = [
        "kualifikasi",
        "persyaratan",
        "requirement",
        "requirements",
        "qualification",
        "qualifications",
        "must have",
    ]
    resp_kw = [
        "tanggung jawab",
        "responsibility",
        "responsibilities",
        "job description",
        "what you'll do",
        "aktivitas pembelajaran",
        "job desk",
    ]

    def section_of(line: str) -> str:
        lowered = line.lower().strip(" :")
        if any(k in lowered for k in req_kw):
            return "req"
        if any(k in lowered for k in resp_kw):
            return "resp"
        return ""

    req, resp = [], []
    current = ""
    for line in lines:
        section = section_of(line)
        if section:
            current = section
            continue

        is_short_heading = bool(re.match(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s/&\-]{0,60}:?$", line)) and len(line.split()) <= 6
        if is_short_heading:
            continue

        if current == "req":
            req.append(line)
        elif current == "resp":
            resp.append(line)

    if not req and not resp:
        req = [ln for ln in lines if any(k in ln.lower() for k in ["skill", "experience", "degree"])]
        resp = [ln for ln in lines if ln not in req]
    req_text = normalize_bullets("\n".join(req[:20]))
    resp_text = normalize_bullets("\n".join(resp[:20]))
    if req_text and resp_text:
        req_set = {x.strip().lower() for x in req_text.split(" | ") if x.strip()}
        resp_text = " | ".join([x for x in resp_text.split(" | ") if x.strip().lower() not in req_set])
    return req_text, resp_text


def extract_json_ld(dsoup: BeautifulSoup) -> dict:
    for tag in dsoup.select("script[type='application/ld+json']"):
        raw = (tag.string or tag.get_text("", strip=True) or "").strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        nodes = payload if isinstance(payload, list) else [payload]
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if "jobposting" not in str(node.get("@type", "")).lower():
                continue
            out = {
                "employmentType": normalize_space(node.get("employmentType") or ""),
                "datePosted": normalize_space(node.get("datePosted") or ""),
                "description": node.get("description") or "",
                "company": normalize_space((node.get("hiringOrganization") or {}).get("name") if isinstance(node.get("hiringOrganization"), dict) else ""),
                "salary": "",
            }
            base_salary = node.get("baseSalary")
            if isinstance(base_salary, dict):
                val = base_salary.get("value")
                if isinstance(val, dict):
                    min_v = val.get("minValue")
                    max_v = val.get("maxValue")
                    if min_v is not None and max_v is not None:
                        out["salary"] = f"{min_v} - {max_v}"
            return out
    return {}


def parse_detail_fields(html_text: str) -> dict:
    dsoup = BeautifulSoup(html_text, "html.parser")
    result = {
        "job_type": "",
        "experience_level": "",
        "education_req": "",
        "salary_range": "",
        "job_requirements": "",
        "job_responsibilities": "",
        "location": "",
        "company_name": "",
        "posted_date": "",
    }
    jld = extract_json_ld(dsoup)
    desc_el = dsoup.select_one("div.show-more-less-html__markup, section.show-more-less-html, div.description__text")
    desc_html = desc_el.decode_contents() if desc_el else (jld.get("description") or "")
    req, resp = split_desc_sections(desc_html)
    result["job_requirements"] = req
    result["job_responsibilities"] = resp
    result["job_type"] = jld.get("employmentType", "")
    result["salary_range"] = jld.get("salary", "")
    result["company_name"] = jld.get("company", "")
    if re.match(r"\d{4}-\d{2}-\d{2}", jld.get("datePosted", "")):
        result["posted_date"] = jld["datePosted"][:10]

    for item in dsoup.select("li.description__job-criteria-item"):
        label = normalize_space((item.select_one("h3, span.description__job-criteria-subheader") or item).get_text(" ", strip=True)).lower()
        value = normalize_space((item.select_one("span.description__job-criteria-text") or item).get_text(" ", strip=True))
        if not value:
            continue
        if "employment type" in label:
            result["job_type"] = value
        elif "seniority level" in label:
            result["experience_level"] = value

    plain_desc = BeautifulSoup(desc_html, "html.parser").get_text(" ", strip=True)
    if not result["education_req"]:
        result["education_req"] = infer_education(plain_desc)
    if not result["salary_range"]:
        result["salary_range"] = infer_salary(plain_desc)
    return result


def scrape_linkedin_simple(base_url: str, pages: int, max_pages: int = 100, fetch_detail: bool = False, detail_timeout: int = 12) -> List[Job]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "id,en;q=0.9"})
    jobs: List[Job] = []

    page = 1
    hard_limit = max(max_pages, 1)
    while True:
        if pages > 0 and page > pages:
            break
        if pages <= 0 and page > hard_limit:
            break

        try:
            resp = session.get(with_start(base_url, page), timeout=30)
            resp.raise_for_status()
        except requests.RequestException:
            if pages > 0:
                page += 1
                continue
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.base-card, li.jobs-search__results-list li")
        if not cards:
            if pages > 0:
                page += 1
                continue
            break

        before = len(jobs)
        for card in cards:
            title = normalize_space((card.select_one("h3.base-search-card__title") or card).get_text(" ", strip=True))
            company = normalize_space((card.select_one("h4.base-search-card__subtitle, a.hidden-nested-link") or card).get_text(" ", strip=True))
            location = normalize_space((card.select_one("span.job-search-card__location") or card).get_text(" ", strip=True))
            date_el = card.select_one("time.job-search-card__listdate, time")
            date_raw = normalize_space((date_el.get("datetime") if date_el else "") or (date_el.get_text(" ", strip=True) if date_el else ""))
            link_el = card.select_one("a.base-card__full-link")
            job_url = normalize_space(link_el.get("href") if link_el else "")
            if job_url:
                job_url = urljoin("https://www.linkedin.com", job_url)

            detail = {
                "job_type": "",
                "experience_level": "",
                "education_req": "",
                "salary_range": "",
                "job_requirements": "",
                "job_responsibilities": "",
                "location": "",
                "company_name": "",
                "posted_date": "",
            }
            if fetch_detail and job_url:
                try:
                    d = session.get(job_url, timeout=detail_timeout)
                    d.raise_for_status()
                    detail = parse_detail_fields(d.text)
                except requests.RequestException:
                    pass

            if not title:
                continue
            jobs.append(
                Job(
                    job_title=title,
                    company_name=detail.get("company_name") or company,
                    location=detail.get("location") or location,
                    job_type=detail.get("job_type") or "Tidak Disebutkan",
                    experience_level=detail.get("experience_level") or "",
                    education_req=detail.get("education_req") or "",
                    salary_range=detail.get("salary_range") or "",
                    job_requirements=detail.get("job_requirements") or "",
                    job_responsibilities=detail.get("job_responsibilities") or "",
                    posted_date=detail.get("posted_date") or normalize_posted_date(date_raw),
                    source_platform="LinkedIn",
                    job_url=job_url,
                )
            )

        if len(jobs) == before and pages <= 0:
            break
        page += 1

    return dedupe_jobs(jobs)


def dedupe_jobs(jobs: Iterable[Job]) -> List[Job]:
    out: List[Job] = []
    seen = set()
    for job in jobs:
        key = (
            job.source_platform,
            job.job_title.strip().lower(),
            job.company_name.strip().lower(),
            job.location.strip().lower(),
            job.posted_date.strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(job)
    return out


def count_filled_fields(job: Job) -> int:
    return sum(1 for field in COMPLETENESS_FIELDS if str(getattr(job, field, "") or "").strip())


def filter_by_completeness(jobs: List[Job], min_filled: int) -> List[Job]:
    if min_filled <= 0:
        return jobs
    return [job for job in jobs if count_filled_fields(job) >= min_filled]


def save_csv(jobs: List[Job], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for job in jobs:
            writer.writerow({k: getattr(job, k) for k in OUTPUT_FIELDS})


def save_json(jobs: List[Job], output_path: Path) -> None:
    rows = [{k: getattr(job, k) for k in OUTPUT_FIELDS} for job in jobs]
    output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
