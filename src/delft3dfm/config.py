import os, yaml
_CFG = None
def load():
    global _CFG
    if _CFG is None:
        p = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(p, "r", encoding="utf-8") as f:
            _CFG = yaml.safe_load(f)
    return _CFG
