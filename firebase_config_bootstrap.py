import os
import json
from typing import Optional, Dict

def _read_facturas_config(config_path: str) -> Dict:
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = data.get("facturas_config", {})
        if isinstance(cfg, str):
            try:
                cfg = json.loads(cfg)
            except Exception:
                cfg = {}
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}

def _write_facturas_config(config_path: str, cfg: Dict):
    data: Dict = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["facturas_config"] = cfg
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def ensure_firebase_config(parent=None, config_path: str = "facturas_config") -> Optional[Dict]:
    ...
    """
    Devuelve dict con {'service_account_json': path} si ya hay config válida o el usuario la selecciona.
    Si el usuario cancela o falta el diálogo, devuelve None.
    """
    cfg = _read_facturas_config(config_path)
    cred_path = cfg.get("firebase_credentials_path", "")
    if cred_path and os.path.exists(cred_path):
        return {"service_account_json": cred_path}

    try:
        import firebase_config_dialog
    except Exception:
        return None

    # Pequeño proxy de settings para reutilizar el diálogo
    class _ConfigProxy:
        def get_setting(self, key, default=None):
            if key == "facturas_config":
                return _read_facturas_config(config_path)
            return default
        def set_setting(self, key, value):
            if key == "facturas_config":
                _write_facturas_config(config_path, value)

    proxy = _ConfigProxy()
    accepted = firebase_config_dialog.show_firebase_config_dialog(parent, controller=proxy)
    if not accepted:
        return None

    cfg = _read_facturas_config(config_path)
    cred_path = cfg.get("firebase_credentials_path", "")
    if cred_path and os.path.exists(cred_path):
        return {"service_account_json": cred_path}
    return None