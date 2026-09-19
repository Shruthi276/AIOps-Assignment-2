import csv, os, re, json,time

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def main():
    completion_index = int(os.environ.get("JOB_COMPLETION_INDEX", "0"))
    pod_name = os.environ.get("POD_NAME", "unknown")
    node_name = os.environ.get("NODE_NAME", "unknown")

    shard_path = f"/data/shard_{completion_index}.csv"
    invalid, total = 0, 0
    with open(shard_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            email = row.get("email", "")
            if not email or not EMAIL_RE.match(email):
                invalid += 1

    result = {
        "completion_index": completion_index,
        "total_rows": total,
        "invalid_rows": invalid,
        "pod_name": pod_name,
        "node_name": node_name,
    }
    time.sleep(int(os.environ.get("SLEEP_SECONDS", "0")))  
    print("RESULT_JSON:" + json.dumps(result), flush=True)

if __name__ == "__main__":
    main()
