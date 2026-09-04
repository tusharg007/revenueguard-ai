import argparse
import json
from collections import Counter

from data.generator import SyntheticDataGenerator


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic payment failure events")
    parser.add_argument("--output", type=str, default="data/test_batch.json", help="Output JSON file path")
    parser.add_argument("--count", type=int, default=523, help="Number of events to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    gen = SyntheticDataGenerator(seed=args.seed, num_events=args.count)
    gen.save_batch(args.output)

    with open(args.output, encoding="utf-8") as f:
        events = json.load(f)

    recoverable = sum(1 for e in events if e["ground_truth"]["is_recoverable"])
    total_amount = sum(e["amount_paise"] for e in events)
    event_types = Counter(e["event_type"] for e in events)
    methods = Counter(e["metadata"]["payment_method"] for e in events)

    print(f"Saved {len(events)} events to {args.output}")
    print(f"Recoverable: {recoverable} ({recoverable / len(events) * 100:.1f}%)")
    print(f"Revenue at risk: INR {total_amount / 100:,.0f}")
    print(f"Event types: {dict(event_types)}")
    print(f"Payment methods: {dict(methods)}")


if __name__ == "__main__":
    main()
