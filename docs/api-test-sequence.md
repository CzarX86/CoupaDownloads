# API Test Sequence for Plan 39 Backend Services

This document provides manual testing sequences to validate the database-backed backend services implemented in Plan 39.

## Prerequisites

1. Start the FastAPI server:
```bash
cd /Users/juliocezar/Dev/work/CoupaDownloads
PYTHONPATH=src poetry run python -m server.pdf_training_app.main
```

2. The server will be available at `http://127.0.0.1:8008`

## Test Sequence 1: Health and System Status

### Health Check
```bash
curl -X GET "http://127.0.0.1:8008/api/pdf-training/health" -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-23T17:35:00.000Z"
}
```

### System Status
```bash
curl -X GET "http://127.0.0.1:8008/api/pdf-training/system-status" -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "document_count": 0,
  "job_count": 0,
  "timestamp": "2025-09-23T17:35:00.000Z"
}
```

## Test Sequence 2: Document Upload and Management

### Upload a Test PDF
```bash
curl -X POST "http://127.0.0.1:8008/api/pdf-training/documents" \
  -F "file=@test.pdf" \
  -F 'metadata={"ingested_by": "test", "source": "manual_test"}'
```

**Expected Response:** Document details with ID, versions, and annotations

### List Documents
```bash
curl -X GET "http://127.0.0.1:8008/api/pdf-training/documents" -H "Content-Type: application/json"
```

**Expected Response:** List containing the uploaded document

### Get Specific Document
```bash
curl -X GET "http://127.0.0.1:8008/api/pdf-training/documents/{document_id}" -H "Content-Type: application/json"
```

**Expected Response:** Detailed document information

## Test Sequence 3: Analysis and Annotation Workflow

### Start Document Analysis
```bash
curl -X POST "http://127.0.0.1:8008/api/pdf-training/documents/{document_id}/analyze" -H "Content-Type: application/json"
```

**Expected Response:** Job ID and status

### Check Job Status
```bash
curl -X GET "http://127.0.0.1:8008/api/pdf-training/jobs/{job_id}" -H "Content-Type: application/json"
```

**Expected Response:** Job details with current status

### Ingest Label Studio Export
```bash
curl -X POST "http://127.0.0.1:8008/api/pdf-training/documents/{document_id}/annotations/ingest" \
  -F "export_json=@label_studio_export.json"
```

**Expected Response:** Annotation details with completed status

## Test Sequence 4: Training Run

### Create Training Run
```bash
curl -X POST "http://127.0.0.1:8008/api/pdf-training/training-runs" \
  -H "Content-Type: application/json" \
  -d '{
    "document_ids": ["{document_id}"],
    "triggered_by": "manual_test"
  }'
```

**Expected Response:** Training job ID and status

### List All Jobs
```bash
curl -X GET "http://127.0.0.1:8008/api/pdf-training/jobs" -H "Content-Type: application/json"
```

**Expected Response:** List of all jobs with their statuses

## Test Sequence 5: Error Handling

### Invalid Document ID
```bash
curl -X GET "http://127.0.0.1:8008/api/pdf-training/documents/invalid_id" -H "Content-Type: application/json"
```

**Expected Response:** 404 error with "Document not found" message

### Invalid JSON Metadata
```bash
curl -X POST "http://127.0.0.1:8008/api/pdf-training/documents" \
  -F "file=@test.pdf" \
  -F "metadata=invalid_json"
```

**Expected Response:** 400 error with "Invalid JSON metadata" message

### Invalid Label Studio Export
```bash
curl -X POST "http://127.0.0.1:8008/api/pdf-training/documents/{document_id}/annotations/ingest" \
  -F "export_json=@invalid_export.json"
```

**Expected Response:** 400 error with validation message

## Validation Checklist

- [ ] Health endpoints return proper status
- [ ] Document upload creates proper database records
- [ ] Document listing shows uploaded documents
- [ ] Analysis job starts and updates status
- [ ] Annotation ingestion works with valid Label Studio export
- [ ] Training run creates job and updates database
- [ ] Error handling returns appropriate HTTP status codes
- [ ] All endpoints use database-backed services (no CSV dependencies)

## Database Verification

After running the tests, verify the database state:

```bash
PYTHONPATH=src poetry run python -m server.db.show_tables
```

Check that all expected tables have records:
- documents
- document_versions
- annotations
- jobs
- training_runs
- model_versions
- metrics

## Integration Test Run

Run the automated integration tests:

```bash
PYTHONPATH=src poetry run pytest tests/server/pdf_training_app/test_api.py -v
```

All tests should pass, confirming the database-backed backend services are working correctly.