import argparse
import csv
import html
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

import requests


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

DEFAULT_KARIR_URL = "https://gateway2-beta.karir.com/v2/search/opportunities"

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


def format_idr(amount) -> str:
    if amount is None:
        return ""
    return f"Rp {int(amount):,}".replace(",", ".")


def format_salary_from_bounds(min_amount, max_amount) -> str:
    if min_amount is None and max_amount is None:
        return ""
    if min_amount is None:
        return format_idr(max_amount)
    if max_amount is None:
        return format_idr(min_amount)
    if min_amount == max_amount:
        return format_idr(min_amount)
    return f"{format_idr(min_amount)} - {format_idr(max_amount)}"


def format_posted_date(value: str) -> str:
    if not value:
        return ""

    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date().isoformat()
    except ValueError:
        pass

    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue

    return ""


def normalize_min_experience_text(value) -> str:
    if value in (None, ""):
        return ""

    if isinstance(value, (int, float)):
        num = int(value)
        return f"{num} tahun" if num > 0 else ""

    text = str(value).strip()
    if not text:
        return ""

    lower = text.lower()
    if "tahun" in lower or "year" in lower:
        return text

    match = re.search(r"\d+", text)
    if match:
        return f"{match.group(0)} tahun"

    return text


def iter_key_values(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key, value
            yield from iter_key_values(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_key_values(item)


def parse_min_experience_from_text(text: str) -> str:
    raw = str(text or "")
    if not raw:
        return ""

    normalized = normalize_html_text(raw).lower()
    if not normalized:
        return ""

    patterns = [
        r"(?:pengalaman|experience)\s*(?:minimal|min\.?|minimum)\s*(\d+)\s*(?:tahun|year)",
        r"(?:minimal|min\.?|minimum)\s*(\d+)\s*(?:tahun|year)\s*(?:pengalaman|experience)?",
        r"(?:pengalaman|experience)\s*(\d+)\s*(?:tahun|year)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.I)
        if match:
            return f"{match.group(1)} tahun"

    return ""


def get_min_experience(source: dict, requirements_text: str = "") -> str:
    for key in [
        "minimum_experience",
        "min_experience",
        "minimum_experience_year",
        "minimum_experience_years",
        "min_experience_year",
        "min_experience_years",
        "experience_min",
        "experience_year",
        "year_experience",
        "minimal_experience",
    ]:
        value = source.get(key)
        normalized = normalize_min_experience_text(value)
        if normalized:
            return normalized

    min_year = source.get("min_years_of_experience")
    max_year = source.get("max_years_of_experience")
    min_text = normalize_min_experience_text(min_year)
    max_text = normalize_min_experience_text(max_year)

    if min_text and max_text:
        min_num = re.search(r"\d+", min_text)
        max_num = re.search(r"\d+", max_text)
        if min_num and max_num:
            return f"{min_num.group(0)}-{max_num.group(0)} tahun"
        return min_text

    if min_text:
        return min_text

    if max_text:
        max_num = re.search(r"\d+", max_text)
        return f"<= {max_num.group(0)} tahun" if max_num else max_text

    for key, value in iter_key_values(source):
        if not isinstance(key, str):
            continue
        key_norm = key.lower().replace("-", "_")
        if (
            "experience" in key_norm
            or "pengalaman" in key_norm
            or ("minimal" in key_norm and "tahun" in key_norm)
        ):
            normalized = normalize_min_experience_text(value)
            if normalized:
                return normalized

    from_req = parse_min_experience_from_text(requirements_text)
    if from_req:
        return from_req

    return ""


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
            writer.writerow(
                {
                    "job_title": job.job_title,
                    "company_name": job.company_name,
                    "location": job.location,
                    "job_type": job.job_type,
                    "experience_level": job.experience_level,
                    "education_req": job.education_req,
                    "salary_range": job.salary_range,
                    "job_requirements": job.job_requirements,
                    "job_responsibilities": job.job_responsibilities,
                    "posted_date": job.posted_date,
                    "source_platform": job.source_platform,
                }
            )


def save_json(jobs: List[Job], output_path: Path) -> None:
    rows = [
        {
            "job_title": job.job_title,
            "company_name": job.company_name,
            "location": job.location,
            "job_type": job.job_type,
            "experience_level": job.experience_level,
            "education_req": job.education_req,
            "salary_range": job.salary_range,
            "job_requirements": job.job_requirements,
            "job_responsibilities": job.job_responsibilities,
            "posted_date": job.posted_date,
            "source_platform": job.source_platform,
        }
        for job in jobs
    ]
    output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_list_or_text(value) -> str:
    if isinstance(value, list):
        cleaned = [str(x).strip() for x in value if str(x).strip()]
        return ", ".join(dict.fromkeys(cleaned)) if cleaned else ""
    if isinstance(value, str):
        return value.strip()
    return ""


def get_location(item: dict) -> str:
    for key in ["branch_location_names", "city_name", "location", "province_name"]:
        val = item.get(key)
        text = normalize_list_or_text(val)
        if text:
            return text
    return ""


def get_requirements(item: dict) -> str:
    for key in ["requirements", "requirement", "qualification", "qualifications", "skill_name", "skills"]:
        val = item.get(key)
        text = normalize_list_or_text(val)
        if text:
            return text
    return ""


def get_responsibilities(item: dict) -> str:
    for key in ["job_desc", "job_description", "responsibilities", "responsibility"]:
        val = item.get(key)
        text = normalize_list_or_text(val)
        if text:
            return text
    return ""


def normalize_html_text(value) -> str:
    text = normalize_list_or_text(value)
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<\s*br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<\s*/?\s*(p|div|li)\b[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[\t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def normalize_location_text(value) -> str:
    text = normalize_html_text(value)
    if not text:
        return ""
    text = text.replace("\n", ", ")
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r",\s*,+", ", ", text)
    return text.strip(" ,")


def normalize_bulleted_text(value) -> str:
    text = normalize_html_text(value)
    if not text:
        return ""
    parts = re.split(r"\n+|\s*\|\s*", text)
    cleaned = []
    seen = set()
    for part in parts:
        chunk = re.sub(r"^[\s\-•●\*\d\.)\(]+", "", part).strip(" -|")
        if not chunk:
            continue
        key = chunk.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(chunk)
    return " | ".join(cleaned)


def fetch_html(url: str, timeout: int = 30) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id,en;q=0.9",
    }
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_script_jsons(html: str) -> List[dict]:
    payloads: List[dict] = []

    next_match = re.search(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        re.S,
    )
    if next_match:
        raw = next_match.group(1).strip()
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                payloads.append(obj)
        except json.JSONDecodeError:
            pass

    for raw in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S):
        text = raw.strip()
        if not text:
            continue
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            payloads.append(obj)
        elif isinstance(obj, list):
            payloads.extend([x for x in obj if isinstance(x, dict)])

    return payloads


def walk_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk_dicts(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk_dicts(item)


def item_to_job(item: dict, fallback_url: str = ""):
    source = item.get("data") if isinstance(item.get("data"), dict) else item

    if not isinstance(source, dict):
        return None

    has_job_signal = any(
        key in source
        for key in (
            "job_position",
            "opportunities_link",
            "posted_at",
            "updated_at",
            "salary_lower",
            "salary_upper",
            "requirements",
            "responsibilities",
            "datePosted",
        )
    )
    if not has_job_signal:
        return None

    title = (
        source.get("job_position")
        or source.get("title")
        or source.get("name")
        or source.get("headline")
        or ""
    )
    title = str(title).strip()
    if not title:
        return None

    company_name = source.get("company_name")
    if not company_name and isinstance(source.get("company"), dict):
        company_name = source.get("company", {}).get("name")
    company_name = str(company_name or "").strip()

    url = source.get("opportunities_link") or source.get("url") or fallback_url
    if not url:
        job_id = str(source.get("id") or "").strip()
        if job_id:
            url = f"https://www.karir.com/opportunities/{job_id}"
    if url and isinstance(url, str) and url.startswith("/"):
        url = f"https://www.karir.com{url}"

    education_req = source.get("degree_name") or source.get("degree") or source.get("degrees") or ""
    if isinstance(education_req, list):
        education_req = ", ".join([str(x).strip() for x in education_req if str(x).strip()])

    salary_lower = source.get("salary_lower")
    salary_upper = source.get("salary_upper")
    try:
        salary_lower = int(salary_lower) if salary_lower not in (None, "") else None
    except (TypeError, ValueError):
        salary_lower = None
    try:
        salary_upper = int(salary_upper) if salary_upper not in (None, "") else None
    except (TypeError, ValueError):
        salary_upper = None

    requirements = get_requirements(source)
    if not requirements:
        requirements = source.get("requirements") or source.get("qualification") or ""

    responsibilities = get_responsibilities(source)
    if not responsibilities:
        responsibilities = source.get("responsibilities") or source.get("job_description") or source.get("job_desc") or ""

    job = Job(
        job_title=title,
        company_name=company_name,
        location=normalize_location_text(get_location(source)),
        job_type=str(source.get("job_type") or source.get("job_type_name") or source.get("workplace") or "").strip(),
        experience_level=(
            get_min_experience(source, requirements_text=requirements)
            or str(source.get("experience") or source.get("level_name") or source.get("level") or "").strip()
        ),
        education_req=normalize_location_text(str(education_req).strip()),
        salary_range=format_salary_from_bounds(salary_lower, salary_upper),
        job_requirements=normalize_bulleted_text(requirements),
        job_responsibilities=normalize_bulleted_text(responsibilities),
        posted_date=format_posted_date(
            str(source.get("updated_at") or source.get("posted_at") or source.get("datePosted") or "")
        ),
        source_platform="Karir.com",
        job_url=str(url or "").strip(),
    )
    return job


def scrape_karir_public(pages: int, page_size: int, keyword: str):
    jobs: List[Job] = []
    keyword_lower = keyword.strip().lower()
    target_count = None if pages <= 0 else (max(pages, 1) * max(page_size, 1))

    try:
        sitemap_xml = fetch_html("https://www.karir.com/sitemap.xml")
    except requests.RequestException:
        return []

    opportunity_urls = []
    for loc in re.findall(r"<loc>(.*?)</loc>", sitemap_xml):
        if "/opportunities/" not in loc:
            continue
        url = loc.replace("http://", "https://")
        url = url.replace("https://www.karir.com", "https://karir.com")
        opportunity_urls.append(url)

    seen_urls = set()
    ordered_urls = []
    for url in opportunity_urls:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        ordered_urls.append(url)

    scan_limit = len(ordered_urls) if target_count is None else min(len(ordered_urls), target_count * 8)

    for detail_url in ordered_urls[:scan_limit]:
        if target_count is not None and len(jobs) >= target_count:
            break
        try:
            detail_html = fetch_html(detail_url)
        except requests.RequestException:
            continue

        for payload in parse_script_jsons(detail_html):
            for candidate in walk_dicts(payload):
                job = item_to_job(candidate, fallback_url=detail_url)
                if not job:
                    continue
                if keyword_lower:
                    haystack = " ".join(
                        [
                            job.job_title,
                            job.company_name,
                            job.location,
                            job.job_requirements,
                            job.job_responsibilities,
                        ]
                    ).lower()
                    if keyword_lower not in haystack:
                        continue
                jobs.append(job)

    deduped = dedupe_jobs(jobs)
    if target_count is None:
        return deduped
    return deduped[:target_count]


def build_auth_header(token: str) -> str:
    token = token.strip()
    if token.lower().startswith("bearer "):
        return token
    return f"Bearer {token}"


def fetch_karir_page(
    base_url: str,
    auth_token: str,
    page: int,
    page_size: int,
    keyword: str,
    timeout: int = 30,
) -> List[dict]:
    def clean_payload(payload: dict) -> dict:
        return {k: v for k, v in payload.items() if v is not None}

    offset = max(page - 1, 0) * page_size
    full_payload = {
        "keyword": keyword,
        "location_ids": [],
        "company_ids": [],
        "industry_ids": [],
        "job_function_ids": [],
        "degree_ids": [],
        "locale": "id",
        "limit": page_size,
        "offset": offset,
        "level": "",
        "min_employee": 0,
        "max_employee": 50,
        "is_opportunity": True,
        "sort_order": "",
        "is_recomendation": False,
        "is_preference": False,
        "is_choice_opportunity": False,
        "is_subscribe": False,
        "workplace": None,
        "expected_salary": None,
        "min_salary": None,
        "max_salary": None,
    }
    minimal_payload = {
        "keyword": keyword,
        "location_ids": [],
        "company_ids": [],
        "industry_ids": [],
        "job_function_ids": [],
        "degree_ids": [],
        "locale": "id",
        "limit": min(page_size, 5),
        "offset": max(page - 1, 0) * min(page_size, 5),
        "is_opportunity": True,
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Authorization": build_auth_header(auth_token),
        "Origin": "https://karir.com",
        "Referer": "https://karir.com/search-lowongan",
        "Accept-Language": "id,en;q=0.9",
    }

    endpoint_candidates = [base_url]
    if "gateway2-beta.karir.com" in base_url:
        endpoint_candidates.append(base_url.replace("gateway2-beta.karir.com", "gateway2.karir.com"))

    last_error = None
    for endpoint in dict.fromkeys(endpoint_candidates):
        for payload in (clean_payload(full_payload), clean_payload(minimal_payload)):
            try:
                response = requests.post(endpoint, json=payload, headers=headers, timeout=timeout)
                body = response.json()
            except ValueError:
                response = requests.post(endpoint, json=payload, headers=headers, timeout=timeout)
                body = {"message": response.text[:500]}
            except requests.RequestException as exc:
                last_error = f"{endpoint} -> {exc}"
                continue

            if response.status_code >= 400:
                message = ""
                if isinstance(body, dict):
                    message = body.get("message") or body.get("error") or json.dumps(body, ensure_ascii=False)
                if not message:
                    message = response.text[:500]
                last_error = f"{endpoint} -> HTTP {response.status_code}: {message}"
                continue

            if isinstance(body, dict):
                code = body.get("code")
                message = body.get("message")
                if code is not None and str(code) != "200":
                    last_error = f"{endpoint} -> Karir API code {code}: {message}"
                    continue
                if isinstance(body.get("error"), str) and body.get("error"):
                    last_error = f"{endpoint} -> Karir API error: {body['error']}"
                    continue

                data = body.get("data")
                if not isinstance(data, dict):
                    last_error = f"{endpoint} -> Karir API response tidak mengandung object 'data'"
                    continue

                opportunities = data.get("opportunities")
                if opportunities is None:
                    last_error = f"{endpoint} -> Karir API response tidak mengandung field 'opportunities'"
                    continue

                return opportunities if isinstance(opportunities, list) else []

            last_error = f"{endpoint} -> Karir API response bukan JSON object yang valid"

    raise RuntimeError(last_error or "Request Karir gagal tanpa detail error")


def scrape_karir(base_url: str, pages: int, auth_token: str, page_size: int, keyword: str, max_pages: int = 300):
    jobs: List[Job] = []
    last_error = None

    page = 1
    safe_limit = max(max_pages, 1)

    while True:
        if pages > 0 and page > pages:
            break
        if pages <= 0 and page > safe_limit:
            break

        try:
            opportunities = fetch_karir_page(
                base_url=base_url,
                auth_token=auth_token,
                page=page,
                page_size=page_size,
                keyword=keyword,
            )
        except (requests.RequestException, RuntimeError) as exc:
            last_error = f"page={page} -> {exc}"
            if page == 1:
                raise RuntimeError(f"Gagal request Karir: {last_error}") from exc
            break

        if not opportunities:
            break

        for item in opportunities:
            job_id = str(item.get("id") or "").strip()
            fallback_url = f"https://karir.com/opportunities/{job_id}" if job_id else ""
            job = item_to_job(item, fallback_url=fallback_url)
            if not job:
                continue
            jobs.append(job)

        page += 1

    if not jobs and last_error:
        raise RuntimeError(f"Tidak ada data Karir. Detail: {last_error}")

    return dedupe_jobs(jobs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraper khusus Karir.com")
    parser.add_argument(
        "--url",
        default=DEFAULT_KARIR_URL,
        help="Endpoint API Karir",
    )
    parser.add_argument(
        "--token",
        default="",
        help="Bearer token Karir (boleh isi full 'Bearer ...' atau token saja). Bisa dari env KARIR_TOKEN",
    )
    parser.add_argument("--pages", type=int, default=0, help="Jumlah halaman (0 = ambil semua)")
    parser.add_argument("--max-pages", type=int, default=300, help="Batas aman halaman saat --pages 0")
    parser.add_argument("--page-size", type=int, default=30, help="Jumlah data per halaman")
    parser.add_argument("--keyword", default="", help="Keyword pencarian")
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.add_argument("--output", default="karir_jobs", help="Nama file output tanpa ekstensi")
    args = parser.parse_args()

    token = (args.token or os.getenv("KARIR_TOKEN", "")).strip()

    jobs: List[Job] = []
    api_error = ""

    if token:
        try:
            jobs = scrape_karir(
                base_url=args.url,
                pages=args.pages,
                auth_token=token,
                page_size=max(args.page_size, 1),
                keyword=args.keyword.strip(),
                max_pages=max(args.max_pages, 1),
            )
        except (RuntimeError, requests.RequestException) as exc:
            api_error = str(exc)

    if not jobs:
        jobs = scrape_karir_public(
            pages=args.pages,
            page_size=max(args.page_size, 1),
            keyword=args.keyword.strip(),
        )

    if not jobs:
        detail = f" API error: {api_error}" if api_error else ""
        parser.exit(1, f"[karir] error: Tidak ada data yang berhasil diambil.{detail}\n")

    output_path = Path(f"{args.output}.{args.format}")
    if args.format == "csv":
        save_csv(jobs, output_path)
    else:
        save_json(jobs, output_path)

    print(f"[karir] {len(jobs)} lowongan")
    print(f"Output: {output_path.resolve()}")


if __name__ == "__main__":
    main()
