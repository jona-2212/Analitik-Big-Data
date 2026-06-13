import argparse
from pathlib import Path

from linkedin_simple import filter_by_completeness, save_csv, save_json, scrape_linkedin_simple


def main() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn scraper mode data lengkap")
    parser.add_argument(
        "--url",
        default="https://www.linkedin.com/jobs/search/?keywords=&location=Indonesia",
        help="LinkedIn search URL",
    )
    parser.add_argument("--pages", type=int, default=4, help="Jumlah halaman (0 = ambil semua)")
    parser.add_argument("--max-pages", type=int, default=100, help="Batas aman saat --pages 0")
    parser.add_argument("--fetch-detail", action="store_true", default=True, help="Ambil halaman detail tiap job (default: aktif)")
    parser.add_argument("--no-fetch-detail", action="store_false", dest="fetch_detail", help="Nonaktifkan ambil detail")
    parser.add_argument("--detail-timeout", type=int, default=12, help="Timeout request detail per job (detik)")
    parser.add_argument("--min-filled", type=int, default=8, help="Minimal jumlah field terisi dari 10 field utama")
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.add_argument("--output", default="linkedin_lengkap", help="Nama output tanpa ekstensi")
    args = parser.parse_args()

    jobs = scrape_linkedin_simple(
        base_url=args.url,
        pages=args.pages,
        max_pages=max(args.max_pages, 1),
        fetch_detail=bool(args.fetch_detail),
        detail_timeout=max(args.detail_timeout, 3),
    )
    jobs = filter_by_completeness(jobs, max(args.min_filled, 0))

    if not jobs:
        parser.exit(1, "[linkedin] error: Tidak ada data yang berhasil diambil.\n")

    output_path = Path(f"{args.output}.{args.format}")
    if args.format == "csv":
        save_csv(jobs, output_path)
    else:
        save_json(jobs, output_path)

    print(f"[linkedin] {len(jobs)} lowongan")
    print(f"Filter kelengkapan: >= {args.min_filled}/10 field")
    print(f"Output: {output_path.resolve()}")


if __name__ == "__main__":
    main()
