import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))

import main


def test_follow_up_date_and_export_support(tmp_path):
    db_path = tmp_path / 'jobs.db'
    main.DB_PATH = db_path
    main.init_db()

    client = TestClient(main.app)
    response = client.post(
        '/api/jobs',
        json={
            'company': 'Example Co',
            'position': 'Product Manager',
            'date_applied': '2026-10-20',
            'status': 'interview',
            'notes': 'Follow-up needed',
            'follow_up_date': '2026-10-30',
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload['follow_up_date'] == '2026-10-30'

    jobs_response = client.get('/api/jobs')
    assert jobs_response.status_code == 200
    jobs = jobs_response.json()
    assert any(job['follow_up_date'] == '2026-10-30' for job in jobs)

    export_response = client.get('/api/jobs/export')
    assert export_response.status_code == 200
    csv_text = export_response.text
    assert 'company,position' in csv_text
    assert 'Example Co' in csv_text
