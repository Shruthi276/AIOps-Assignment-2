# AIOps Module 3 — Infrastructure & Containerization

A spam-detection REST API (TF-IDF + Naive Bayes) containerized and deployed four ways:
Docker multi-stage builds, Docker Compose with Redis caching, a Kubernetes Indexed Job
for batch validation, and a Kubernetes Deployment with self-healing/rolling updates.

Each question folder is self-contained, with its own `app/` subfolder holding the exact
version of the code, model, and dependencies that question needs.

## Repo structure

```
.
├── 2-page-writeup.pdf          # 2-page report
├── q1/
│   ├── app/
│   │   ├── app.py              # Flask API: /predict, /healthz
│   │   ├── generate_dataset.py # generates spam_dataset.csv
│   │   ├── train.py            # trains TF-IDF + Naive Bayes, saves model.joblib
│   │   ├── model.joblib
│   │   ├── spam_dataset.csv
│   │   └── requirements.txt
│   ├── Dockerfile              # naive, single-stage build
│   └── Dockerfile.multi        # multi-stage build
├── q2/
│   ├── app/
│   │   ├── app.py              # adds Redis cache check before predicting
│   │   ├── model.joblib
│   │   └── requirements.txt
│   ├── Dockerfile              # multi-stage, reused from Q1
│   └── docker-compose.yml      # api + cache (redis:7-alpine) services
├── q3/
│   ├── generate_shards.py      # generates 8 seeded CSV shards
│   ├── shards/shard_0..7.csv
│   ├── ground_truth.txt        # expected invalid-row count per shard
│   ├── validator.py            # runs inside each pod, validates one shard
│   ├── Dockerfile
│   ├── job.yaml                # Indexed Job manifest
│   ├── collect_results.py      # reads pod logs via Kubernetes API
│   └── results.csv
└── q4/
    ├── app/
    │   ├── app.py              # adds VERSION to /healthz
    │   ├── model.joblib
    │   └── requirements.txt
    ├── Dockerfile               # sets ENV APP_VERSION
    ├── deployment.yaml
    └── service.yaml
```

## Prerequisites

- Docker (Docker Engine or Docker Desktop)
- Python 3.11, `venv`
- minikube + `kubectl` (for Q3 and Q4)


## API contract (Q1, Q2, Q4)

`POST /predict` — `{"text": "..."}` → `{"label": "spam"|"ham"}`
`GET /healthz` — `{"status": "ok"}` (Q4 also returns `"version"`)

---

## Question 1 — Naive vs. Multi-Stage Docker Build

Generate the dataset and train the model first:

```bash
cd q1/app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 generate_dataset.py   # writes spam_dataset.csv
python3 train.py              # writes model.joblib
```

Build and compare both images:

```bash
cd q1
docker build -f Dockerfile -t spam-api-single .
docker build -f Dockerfile.multi -t spam-api-multi .
docker images | grep spam-api
```

- **`Dockerfile`** (naive): single stage on full `python:3.11`.
- **`Dockerfile.multi`**: `python:3.11-slim` builder installs dependencies to
  `/install`; a fresh `python:3.11-slim` final stage copies only that directory in,
  discarding the build layer entirely.

**Result:** naive 2.09 GB → multi-stage 678 MB (~67.6% smaller).

Run either image locally:

```bash
docker run -d -p 5000:5000 spam-api-multi
curl http://localhost:5000/healthz
curl -X POST http://localhost:5000/predict -H "Content-Type: application/json" \
  -d '{"text": "WIN a FREE iPhone now!"}'
```

---

## Question 2 — Docker Compose + Redis Caching

`app.py` checks Redis (`cache` service) before running inference; on a miss it computes
and stores the prediction with a 300s TTL, on a hit it returns the cached label.

```bash
cd q2
docker compose up -d --build
docker compose ps
```

Test cache behavior (identical request twice):

```bash
curl -X POST http://localhost:5000/predict -H "Content-Type: application/json" \
  -d '{"text": "..."}'   # {"cached": false, ...}
curl -X POST http://localhost:5000/predict -H "Content-Type: application/json" \
  -d '{"text": "..."}'   # {"cached": true, ...} — served from Redis
```

Measured: cache miss ~1.33s, cache hit ~0.15s (~9x faster).

```bash
docker compose down
```

---

## Question 3 — Kubernetes Indexed Job (Parallel Shard Validation)

An unrelated batch workload: 8 synthetic user-signup CSV shards, each with a known,
seeded number of invalid email rows. An Indexed Job runs 8 pods, one per shard, each
reporting its invalid-row count.

```bash
cd q3
python3 -m venv venv && source venv/bin/activate
pip install kubernetes pandas

python3 generate_shards.py | tee ground_truth.txt   # writes shards/shard_0..7.csv

minikube start --nodes=2 --cpus=2 --memory=4096 --driver=docker
kubectl get nodes -o wide

docker build -t shard-validator:1.1 .
minikube image load shard-validator:1.1
minikube ssh -n minikube     "sudo crictl images | grep shard-validator"
minikube ssh -n minikube-m02 "sudo crictl images | grep shard-validator"

kubectl apply -f job.yaml
kubectl get pods -o wide -w       
kubectl get job shard-validator    # COMPLETIONS 8/8

python3 collect_results.py --job-name shard-validator --out results.csv
```

**Design choices:**
- `parallelism: 4`, `completions: 8` — 2 nodes × 2 CPUs = 4 CPUs; each pod requests/limits
  1 CPU, so 4 is the real concurrency ceiling and the Job runs in two waves of 4.
- Results are collected via the Kubernetes API (pod logs)

Cleanup:

```bash
kubectl delete job shard-validator
minikube stop
```

---

## Question 4 — Kubernetes Deployment (Self-Healing & Rolling Update)

Deploys the spam-detection API as a 2-replica Deployment with a `readinessProbe` on
`/healthz`, exposed via a `NodePort` Service.

```bash
cd q4
minikube image build -t spam-api:1.0 -f Dockerfile --all .
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl get pods -o wide
```

**Self-healing:**

```bash
kubectl delete pod <pod-name>
kubectl get pods -l app=spam-api -w   # replacement pod appears at age 0s
```

**Rolling update** (bumps `APP_VERSION` via the Dockerfile, visible in `/healthz`):

```bash
# edit Dockerfile: ENV APP_VERSION=1.1
minikube image build -t spam-api:1.1 -f Dockerfile --all .

# terminal 1 — no-downtime check
while true; do curl -s $(minikube service spam-api-svc --url)/healthz; echo; sleep 1; done

# terminal 2
kubectl set image deployment/spam-api spam-api=spam-api:1.1
kubectl rollout status deployment/spam-api
kubectl rollout history deployment/spam-api
```

Cleanup:

```bash
kubectl delete -f deployment.yaml -f service.yaml
minikube stop
```

---

## AI Disclosure & Academic Integrity



### 1. Which tools were used:
- **ChatGPT (OpenAI)**
- **Claude (Anthropic)**

### 2. How they were used:
- **Question 1 (Debugging & Troubleshooting):** Used ChatGPT to diagnose an initial Docker image build failure where the build process was killed with a *"process exited from signal 9"* error. ChatGPT helped interpret the root cause as container memory/resource starvation and suggested practical Docker build memory and layer optimization steps to build the single-stage and multi-stage images successfully.
- **Question 2 (Boilerplate Generation & Syntax Reference):** Used ChatGPT and Claude for standard boilerplate syntax in `app.py` to integrate the Redis caching layer (checking key existence, computing on cache miss, setting TTL, and returning cached payloads on cache hit) as well as the standard service configuration structure in `docker-compose.yml`.
- **Question 3 (Boilerplate Generation & Syntax Reference):** Used Claude to assist with boilerplate logic for the deterministic CSV shard generation script (`generate_shards.py`), the syntax for `topologySpreadConstraints` in `job.yaml`, and standard API client boilerplate in `collect_results.py` using the official `kubernetes` Python SDK to retrieve pod logs.
- **Question 4 (Boilerplate Generation & Conceptual Clarification):** Used Claude to draft standard Kubernetes Deployment and Service manifest boilerplate (`deployment.yaml`, `service.yaml`) and clarify the pattern for returning dynamic version strings from `/healthz` to make zero-downtime rolling updates observable and verifiable during `kubectl rollout`.

### 3. Impact:
The AI tools helped accelerate boilerplate creation, resolve an infrastructure resource termination error during Docker build, and provide rapid syntax references for Kubernetes API client scripting and manifest configuration. All code, manifests, and benchmark measurements were executed, tested, and validated locally, maintaining full transparency and comprehension across the entire deployment lifecycle.

