import argparse, json, re
import pandas as pd
from kubernetes import client, config

RESULT_LINE_RE = re.compile(r"RESULT_JSON:(\{.*\})")

def load_kube_config():
    try:
        config.load_kube_config()
    except Exception:
        config.load_incluster_config()

def collect(job_name, namespace="default"):
    load_kube_config()
    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod(namespace, label_selector=f"job-name={job_name}")
    rows = []
    for pod in pods.items:
        logs = v1.read_namespaced_pod_log(pod.metadata.name, namespace)
        match = RESULT_LINE_RE.search(logs)
        if not match:
            continue
        result = json.loads(match.group(1))
        result["k8s_pod_phase"] = pod.status.phase
        rows.append(result)
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("completion_index").reset_index(drop=True)
    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-name", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    df = collect(args.job_name)
    print(df.to_string(index=False))
    if args.out:
        df.to_csv(args.out, index=False)
