import os, yaml
_CFG = None
def load():
    global _CFG
    if _CFG is None:
        here = os.path.dirname(__file__)
        with open(os.path.join(here, "config.yaml"), "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        with open(os.path.join(here, "mesh", "config.yaml"), "r", encoding="utf-8") as f:
            cfg["mesh"] = yaml.safe_load(f)
        _CFG = cfg
    return _CFG
