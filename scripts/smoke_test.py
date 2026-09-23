import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.demo_data import generate_demo_posts
from exporters.excel_exporter import build_excel
from pipeline import process_posts
from scoring.opportunity_score import score_posts


if __name__ == "__main__":
    processed = process_posts(generate_demo_posts())
    scored = score_posts(processed)
    payload = build_excel(scored)
    assert len(scored) >= 30
    assert scored["opportunity_score"].between(0, 100).all()
    assert len(payload) > 5_000
    print(f"Smoke test passed: {len(scored)} posts, {len(payload):,} Excel bytes")
