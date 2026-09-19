import random, csv, os

os.makedirs("shards", exist_ok=True)

FIRST = ["Aarav", "Arjun", "Aditya", "Rahul", "Rohan", "Vikram", "Priya", "Ananya"]
DOMAINS = ["example.com", "mail.com", "test.org"]

for shard_idx in range(8):
    random.seed(100 + shard_idx)
    n_rows = 50
    n_invalid = random.randint(2, 6)
    invalid_positions = set(random.sample(range(n_rows), n_invalid))

    rows = []
    for i in range(n_rows):
        name = random.choice(FIRST) + str(i)
        if i in invalid_positions:
            choice = random.choice(["bad_email", "missing_field"])
            if choice == "bad_email":
                email = name + "AT" + random.choice(DOMAINS)
            else:
                email = ""
        else:
            email = f"{name}@{random.choice(DOMAINS)}"
        rows.append([name, email])

    path = f"shards/shard_{shard_idx}.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "email"])
        w.writerows(rows)
    print(f"{path}: {n_invalid} seeded invalid rows")
