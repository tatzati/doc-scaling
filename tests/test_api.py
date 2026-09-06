import time


def test_health_and_readiness(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}


def test_document_can_be_created_listed_and_fetched(client):
    response = client.post(
        "/documents",
        json={"name": "report.pdf", "content_type": "application/pdf", "size_bytes": 2048},
    )

    assert response.status_code == 201
    document = response.json()
    assert document["name"] == "report.pdf"
    assert client.get(f"/documents/{document['id']}").json() == document
    assert client.get("/documents").json() == [document]


def test_processing_job_reaches_completed(client):
    document = client.post(
        "/documents",
        json={"name": "report.pdf", "content_type": "application/pdf", "size_bytes": 2048},
    ).json()

    response = client.post(f"/documents/{document['id']}/process")
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        job = client.get(f"/jobs/{job_id}").json()
        if job["status"] == "completed":
            break
        time.sleep(0.02)

    assert job["status"] == "completed"
    assert job["document_id"] == document["id"]


def test_missing_resources_return_not_found(client):
    assert client.get("/documents/999").status_code == 404
    assert client.post("/documents/999/process").status_code == 404
    assert client.get("/jobs/999").status_code == 404


def test_metrics_are_exposed(client):
    client.get("/health")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text
