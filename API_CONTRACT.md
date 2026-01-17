# Chalk Processor API Contract

This document outlines the API endpoints for the Chalk Processor service. The service allows users to upload images of chalkboards, which are then processed to extract content, generate stylized variations ("Ugly", "Pretty"), and generate descriptive text ("Slop").

## Base URL
`https://chalk-pyserver.onrender.com` (Production)
`http://localhost:5001` (Local)

## Endpoints

### 1. Health Check
Checks if the API service is running.

- **URL:** `/`
- **Method:** `GET`
- **Response:**
  - **Code:** `200 OK`
  - **Content-Type:** `application/json`
  - **Body:**
    ```json
    {
      "status": "ok",
      "message": "Chalk Processor API is running"
    }
    ```

### 2. Initiate Extraction (Async Job)
Uploads an image for asynchronous background processing. This endpoint is idempotent if `roomId` is provided.

- **URL:** `/extract` (or `/process`)
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Parameters:**
  - `image` (Required, File): The image file to be processed (e.g., JPEG, PNG).
  - `roomId` (Optional, String): A unique identifier for the room (e.g., "01-114"). **Used for idempotency.**
  - `semester` (Optional, String): A string identifier for the semester (e.g., "Spring 2026").
  - `id` (Optional, String): A client-provided UUID for the scan.
- **Response (New Job Started):**
  - **Code:** `202 Accepted`
  - **Content-Type:** `application/json`
  - **Body:**
    ```json
    {
      "status": "queued",
      "scan_id": "c62143e4-66a3-42f1-807d-304b08705d9f",
      "roomId": "01-114",
      "original_url": "https://...",
      "message": "Processing started in background."
    }
    ```
- **Response (Already Exists - Idempotent):**
  - **Code:** `200 OK`
  - **Content-Type:** `application/json`
  - **Body:** Returns the completed record immediately.
    ```json
    {
      "status": "completed",
      "scan_id": "c62143e4-...",
      "roomId": "01-114",
      "chalkImage": "https://...",
      "prettifyImage": "https://...",
      "uglifyImage": "https://...",
      "sloppifyText": "..."
    }
    ```
- **Error:**
  - **Code:** `400 Bad Request` (`{"error": "No image file provided"}`)
  - **Code:** `500 Internal Server Error`

### 3. Get Scan Status (Polling)
Polls the status of a specific scan job.

- **URL:** `/scans/<scan_id>`
- **Method:** `GET`
- **URL Parameters:**
  - `scan_id` (Required, String): The UUID of the scan to retrieve.
- **Response:**
  - **Success:**
    - **Code:** `200 OK`
    - **Content-Type:** `application/json`
    - **Body:**
      ```json
      {
        "scan_id": "c62143e4-66a3-42f1-807d-304b08705d9f",
        "roomId": "01-114",
        "status": "completed", 
        "chalkImage": "https://.../processed/....jpg",
        "prettifyImage": "https://.../processed/....jpg",
        "uglifyImage": "https://.../processed/....jpg",
        "sloppifyText": "A detailed description of the chalkboard content...",
        "original_url": "https://.../originals/....jpg",
        "semester": "Spring 2026"
      }
      ```
      *Note: `status` values can be `queued`, `extracted`, `completed`, or `failed`.*
  - **Error:**
    - **Code:** `404 Not Found`

## Data Schema (Supabase `chalk_scans` table)

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID | Primary Key (scan_id) |
| `room_id` | Text | External identifier (e.g., "01-114") |
| `original_url` | Text | Public URL of the uploaded raw image |
| `processed_url`| Text | Public URL of the extracted chalk content (Mapped to `chalkImage`) |
| `ugly_url` | Text | Public URL of the "deep fried" version (Mapped to `uglifyImage`) |
| `pretty_url` | Text | Public URL of the AI-reimagined version (Mapped to `prettifyImage`) |
| `slop_text` | Text | Generated descriptive text (Mapped to `sloppifyText`) |
| `status` | Text | Current processing status |
| `semester` | Text | Metadata |