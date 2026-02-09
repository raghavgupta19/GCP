# GCP Multi-Page Form App

A simple multi-page web application hosted on a Google Cloud VM, with frontend and backend separated, that allows users to submit data which is stored in a Google Cloud Storage bucket. Built for learning GCP, VM management, service accounts, and cloud storage.

---

## Features

* Multi-page frontend with basic, responsive design
* Backend powered by Flask (Python)
* Data storage in a Google Cloud Storage (GCS) bucket
* Environment variables used for sensitive data
* Fully hosted on a single GCP VM instance
* Separate frontend and backend architecture

---

## Architecture

```
VM Instance (GCP)
├─ Frontend (Python HTTP Server, port 8080)
│  └─ HTML/CSS/JS files
└─ Backend (Flask, port 3000)
   └─ Handles form submissions
   └─ Stores data in GCS using service account
```

* **Frontend**: Serves HTML pages with a central form card design
* **Backend**: Receives POST requests, writes to GCS bucket
* **GCS Bucket**: Stores raw form submission data

---

## Prerequisites

* Google Cloud account (Free trial works)
* One GCP project
* One VM instance
* One GCS bucket
* Service account with Storage Object Admin role
* Python 3.11+ installed on VM

---

## Setup Instructions

1. **Clone Repository**

```bash
git clone git@github.com:YOUR_USERNAME/GCP.git
cd GCP
```

2. **Create Virtual Environment**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

3. **Set Environment Variables**

```bash
export GCS_BUCKET_NAME=<your-bucket-name>
```

4. **Run Backend**

```bash
python -m backend.api.app
```

* Runs on port `3000`

5. **Run Frontend** (in another terminal)

```bash
cd frontend
python3 -m http.server 8080
```

6. **Open in Browser**

```
http://<VM_EXTERNAL_IP>:8080/pages/index.html
```

---

## Folder Structure

```
webApp/
├─ backend/
│  ├─ api/
│  │  └─ app.py
│  ├─ services/
│  │  └─ storage.py
│  ├─ requirements.txt
│  └─ venv/
├─ frontend/
│  ├─ pages/
│  │  ├─ index.html
│  │  └─ form.html
│  └─ assets/
│     ├─ style.css
│     └─ app.js
└─ .env
```

---

## Environment Variables

* `GCS_BUCKET_NAME` – your Google Cloud Storage bucket name

---

## Notes

* Backend must be running for form submissions to work
* Frontend files must be served from the HTTP server
* To save GCP credits, **stop the VM** when not in use
* Data is append-only in the GCS bucket

---

## Screenshots
![Form Image UI](/Form.png)


---

## License

This project is for educational purposes and personal learning.
