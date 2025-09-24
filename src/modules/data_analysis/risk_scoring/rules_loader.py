# rules_loader.py
from pathlib import Path
import yaml, hashlib

class RulesError(Exception):
    pass

def load_rules(path="rules.yml", require_targets=True):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"rules file not found: {p.resolve()}")

    text = p.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        raise RulesError(f"YAML parse error: {e}")

    if require_targets and "targets" not in data:
        raise RulesError("top-level 'targets' is required")

    data["_hash"] = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    data["_path"] = str(p.resolve())
    return data

def rules_version(meta: dict) -> str:
    return f'{meta.get("version","na")}#{meta.get("_hash","----")}'
