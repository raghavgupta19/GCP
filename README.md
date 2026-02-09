# Cloud Run Practical Assignment

**Objective:**
Demonstrate proficiency in Linux shell scripting, containerization, and deploying a serverless application to **Google Cloud Run**.

---

## Project Structure

```
deploy_app/
│
├─ sys_check.sh          # Linux system check script
├─ main.py               # Flask web application
├─ requirements.txt      # Python dependencies
├─ Dockerfile            # Container definition
└─ .dockerignore         # Files/folders to ignore in Docker build
```

---

## Task 1: Linux & Shell Scripting

**sys_check.sh** script does the following:

1. Outputs current date/time, disk usage, and logged-in user to `log.txt`.
2. Checks if a directory `deploy_app` exists; if not, creates it.
3. Moves `log.txt` into `deploy_app`.

**Commands to run script:**

```bash
cd ~/deploy_app
chmod +x sys_check.sh        # Make script executable
./sys_check.sh                # Run script
cat deploy_app/log.txt        # Check the log file
```

---

## Task 2: Python Flask Application

* **main.py**: Basic Flask app that returns:

```
Hello from Cloud Run! System check complete.
```

* **requirements.txt**:

```
Flask==3.1.2
gunicorn==25.0.3
blinker==1.9.0
click==8.3.1
itsdangerous==2.2.0
Jinja2==3.1.6
MarkupSafe==3.0.3
packaging==26.0
Werkzeug==3.1.5
```

**Test Flask app locally:**

```bash
source venv/bin/activate            # Activate virtual environment
export FLASK_APP=main.py
flask run --host=0.0.0.0 --port=8080
```

* Open `http://127.0.0.1:8080` in browser to verify.

---

## Task 3: Containerization (Docker)

**Dockerfile example:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["gunicorn", "-b", ":8080", "main:app"]
```

**Build Docker image locally:**

```bash
docker build -t hello-cloud-run .
```

**Test Docker container locally:**

```bash
docker run -p 8080:8080 hello-cloud-run
```

* Open `http://localhost:8080` to verify.

---

## Task 4: Deploy to Google Cloud Run

### Step 1: Authenticate & Configure GCloud

```bash
gcloud auth login                           # Login to your Google account
gcloud config set project [PROJECT-ID]      # Set your Google Cloud project
gcloud auth configure-docker               # Authenticate Docker with GCP
```

> Replace `[PROJECT-ID]` with your project ID (no brackets).

---

### Step 2: Build & Push Docker Image to GCR

```bash
gcloud builds submit --tag gcr.io/[PROJECT-ID]/hello-cloud-run
```

* Cloud Build will build and push your Docker image to **Google Container Registry**.

---

### Step 3: Deploy to Cloud Run

```bash
gcloud run deploy hello-cloud-run \
  --image gcr.io/[PROJECT-ID]/hello-cloud-run \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

* After deployment, you will get a **Service URL**, e.g.:

```
https://hello-cloud-run-16968455824.us-central1.run.app
```

* Open the URL in a browser or test with:

```bash
curl https://hello-cloud-run-16968455824.us-central1.run.app
```

* It should return: `Hello from Cloud Run! System check complete.`

---

* Open the Live URL in a browser for a demo:

```
https://raghav-gupta-16968455824.us-central1.run.app
```

* You should see: `Hello from Cloud Run! System check complete.`

---
## Task 5: Extended Flask Endpoint (/analyze)

The `/analyze` endpoint returns dynamic system metrics as JSON:

**Example JSON response:**
```json
{
  "timestamp": "2026-02-09T05:30:12Z",
  "uptime_seconds": 3600,
  "cpu_metric": 23.5,
  "memory_metric": 512,
  "health_score": 85,
  "message": "All systems normal"
}
```
## Testing

1. Run Flask app locally to verify endpoints.
2. Build Docker image and test container locally.
3. Deploy to Cloud Run.
4. Verify `/` and `/analyze` endpoints using curl or browser.

## Deliverables

1. `sys_check.sh` — Linux system check script
2. `main.py` — Flask web app
3. `requirements.txt` — Python dependencies
4. `Dockerfile` — Container definition
5. **Service URL** — Cloud Run live link
