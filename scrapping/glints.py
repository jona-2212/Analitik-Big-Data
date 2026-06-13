import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import cloudscraper
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


def new_scraper() -> cloudscraper.CloudScraper:
    return cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )


def fetch_html(url: str, scraper: cloudscraper.CloudScraper, timeout: int = 30) -> str:
    response = scraper.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    response.raise_for_status()
    return response.text


def normalize_enum(value: str) -> str:
    if not value:
        return ""
    return value.replace("_", " ").title()


def format_experience(min_years, max_years) -> str:
    if min_years is None and max_years is None:
        return ""
    if min_years is None:
        return f"<= {max_years} tahun"
    if max_years is None:
        return f">= {min_years} tahun"
    if min_years == max_years:
        return f"{min_years} tahun"
    return f"{min_years}-{max_years} tahun"


def format_idr(amount) -> str:
    if amount is None:
        return ""
    return f"Rp {int(amount):,}".replace(",", ".")


def format_salary_range(salaries: list) -> str:
    if not salaries:
        return ""
    basic = [s for s in salaries if (s or {}).get("salaryType") == "BASIC"]
    salary_item = basic[0] if basic else salaries[0]
    min_amount = (salary_item or {}).get("minAmount")
    max_amount = (salary_item or {}).get("maxAmount")
    if min_amount is None and max_amount is None:
        return ""
    if min_amount is None:
        return format_idr(max_amount)
    if max_amount is None:
        return format_idr(min_amount)
    if min_amount == max_amount:
        return format_idr(min_amount)
    return f"{format_idr(min_amount)} - {format_idr(max_amount)}"


def format_posted_date(updated_at: str) -> str:
    if not updated_at:
        return ""
    try:
        return datetime.fromisoformat(updated_at.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "job"


def with_page(url: str, page: int) -> str:
    parsed = urlparse(url)
    query_pairs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() != "page"]
    query_pairs.append(("page", str(page)))
    return urlunparse(parsed._replace(query=urlencode(query_pairs, doseq=True)))


def dedupe_jobs(jobs: Iterable[Job]) -> List[Job]:
    results: List[Job] = []
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
        results.append(job)
    return results


def save_csv(jobs: List[Job], output_path: Path) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for job in jobs:
            writer.writerow({k: getattr(job, k) for k in OUTPUT_FIELDS})


def save_json(jobs: List[Job], output_path: Path) -> None:
    rows = [{k: getattr(job, k) for k in OUTPUT_FIELDS} for job in jobs]
    output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def extract_location(location_data: dict) -> str:
    if not location_data:
        return ""
    values = [location_data.get("formattedName")]
    for parent in location_data.get("parents") or []:
        if parent.get("level") in (2, 3):
            values.append(parent.get("formattedName"))
    ordered = []
    seen = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ", ".join(ordered)


def parse_description_blocks(description_json_string: str):
    if not description_json_string:
        return []
    try:
        payload = json.loads(description_json_string)
    except json.JSONDecodeError:
        return []
    blocks = payload.get("blocks")
    return blocks if isinstance(blocks, list) else []


def collect_section_items(blocks, markers):
    marker_set = [m.lower() for m in markers]
    capturing = False
    items = []

    for block in blocks:
        text = (block.get("text") or "").strip()
        if not text:
            continue
        text_lower = text.lower()

        if any(marker in text_lower for marker in marker_set):
            capturing = True
            continue

        if capturing and text_lower.endswith(":"):
            break

        if capturing:
            cleaned = re.sub(r"\s+", " ", text)
            cleaned = re.sub(r"^[\-•\d\.)\s]+", "", cleaned).strip()
            if cleaned:
                items.append(cleaned)

    return " | ".join(items)


def extract_responsibilities(description_json_string: str) -> str:
    blocks = parse_description_blocks(description_json_string)
    markers = [
        "tanggung jawab",
        "job description",
        "jobdesc",
        "job desk",
        "deskripsi pekerjaan",
        "uraian tugas",
    ]
    return collect_section_items(blocks, markers)


def scrape_glints(base_url: str, pages: int, max_pages: int = 200):
    scraper = new_scraper()
    jobs = []
    seen_ids = set()
    page = 1
    hard_limit = max(max_pages, 1)

    def should_continue(current_page: int) -> bool:
        if pages > 0:
            return current_page <= pages
        return current_page <= hard_limit

    while should_continue(page):
        url = with_page(base_url, page)
        try:
            html = fetch_html(url, scraper=scraper)
        except requests.RequestException:
            if pages > 0:
                page += 1
                continue
            break

        soup = BeautifulSoup(html, "html.parser")
        data = soup.select_one("script#__NEXT_DATA__")
        if not data or not data.string:
            if pages > 0:
                page += 1
                continue
            break

        payload = json.loads(data.string)
        jobs_in_page = (
            payload.get("props", {})
            .get("pageProps", {})
            .get("initialJobs", {})
            .get("jobsInPage", [])
        )

        if not jobs_in_page:
            if pages > 0:
                page += 1
                continue
            break

        added_in_page = 0

        for item in jobs_in_page:
            job_id = (item.get("id") or "").strip()
            title = (item.get("title") or "").strip()
            if not job_id or not title:
                continue
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            jobs.append(
                Job(
                    job_title=title,
                    company_name=((item.get("company") or {}).get("name") or ""),
                    location=extract_location(item.get("location") or {}),
                    job_type=normalize_enum(item.get("type", "")),
                    experience_level=format_experience(item.get("minYearsOfExperience"), item.get("maxYearsOfExperience")),
                    education_req=normalize_enum(item.get("educationLevel", "")),
                    salary_range=format_salary_range(item.get("salaries") or []),
                    job_requirements=", ".join(
                        dict.fromkeys(
                            [((x.get("skill") or {}).get("name") or "") for x in (item.get("skills") or []) if ((x.get("skill") or {}).get("name"))]
                        )
                    ),
                    job_responsibilities="",
                    posted_date=format_posted_date(item.get("updatedAt", "")),
                    source_platform="Glints",
                    job_url=f"https://glints.com/id/opportunities/jobs/{slugify(title)}/{job_id}",
                )
            )
            added_in_page += 1

        if pages <= 0 and added_in_page == 0:
            break

        page += 1

    for job in jobs:
        if not job.job_url:
            continue
        try:
            detail_html = fetch_html(job.job_url, scraper=scraper)
            soup = BeautifulSoup(detail_html, "html.parser")
            data = soup.select_one("script#__NEXT_DATA__")
            if not data or not data.string:
                continue
            payload = json.loads(data.string)
            job_id = [p for p in urlparse(job.job_url).path.split("/") if p][-1]
            job_obj = payload.get("props", {}).get("apolloCache", {}).get(f"Job:{job_id}", {})
            job.job_responsibilities = extract_responsibilities(job_obj.get("descriptionJsonString", ""))
        except requests.RequestException:
            continue

    return dedupe_jobs(jobs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraper khusus Glints")
    parser.add_argument(
        "--url",
        default="https://glints.com/id/opportunities/jobs/explore?country=ID&locationName=All%20Cities%2FProvinces",
        help="URL halaman explore Glints",
    )
    parser.add_argument("--pages", type=int, default=0, help="Jumlah halaman (0 = ambil semua sampai habis)")
    parser.add_argument("--max-pages", type=int, default=200, help="Batas aman halaman saat --pages 0")
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.add_argument("--output", default="glints_jobs", help="Nama file output tanpa ekstensi")
    args = parser.parse_args()

    jobs = scrape_glints(args.url, args.pages, max_pages=max(args.max_pages, 1))
    output_path = Path(f"{args.output}.{args.format}")

    if args.format == "csv":
        save_csv(jobs, output_path)
    else:
        save_json(jobs, output_path)

    print(f"[glints] {len(jobs)} lowongan")
    print(f"Output: {output_path.resolve()}")


if __name__ == "__main__":
    main()

