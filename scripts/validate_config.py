from pathlib import Path
import sys

from domain_config import parse_simple_yaml


def fail(msg: str):
    print(f"ERROR: {msg}")
    sys.exit(1)


def require_keys(obj: dict, keys: list[str], prefix: str):
    for k in keys:
        if k not in obj or obj[k] in (None, "", []):
            fail(f"Missing required key: {prefix}{k}")


def main():
    domain_path = Path("data/domain.yaml")
    theme_path = Path("data/theme.yaml")

    if not domain_path.exists():
        fail("data/domain.yaml not found")
    if not theme_path.exists():
        fail("data/theme.yaml not found")

    domain = parse_simple_yaml(domain_path)
    theme = parse_simple_yaml(theme_path)

    require_keys(domain, ["domain", "brand_name", "niche", "country", "language", "audience"], "domain.")
    require_keys(domain, ["homepage", "seo", "cta", "analytics", "content"], "domain.")
    require_keys(domain.get("analytics", {}), ["ga_measurement_id", "event_name", "event_category"], "domain.analytics.")
    require_keys(domain.get("content", {}), ["article_tone", "image_style_hints", "article_cta"], "domain.content.")

    require_keys(theme, ["palette", "background", "effects", "button_style", "card_style"], "theme.")

    print("Config validation passed")


if __name__ == "__main__":
    main()
