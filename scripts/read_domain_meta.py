import argparse
from pathlib import Path

from domain_config import load_domain_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="data/domain.yaml")
    parser.add_argument("--field", choices=["domain", "brand_name"], default="domain")
    parser.add_argument("--github-output", action="store_true")
    args = parser.parse_args()

    cfg = load_domain_config(Path(args.config))
    value = cfg.get(args.field, "")

    if args.github_output:
        key = args.field
        print(f"{key}={value}")
    else:
        print(value)


if __name__ == "__main__":
    main()
