import os
import json
import datetime
from typing import Optional, List, Dict, Any

# Intentamos usar firebase_admin (ya lo utilizas en migration_dialog indirectamente)
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage
    from google.cloud.firestore_v1 import FieldFilter
except Exception:
    firebase_admin = None
    credentials = None
    firestore = None
    storage = None
    FieldFilter = None


class LogicControllerFirebase:
    """
    Controlador que replica la interfaz del LogicControllerQt, pero usando
    Firebase Firestore como backend de datos.

    Se apoya en el archivo config.json, clave "facturas_config", que contiene:
      - firebase_credentials_path
      - firebase_project_id
      - firebase_storage_bucket
    """
    def __init__(
        self,
        config_path: str = "facturas_config",  # <- antes "config.json"
        service_account_json_path: Optional[str] = None,
        storage_bucket: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        self.config_path = config_path

        # Estado de Firebase
        self._firebase_app = None
        self._db = None          # Firestore client
        self._bucket = None      # Firebase Storage bucket

        # Estado de la app
        self.active_company_id: Optional[int] = None
        self.active_company_name: Optional[str] = None
        self.tx_filter: Optional[str] = None  # 'emitida' | 'gasto' | None

        # Si nos pasan la ruta del JSON (por bootstrap), persistirla antes de init
        if service_account_json_path:
            self._persist_firebase_credentials(
                cred_path=service_account_json_path,
                storage_bucket=storage_bucket,
                project_id=project_id,
            )

        # Inicializar Firebase
        self._init_firebase_from_settings()


    def _normalize_company_id(self, company_id_or_name) -> str:
        """
        Normaliza el company_id para asegurar consistencia.
        
        - Si recibe un número, lo convierte a string
        - Si recibe un nombre, busca el ID real en Firestore
        - Como fallback, sanitiza el nombre
        """
        if not company_id_or_name: 
            return ""
        
        # Si es número, convertir a string
        company_id_str = str(company_id_or_name)
        
        # Si es un número puro (ej: "1", "2"), buscar nombre real
        if company_id_str.isdigit():
            try:
                doc = self._db.collection("companies").document(company_id_str).get()
                if doc.exists:
                    company_name = doc.to_dict().get("name", "")
                    if company_name:
                        # Sanitizar nombre
                        company_id_str = company_name.lower().replace(" ", "_")
                        company_id_str = "". join(c for c in company_id_str if c.isalnum() or c == "_")
            except Exception as e:
                print(f"[NORMALIZE_ID] Error buscando empresa {company_id_str}: {e}")
        
        # Si ya es un nombre sanitizado, devolverlo
        if "_" in company_id_str or company_id_str.islower():
            return company_id_str
        
        # Sanitizar si es nombre sin sanitizar
        company_id_str = company_id_str.lower().replace(" ", "_")
        company_id_str = "".join(c for c in company_id_str if c.isalnum() or c == "_")
        
        return company_id_str

    def _get_timestamp(self):
        """
        Devuelve un timestamp de Firestore para usar en created_at/updated_at.
        """
        from google.cloud import firestore
        return firestore.SERVER_TIMESTAMP


    def _persist_firebase_credentials(
        self,
        cred_path: str,
        storage_bucket: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> None:
        """Guarda en config.json (clave facturas_config) la ruta de credenciales y opcionalmente bucket y project_id."""
        try:
            data: Dict[str, Any] = {}
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}

            cfg = data.get("facturas_config", {})
            if isinstance(cfg, str):
                try:
                    cfg = json.loads(cfg)
                except Exception:
                    cfg = {}
            if not isinstance(cfg, dict):
                cfg = {}

            cfg["firebase_credentials_path"] = cred_path

            # Si no viene project_id, intentar leerlo del JSON
            if not project_id:
                try:
                    with open(cred_path, "r", encoding="utf-8") as f:
                        cred = json.load(f)
                        project_id = cred.get("project_id")
                except Exception:
                    project_id = None
            if project_id:
                cfg["firebase_project_id"] = project_id

            if storage_bucket:
                cfg["firebase_storage_bucket"] = storage_bucket

            data["facturas_config"] = cfg
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[FIREBASE] No se pudo guardar credenciales en config: {e}")

    # ------------------------------------------------------------------ #
    # Inicialización Firebase (Firestore + Storage)
    # ------------------------------------------------------------------ #
    def _init_firebase_from_settings(self):
        """Inicializa Firestore y Storage usando la configuración de 'facturas_config'."""
        if firebase_admin is None or credentials is None or firestore is None:
            print("[FIREBASE] firebase_admin no está disponible. Instala firebase-admin.")
            return

        raw = self.get_setting("facturas_config", {})
        if isinstance(raw, str):
            try:
                cfg = json.loads(raw)
            except Exception:
                cfg = {}
        elif isinstance(raw, dict):
            cfg = raw
        else:
            cfg = {}

        cred_path = cfg.get("firebase_credentials_path")
        project_id = cfg.get("firebase_project_id")
        storage_bucket = cfg.get("firebase_storage_bucket")  # puede ser None

        if not cred_path or not os.path.exists(cred_path):
            print("[FIREBASE] credenciales no configuradas o archivo no existe.")
            return

        if not project_id:
            # Intentar leer project_id desde el JSON de credenciales
            try:
                with open(cred_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    project_id = data.get("project_id")
            except Exception:
                project_id = None

        if not project_id:
            print("[FIREBASE] project_id no definido; no se puede inicializar Firebase.")
            return

        try:
            if not self._firebase_app:
                cred = credentials.Certificate(cred_path)
                options = {
                    "projectId": project_id,
                }
                if storage_bucket:
                    options["storageBucket"] = storage_bucket
                self._firebase_app = firebase_admin.initialize_app(cred, options)

            # Firestore
            self._db = firestore.client()

            # Storage
            if storage is not None:
                try:
                    if storage_bucket:
                        self._bucket = storage.bucket(storage_bucket)
                    else:
                        self._bucket = storage.bucket()
                except Exception:
                    self._bucket = None
            else:
                self._bucket = None

        except Exception:
            self._db = None
            self._bucket = None

    # ------------------------------------------------------------------ #
    # Settings (compatibles con LogicControllerQt)
    # ------------------------------------------------------------------ #
    def get_setting(self, key: str, default=None):
        """Lee una clave del config.json. Se usa especialmente 'facturas_config'."""
        if not os.path.exists(self.config_path):
            return default
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return cfg.get(key, default)
        except Exception:
            return default

    def set_setting(self, key: str, value):
        """Escribe una clave en config.json. Si ya existe el archivo, se mergea."""
        data: Dict[str, Any] = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[key] = value
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def on_firebase_config_updated(self):
        """Llamado desde la UI moderna después de cambiar la configuración."""
        self._firebase_app = None
        self._db = None
        self._bucket = None
        self._init_firebase_from_settings()

    # ------------------------------------------------------------------ #
    # API esperada por ModernMainWindow
    # ------------------------------------------------------------------ #
    # Empresas
    # ------------------------------------------------------------------ #
    def list_companies(self) -> List[str]:
        """Devuelve solo los nombres de empresas, para poblar el combo del sidebar."""
        companies = self.get_companies()
        return [c.get("name", "") for c in companies]

    def get_companies(self) -> List[Dict[str, Any]]:
        """
        Recupera todas las empresas como lista de dicts desde la colección
        'companies' de Firestore.
        """
        if self._db is None:
            print("[FIREBASE] Firestore no está inicializado.")
            return []

        results: List[Dict[str, Any]] = []
        try:
            docs = self._db.collection("companies").order_by("name").stream()
            for doc in docs:
                data = doc.to_dict() or {}
                try:
                    data["id"] = int(doc.id)
                except Exception:
                    data["id"] = doc.id
                results.append(data)
        except Exception:
            pass
        return results

    def get_all_companies(self) -> List[Dict[str, Any]]:
        """Alias para compatibilidad."""
        return self.get_companies()

    def set_active_company(self, name: str) -> None:
        """
        Establece la empresa activa dado su nombre (viene del combo).
        """
        self.active_company_name = name or None
        self.active_company_id = None

        if not name or self._db is None:
            return

        try:
            if FieldFilter is None:
                # fallback a where clásico si no está disponible
                q = self._db.collection("companies").where("name", "==", name).limit(1)
            else:
                q = (
                    self._db.collection("companies")
                    .where(filter=FieldFilter("name", "==", name))
                    .limit(1)
                )
            docs = list(q.stream())
            if docs:
                try:
                    self.active_company_id = int(docs[0].id)
                except Exception:
                    self.active_company_id = docs[0].id
        except Exception as e:
            print(f"[FIREBASE] Error estableciendo empresa activa: {e}")

    # ------------------------------------------------------------------ #
    # Filtros / años disponibles
    # ------------------------------------------------------------------ #
    def set_transaction_filter(self, tx_type: Optional[str]) -> None:
        """Guarda el filtro actual de transacciones ('emitida'|'gasto'|None)."""
        self.tx_filter = tx_type

    def get_unique_invoice_years(self, company_id=None) -> List[int]:
            """
            Devuelve los años distintos en los que hay facturas para la empresa activa.
            Lee siempre invoice_date (string o timestamp). CORREGIDO PARA DATETIME DE FIREBASE.
            """
            if self._db is None:
                return []

            company = company_id or self.active_company_id
            if not company:
                return []

            years = set()
            try:
                if FieldFilter is None:
                    q = self._db.collection("invoices").where("company_id", "==", company)
                else:
                    q = self._db.collection("invoices").where(
                        filter=FieldFilter("company_id", "==", company)
                    )
                docs = list(q.stream())

                # --- CORRECCIÓN: Función de normalización robusta ---
                def _norm_date(v) -> Optional[datetime.date]:
                    if v is None:
                        return None
                    # Duck typing: si tiene método .date() (cubre DatetimeWithNanoseconds y datetime)
                    if hasattr(v, "date") and callable(v.date):
                        return v.date()
                    # Si ya es date
                    if isinstance(v, datetime.date):
                        return v
                    # Intentar parsear string
                    try:
                        s = str(v)
                        return datetime.datetime.strptime(s[:10], "%Y-%m-%d").date()
                    except Exception:
                        return None
                # ----------------------------------------------------

                for doc in docs:
                    data = doc.to_dict() or {}
                    d = _norm_date(data.get("invoice_date"))
                    if d is not None:
                        years.add(d.year)

            except Exception:
                return []

            return sorted(years, reverse=True)
    # ------------------------------------------------------------------ #
    # Dashboard: resumen y tabla
    # ------------------------------------------------------------------ #
    def _refresh_dashboard(self, month: Optional[str], year: Optional[int]) -> Dict[str, float]:
        """
        Calcula los KPIs del dashboard para la empresa activa usando Firestore.

        month: código de mes "01".."12" o None
        year: año como entero o None
        """
        if self._db is None or not self.active_company_id:
            return {
                "income": 0.0,
                "income_itbis": 0.0,
                "expense": 0.0,
                "expense_itbis": 0.0,
                "net_itbis": 0.0,
                "payable": 0.0,
                "itbis_adelantado": 0.0,
                "payable_estimated": 0.0,
            }

        invoices = self._query_invoices(
            self.active_company_id,
            month,
            year,
            tx_type=self.tx_filter,
        )

        emitted = [inv for inv in invoices if inv.get("invoice_type") == "emitida"]
        expenses = [inv for inv in invoices if inv.get("invoice_type") == "gasto"]

        total_ingresos = sum(float(inv.get("total_amount_rd", 0.0)) for inv in emitted)
        total_gastos = sum(float(inv.get("total_amount_rd", 0.0)) for inv in expenses)

        def _fx(inv:  Dict[str, Any]) -> float:
            try:
                rate = float(inv.get("exchange_rate", 1.0) or 1.0)
                return rate if rate != 0 else 1.0
            except Exception:
                return 1.0

        # ✅ CORRECCIÓN: El ITBIS ya está en RD$ después de nuestra corrección
        # Ya no necesitamos multiplicar por _fx(inv) porque el campo "itbis" 
        # ahora siempre está en RD$ gracias al fix en add_invoice()
        # Solo usamos itbis_rd si existe, sino fallback a itbis (que ya debería estar en RD$)
        itbis_ingresos = sum(
            float(inv.get("itbis_rd") or inv.get("itbis", 0.0) or 0.0) 
            for inv in emitted
        )
        itbis_gastos = sum(
            float(inv.get("itbis_rd") or inv.get("itbis", 0.0) or 0.0) 
            for inv in expenses
        )

        net_itbis = itbis_ingresos - itbis_gastos

        # ITBIS adelantado del mes/año actual (para esta empresa)
        itbis_adelantado = 0.0
        try:
            if hasattr(self, "get_itbis_adelantado_period") and month and year:
                itbis_adelantado = float(
                    self.get_itbis_adelantado_period(
                        self.active_company_id, month, year
                    )
                    or 0.0
                )
        except Exception: 
            itbis_adelantado = 0.0

        # ✅ CORRECCIÓN: A pagar estimado = neto - adelantado
        payable_estimated = net_itbis - itbis_adelantado

        # ✅ CORRECCIÓN: payable debe ser igual al estimado (no al neto)
        payable = payable_estimated

        return {
            "income": total_ingresos,
            "income_itbis": itbis_ingresos,
            "expense": total_gastos,
            "expense_itbis": itbis_gastos,
            "net_itbis": net_itbis,
            "payable": payable,
            "itbis_adelantado": itbis_adelantado,
            "payable_estimated": payable_estimated,
        }
        

    def _populate_transactions_table(
            self,
            month: Optional[str],
            year: Optional[int],
            tx_type: Optional[str],
        ) -> List[Dict[str, Any]]:
            """
            Devuelve la lista de transacciones normalizadas para poblar la tabla.
            """
            if self._db is None or not self.active_company_id:
                return []

            invoices = self._query_invoices(
                self.active_company_id,
                month,
                year,
                tx_type=tx_type,
            )

            # Reordenar por seguridad (aunque _query_invoices ya lo hace)
            def _norm_date_sort(v):
                if hasattr(v, "date") and callable(v.date): return v.date()
                if isinstance(v, datetime.date): return v
                return datetime.date(1970, 1, 1)

            invoices_sorted = sorted(invoices, key=lambda x: _norm_date_sort(x.get("invoice_date")), reverse=True)

            # --- CORRECCIÓN: Formateo seguro para display ---
            def _format_date_for_display(v) -> str:
                if v is None:
                    return ""
                # Duck typing para DatetimeWithNanoseconds y datetime
                if hasattr(v, "date") and callable(v.date):
                    return v.date().strftime("%Y-%m-%d")
                if isinstance(v, datetime.date):
                    return v.strftime("%Y-%m-%d")
                # String fallback
                s = str(v)
                return s[:10]
            # ------------------------------------------------

            rows: List[Dict[str, Any]] = []
            for inv in invoices_sorted:
                # ✅ NUEVO: Incluir campos de moneda original
                currency = inv.get("currency", "RD$")
                exchange_rate = float(inv.get("exchange_rate", 1.0) or 1.0)
                
                # Obtener valores originales si existen
                itbis_original = inv.get("itbis_original_currency")
                total_original = inv.get("total_amount_original_currency")
                
                # Si no existen campos originales y la moneda no es RD$, calcular desde RD$
                if itbis_original is None and currency not in ["RD$", "DOP", "RD", "DOP$"]:
                    itbis_rd = float(inv.get("itbis_rd") or inv.get("itbis", 0.0) or 0.0)
                    if exchange_rate > 0:
                        itbis_original = itbis_rd / exchange_rate
                    else:
                        itbis_original = 0.0
                elif itbis_original is None:
                    # Para RD$, usar el valor en RD$
                    itbis_original = float(inv.get("itbis_rd") or inv.get("itbis", 0.0) or 0.0)
                else:
                    itbis_original = float(itbis_original or 0.0)
                
                if total_original is None and currency not in ["RD$", "DOP", "RD", "DOP$"]:
                    total_rd = float(inv.get("total_amount_rd") or inv.get("total_amount", 0.0) or 0.0)
                    if exchange_rate > 0:
                        total_original = total_rd / exchange_rate
                    else:
                        total_original = 0.0
                elif total_original is None:
                    # Para RD$, usar el valor en RD$
                    total_original = float(inv.get("total_amount_rd") or inv.get("total_amount", 0.0) or 0.0)
                else:
                    total_original = float(total_original or 0.0)
                
                rows.append(
                    {
                        "date": _format_date_for_display(inv.get("invoice_date")),
                        "type": inv.get("invoice_type", ""),
                        "number": inv.get("invoice_number", ""),
                        "party": inv.get("third_party_name", ""),
                        "currency": currency,
                        "itbis": float(inv.get("itbis", 0.0)),
                        "itbis_original_currency": itbis_original,
                        "itbis_rd": float(inv.get("itbis_rd") or inv.get("itbis", 0.0) or 0.0),
                        "total": float(
                            inv.get("total_amount_rd", inv.get("total_amount", 0.0))
                        ),
                        "total_amount_original_currency": total_original,
                        "total_amount_rd": float(inv.get("total_amount_rd") or inv.get("total_amount", 0.0) or 0.0),
                    }
                )
            return rows
    def _query_invoices(
            self,
            company_id: int,
            month_str: Optional[str],
            year_int: Optional[int],
            tx_type: Optional[str] = None,
        ) -> List[dict]:
            """
            Devuelve lista de facturas para una empresa.
            CORREGIDO: Manejo seguro de DatetimeWithNanoseconds para evitar error de ordenamiento.
            """
            if self._db is None:
                return []

            try:
                col = self._db.collection("invoices")

                if FieldFilter is None:
                    q = col.where("company_id", "==", int(company_id))
                    if tx_type:
                        q = q.where("invoice_type", "==", tx_type)
                else:
                    q = col.where(
                        filter=FieldFilter("company_id", "==", int(company_id))
                    )
                    if tx_type:
                        q = q.where(
                            filter=FieldFilter("invoice_type", "==", tx_type)
                        )

                docs = list(q.stream())

                invoices: List[dict] = []
                for doc in docs:
                    data = doc.to_dict() or {}
                    data["id"] = doc.id
                    invoices.append(data)

                # --- CORRECCIÓN: Función de normalización robusta ---
                def _norm_date(v) -> datetime.date:
                    if v is None:
                        return datetime.date(1970, 1, 1)
                    # Duck typing: Funciona para DatetimeWithNanoseconds y datetime
                    if hasattr(v, "date") and callable(v.date):
                        return v.date()
                    # Si ya es date
                    if isinstance(v, datetime.date):
                        return v
                    # Fallback a string
                    try:
                        s = str(v)
                        return datetime.datetime.strptime(s[:10], "%Y-%m-%d").date()
                    except Exception:
                        return datetime.date(1970, 1, 1)
                # ----------------------------------------------------

                filtered: List[dict] = []
                for inv in invoices:
                    d_raw = inv.get("invoice_date")
                    d = _norm_date(d_raw)
                    
                    # Filtro por Año
                    if year_int is not None and d.year != year_int:
                        continue
                    
                    # Filtro por Mes
                    if month_str is not None:
                        try:
                            m_int = int(month_str)
                        except Exception:
                            m_int = None
                        if m_int is not None and d.month != m_int:
                            continue
                    filtered.append(inv)

                # Ordenar usando la fecha normalizada (evita comparar DatetimeWithNanoseconds vs str)
                filtered.sort(
                    key=lambda inv: _norm_date(inv.get("invoice_date")),
                    reverse=True,
                )

                return filtered

            except Exception as e:
                print(f"[FIREBASE-DASH] Error en _query_invoices: {e}")
                return []
    # ------------------------------------------------------------------ #
    # Diagnóstico / helpers
    # ------------------------------------------------------------------ #
    def diagnose_row(self, number: str):
        """Diagnóstico básico de una factura a partir de su invoice_number."""
        if self._db is None or not self.active_company_id or not number:
            print(
                f"[FIREBASE] diagnose_row: sin datos suficientes "
                f"(company={self.active_company_id}, number={number})"
            )
            return

        try:
            if FieldFilter is None:
                q = (
                    self._db.collection("invoices")
                    .where("company_id", "==", self.active_company_id)
                    .where("invoice_number", "==", number)
                    .limit(1)
                )
            else:
                q = (
                    self._db.collection("invoices")
                    .where(
                        filter=FieldFilter("company_id", "==", self.active_company_id)
                    )
                    .where(filter=FieldFilter("invoice_number", "==", number))
                    .limit(1)
                )
            docs = list(q.stream())
            if not docs:
                return
            inv = docs[0].to_dict() or {}
            print(
                f"[FIREBASE] Diagnóstico factura {number}: "
                f"{json.dumps(inv, indent=2, ensure_ascii=False)}"
            )
        except Exception as e:
            print(f"[FIREBASE] Error en diagnose_row: {e}")
    # ------------------------------------------------------------------ #
    # Alta de facturas en Firebase
    # ------------------------------------------------------------------ #
    def add_invoice(self, invoice_data: dict) -> tuple[bool, str]:
        """
        Crea una factura en la colección 'invoices'.
        
        ✅ NUEVO: Valida duplicados antes de guardar. 
        
        Normaliza: 
        - company_id
        - total_amount_rd
        - fechas (invoice_date / imputation_date / due_date)
        - invoice_year / invoice_month
        Y asegura el registro del tercero en 'third_parties'.
        """
        
        # ✅ DEBUG PASO 0: Datos crudos recibidos
        print("\n" + "="*80)
        print("🐛 DEBUG add_invoice - DATOS RECIBIDOS (CRUDOS)")
        print("="*80)
        for k, v in invoice_data.items():
            if k in ("total_amount", "factura_total", "itbis", "exchange_rate",
                      "total_amount_rd", "tasa_cambio", "company_id"):
                print(f"   {k} = {v!r}  (tipo: {type(v).__name__})")
        print("="*80)
        
        if self._db is None:
            return False, "Firestore no está inicializado."

        if not self.active_company_id and not invoice_data.get("company_id"):
            return False, "No hay empresa activa seleccionada."

        company_id = invoice_data.get("company_id") or self.active_company_id
        try:
            invoice_data["company_id"] = int(company_id)
        except Exception:
            invoice_data["company_id"] = company_id

        # ✅ VALIDACIÓN DE DUPLICADOS
        rnc = str(invoice_data.get("rnc") or invoice_data.get("client_rnc") or "").strip()
        invoice_number = str(invoice_data.get("invoice_number") or "").strip()
        
        # Calcular monto total en RD$ para comparación
        try:
            rate = float(invoice_data.get("exchange_rate", 1.0) or 1.0)
        except Exception:
            rate = 1.0
        try:
            total = float(invoice_data.get("total_amount", 0.0))
        except Exception:
            total = 0.0
        total_rd = total * (rate or 1.0)
        
        # ✅ DEBUG PASO 1: Cálculo de total_rd
        print("\n🐛 DEBUG PASO 1 - CÁLCULO total_rd:")
        print(f"   invoice_data['total_amount'] (raw) = {invoice_data.get('total_amount')!r}")
        print(f"   invoice_data['factura_total'] (raw) = {invoice_data.get('factura_total')!r}")
        print(f"   invoice_data['exchange_rate'] (raw) = {invoice_data.get('exchange_rate')!r}")
        print(f"   total (float) = {total}")
        print(f"   rate (float) = {rate}")
        print(f"   total_rd = total × rate = {total} × {rate} = {total_rd}")
        
        # ✅ PROTECCIÓN: Advertir si los montos parecen absurdos
        if total > 100_000_000:
            print(f"   ⚠️ ALERTA: total_amount = {total} parece MUY ALTO")
        if total_rd > 100_000_000:
            print(f"   ⚠️ ALERTA: total_rd = {total_rd} parece MUY ALTO")
        
        # Verificar si ya existe
        duplicate = self.check_duplicate_invoice(
            rnc=rnc,
            invoice_number=invoice_number,
            total_amount=total_rd,
            exclude_invoice_id=None,
        )
        
        if duplicate:
            # Construir mensaje de advertencia
            dup_company = duplicate.get("company_name", "Desconocida")
            dup_date = duplicate.get("invoice_date", "Desconocida")
            dup_type = duplicate.get("invoice_type", "")
            dup_third_party = duplicate.get("third_party_name", "Desconocido")
            
            tipo_str = "INGRESO" if dup_type == "emitida" else "GASTO" if dup_type == "gasto" else dup_type
            
            warning_msg = (
                f"⚠️ FACTURA DUPLICADA DETECTADA\n\n"
                f"Ya existe una factura con los mismos datos:\n\n"
                f"📄 NCF: {invoice_number}\n"
                f"🏢 RNC: {rnc}\n"
                f"💰 Monto: RD$ {total_rd:,.2f}\n\n"
                f"Registrada en:\n"
                f"• Empresa: {dup_company}\n"
                f"• Fecha: {dup_date}\n"
                f"• Tipo: {tipo_str}\n"
                f"• Tercero: {dup_third_party}\n\n"
                f"¿Desea continuar y guardar esta factura de todas formas?"
            )
            
            return False, warning_msg

        try:
            # total_amount_rd
            if "total_amount_rd" not in invoice_data:
                invoice_data["total_amount_rd"] = total_rd

            # ✅ DEBUG PASO 2: Antes de calcular ITBIS
            print("\n🐛 DEBUG PASO 2 - ANTES DE ITBIS:")
            print(f"   invoice_data['itbis'] (antes) = {invoice_data.get('itbis')!r}")
            print(f"   invoice_data['total_amount_rd'] = {invoice_data.get('total_amount_rd')!r}")

            # Calcular ITBIS en RD$ (multiplicar por tasa de cambio)
            try:
                itbis_original = float(invoice_data.get("itbis", 0.0))
                itbis_rd = itbis_original * rate
                
                # ✅ DEBUG PASO 3: Cálculo de ITBIS
                print("\n🐛 DEBUG PASO 3 - CÁLCULO ITBIS:")
                print(f"   itbis_original = {itbis_original}")
                print(f"   rate = {rate}")
                print(f"   itbis_rd = itbis_original × rate = {itbis_original} × {rate} = {itbis_rd}")
                
                # Guardar tanto el ITBIS original como el convertido
                invoice_data["itbis_original_currency"] = itbis_original
                invoice_data["itbis_rd"] = itbis_rd
                invoice_data["itbis"] = itbis_rd  # El campo principal ahora es en RD$
            except Exception as e:
                print(f"[FIREBASE] WARN calculando ITBIS: {e}")
                
            # Guardar total original también
            try:
                invoice_data["total_amount_original_currency"] = total
            except Exception:
                pass

            # ✅ DEBUG PASO 4: Valores finales ANTES de guardar
            print("\n🐛 DEBUG PASO 4 - VALORES FINALES ANTES DE GUARDAR:")
            print(f"   invoice_data['total_amount'] = {invoice_data.get('total_amount')!r}")
            print(f"   invoice_data['total_amount_rd'] = {invoice_data.get('total_amount_rd')!r}")
            print(f"   invoice_data['total_amount_original_currency'] = {invoice_data.get('total_amount_original_currency')!r}")
            print(f"   invoice_data['factura_total'] = {invoice_data.get('factura_total')!r}")
            print(f"   invoice_data['itbis'] = {invoice_data.get('itbis')!r}")
            print(f"   invoice_data['itbis_rd'] = {invoice_data.get('itbis_rd')!r}")
            print(f"   invoice_data['itbis_original_currency'] = {invoice_data.get('itbis_original_currency')!r}")
            print(f"   invoice_data['exchange_rate'] = {invoice_data.get('exchange_rate')!r}")
            print(f"   invoice_data['company_id'] = {invoice_data.get('company_id')!r}")
            print(f"   invoice_data['invoice_number'] = {invoice_data.get('invoice_number')!r}")
            
            # ✅ PROTECCIÓN: Verificación final de montos
            final_total = invoice_data.get('total_amount_rd') or invoice_data.get('total_amount') or 0
            final_itbis = invoice_data.get('itbis') or 0
            try:
                if float(final_total) > 100_000_000:
                    print(f"\n   ⚠️⚠️⚠️ ALERTA CRÍTICA: total_amount_rd = {final_total}")
                    print(f"   Esto parece un error. Revisa el origen de los datos.")
                if float(final_itbis) > 50_000_000:
                    print(f"\n   ⚠️⚠️⚠️ ALERTA CRÍTICA: itbis = {final_itbis}")
                    print(f"   Esto parece un error. Revisa el origen de los datos.")
            except Exception:
                pass

            # Normalizar fechas: date -> datetime
            def _normalize_date_field(key: str):
                val = invoice_data.get(key)
                if isinstance(val, datetime.date) and not isinstance(val, datetime.datetime):
                    invoice_data[key] = datetime.datetime(val.year, val.month, val.day)

            _normalize_date_field("invoice_date")
            _normalize_date_field("imputation_date")
            _normalize_date_field("due_date")

            # Derivar invoice_year / invoice_month
            inv_date = invoice_data.get("invoice_date")
            year_field = invoice_data.get("invoice_year")
            month_field = invoice_data.get("invoice_month")
            if inv_date and (year_field is None or month_field in (None, "")):
                y = m = None
                if isinstance(inv_date, datetime.datetime):
                    y, m = inv_date.year, inv_date.month
                elif isinstance(inv_date, datetime.date):
                    y, m = inv_date.year, inv_date.month
                else:
                    try:
                        s = str(inv_date)
                        y, m, _ = map(int, s[:10].split("-"))
                    except Exception:
                        y = m = None
                if y is not None and m is not None:
                    invoice_data["invoice_year"] = int(y)
                    invoice_data["invoice_month"] = f"{int(m):02d}"

            # Upsert de tercero
            name = str(invoice_data.get("third_party_name") or invoice_data.get("client_name") or "")
            try:
                if rnc or name:
                    self.add_or_update_third_party(rnc=rnc, name=name, updated_by="logic_firebase")
            except Exception as e:
                print(f"[FIREBASE] WARN upsert third_party: {e}")

            # ✅ DEBUG PASO 5: Justo antes de doc_ref.set()
            print("\n🐛 DEBUG PASO 5 - GUARDANDO EN FIRESTORE...")
            print(f"   Colección: invoices")
            print(f"   Cantidad de campos: {len(invoice_data)}")
            print("="*80 + "\n")

            # Guardar factura
            doc_ref = self._db.collection("invoices").document()
            doc_ref.set(invoice_data)
            
            print("✅ Factura guardada exitosamente en Firestore")
            print("="*80 + "\n")
            
            return True, "Factura registrada correctamente."
            
        except Exception as e:
            print(f"\n❌ ERROR guardando factura: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error al añadir factura en Firebase: {e}"        

    def check_duplicate_invoice(
        self,
        rnc: str,
        invoice_number: str,
        total_amount: float,
        exclude_invoice_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]: 
        """
        Verifica si ya existe una factura con el mismo RNC, NCF y monto. 
        
        Args:
            rnc: RNC del tercero
            invoice_number: Número de NCF de la factura
            total_amount: Monto total de la factura
            exclude_invoice_id: ID de factura a excluir (para ediciones)
        
        Returns:
            Dict con datos de la factura duplicada si existe, None si no hay duplicado
        """
        if not self._db:
            return None
        
        # Normalizar valores para comparación
        rnc = (rnc or "").strip().upper()
        invoice_number = (invoice_number or "").strip().upper()
        
        if not rnc or not invoice_number:
            return None
        
        try:
            # Buscar facturas con el mismo RNC y NCF
            col = self._db.collection("invoices")
            
            if FieldFilter is not None:
                q = (
                    col.where(filter=FieldFilter("rnc", "==", rnc))
                    .where(filter=FieldFilter("invoice_number", "==", invoice_number))
                )
            else:
                q = col.where("rnc", "==", rnc).where("invoice_number", "==", invoice_number)
            
            docs = list(q.stream())
            
            # Revisar montos (con tolerancia de ±0.01 para evitar problemas de redondeo)
            tolerance = 0.01
            
            for doc in docs:
                # Si estamos editando, excluir la factura actual
                if exclude_invoice_id and doc.id == str(exclude_invoice_id):
                    continue
                
                data = doc.to_dict() or {}
                
                # Obtener monto en RD$
                doc_amount = float(data.get("total_amount_rd", 0.0) or 0.0)
                if not doc_amount:
                    rate = float(data.get("exchange_rate", 1.0) or 1.0)
                    doc_amount = float(data.get("total_amount", 0.0) or 0.0) * rate
                
                # Comparar con tolerancia
                if abs(doc_amount - total_amount) <= tolerance:
                    # ¡Duplicado encontrado!
                    data["id"] = doc.id
                    
                    # Obtener nombre de empresa si es posible
                    company_id = data.get("company_id")
                    company_name = "Desconocida"
                    if company_id: 
                        try:
                            comp_doc = self._db.collection("companies").document(str(company_id)).get()
                            if comp_doc.exists:
                                company_name = (comp_doc.to_dict() or {}).get("name", "Desconocida")
                        except Exception:
                            pass
                    
                    data["company_name"] = company_name
                    return data
            
            return None
            
        except Exception as e:
            print(f"[FIREBASE-DUPLICATE] Error verificando duplicados: {e}")
            return None


    # ------------------------------------------------------------------ #
    # Firebase Storage: manejo de anexos
    # ------------------------------------------------------------------ #
    def upload_attachment_to_storage(
        self,
        local_path: str,
        company_id: str,
        invoice_number: str,
        invoice_date: Optional[datetime.date] = None,
        rnc: Optional[str] = None,
    ) -> Optional[str]:
        """
        Sube un archivo local a Firebase Storage.
        
        Args:
            local_path: Ruta absoluta del archivo local
            company_id: ID de la empresa
            invoice_number: Número de factura
            invoice_date: Fecha de la factura (para organizar por año/mes)
            rnc: RNC del tercero (opcional)
        
        Returns:
            str: Ruta en Storage (ej: 'Adjuntos/EMPRESA/2025/01/B010000584_132125177.jpg')
            None: Si falla
        
        Estructura en Storage:
            Adjuntos/{EMPRESA}/{YEAR}/{MONTH}/{INVOICE_NUMBER}_{RNC}.ext
        """
        if not self._bucket:
            print("[STORAGE] ❌ Bucket no inicializado")
            return None

        if not local_path or not os.path.exists(local_path):
            print(f"[STORAGE] ❌ Archivo no existe: {local_path}")
            return None

        try:
            # ========================================
            # 1. NOMBRE SEGURO DE EMPRESA
            # ========================================
            company_name = getattr(self, "active_company_name", None) or str(company_id or "company")
            
            safe_company = (
                "".join(c for c in company_name if c.isalnum() or c in (" ", "-", "_"))
                .strip()
                .replace(" ", "_")
            ) or "company"

            # ========================================
            # 2. AÑO Y MES
            # ========================================
            if isinstance(invoice_date, datetime.date):
                year = invoice_date.strftime("%Y")
                month = invoice_date.strftime("%m")
            elif isinstance(invoice_date, datetime.datetime):
                year = invoice_date.strftime("%Y")
                month = invoice_date.strftime("%m")
            else:
                # Fallback: fecha actual
                today = datetime.date.today()
                year = today.strftime("%Y")
                month = today.strftime("%m")

            # ========================================
            # 3. RNC SEGURO
            # ========================================
            rnc_val = (rnc or "").strip() or "noRNC"
            safe_rnc = "".join(c for c in rnc_val if c.isalnum() or c in ("-", "_")) or "noRNC"

            # ========================================
            # 4. NOMBRE DE ARCHIVO
            # ========================================
            filename = os.path.basename(local_path)
            ext = os.path.splitext(filename)[1].lower()

            invoice_part = (
                "".join(c for c in (invoice_number or "") if (c.isalnum() or c in ("-", "_")))
                or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            )
            
            file_name = f"{invoice_part}_{safe_rnc}{ext}"

            # ========================================
            # 5. RUTA EN STORAGE
            # ========================================
            object_name = f"Adjuntos/{safe_company}/{year}/{month}/{file_name}"
            object_name = object_name.replace("\\", "/")

            print(f"[STORAGE] 📤 Subiendo archivo...")
            print(f"   Local: {local_path}")
            print(f"   Storage: {object_name}")

            # ========================================
            # 6. SUBIR A STORAGE
            # ========================================
            blob = self._bucket.blob(object_name)
            blob.upload_from_filename(local_path)

            # Verificar tamaño
            file_size = os.path.getsize(local_path)
            print(f"   ✅ Subido exitosamente ({file_size / 1024:.1f} KB)")

            return object_name

        except Exception as e:
            print(f"[STORAGE] ❌ Error subiendo adjunto: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_attachment_download_url(self, storage_path: str) -> Optional[str]:
        """
        Obtiene URL de descarga para un archivo en Storage.
        
        Args:
            storage_path: Ruta en Storage (ej: 'Adjuntos/EMPRESA/2025/01/file.jpg')
        
        Returns:
            str: URL pública del archivo
            None: Si falla o el archivo no existe
        
        Nota:
            - Intenta usar URL pública si el blob es público
            - Si no es público, genera URL firmada (signed URL) válida por 1 hora
        """
        if not self._bucket or not storage_path:
            return None

        try:
            # Normalizar ruta
            sp = str(storage_path).strip().replace("\\", "/")
            
            blob = self._bucket.blob(sp)
            
            # Verificar que existe
            if not blob.exists():
                print(f"[STORAGE] ⚠️ Archivo no existe en Storage: {sp}")
                return None

            # ========================================
            # OPCIÓN 1: URL PÚBLICA (si el blob es público)
            # ========================================
            try:
                if blob.public_url:
                    return blob.public_url
            except:
                pass

            # ========================================
            # OPCIÓN 2: URL FIRMADA (Signed URL - válida por tiempo limitado)
            # ========================================
            try:
                import datetime
                from google.cloud.storage import Blob
                
                # URL válida por 1 hora
                expiration = datetime.timedelta(hours=1)
                
                signed_url = blob.generate_signed_url(
                    version="v4",
                    expiration=expiration,
                    method="GET"
                )
                
                return signed_url
                
            except Exception as e:
                print(f"[STORAGE] ⚠️ No se pudo generar signed URL: {e}")

            # ========================================
            # FALLBACK: Hacer público y devolver URL
            # ========================================
            try:
                blob.make_public()
                return blob.public_url
            except Exception as e:
                print(f"[STORAGE] ⚠️ No se pudo hacer público: {e}")
                return None

        except Exception as e:
            print(f"[STORAGE] ❌ Error obteniendo URL: {e}")
            return None



    def add_or_update_third_party(self, rnc: str, name: str, updated_by: str | None = None):
        """
        Upsert en third_parties con normalización básica.
        - Sobrescribe el nombre si llega uno distinto y no vacío (y opcionalmente más largo).
        """
        if self._db is None:
            return None
        rnc = (rnc or "").strip()
        name = (name or "").strip()
        if not rnc or not name:
            return None

        now = datetime.datetime.utcnow().isoformat()
        rnc_norm = rnc.upper()
        name_norm = " ".join(name.upper().split())

        coll = self._db.collection("third_parties")
        try:
            existing = list(coll.where("rnc", "==", rnc).limit(1).stream())
        except Exception:
            existing = []

        if existing:
            ref = existing[0].reference
            data_old = existing[0].to_dict() or {}
            old_name = (data_old.get("name") or "").strip()
            payload = {
                "rnc": rnc,
                "rnc_norm": rnc_norm,
                "name": old_name,
                "name_norm": data_old.get("name_norm", old_name.upper()),
                "updated_at": now,
                "updated_by": updated_by,
            }
            if name != old_name and len(name) >= len(old_name):
                payload["name"] = name
                payload["name_norm"] = name_norm
            ref.set(payload, merge=True)
            return ref.id
        else:
            doc = coll.document()
            doc.set(
                {
                    "rnc": rnc,
                    "rnc_norm": rnc_norm,
                    "name": name,
                    "name_norm": name_norm,
                    "created_at": now,
                    "updated_at": now,
                    "updated_by": updated_by,
                    "company_id": self.active_company_id,
                }
            )
            return doc.id


    def _ensure_third_party(self, rnc: str, name: str) -> None:
        """
        Crea un registro en 'third_parties' si no existe ya uno con el mismo RNC
        para la empresa activa. Es idempotente.
        """
        if self._db is None or FieldFilter is None:
            return
        rnc = (rnc or "").strip()
        name = (name or "").strip()
        if not rnc and not name:
            return

        try:
            col = self._db.collection("third_parties")
            if self.active_company_id is not None:
                q = (
                    col.where(
                        filter=FieldFilter("company_id", "==", self.active_company_id)
                    )
                    .where(filter=FieldFilter("rnc", "==", rnc))
                    .limit(1)
                )
            else:
                q = col.where(filter=FieldFilter("rnc", "==", rnc)).limit(1)

            docs = list(q.stream())
            if docs:
                return  # ya existe

            payload = {
                "rnc": rnc,
                "name": name,
                "name_normalized": name.lower(),
                "company_id": self.active_company_id,
                "created_at": datetime.datetime.utcnow().isoformat(),
            }
            col.add(payload)
        except Exception as e:
            print(f"[FIREBASE] Error creando third_party: {e}")

    # ------------------------------------------------------------------ #
    # Integración con ventanas clásicas de facturas
    # ------------------------------------------------------------------ #
    def open_add_income_invoice_window(self, parent=None):
        from PyQt6.QtWidgets import QApplication
        from add_invoice_window_qt import AddInvoiceWindowQt

        app = QApplication.instance()
        if app is None:
            print(
                "[FIREBASE] open_add_income_invoice_window: no hay QApplication activa."
            )
            return
        if parent is None:
            parent = app.activeWindow()

        def on_save(dialog, form_data, invoice_type, invoice_id=None):
            fecha = form_data.get("invoice_date") or form_data.get("fecha")
            invoice_num = (
                form_data.get("invoice_number")
                or form_data.get("número_de_factura")
            )
            currency = form_data.get("currency") or form_data.get("moneda")
            rnc = form_data.get("rnc") or form_data.get("rnc_cédula")
            tercero = (
                form_data.get("third_party_name")
                or form_data.get("empresa_a_la_que_se_emitió")
                or form_data.get("empresa")
            )
            itbis = form_data.get("itbis") or 0.0
            total = (
                form_data.get("total_amount")
                or form_data.get("factura_total")
                or 0.0
            )
            exchange = (
                form_data.get("exchange_rate")
                or form_data.get("tasa_cambio")
                or 1.0
            )

            try:
                itbis = float(itbis)
            except Exception:
                itbis = 0.0
            try:
                total = float(total)
            except Exception:
                total = 0.0
            try:
                exchange = float(exchange)
            except Exception:
                exchange = 1.0

            invoice_data = {
                "company_id": self.active_company_id,
                "invoice_type": "emitida",
                "invoice_date": fecha,
                "imputation_date": fecha,
                "invoice_number": invoice_num,
                "invoice_category": None,
                "rnc": rnc,
                "third_party_name": tercero,
                "currency": currency,
                "itbis": itbis,
                "total_amount": total,
                "exchange_rate": exchange,
                "attachment_path": None,
                "client_name": tercero,
                "client_rnc": rnc,
                "excel_path": None,
                "pdf_path": None,
                "due_date": None,
            }

            ok, msg = self.add_invoice(invoice_data)
            return ok, msg

        dlg = AddInvoiceWindowQt(
            parent=parent,
            controller=self,
            tipo_factura="emitida",
            on_save=on_save,
        )
        if dlg.exec() and parent is not None and hasattr(parent, "refresh_dashboard"):
            parent.refresh_dashboard()

    def open_add_expense_invoice_window(self, parent=None):
        """
        Abre AddExpenseWindowQt para facturas de gasto,
        pero guardando el resultado en Firestore.
        """
        from PyQt6.QtWidgets import QApplication
        from add_expense_window_qt import AddExpenseWindowQt

        app = QApplication.instance()
        if app is None:
            print(
                "[FIREBASE] open_add_expense_invoice_window: no hay QApplication activa."
            )
            return
        if parent is None:
            parent = app.activeWindow()

        def on_save(dialog, form_data, invoice_type, invoice_id=None):
            # Extraemos valores normalizados desde form_data
            fecha = form_data.get("invoice_date") or form_data.get("fecha")
            invoice_num = (
                form_data.get("invoice_number")
                or form_data.get("número_de_factura")
            )
            currency = form_data.get("currency") or form_data.get("moneda")
            rnc = form_data.get("rnc") or form_data.get("rnc_cédula")
            tercero = (
                form_data.get("third_party_name")
                or form_data.get("empresa_a_la_que_se_emitió")
                or form_data.get("lugar_de_compra_empresa")
            )
            itbis = form_data.get("itbis") or 0.0
            total = (
                form_data.get("total_amount")
                or form_data.get("factura_total")
                or 0.0
            )
            exchange = (
                form_data.get("exchange_rate")
                or form_data.get("tasa_cambio")
                or 1.0
            )
            attach = form_data.get("attachment_path")
            attach_storage = form_data.get("attachment_storage_path")  # <- NUEVO

            try:
                itbis = float(itbis)
            except Exception:
                itbis = 0.0
            try:
                total = float(total)
            except Exception:
                total = 0.0
            try:
                exchange = float(exchange)
            except Exception:
                exchange = 1.0

            invoice_data = {
                "company_id": self.active_company_id,
                "invoice_type": "gasto",
                "invoice_date": fecha,
                "imputation_date": fecha,
                "invoice_number": invoice_num,
                "invoice_category": None,
                "rnc": rnc,
                "third_party_name": tercero,
                "currency": currency,
                "itbis": itbis,
                "total_amount": total,
                "exchange_rate": exchange,
                "attachment_path": attach,
                "attachment_storage_path": attach_storage,  # <- NUEVO
                "client_name": None,
                "client_rnc": None,
                "excel_path": None,
                "pdf_path": None,
                "due_date": None,
            }

            ok, msg = self.add_invoice(invoice_data)
            return ok, msg

        dlg = AddExpenseWindowQt(parent=parent, controller=self, on_save=on_save)
        if dlg.exec() and parent is not None and hasattr(parent, "refresh_dashboard"):
            parent.refresh_dashboard()

        def on_save(dialog, form_data, invoice_type, invoice_id=None):
            fecha = form_data.get("invoice_date") or form_data.get("fecha")
            invoice_num = (
                form_data.get("invoice_number")
                or form_data.get("número_de_factura")
            )
            currency = form_data.get("currency") or form_data.get("moneda")
            rnc = form_data.get("rnc") or form_data.get("rnc_cédula")
            tercero = (
                form_data.get("third_party_name")
                or form_data.get("empresa_a_la_que_se_emitió")
                or form_data.get("lugar_de_compra_empresa")
            )
            itbis = form_data.get("itbis") or 0.0
            total = (
                form_data.get("total_amount")
                or form_data.get("factura_total")
                or 0.0
            )
            exchange = (
                form_data.get("exchange_rate")
                or form_data.get("tasa_cambio")
                or 1.0
            )
            attach = form_data.get("attachment_path")

            try:
                itbis = float(itbis)
            except Exception:
                itbis = 0.0
            try:
                total = float(total)
            except Exception:
                total = 0.0
            try:
                exchange = float(exchange)
            except Exception:
                exchange = 1.0

            invoice_data = {
                "company_id": self.active_company_id,
                "invoice_type": "gasto",
                "invoice_date": fecha,
                "imputation_date": fecha,
                "invoice_number": invoice_num,
                "invoice_category": None,
                "rnc": rnc,
                "third_party_name": tercero,
                "currency": currency,
                "itbis": itbis,
                "total_amount": total,
                "exchange_rate": exchange,
                "attachment_path": attach,
                "client_name": None,
                "client_rnc": None,
                "excel_path": None,
                "pdf_path": None,
                "due_date": None,
            }

            ok, msg = self.add_invoice(invoice_data)
            return ok, msg

        dlg = AddExpenseWindowQt(parent=parent, controller=self, on_save=on_save)
        if dlg.exec() and parent is not None and hasattr(parent, "refresh_dashboard"):
            parent.refresh_dashboard()

    # ------------------------------------------------------------------ #
    # Reportes / Cálculo impuestos (stubs por ahora)
    # ------------------------------------------------------------------ #
    def _open_tax_calculation_manager(self):
        print("[FIREBASE] _open_tax_calculation_manager: no implementado aún.")

    def _open_report_window(self):
        print("[FIREBASE] _open_report_window: no implementado aún.")

    def create_sql_backup(self, retention_days: int = 30) -> str:
        """
        Mantener firma para el menú 'Crear backup SQL manual'.
        En Firebase no aplica, devolvemos un placeholder.
        """
        path = f"backup_firestore_placeholder_{datetime.date.today().isoformat()}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write("Backup simbólico: Firestore no usa SQLite.\n")
        return os.path.abspath(path)

    # ------------------------------------------------------------------ #
    # Terceros (third_parties): búsqueda por RNC / nombre
    # ------------------------------------------------------------------ #
    def search_third_parties(self, query: str, search_by: str = "rnc") -> List[Dict[str, Any]]:
        """
        Búsqueda robusta sin depender de índices especiales:
        - search_by='rnc': primero igualdad exacta; si no, recorre recientes (updated_at desc) y filtra por subcadena.
        - search_by='name': recorre recientes y filtra por subcadena case-insensitive.
        Limita a 20 resultados.
        """
        if self._db is None:
            return []

        query = (query or "").strip()
        if not query:
            return []

        q_lower = query.lower()
        col = self._db.collection("third_parties")
        results: List[Dict[str, Any]] = []

        try:
            # Igualdad exacta por RNC si aplica
            if search_by == "rnc" and len(query) >= 3:
                exact = list(col.where("rnc", "==", query).limit(1).stream())
                if exact:
                    d = exact[0]
                    data = d.to_dict() or {}
                    data["id"] = d.id
                    return [data]

            # Recientes (ordenados por updated_at desc si es posible)
            try:
                docs = list(col.order_by("updated_at", direction=firestore.Query.DESCENDING).limit(500).stream())
            except Exception:
                docs = list(col.limit(500).stream())

            for d in docs:
                data = d.to_dict() or {}
                data["id"] = d.id
                if search_by == "rnc":
                    if q_lower in str(data.get("rnc", "")).lower():
                        results.append(data)
                else:
                    if q_lower in str(data.get("name", "")).lower():
                        results.append(data)
                if len(results) >= 20:
                    break
        except Exception as e:
            print(f"[FIREBASE] Error en search_third_parties: {e}")
        return results
    # ==================================================================
    #  Cálculos de impuestos / retenciones (tax_calculations)
    # ==================================================================

    def get_emitted_invoices_for_period(
        self,
        company_id: int | None,
        start_date: str,
        end_date: str,
    ):
        """
        Devuelve facturas EMITIDAS (ingresos) para una empresa en un rango de fechas.   
        
        ✅ CORREGIDO: Usa filtro Python porque Firestore tiene fechas en formato mixto (str y datetime).
        """
        print(
            f"[DEBUG-TAX] get_emitted_invoices_for_period("
            f"company_id={company_id}, start_date={start_date}, end_date={end_date})"
        )

        if not self._db:
            print("[DEBUG-TAX] _db es None; devolviendo lista vacía.")
            return []

        col = self._db.collection("invoices")

        # 1) Filtro base por tipo e empresa (SIN FILTRO DE FECHAS)
        try:  
            if FieldFilter is not None:  
                query = col.where(filter=FieldFilter("invoice_type", "==", "emitida"))
                if company_id is not None:  
                    query = query.where(filter=FieldFilter("company_id", "==", int(company_id)))
            else:
                query = col. where("invoice_type", "==", "emitida")
                if company_id is not None:     
                    query = query.where("company_id", "==", int(company_id))
        except Exception as e:  
            print(f"[FIREBASE-TAX] Error construyendo query: {e}")
            return []

        # 2) Parsear fechas para filtro Python
        start_d = None
        end_d = None
        try:  
            start_d = datetime. datetime.strptime(start_date, "%Y-%m-%d").date()
            end_d = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            print(f"[DEBUG-TAX] Filtro Python: {start_d} a {end_d}")
        except Exception as e:  
            print(f"[DEBUG-TAX] Error parseando fechas: {e}")
            return []

        # 3) Ejecutar query (SIN filtro de fechas en Firestore)
        try:  
            docs = list(query.stream())
            print(f"[DEBUG-TAX] Facturas obtenidas de Firestore (sin filtro de fecha): {len(docs)}")
        except Exception as e:  
            print(f"[FIREBASE-TAX] Error ejecutando query:  {e}")
            return []

        results = []

        # Helper para normalizar fecha (maneja str y datetime)
        try:
            from google.cloud. firestore_v1._helpers import DatetimeWithNanoseconds
        except:  
            DatetimeWithNanoseconds = None

        def _to_date(value):
            if value is None:
                return None
            # Ya es date (no datetime)
            if isinstance(value, datetime.date) and not isinstance(value, datetime. datetime):
                return value
            # DatetimeWithNanoseconds o datetime
            try:
                if isinstance(value, datetime.datetime):
                    return value. date()
            except:
                pass
            try:  
                if DatetimeWithNanoseconds and isinstance(value, DatetimeWithNanoseconds):
                    return value.date()
            except:
                pass
            # ✅ STRING (el caso de las 4 facturas faltantes)
            if isinstance(value, str):
                s = value.strip()
                if len(s) >= 10:
                    try:  
                        return datetime.datetime. strptime(s[: 10], "%Y-%m-%d").date()
                    except:
                        pass
            return None

        # Procesar docs y filtrar por fecha EN PYTHON
        filtered_count = 0
        for d in docs:  
            try:
                data = d.to_dict() or {}
            except:
                continue

            try:
                data["id"] = int(d.id) if str(d.id).isdigit() else d.id
            except:
                data["id"] = d.id

            # Normalizar invoice_date
            inv_raw = data.get("invoice_date") or data.get("fecha")
            inv_date_obj = _to_date(inv_raw)
            
            if inv_date_obj:   
                data["_invoice_date_obj"] = inv_date_obj
                data["invoice_date"] = inv_date_obj.isoformat()
            else:
                data["_invoice_date_obj"] = None
                data["invoice_date"] = str(inv_raw) if inv_raw else ""
                print(f"[DEBUG-TAX] ⚠️ Sin fecha normalizable: {data. get('invoice_number')} | raw: {inv_raw}")
                continue

            # ✅ FILTRAR EN PYTHON por rango de fechas
            ddate = data["_invoice_date_obj"]
            if ddate < start_d or ddate > end_d:
                continue
            
            filtered_count += 1

            # Asegurar campos
            if "total_amount_rd" not in data:
                try:
                    rate = float(data. get("exchange_rate", 1.0) or 1.0)
                    total = float(data.get("total_amount", 0.0) or 0.0)
                    data["total_amount_rd"] = total * rate
                except:
                    data["total_amount_rd"] = 0.0

            try:
                data. setdefault("itbis", 0.0)
                data.setdefault("exchange_rate", 1.0)
                data.setdefault("invoice_number", data.get("invoice_number", ""))
                data.setdefault("third_party_name", data.get("third_party_name", ""))
            except:
                pass

            results.append(data)

        print(f"[DEBUG-TAX] Facturas tras filtro Python: {filtered_count}")
        print(f"[DEBUG-TAX] Facturas finales: {len(results)}")
        
        results. sort(key=lambda x: x.get("_invoice_date_obj") or datetime.date(1970, 1, 1), reverse=True)
        
        return results


    def get_tax_calculations(self, company_id: int | None):
        print(f"[DEBUG-TAX] get_tax_calculations(company_id={company_id!r})")

        if not self._db:
            print("[DEBUG-TAX] _db es None; devolviendo lista vacía.")
            return []

        col = self._db.collection("tax_calculations")

        try:
            if company_id is not None:
                if FieldFilter is not None:
                    query = col.where(
                        filter=FieldFilter("company_id", "==", int(company_id))
                    )
                else:
                    query = col.where("company_id", "==", int(company_id))
            else:
                query = col
            query = query.order_by("created_at")
        except Exception as e:
            print(f"[FIREBASE-TAX] Error construyendo query tax_calculations: {e}")
            return []

        try:
            docs = list(query.stream())
            print(f"[DEBUG-TAX] cálculos leídos de Firestore: {len(docs)}")
        except Exception as e:
            print(f"[FIREBASE-TAX] Error leyendo tax_calculations: {e}")
            return []

        results: list[dict] = []
        for d in docs:
            data = d.to_dict() or {}
            data["id"] = int(d.id) if str(d.id).isdigit() else d.id
            if "created_at" not in data and "creation_date" in data:
                data["created_at"] = data["creation_date"]
            results.append(data)

        print(f"[DEBUG-TAX] cálculos devueltos tras normalizar: {len(results)}")
        return results
    def save_tax_calculation(
        self,
        calc_id,
        company_id,
        name: str,
        start_date: str,
        end_date: str,
        percent: float,
        details: dict,
    ):
        """
        Crea o actualiza un cálculo en:
          - tax_calculations
          - tax_calculation_details

        NOTA: company_id se guarda siempre como entero (si es posible) para
        ser compatible con los filtros de get_tax_calculations.
        
        Ahora también calcula y guarda:
          - total_amount: suma de montos de facturas seleccionadas
          - is_paid: inicialmente False para nuevos cálculos
        """
        if not self._db:
            return False, "Firestore no está inicializado."

        from firebase_admin import firestore as fb_fs

        doc_id = str(calc_id) if calc_id is not None else None

        try:
            col = self._db.collection("tax_calculations")
            if doc_id:
                doc_ref = col.document(doc_id)
            else:
                doc_ref = col.document()

            try:
                company_id_normalized = int(company_id) if company_id is not None else None
            except Exception:
                company_id_normalized = company_id

            # Calcular total_amount sumando montos de facturas seleccionadas
            total_amount = 0.0
            if details:
                for inv_id, state in details.items():
                    if bool(state.get("selected", False)):
                        try:
                            monto = float(state.get("monto") or state.get("amount") or state.get("total") or 0)
                            total_amount += monto
                        except (ValueError, TypeError):
                            pass

            payload = {
                "company_id": company_id_normalized,
                "name": name,
                "start_date": start_date,
                "end_date": end_date,
                "percent_to_pay": float(percent or 0.0),
                "total_amount": total_amount,
                "updated_at": fb_fs.SERVER_TIMESTAMP,
            }
            if not calc_id:
                payload["created_at"] = fb_fs.SERVER_TIMESTAMP
                payload["is_paid"] = False  # Nuevos cálculos son pendientes

            payload = {k: v for k, v in payload.items() if v is not None}
            doc_ref.set(payload, merge=True)

            final_calc_id = int(doc_ref.id) if str(doc_ref.id).isdigit() else doc_ref.id

            details_col = self._db.collection("tax_calculation_details")
            existing = list(
                details_col.where("calculation_id", "==", final_calc_id).stream()
            )
            if existing:
                batch_del = self._db.batch()
                for d in existing:
                    batch_del.delete(d.reference)
                batch_del.commit()

            batch = self._db.batch()
            count = 0
            for inv_id, state in (details or {}).items():
                selected = bool(state.get("selected"))
                retention = bool(state.get("retention"))
                if not selected:
                    continue

                try:
                    inv_key = int(inv_id)
                except Exception:
                    inv_key = inv_id

                det_payload = {
                    "calculation_id": final_calc_id,
                    "invoice_id": inv_key,
                    "selected": selected,
                    "retention": retention,
                    "updated_at": fb_fs.SERVER_TIMESTAMP,
                }
                det_ref = details_col.document()
                batch.set(det_ref, det_payload)
                count += 1

                if count % 400 == 0:
                    batch.commit()
                    batch = self._db.batch()

            if count % 400 != 0:
                batch.commit()

            msg = (
                "Cálculo creado correctamente."
                if not calc_id
                else "Cálculo actualizado correctamente."
            )
            return True, msg

        except Exception as e:
            print(f"[FIREBASE-TAX] Error guardando cálculo: {e}")
            return False, f"Error guardando cálculo: {e}"

    def delete_tax_calculation(self, calc_id):
        """
        Elimina un cálculo y sus detalles asociados.
        """
        if not self._db:
            return False, "Firestore no está inicializado."

        if calc_id is None:
            return False, "ID de cálculo inválido."

        doc_id = str(calc_id)
        try:
            calc_ref = self._db.collection("tax_calculations").document(doc_id)
            calc_doc = calc_ref.get()
            if not calc_doc.exists:
                return False, "El cálculo no existe en Firebase."

            try:
                final_calc_id = int(doc_id)
            except Exception:
                final_calc_id = doc_id

            details_col = self._db.collection("tax_calculation_details")
            detail_docs = list(
                details_col.where("calculation_id", "==", final_calc_id).stream()
            )
            if detail_docs:
                batch = self._db.batch()
                for d in detail_docs:
                    batch.delete(d.reference)
                batch.commit()

            calc_ref.delete()

            return True, "Cálculo y sus detalles han sido eliminados."

        except Exception as e:
            print(f"[FIREBASE-TAX] Error eliminando cálculo: {e}")
            return False, f"No se pudo eliminar el cálculo: {e}"

    def update_tax_calculation_paid_status(self, calc_id, is_paid: bool):
        """
        Actualiza el estado de pago (is_paid) de un cálculo.
        
        Args:
            calc_id: ID del cálculo
            is_paid: True si está pagado, False si está pendiente
            
        Returns:
            Tupla (success: bool, message: str)
        """
        if not self._db:
            return False, "Firestore no está inicializado."

        if calc_id is None:
            return False, "ID de cálculo inválido."

        from firebase_admin import firestore as fb_fs

        doc_id = str(calc_id)
        try:
            calc_ref = self._db.collection("tax_calculations").document(doc_id)
            calc_ref.set({
                "is_paid": bool(is_paid),
                "updated_at": fb_fs.SERVER_TIMESTAMP,
            }, merge=True)
            
            status_text = "Pagado" if is_paid else "Pendiente"
            return True, f"Estado actualizado a: {status_text}"

        except Exception as e:
            print(f"[FIREBASE-TAX] Error actualizando estado de pago: {e}")
            return False, f"Error al actualizar estado: {e}"

    def recalculate_tax_calculation_totals(self, calc_id):
        """
        Recalcula el total_amount de un cálculo basándose en sus detalles.
        Útil para migrar cálculos antiguos que no tienen monto guardado.
        
        Args:
            calc_id: ID del cálculo
            
        Returns:
            Tupla (success: bool, total_amount: float, message: str)
        """
        if not self._db:
            return False, 0.0, "Firestore no está inicializado."

        doc_id = str(calc_id)
        
        try:
            from firebase_admin import firestore as fb_fs
            
            # Obtener los detalles del cálculo
            details_col = self._db.collection("tax_calculation_details")
            detail_docs = list(
                details_col.where("calculation_id", "==", int(calc_id) if str(calc_id).isdigit() else calc_id)
                .where("selected", "==", True)
                .stream()
            )
            
            total_amount = 0.0
            
            # Para cada factura en el cálculo, obtener su monto
            for detail_doc in detail_docs:
                detail = detail_doc.to_dict()
                invoice_id = detail.get("invoice_id")
                
                if invoice_id:
                    try:
                        # Obtener la factura
                        invoice_ref = self._db.collection("invoices").document(str(invoice_id))
                        invoice_doc = invoice_ref.get()
                        
                        if invoice_doc.exists:
                            invoice_data = invoice_doc.to_dict()
                            # Usar total en RD$
                            monto = float(
                                invoice_data.get("total_amount_rd") or 
                                invoice_data.get("total_amount") or 
                                0.0
                            )
                            total_amount += monto
                    except Exception as e:
                        print(f"[FIREBASE-TAX] Error calculando monto de factura {invoice_id}: {e}")
                        continue
            
            # Guardar el total calculado
            calc_ref = self._db.collection("tax_calculations").document(doc_id)
            calc_ref.set({
                "total_amount": total_amount,
                "updated_at": fb_fs.SERVER_TIMESTAMP,
            }, merge=True)
            
            return True, total_amount, f"Total recalculado: RD$ {total_amount:,.2f}"
        
        except Exception as e:
            print(f"[FIREBASE-TAX] Error recalculando totales: {e}")
            return False, 0.0, f"Error recalculando: {e}"
        

    def get_tax_calculation_details(self, calc_id):
        """
        Devuelve un cálculo y sus detalles en el formato esperado por AdvancedRetentionWindowQt.
        """
        if not self._db or calc_id is None:
            return None

        doc_id = str(calc_id)

        try:
            doc = self._db.collection("tax_calculations").document(doc_id).get()
        except Exception:
            return None

        if not doc.exists:
            return None

        main = doc.to_dict() or {}
        main["id"] = int(doc.id) if str(doc.id).isdigit() else doc.id

        try:
            detail_query = (
                self._db.collection("tax_calculation_details")
                .where("calculation_id", "==", main["id"])
            )
            detail_docs = list(detail_query.stream())
        except Exception:
            detail_docs = []

        details: dict[int, dict] = {}
        for d in detail_docs:
            data = d.to_dict() or {}
            inv_id = data.get("invoice_id")
            if inv_id is None:
                continue
            try:
                key = int(inv_id)
            except Exception:
                key = inv_id
            details[key] = {
                "selected": bool(data.get("selected", False)),
                "retention": bool(data.get("retention", False)),
            }

        return {"main": main, "details": details}

    def save_tax_calculation(
        self,
        calc_id,
        company_id,
        name: str,
        start_date: str,
        end_date: str,
        percent: float,
        details: dict,
    ):
        """
        Crea o actualiza un cálculo en:
          - tax_calculations
          - tax_calculation_details
        """
        if not self._db:
            return False, "Firestore no está inicializado."

        from firebase_admin import firestore as fb_fs

        doc_id = str(calc_id) if calc_id is not None else None

        try:
            col = self._db.collection("tax_calculations")
            if doc_id:
                doc_ref = col.document(doc_id)
            else:
                doc_ref = col.document()

            payload = {
                "company_id": int(company_id) if company_id is not None else None,
                "name": name,
                "start_date": start_date,
                "end_date": end_date,
                "percent_to_pay": float(percent or 0.0),
                "updated_at": fb_fs.SERVER_TIMESTAMP,
            }
            if not calc_id:
                payload["created_at"] = fb_fs.SERVER_TIMESTAMP

            payload = {k: v for k, v in payload.items() if v is not None}
            doc_ref.set(payload, merge=True)

            final_calc_id = int(doc_ref.id) if str(doc_ref.id).isdigit() else doc_ref.id

            details_col = self._db.collection("tax_calculation_details")
            existing = list(
                details_col.where("calculation_id", "==", final_calc_id).stream()
            )
            if existing:
                batch_del = self._db.batch()
                for d in existing:
                    batch_del.delete(d.reference)
                batch_del.commit()

            batch = self._db.batch()
            count = 0
            for inv_id, state in (details or {}).items():
                selected = bool(state.get("selected"))
                retention = bool(state.get("retention"))
                if not selected:
                    continue

                try:
                    inv_key = int(inv_id)
                except Exception:
                    inv_key = inv_id

                det_payload = {
                    "calculation_id": final_calc_id,
                    "invoice_id": inv_key,
                    "selected": selected,
                    "retention": retention,
                    "updated_at": fb_fs.SERVER_TIMESTAMP,
                }
                det_ref = details_col.document()
                batch.set(det_ref, det_payload)
                count += 1

                if count % 400 == 0:
                    batch.commit()
                    batch = self._db.batch()

            if count % 400 != 0:
                batch.commit()

            msg = (
                "Cálculo creado correctamente."
                if not calc_id
                else "Cálculo actualizado correctamente."
            )
            return True, msg

        except Exception as e:
            print(f"[FIREBASE-TAX] Error guardando cálculo: {e}")
            return False, f"Error guardando cálculo: {e}"

    def delete_tax_calculation(self, calc_id):
        """
        Elimina un cálculo y sus detalles asociados.
        """
        if not self._db:
            return False, "Firestore no está inicializado."

        if calc_id is None:
            return False, "ID de cálculo inválido."

        doc_id = str(calc_id)
        try:
            calc_ref = self._db.collection("tax_calculations").document(doc_id)
            calc_doc = calc_ref.get()
            if not calc_doc.exists:
                return False, "El cálculo no existe en Firebase."

            try:
                final_calc_id = int(doc_id)
            except Exception:
                final_calc_id = doc_id

            details_col = self._db.collection("tax_calculation_details")
            detail_docs = list(
                details_col.where("calculation_id", "==", final_calc_id).stream()
            )
            if detail_docs:
                batch = self._db.batch()
                for d in detail_docs:
                    batch.delete(d.reference)
                batch.commit()

            calc_ref.delete()

            return True, "Cálculo y sus detalles han sido eliminados."

        except Exception as e:
            print(f"[FIREBASE-TAX] Error eliminando cálculo: {e}")
            return False, f"No se pudo eliminar el cálculo: {e}"
        
    def get_itbis_month_summary(
        self,
        company_id: int | None,
        month_str: str | None,
        year_int: int | None,
    ) -> dict:
        """
        Resume para una empresa y mes/año:
          - total_income, total_expense
          - itbis_income, itbis_expense
          - itbis_neto, total_neto

        Reutiliza _query_invoices para respetar toda la lógica de fechas.
        """
        if not self._db or not company_id:
            return {
                "total_income": 0.0,
                "total_expense": 0.0,
                "itbis_income": 0.0,
                "itbis_expense": 0.0,
                "itbis_neto": 0.0,
                "total_neto": 0.0,
            }

        invoices = self._query_invoices(
            company_id=company_id,
            month_str=month_str,
            year_int=year_int,
            tx_type=None,
        )

        def _fx(inv: dict) -> float:
            try:
                rate = float(inv.get("exchange_rate", 1.0) or 1.0)
                return rate if rate != 0 else 1.0
            except Exception:
                return 1.0

        total_income = 0.0
        total_expense = 0.0
        itbis_income = 0.0
        itbis_expense = 0.0

        for inv in invoices:
            tipo = inv.get("invoice_type")
            total_rd = float(inv.get("total_amount_rd", inv.get("total_amount", 0.0)))
            itbis_orig = float(inv.get("itbis", 0.0))
            itbis_rd = itbis_orig * _fx(inv)

            if tipo == "emitida":
                total_income += total_rd
                itbis_income += itbis_rd
            elif tipo == "gasto":
                total_expense += total_rd
                itbis_expense += itbis_rd

        itbis_neto = itbis_income - itbis_expense
        total_neto = total_income - total_expense

        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "itbis_income": itbis_income,
            "itbis_expense": itbis_expense,
            "itbis_neto": itbis_neto,
            "total_neto": total_neto,
        }
    
    def get_itbis_adelantado(self, company_id) -> float:
        """Obtiene el ITBIS adelantado para una empresa específica (desde companies.itbis_adelantado)."""
        if not self._db or company_id is None:
            return 0.0
        try:
            doc = self._db.collection("companies").document(str(company_id)).get()
            if not doc.exists:
                return 0.0
            data = doc.to_dict() or {}
            return float(data.get("itbis_adelantado", 0.0) or 0.0)
        except Exception:
            return 0.0

    def update_itbis_adelantado(self, company_id, value: float) -> bool:
        """Actualiza el ITBIS adelantado para una empresa específica (companies.itbis_adelantado)."""
        if not self._db or company_id is None:
            return False
        try:
            self._db.collection("companies").document(str(company_id)).set(
                {"itbis_adelantado": float(value or 0.0)}, merge=True
            )
            return True
        except Exception as e:
            print(f"[FIREBASE] Error al actualizar ITBIS adelantado: {e}")
            return False
        
    # ------------------------------------------------------------------
    # ITBIS adelantado por periodo (empresa + mes + año)
    # ------------------------------------------------------------------
    def get_itbis_adelantado_period(
        self,
        company_id: int | None,
        month_str: str | None,
        year_int: int | None,
    ) -> float:
        """
        Devuelve el ITBIS adelantado para company_id en un mes/año específico.
        Usa la colección 'itbis_adelantado_period'.
        """
        if not self._db or company_id is None or not month_str or year_int is None:
            return 0.0
        try:
            doc_id = f"{company_id}_{year_int}_{month_str}"
            doc = self._db.collection("itbis_adelantado_period").document(doc_id).get()
            if not doc.exists:
                return 0.0
            data = doc.to_dict() or {}
            return float(data.get("amount", 0.0) or 0.0)
        except Exception:
            return 0.0

    def update_itbis_adelantado_period(
        self,
        company_id: int | None,
        month_str: str | None,
        year_int: int | None,
        value: float,
    ) -> bool:
        """
        Actualiza/crea el ITBIS adelantado para company_id, mes y año en
        la colección 'itbis_adelantado_period'.
        """
        if not self._db or company_id is None or not month_str or year_int is None:
            return False
        try:
            from firebase_admin import firestore as fb_fs
        except Exception:
            fb_fs = None

        try:
            doc_id = f"{company_id}_{year_int}_{month_str}"
            payload = {
                "company_id": int(company_id),
                "year": int(year_int),
                "month": str(month_str),
                "amount": float(value or 0.0),
            }
            if fb_fs is not None:
                payload["updated_at"] = fb_fs.SERVER_TIMESTAMP
            self._db.collection("itbis_adelantado_period").document(doc_id).set(
                payload, merge=True
            )
            return True
        except Exception as e:
            print(f"[FIREBASE] Error al actualizar ITBIS adelantado periodo: {e}")
            return False
        
    def get_monthly_report_data(
        self,
        company_id: int,
        month: int,
        year: int,
    ) -> dict:
        """
        Devuelve los datos para el reporte mensual en el mismo formato que
        usaba la versión SQLite:

        {
          "summary": {
              "total_ingresos": float,
              "total_gastos": float,
              "total_neto": float,
              "itbis_ingresos": float,
              "itbis_gastos": float,
              "itbis_neto": float,
          },
          "emitted_invoices": [ ... ],
          "expense_invoices": [ ... ],
        }

        - Usa _query_invoices para obtener las facturas de ese mes/año.
        - Calcula montos en RD$ respetando exchange_rate y total_amount_rd.
        """
        if not self._db or not company_id:
            return {
                "summary": {
                    "total_ingresos": 0.0,
                    "total_gastos": 0.0,
                    "total_neto": 0.0,
                    "itbis_ingresos": 0.0,
                    "itbis_gastos": 0.0,
                    "itbis_neto": 0.0,
                },
                "emitted_invoices": [],
                "expense_invoices": [],
            }

        # mes como string "01".."12" para _query_invoices
        month_str = f"{int(month):02d}"
        year_int = int(year)

        # Traer TODAS las facturas del mes (emitidas + gastos)
        invoices = self._query_invoices(
            company_id=company_id,
            month_str=month_str,
            year_int=year_int,
            tx_type=None,
        )

        emitted = [inv for inv in invoices if inv.get("invoice_type") == "emitida"]
        expenses = [inv for inv in invoices if inv.get("invoice_type") == "gasto"]

        def _fx(inv: dict) -> float:
            try:
                rate = float(inv.get("exchange_rate", 1.0) or 1.0)
                return rate if rate != 0 else 1.0
            except Exception:
                return 1.0

        # Totales por grupo
        total_ingresos = 0.0
        total_gastos = 0.0
        itbis_ingresos = 0.0
        itbis_gastos = 0.0

        for inv in emitted:
            rate = _fx(inv)
            total_rd = float(inv.get("total_amount_rd", 0.0) or 0.0)
            if not total_rd:
                total_rd = float(inv.get("total_amount", 0.0) or 0.0) * rate
            itbis_orig = float(inv.get("itbis", 0.0) or 0.0)
            total_ingresos += total_rd
            itbis_ingresos += itbis_orig * rate

        for inv in expenses:
            rate = _fx(inv)
            total_rd = float(inv.get("total_amount_rd", 0.0) or 0.0)
            if not total_rd:
                total_rd = float(inv.get("total_amount", 0.0) or 0.0) * rate
            itbis_orig = float(inv.get("itbis", 0.0) or 0.0)
            total_gastos += total_rd
            itbis_gastos += itbis_orig * rate

        itbis_neto = itbis_ingresos - itbis_gastos
        total_neto = total_ingresos - total_gastos

        summary = {
            "total_ingresos": total_ingresos,
            "total_gastos": total_gastos,
            "total_neto": total_neto,
            "itbis_ingresos": itbis_ingresos,
            "itbis_gastos": itbis_gastos,
            "itbis_neto": itbis_neto,
        }

        # El reporte espera listas "emitted_invoices" y "expense_invoices"
        # con los campos que ya se usan en ReportWindowQt y report_generator.
        return {
            "summary": summary,
            "emitted_invoices": emitted,
            "expense_invoices": expenses,
        }
    
    def get_report_by_third_party(
        self,
        company_id: int | None,
        rnc: str,
    ) -> dict:
        """
        Devuelve un reporte resumido por tercero (cliente/proveedor) para la empresa dada.

        Formato:
        {
          "summary": {
            "total_ingresos": float,
            "total_gastos": float,
          },
          "emitted_invoices": [ ... ],   # facturas 'emitida' para ese RNC
          "expense_invoices": [ ... ],   # facturas 'gasto'   para ese RNC
        }

        - Filtra por company_id (si se pasa) y por rnc en la colección 'invoices'.
        - No limita por mes/año; es histórico completo para ese tercero y empresa.
        """
        if not self._db or not rnc:
            return {
                "summary": {
                    "total_ingresos": 0.0,
                    "total_gastos": 0.0,
                },
                "emitted_invoices": [],
                "expense_invoices": [],
            }

        rnc = str(rnc).strip()
        if not rnc:
            return {
                "summary": {
                    "total_ingresos": 0.0,
                    "total_gastos": 0.0,
                },
                "emitted_invoices": [],
                "expense_invoices": [],
            }

        try:
            col = self._db.collection("invoices")

            # Filtro por empresa si se proporciona
            if company_id is not None:
                col = col.where("company_id", "==", int(company_id))

            # Filtro por RNC (campo 'rnc' o 'client_rnc' como fallback)
            # No podemos hacer OR en Firestore, así que primero probamos rnc,
            # y si no hay suficientes resultados, intentamos client_rnc.
            emitted: list[dict] = []
            expenses: list[dict] = []

            # Helper para sumar totales
            def _fx(inv: dict) -> float:
                try:
                    rate = float(inv.get("exchange_rate", 1.0) or 1.0)
                    return rate if rate != 0 else 1.0
                except Exception:
                    return 1.0

            # 1) Buscar por campo 'rnc'
            q_base = col.where("rnc", "==", rnc)
            docs = list(q_base.stream())

            # 2) Si no hay nada y el RNC está grabado como client_rnc, intentamos ese campo
            if not docs:
                q_base = col.where("client_rnc", "==", rnc)
                docs = list(q_base.stream())

            invoices: list[dict] = []
            for d in docs:
                data = d.to_dict() or {}
                data["id"] = d.id
                invoices.append(data)

            # Separar por tipo
            for inv in invoices:
                tipo = inv.get("invoice_type")
                if tipo == "emitida":
                    emitted.append(inv)
                elif tipo == "gasto":
                    expenses.append(inv)

            # Calcular totales (en RD$)
            total_ingresos = 0.0
            total_gastos = 0.0

            for inv in emitted:
                rate = _fx(inv)
                total_rd = float(inv.get("total_amount_rd", 0.0) or 0.0)
                if not total_rd:
                    total_rd = float(inv.get("total_amount", 0.0) or 0.0) * rate
                total_ingresos += total_rd

            for inv in expenses:
                rate = _fx(inv)
                total_rd = float(inv.get("total_amount_rd", 0.0) or 0.0)
                if not total_rd:
                    total_rd = float(inv.get("total_amount", 0.0) or 0.0) * rate
                total_gastos += total_rd

            summary = {
                "total_ingresos": total_ingresos,
                "total_gastos": total_gastos,
            }

            return {
                "summary": summary,
                "emitted_invoices": emitted,
                "expense_invoices": expenses,
            }

        except Exception as e:
            print(f"[FIREBASE-REPORT] Error en get_report_by_third_party: {e}")
            return {
                "summary": {
                    "total_ingresos": 0.0,
                    "total_gastos": 0.0,
                },
                "emitted_invoices": [],
                "expense_invoices": [],
            }
        
# ========================================
# MÉTODOS DE GESTIÓN DE ADJUNTOS (STORAGE)
# ========================================

    def download_invoice_attachments_for_report(
        self,
        invoices: list[dict],
    ) -> dict[str, str]:
        """
        Descarga anexos de facturas desde Firebase Storage a carpeta temporal.
        
        Args:
            invoices: Lista de facturas con campos:
                - id o invoice_number (identificador)
                - attachment_storage_path o storage_path (ruta en Storage)
        
        Returns:
            dict: {invoice_id: local_temp_path}
        
        Ejemplo:
            {
                'E3100000239': '/tmp/facturas_report_abc123/E3100000239_132125177.jpg',
                'B0100005512': '/tmp/facturas_report_abc123/B0100005512.pdf'
            }
        """
        import tempfile
        import os

        print("\n" + "="*80)
        print("📥 DESCARGANDO ADJUNTOS DESDE FIREBASE STORAGE (PARA REPORTE)")
        print("="*80)
        
        result: dict[str, str] = {}
        
        if not self._bucket:
            print("❌ Bucket de Storage no inicializado")
            return result
        
        if not invoices:
            print("⚠️ No hay facturas para procesar")
            return result

        try:
            temp_dir = tempfile.mkdtemp(prefix="facturas_report_")
            print(f"📁 Carpeta temporal creada: {temp_dir}")
        except Exception as e:
            print(f"❌ Error creando carpeta temporal: {e}")
            return result

        stats = {
            'total': len(invoices),
            'con_storage': 0,
            'sin_storage': 0,
            'exitosos': 0,
            'fallidos': 0,
        }

        for idx, inv in enumerate(invoices, 1):
            try:
                # Obtener identificador
                inv_id = str(inv.get("id") or inv.get("invoice_number") or "")
                if not inv_id:
                    print(f"⚠️ Factura {idx}/{stats['total']}: Sin ID")
                    continue

                # Obtener ruta de Storage
                storage_path = (
                    inv.get("attachment_storage_path")
                    or inv.get("storage_path")
                    or None
                )
                
                if not storage_path:
                    stats['sin_storage'] += 1
                    print(f"⚠️ {idx}/{stats['total']} - {inv_id}: Sin storage_path")
                    continue

                stats['con_storage'] += 1
                
                # Normalizar ruta
                sp = str(storage_path).strip().replace("\\", "/")
                if not sp:
                    stats['sin_storage'] += 1
                    continue

                print(f"🔄 {idx}/{stats['total']} - {inv_id}")
                print(f"   └─ Descargando: {sp}")

                # Descargar desde Storage
                blob = self._bucket.blob(sp)
                
                # Generar nombre de archivo local
                base_name = os.path.basename(sp) or f"{inv_id}.bin"
                local_path = os.path.join(temp_dir, base_name)

                # Descargar
                blob.download_to_filename(local_path)
                
                # Verificar que se descargó
                if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                    result[inv_id] = local_path
                    stats['exitosos'] += 1
                    size_kb = os.path.getsize(local_path) / 1024
                    print(f"   └─ ✅ Descargado: {local_path} ({size_kb:.1f} KB)")
                else:
                    stats['fallidos'] += 1
                    print(f"   └─ ❌ Archivo vacío o no existe")

            except Exception as e:
                stats['fallidos'] += 1
                print(f"   └─ ❌ Error: {e}")
                continue

        # Resumen
        print("\n" + "="*80)
        print("📊 RESUMEN DE DESCARGA")
        print("="*80)
        print(f"   Total facturas: {stats['total']}")
        print(f"   Con storage_path: {stats['con_storage']}")
        print(f"   Sin storage_path: {stats['sin_storage']}")
        print(f"   ✅ Exitosos: {stats['exitosos']}")
        print(f"   ❌ Fallidos: {stats['fallidos']}")
        print(f"   📁 Archivos disponibles: {len(result)}")
        print("="*80 + "\n")

        return result


    def download_attachment_from_storage(
        self,
        storage_path: str,
        local_destination: str
    ) -> bool:
        """
        Descarga un archivo desde Firebase Storage.
        
        Args:
            storage_path: Ruta en Storage
            local_destination: Ruta local donde guardar
        
        Returns:
            bool: True si se descargó correctamente
        """
        if not self._bucket:
            print("[STORAGE] ❌ Bucket no inicializado")
            return False

        try:
            # Normalizar ruta
            sp = str(storage_path).strip().replace("\\", "/")
            
            blob = self._bucket.blob(sp)
            
            # Verificar que existe
            if not blob.exists():
                print(f"[STORAGE] ❌ Archivo no existe: {sp}")
                return False

            # Crear directorio si no existe
            import os
            os.makedirs(os.path.dirname(local_destination), exist_ok=True)

            # Descargar
            blob.download_to_filename(local_destination)

            # Verificar
            if os.path.exists(local_destination) and os.path.getsize(local_destination) > 0:
                size_kb = os.path.getsize(local_destination) / 1024
                print(f"[STORAGE] ✅ Descargado: {sp} ({size_kb:.1f} KB)")
                return True
            else:
                print(f"[STORAGE] ❌ Descarga falló (archivo vacío)")
                return False

        except Exception as e:
            print(f"[STORAGE] ❌ Error descargando: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def migrate_invoice_attachment_from_local(
        self,
        invoice: dict,
        local_full_path: str,
    ) -> bool:
        """
        Migra un anexo local a Firebase Storage y actualiza el documento.
        
        Args:
            invoice: Diccionario de factura (debe tener 'id')
            local_full_path: Ruta absoluta del archivo local
        
        Returns:
            bool: True si migró exitosamente
        
        Características:
            - NO sobreescribe si ya tiene attachment_storage_path
            - Actualiza el documento en Firestore automáticamente
            - Valida que el archivo exista antes de subir
        """
        # ========================================
        # VALIDACIONES INICIALES
        # ========================================
        if not self._db or not self._bucket:
            print("[MIGRATE] ❌ DB o Bucket no inicializados")
            return False

        if not local_full_path or not os.path.exists(local_full_path):
            print(f"[MIGRATE] ❌ Archivo no existe: {local_full_path}")
            return False

        # Si ya tiene storage_path, no migramos
        if invoice.get("attachment_storage_path") or invoice.get("storage_path"):
            print(f"[MIGRATE] ⚠️ Factura ya tiene storage_path (skipping)")
            return False

        doc_id = invoice.get("id")
        if not doc_id:
            print(f"[MIGRATE] ❌ Factura sin ID")
            return False

        # ========================================
        # EXTRAER DATOS DE LA FACTURA
        # ========================================
        company_id = invoice.get("company_id")
        invoice_number = (
            invoice.get("invoice_number") 
            or invoice.get("número_de_factura")
            or str(doc_id)
        )
        
        invoice_date = invoice.get("invoice_date") or invoice.get("fecha")
        rnc = (
            invoice.get("rnc") 
            or invoice.get("client_rnc") 
            or invoice.get("rnc_cédula")
            or invoice.get("third_party_rnc")
        )

        # ========================================
        # NORMALIZAR FECHA
        # ========================================
        inv_date_py = None
        try:
            if isinstance(invoice_date, datetime.date):
                inv_date_py = invoice_date
            elif isinstance(invoice_date, datetime.datetime):
                inv_date_py = invoice_date.date()
            elif invoice_date:
                # Intentar parsear string
                s = str(invoice_date)
                inv_date_py = datetime.datetime.strptime(s[:10], "%Y-%m-%d").date()
        except Exception as e:
            print(f"[MIGRATE] ⚠️ Error parseando fecha: {e}")
            inv_date_py = None

        print(f"\n[MIGRATE] 🔄 Migrando anexo a Storage...")
        print(f"   Factura: {invoice_number}")
        print(f"   Doc ID: {doc_id}")
        print(f"   Archivo: {local_full_path}")

        try:
            # ========================================
            # SUBIR A STORAGE
            # ========================================
            storage_path = self.upload_attachment_to_storage(
                local_path=str(local_full_path),
                company_id=str(company_id or ""),
                invoice_number=str(invoice_number),
                invoice_date=inv_date_py,
                rnc=str(rnc or ""),
            )

            if not storage_path:
                print(f"[MIGRATE] ❌ Fallo subiendo a Storage")
                return False

            # ========================================
            # ACTUALIZAR FIRESTORE
            # ========================================
            col = self._db.collection("invoices")
            doc_ref = col.document(str(doc_id))
            
            doc_ref.update({
                "attachment_storage_path": storage_path,
                "migrated_to_storage": True,
                "migration_date": self._get_timestamp(),
            })

            print(f"[MIGRATE] ✅ Migración exitosa")
            print(f"   Storage path: {storage_path}")

            return True

        except Exception as e:
            print(f"[MIGRATE] ❌ Error migrando anexo: {e}")
            import traceback
            traceback.print_exc()
            return False

    def list_attachments_in_storage(
        self,
        company_id: str,
        year: int = None,
        month: int = None,
        limit: int = 100
    ) -> list[dict]:
        """
        Lista archivos de adjuntos en Storage.
        
        Args:
            company_id: ID de la empresa
            year: Año (opcional)
            month: Mes (opcional)
            limit: Máximo de resultados
        
        Returns:
            list: [{'name': str, 'size': int, 'updated': datetime, 'url': str}, ...]
        """
        if not self._bucket:
            return []
        
        try:
            # Construir prefijo
            prefix = f"Adjuntos/{company_id}/"
            if year:
                prefix += f"{year}/"
                if month:
                    prefix += f"{month:02d}/"
            
            print(f"[STORAGE] 🔍 Listando archivos con prefijo: {prefix}")
            
            blobs = self._bucket.list_blobs(prefix=prefix, max_results=limit)
            
            result = []
            for blob in blobs:
                result.append({
                    'name': blob.name,
                    'size': blob.size,
                    'updated': blob.updated,
                    'content_type': blob.content_type,
                    'public_url': blob.public_url if blob.public else None,
                })
            
            print(f"[STORAGE] ✅ Encontrados {len(result)} archivos")
            return result
            
        except Exception as e:
            print(f"[STORAGE] ❌ Error listando archivos: {e}")
            return []


    def delete_attachment_from_storage(self, storage_path: str) -> bool:
        """
        Elimina un archivo de Firebase Storage.
        
        Args:
            storage_path: Ruta en Storage (ej: 'Adjuntos/empresa/2025/01/file.jpg')
        
        Returns:
            bool: True si se eliminó correctamente
        """
        if not self._bucket:
            print("[STORAGE] Bucket no inicializado")
            return False
        
        try:
            sp = str(storage_path).strip().replace("\\", "/")
            
            blob = self._bucket.blob(sp)
            
            if not blob.exists():
                print(f"[STORAGE] Archivo no existe (ya eliminado): {sp}")
                return True  # Consideramos éxito si ya no existe
            
            blob.delete()
            print(f"[STORAGE] ✅ Eliminado: {sp}")
            return True
            
        except Exception as e:
            print(f"[STORAGE] ❌ Error eliminando {storage_path}: {e}")
            return False


    # —––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
    # Métodos para editar / eliminar / ver adjuntos desde la GUI moderna
    # —––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––

    def _find_invoice_doc_by_number(self, invoice_number: str):
        """
        Busca un documento en 'invoices' por company_id + invoice_number.
        Devuelve (doc_ref, data) o (None, None).
        """
        if not self._db or not self.active_company_id or not invoice_number:
            return None, None

        try:
            col = self._db.collection("invoices")
            if FieldFilter is None:
                q = (
                    col.where("company_id", "==", int(self.active_company_id))
                    .where("invoice_number", "==", invoice_number)
                    .limit(1)
                )
            else:
                q = (
                    col.where(
                        filter=FieldFilter("company_id", "==", int(self.active_company_id))
                    )
                    .where(filter=FieldFilter("invoice_number", "==", invoice_number))
                    .limit(1)
                )
            docs = list(q.stream())
            if not docs:
                return None, None
            doc = docs[0]
            data = doc.to_dict() or {}
            data["id"] = doc.id
            return doc.reference, data
        except Exception as e:
            print(f"[FIREBASE] Error buscando invoice {invoice_number}: {e}")
            return None, None

    def edit_invoice_by_number(self, invoice_number: str, parent=None):
            """
            Abre la ventana de edición para la factura dada por invoice_number.
            CORREGIDO: Convierte datetime.date a datetime.datetime para evitar error en Firestore.
            """
            if not self._db or not self.active_company_id:
                raise RuntimeError("Firestore o empresa activa no disponibles.")

            from PyQt6.QtWidgets import QApplication, QMessageBox
            from add_invoice_window_qt import AddInvoiceWindowQt
            from add_expense_window_qt import AddExpenseWindowQt

            doc_ref, data = self._find_invoice_doc_by_number(invoice_number)
            if not doc_ref or not data:
                raise RuntimeError("Factura no encontrada en Firebase.")

            tipo = data.get("invoice_type", "")
            app = QApplication.instance()
            if app is None:
                raise RuntimeError("No hay QApplication activa.")
            if parent is None:
                parent = app.activeWindow()

            # Normalizar fechas para pasarlas al DIÁLOGO (el diálogo usa QDate o date)
            def _to_date_obj(v):
                if not v:
                    return None
                if isinstance(v, datetime.datetime):
                    return v.date()
                if isinstance(v, datetime.date):
                    return v
                try:
                    s = str(v)
                    return datetime.datetime.strptime(s[:10], "%Y-%m-%d").date()
                except Exception:
                    return None

            data["invoice_date"] = _to_date_obj(data.get("invoice_date"))

            # --- CALLBACK DE GUARDADO ---
            def on_save(dialog, form_data, invoice_type, invoice_id=None):
                # 1. Obtener fecha cruda del formulario
                fecha_raw = form_data.get("invoice_date") or form_data.get("fecha")
                
                # 2. CONVERSIÓN OBLIGATORIA A DATETIME (Firestore no acepta datetime.date)
                fecha_dt = None
                if isinstance(fecha_raw, datetime.date) and not isinstance(fecha_raw, datetime.datetime):
                    # Convertir date -> datetime (con hora 00:00:00)
                    fecha_dt = datetime.datetime(fecha_raw.year, fecha_raw.month, fecha_raw. day)
                elif isinstance(fecha_raw, datetime.datetime):
                    fecha_dt = fecha_raw
                elif isinstance(fecha_raw, str):
                    try:
                        fecha_dt = datetime.datetime.strptime(fecha_raw[: 10], "%Y-%m-%d")
                    except:
                        fecha_dt = datetime.datetime.now()
                else:
                    fecha_dt = datetime.datetime.now()

                invoice_num = (
                    form_data.get("invoice_number")
                    or form_data.get("número_de_factura")
                    or invoice_number
                )
                currency = form_data.get("currency") or form_data.get("moneda")
                rnc = form_data.get("rnc") or form_data.get("rnc_cédula")
                tercero = (
                    form_data.get("third_party_name")
                    or form_data.get("empresa_a_la_que_se_emitió")
                    or form_data.get("empresa")
                    or form_data. get("lugar_de_compra_empresa")
                )
                itbis = form_data.get("itbis") or 0.0
                total = (
                    form_data.get("total_amount")
                    or form_data.get("factura_total")
                    or 0.0
                )
                exchange = (
                    form_data.get("exchange_rate")
                    or form_data.get("tasa_cambio")
                    or 1.0
                )
                attach = form_data.get("attachment_path")
                attach_storage = form_data.get("attachment_storage_path")

                try:
                    itbis = float(itbis)
                except Exception:
                    itbis = 0.0
                try:
                    total = float(total)
                except Exception: 
                    total = 0.0
                try:
                    exchange = float(exchange)
                except Exception:
                    exchange = 1.0

                # ✅ VALIDACIÓN DE DUPLICADOS (EDICIÓN)
                total_rd = total * exchange
                duplicate = self.check_duplicate_invoice(
                    rnc=rnc,
                    invoice_number=invoice_num,
                    total_amount=total_rd,
                    exclude_invoice_id=data.get("id"),  # Excluir la factura actual
                )
                
                if duplicate:
                    dup_company = duplicate.get("company_name", "Desconocida")
                    dup_date = duplicate.get("invoice_date", "Desconocida")
                    dup_type = duplicate.get("invoice_type", "")
                    dup_third_party = duplicate.get("third_party_name", "Desconocido")
                    tipo_str = "INGRESO" if dup_type == "emitida" else "GASTO" if dup_type == "gasto" else dup_type
                    
                    warning_msg = (
                        f"⚠️ FACTURA DUPLICADA DETECTADA\n\n"
                        f"Ya existe otra factura con estos datos:\n\n"
                        f"📄 NCF: {invoice_num}\n"
                        f"🏢 RNC: {rnc}\n"
                        f"💰 Monto: RD$ {total_rd: ,.2f}\n\n"
                        f"Registrada en:\n"
                        f"• Empresa: {dup_company}\n"
                        f"• Fecha: {dup_date}\n"
                        f"• Tipo: {tipo_str}\n"
                        f"• Tercero: {dup_third_party}\n\n"
                        f"¿Desea continuar y actualizar de todas formas?"
                    )
                    
                    return False, warning_msg

                # 3. Construir diccionario de actualización usando fecha_dt
                update_data = {
                    "invoice_date": fecha_dt,      # <--- AQUÍ USAMOS EL DATETIME
                    "imputation_date": fecha_dt,   # <--- AQUÍ TAMBIÉN (esto causaba el error)
                    "invoice_number":  invoice_num,
                    "rnc":  rnc,
                    "third_party_name": tercero,
                    "currency": currency,
                    "itbis": itbis,
                    "total_amount": total,
                    "total_amount_rd": total_rd,  # Recalcular total en RD
                    "exchange_rate": exchange,
                    "attachment_path": attach,
                }
                if attach_storage is not None: 
                    update_data["attachment_storage_path"] = attach_storage

                ok, msg = True, "Actualizado en Firebase."
                try:
                    doc_ref. update(update_data)
                except Exception as e:
                    ok, msg = False, f"Error actualizando factura: {e}"
                return ok, msg

            # Crear diálogo
            if tipo == "emitida":
                dlg = AddInvoiceWindowQt(
                    parent=parent,
                    controller=self,
                    tipo_factura="emitida",
                    on_save=on_save,
                )
            else:
                dlg = AddExpenseWindowQt(
                    parent=parent,
                    controller=self,
                    on_save=on_save,
                )

            # Inyectar datos
            loaded = False
            for attr in ("load_from_dict", "set_form_data", "set_initial_data"):
                fn = getattr(dlg, attr, None)
                if callable(fn):
                    try:
                        fn(data)
                        loaded = True
                        break
                    except Exception as e: 
                        print(f"[FIREBASE] Error usando {attr}: {e}")

            if not loaded and hasattr(dlg, "set_data") and callable(getattr(dlg, "set_data")):
                try:
                    dlg.set_data(data)
                except Exception: 
                    pass

            dlg.exec()

    def delete_invoice_by_number(self, invoice_number: str, parent=None):
        """
        Elimina una factura por invoice_number (y empresa activa).
        También intenta borrar el adjunto en Storage si existe attachment_storage_path.
        """
        if not self._db or not self.active_company_id:
            raise RuntimeError("Firestore o empresa activa no disponibles.")

        doc_ref, data = self._find_invoice_doc_by_number(invoice_number)
        if not doc_ref or not data:
            raise RuntimeError("Factura no encontrada en Firebase.")

        # Borrar adjunto en Storage si existe
        try:
            storage_path = data.get("attachment_storage_path") or data.get("storage_path")
            if self._bucket and storage_path:
                sp = str(storage_path).replace("\\", "/")
                blob = self._bucket.blob(sp)
                try:
                    blob.delete()
                except Exception:
                    print(f"[FIREBASE] No se pudo borrar blob {sp}")
        except Exception as e:
            print(f"[FIREBASE] Error al intentar borrar adjunto: {e}")

        # Borrar el doc de Firestore
        try:
            doc_ref.delete()
        except Exception as e:
            raise RuntimeError(f"No se pudo borrar el documento en Firestore: {e}")

    def view_invoice_attachment_by_number(self, invoice_number: str, parent=None):
        """
        Abre el adjunto de la factura:
        - Si tiene attachment_storage_path => bajar de Storage a temp y abrir.
        - Si no, intenta attachment_path local.
        """
        import tempfile
        import webbrowser

        if not self._db:
            raise RuntimeError("Firestore no está inicializado.")

        doc_ref, data = self._find_invoice_doc_by_number(invoice_number)
        if not doc_ref or not data:
            raise RuntimeError("Factura no encontrada en Firebase.")

        # 1) Intentar desde Storage
        storage_path = data.get("attachment_storage_path") or data.get("storage_path")
        if self._bucket and storage_path:
            try:
                sp = str(storage_path).replace("\\", "/")
                blob = self._bucket.blob(sp)
                if not blob.exists():
                    raise RuntimeError("El adjunto en Storage no existe.")
                tmp_dir = tempfile.mkdtemp(prefix="facturas_attach_")
                local_name = os.path.basename(sp) or f"{invoice_number}.bin"
                local_path = os.path.join(tmp_dir, local_name)
                blob.download_to_filename(local_path)
                webbrowser.open(local_path)
                return
            except Exception as e:
                print(f"[FIREBASE] Error obteniendo adjunto desde Storage: {e}")

        # 2) Fallback: ruta local (attachment_path)
        local_path = data.get("attachment_path")
        if local_path and os.path.exists(local_path):
            webbrowser.open(local_path)
            return

        raise RuntimeError("La factura no tiene adjunto disponible.")
    
    # ==================================================================
    #  Reportes PDF para tax_calculations usando report_generator
    # ==================================================================

    def generate_tax_calculation_pdf(self, calc_id, output_path: str) -> tuple[bool, str]:
        """
        Genera un reporte PDF para un cálculo de impuestos (tax_calculation)
        utilizando report_generator.generate_tax_calculation_pdf(report_data, output_path).
        """
        if not self._db:
            return False, "Firestore no está inicializado."

        if calc_id is None:
            return False, "ID de cálculo inválido."

        try:
            import report_generator
        except Exception as e:
            return False, f"No se pudo importar report_generator: {e}"

        # 1) Obtener cálculo y detalles desde Firebase
        details = self.get_tax_calculation_details(calc_id)
        if not details:
            return False, "No se encontraron datos para el cálculo solicitado."

        main = details.get("main") or {}
        det_map = details.get("details") or {}

        company_id = main.get("company_id") or self.active_company_id
        if not company_id:
            return False, "No hay empresa asociada al cálculo."

        # 2) Obtener facturas emitidas para el rango de fechas del cálculo
        start_date = main.get("start_date")
        end_date = main.get("end_date")
        if not (start_date and end_date):
            return False, "El cálculo no tiene rango de fechas definido."

        emitted_invoices = self.get_emitted_invoices_for_period(
            company_id=company_id,
            start_date=str(start_date),
            end_date=str(end_date),
        )

        if not emitted_invoices:
            return False, "No hay facturas emitidas en el periodo del cálculo."

        # 3) Marcar en cada factura si está incluida / retenida según det_map
        for inv in emitted_invoices:
            inv_id = inv.get("id")
            sel_info = det_map.get(inv_id) or det_map.get(str(inv_id)) or {}
            inv["selected_for_calc"] = bool(sel_info.get("selected", False))
            inv["has_retention"] = bool(sel_info.get("retention", False))

        # 4) Preparar datos para report_generator
        try:
            calc_name = main.get("name") or f"Cálculo {calc_id}"
            percent = float(main.get("percent_to_pay", 0.0) or 0.0)
        except Exception:
            calc_name = f"Cálculo {calc_id}"
            percent = 0.0

        report_data = {
            "calculation": {
                "id": main.get("id", calc_id),
                "name": calc_name,
                "company_id": company_id,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "percent_to_pay": percent,
                "created_at": str(main.get("created_at", "")),
                "updated_at": str(main.get("updated_at", "")),
            },
            "invoices": emitted_invoices,
        }

        # 5) Llamar a la función del generador de reportes
        try:
            res = report_generator.generate_tax_calculation_pdf(
                report_data=report_data,
                output_path=output_path,
            )
        except TypeError:
            # Por si tu función no usa kwargs
            try:
                res = report_generator.generate_tax_calculation_pdf(
                    report_data, output_path
                )
            except Exception as e:
                return False, f"Error generando el PDF: {e}"
        except Exception as e:
            return False, f"Error generando el PDF: {e}"

        if isinstance(res, tuple) and len(res) >= 1:
            ok = bool(res[0])
            msg = res[1] if len(res) > 1 else ""
        else:
            ok = bool(res)
            msg = ""

        if not ok:
            return False, msg or "El generador de reportes devolvió error."

        return True, msg or f"Reporte generado en: {output_path}"


    def open_tax_calculation_pdf(self, calc_id, parent=None) -> None:
        """
        Helper para la UI (TaxCalculationManagementWindowQt):

        - Genera el PDF en una carpeta temporal.
        - Lo abre con el visor de PDFs del sistema.
        """
        import tempfile
        import webbrowser

        success = False
        message = ""

        try:
            tmp_dir = tempfile.mkdtemp(prefix="tax_calc_")
            file_name = f"tax_calculation_{calc_id}.pdf"
            pdf_path = os.path.join(tmp_dir, file_name)

            # Construir report_data enriqueciendo con company_name
            try:
                import report_generator
            except Exception as e:
                raise RuntimeError(f"No se pudo importar report_generator: {e}")

            details = self.get_tax_calculation_details(calc_id)
            if not details:
                raise RuntimeError("No se encontraron datos del cálculo.")

            main = details.get("main") or {}
            det_map = details.get("details") or {}

            company_id = main.get("company_id") or self.active_company_id
            company_name = getattr(self, "active_company_name", None)

            # Resolver nombre de empresa si no lo tenemos
            if not company_name and company_id and self._db:
                try:
                    doc = self._db.collection("companies").document(str(company_id)).get()
                    if doc.exists:
                        company_name = (doc.to_dict() or {}).get("name")
                except Exception:
                    company_name = None

            if company_name:
                main["company_name"] = company_name
            else:
                main["company_name"] = str(company_id or "")

            start_date = main.get("start_date")
            end_date = main.get("end_date")
            if not (start_date and end_date):
                raise RuntimeError("El cálculo no tiene rango de fechas definido.")

            emitted_invoices = self.get_emitted_invoices_for_period(
                company_id=company_id,
                start_date=str(start_date),
                end_date=str(end_date),
            )

            if not emitted_invoices:
                raise RuntimeError("No hay facturas emitidas en el periodo del cálculo.")

            # Marcar selección/retención según det_map
            for inv in emitted_invoices:
                inv_id = inv.get("id")
                sel_info = det_map.get(inv_id) or det_map.get(str(inv_id)) or {}
                inv["selected_for_calc"] = bool(sel_info.get("selected", False))
                inv["has_retention"] = bool(sel_info.get("retention", False))

            report_data = {
                "calculation": main,
                "invoices": emitted_invoices,
            }

            # Llamar generador
            res = report_generator.generate_tax_calculation_pdf(
                report_data=report_data,
                output_path=pdf_path,
            )
            if isinstance(res, tuple) and len(res) >= 1:
                success = bool(res[0])
                message = res[1] if len(res) > 1 else ""
            else:
                success = bool(res)
                message = ""

            if not success:
                QMessageBox = None
                try:
                    from PyQt6.QtWidgets import QMessageBox as _QMB
                    QMessageBox = _QMB
                except Exception:
                    pass
                if QMessageBox is not None and parent is not None:
                    QMessageBox.critical(
                        parent,
                        "Reporte",
                        message or "No se pudo generar el reporte.",
                    )
                else:
                    print("[FIREBASE-TAX] Error:", message)
                return

            webbrowser.open(pdf_path)
        except Exception as e:
            try:
                from PyQt6.QtWidgets import QMessageBox
                if parent is not None:
                    QMessageBox.critical(
                        parent,
                        "Reporte",
                        f"No se pudo generar/abrir el PDF: {e}",
                    )
                else:
                    print(f"[FIREBASE-TAX] No se pudo generar/abrir el PDF: {e}")
            except Exception:
                print(f"[FIREBASE-TAX] No se pudo generar/abrir el PDF: {e}")
                
    # ==================================================================
    #  Gestión de Utilidades y Gastos Adicionales
    # ==================================================================


    def get_additional_expenses(
        self,
        company_id: int | None,
        month_str: str | None,
        year_int: int | None,
    ) -> list[dict]:
        """Devuelve lista de gastos adicionales para una empresa y periodo."""
        if not self._db or not company_id: 
            return []

        try:
            col = self._db.collection("additional_expenses")

            if FieldFilter is not None:
                query = col.where(filter=FieldFilter("company_id", "==", int(company_id)))
                if year_int is not None:
                    query = query.where(filter=FieldFilter("year", "==", int(year_int)))
                if month_str is not None:
                    query = query.where(filter=FieldFilter("month", "==", str(month_str)))
            else:
                query = col.where("company_id", "==", int(company_id))
                if year_int is not None: 
                    query = query.where("year", "==", int(year_int))
                if month_str is not None:
                    query = query.where("month", "==", str(month_str))

            query = query.order_by("date", direction=firestore.Query.DESCENDING)

            docs = list(query.stream())

            results = []
            for d in docs:
                data = d.to_dict() or {}
                data["id"] = d.id
                results.append(data)

            return results

        except Exception as e:
            print(f"[FIREBASE-PROFIT] Error obteniendo gastos adicionales: {e}")
            return []


    def add_additional_expense(self, expense_data: dict) -> tuple[bool, str]:
        """Agrega un nuevo gasto adicional."""
        if not self._db:
            return False, "Firestore no está inicializado."

        try:
            from firebase_admin import firestore as fb_fs

            # Validar campos requeridos
            required = ["company_id", "year", "month", "concept", "amount", "date"]
            for field in required: 
                if field not in expense_data:
                    return False, f"Campo requerido faltante: {field}"

            # Agregar timestamps
            expense_data["created_at"] = fb_fs. SERVER_TIMESTAMP
            expense_data["updated_at"] = fb_fs.SERVER_TIMESTAMP

            # Normalizar fecha a datetime si es necesario
            if isinstance(expense_data. get("date"), datetime.date) and not isinstance(
                expense_data.get("date"), datetime.datetime
            ):
                d = expense_data["date"]
                expense_data["date"] = datetime.datetime(d.year, d.month, d.day)

            # Guardar
            col = self._db.collection("additional_expenses")
            doc_ref = col. document()
            doc_ref.set(expense_data)

            return True, "Gasto adicional registrado correctamente."

        except Exception as e:
            print(f"[FIREBASE-PROFIT] Error agregando gasto:  {e}")
            return False, f"Error al agregar gasto:  {e}"


    def update_additional_expense(
        self, expense_id: str, expense_data: dict
    ) -> tuple[bool, str]:
        """Actualiza un gasto adicional existente."""
        if not self._db:
            return False, "Firestore no está inicializado."

        try:
            from firebase_admin import firestore as fb_fs

            # Normalizar fecha
            if isinstance(expense_data. get("date"), datetime.date) and not isinstance(
                expense_data.get("date"), datetime.datetime
            ):
                d = expense_data["date"]
                expense_data["date"] = datetime.datetime(d.year, d.month, d.day)

            # Actualizar timestamp
            expense_data["updated_at"] = fb_fs.SERVER_TIMESTAMP

            # Actualizar
            doc_ref = self._db.collection("additional_expenses").document(str(expense_id))
            doc_ref.update(expense_data)

            return True, "Gasto actualizado correctamente."

        except Exception as e:
            print(f"[FIREBASE-PROFIT] Error actualizando gasto: {e}")
            return False, f"Error al actualizar gasto: {e}"


    def delete_additional_expense(self, expense_id: str) -> tuple[bool, str]:
        """Elimina un gasto adicional."""
        if not self._db:
            return False, "Firestore no está inicializado."

        try:
            doc_ref = self._db.collection("additional_expenses").document(str(expense_id))
            doc_ref.delete()

            return True, "Gasto eliminado correctamente."

        except Exception as e:
            print(f"[FIREBASE-PROFIT] Error eliminando gasto: {e}")
            return False, f"Error al eliminar gasto: {e}"


    # ========================================================================
    # GASTOS ADICIONALES ACUMULATIVOS (SISTEMA ANUAL)
    # ========================================================================


    def _normalize_company_id(self, company_id_or_name) -> str:
        """
        Normaliza el company_id para asegurar consistencia.
        
        - Si recibe un número, lo convierte a string y busca el nombre
        - Si recibe un nombre, lo sanitiza
        - Devuelve el ID normalizado (nombre sanitizado)
        """
        if not company_id_or_name: 
            return ""
        
        # Convertir a string
        company_id_str = str(company_id_or_name)
        
        # Si es un número (ej: "1", "2"), buscar el nombre real
        if company_id_str.isdigit():
            try:
                doc = self._db.collection("companies").document(company_id_str).get()
                if doc.exists:
                    company_name = doc.to_dict().get("name", "")
                    if company_name:
                        # Sanitizar nombre
                        company_id_str = company_name.lower().replace(" ", "_")
                        company_id_str = "".join(c for c in company_id_str if c.isalnum() or c == "_")
                        return company_id_str
            except Exception as e:
                print(f"[NORMALIZE_ID] Error buscando empresa {company_id_str}: {e}")
        
        # Si ya es un nombre sanitizado, devolverlo
        if "_" in company_id_str and company_id_str.islower():
            return company_id_str
        
        # Sanitizar si es nombre sin sanitizar
        company_id_str = company_id_str.lower().replace(" ", "_")
        company_id_str = "". join(c for c in company_id_str if c.isalnum() or c == "_")
        
        return company_id_str

    def get_annual_expense_concepts(
        self,
        company_id,
        year:  int
    ) -> list[dict]:
        """Obtiene todos los conceptos anuales de una empresa para un año."""
        if not self._db:
            return []

        try: 
            from google.cloud.firestore_v1.base_query import FieldFilter
            
            # ✅ Normalizar company_id
            normalized_id = self._normalize_company_id(company_id)
            
            print(f"[GET_CONCEPTS] Original:  {company_id}, Normalizado: {normalized_id}, Año: {year}")
            
            concepts_ref = (
                self._db.collection("annual_additional_expenses")
                .where(filter=FieldFilter("company_id", "==", normalized_id))
                .where(filter=FieldFilter("year", "==", year))
            )
            
            docs = concepts_ref.stream()
            
            concepts = []
            for doc in docs:
                data = doc. to_dict()
                data["id"] = doc.id
                concepts.append(data)
                print(f"  ✅ {data.get('concept')}")
            
            print(f"[GET_CONCEPTS] Total:  {len(concepts)}")
            return concepts

        except Exception as e:
            print(f"[GET_CONCEPTS] Error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_expense_value_for_month(
        self,
        company_id,
        year:  int,
        month_str: str
    ) -> float:
        """
        Obtiene el valor ACUMULADO de gastos adicionales hasta un mes específico.
        
        Args:
            company_id: ID de la empresa
            year:  Año
            month_str: Mes en formato "01", "02", etc.
        
        Returns:
            Suma de todos los conceptos acumulados hasta ese mes
        """
        if not self._db:
            return 0.0

        try:
            from google.cloud. firestore_v1.base_query import FieldFilter
            
            # Normalizar company_id
            normalized_id = self._normalize_company_id(company_id)
            
            # Obtener todos los conceptos del año
            concepts_ref = (
                self._db.collection("annual_additional_expenses")
                .where(filter=FieldFilter("company_id", "==", normalized_id))
                .where(filter=FieldFilter("year", "==", year))
            )
            
            docs = concepts_ref.stream()
            
            total = 0.0
            
            for doc in docs:
                data = doc.to_dict()
                monthly_values = data.get("monthly_values", {})
                
                # Obtener valor del mes específico
                value = float(monthly_values.get(month_str, 0.0) or 0.0)
                
                # Si no hay valor, buscar el último mes anterior
                if value == 0.0:
                    month_int = int(month_str)
                    for m in range(month_int - 1, 0, -1):
                        m_str = f"{m:02d}"
                        if m_str in monthly_values:
                            value = float(monthly_values[m_str] or 0.0)
                            break
                
                total += value
                
                print(f"  [EXPENSE_VALUE] {data.get('concept')}: RD$ {value:,.2f}")
            
            print(f"[EXPENSE_VALUE] Total mes {month_str}: RD$ {total:,.2f}")
            return total

        except Exception as e:
            print(f"[EXPENSE_VALUE] Error:  {e}")
            import traceback
            traceback.print_exc()
            return 0.0



    def update_annual_expense_value(
        self,
        company_id,
        year:  int,
        month_str: str,
        concept_name: str,
        category:  str,
        value: float,
        note: str = ""
    ) -> tuple[bool, str]:
        """
        Actualiza o crea el valor acumulado de un concepto anual para un mes. 
        
        Args:
            company_id: ID de la empresa
            year:  Año
            month_str: Mes en formato "01", "02", etc.
            concept_name: Nombre del concepto
            category:  Categoría
            value: Valor acumulado hasta ese mes
            note: Nota opcional del mes
        
        Returns:
            (success, message)
        """
        if not self._db:
            return False, "Base de datos no inicializada."

        try:
            # Normalizar company_id
            normalized_id = self._normalize_company_id(company_id)
            
            # Generar concept_id desde el nombre
            concept_id = concept_name.lower().replace(" ", "_")
            concept_id = "". join(c for c in concept_id if c.isalnum() or c == "_")
            
            # ID del documento
            doc_id = f"{normalized_id}_{year}_{concept_id}"
            
            print(f"[UPDATE_ANNUAL_EXPENSE] ===== INICIO =====")
            print(f"[UPDATE_ANNUAL_EXPENSE] Empresa: {normalized_id}")
            print(f"[UPDATE_ANNUAL_EXPENSE] Año: {year}, Mes: {month_str}")
            print(f"[UPDATE_ANNUAL_EXPENSE] Concepto: {concept_name} (ID: {concept_id})")
            print(f"[UPDATE_ANNUAL_EXPENSE] Categoría: {category}")
            print(f"[UPDATE_ANNUAL_EXPENSE] Valor:  {value:.2f}")
            print(f"[UPDATE_ANNUAL_EXPENSE] Doc ID: {doc_id}")
            
            doc_ref = self._db.collection("annual_additional_expenses").document(doc_id)
            doc_snap = doc_ref.get()
            
            if doc_snap. exists: 
                # Actualizar documento existente
                data = doc_snap.to_dict()
                monthly_values = data.get("monthly_values", {})
                monthly_notes = data.get("monthly_notes", {})
                
                # Actualizar valor del mes
                monthly_values[month_str] = value
                
                # Actualizar nota si hay
                if note:
                    monthly_notes[month_str] = note
                elif month_str in monthly_notes: 
                    del monthly_notes[month_str]
                
                doc_ref.update({
                    "monthly_values": monthly_values,
                    "monthly_notes": monthly_notes,
                    "category": category,  # Actualizar categoría por si cambió
                    "updated_at":  self._get_timestamp(),
                })
                
                print(f"[UPDATE_ANNUAL_EXPENSE] ✅ Actualizado correctamente")
                return True, f"Concepto '{concept_name}' actualizado para {month_str}/{year}."
            
            else:
                # Crear nuevo documento
                monthly_values = {f"{m:02d}": 0.0 for m in range(1, 13)}
                monthly_values[month_str] = value
                
                monthly_notes = {}
                if note:
                    monthly_notes[month_str] = note
                
                doc_ref.set({
                    "company_id": normalized_id,
                    "year": year,
                    "concept_id": concept_id,
                    "concept": concept_name,
                    "category": category,
                    "monthly_values": monthly_values,
                    "monthly_notes": monthly_notes,
                    "created_at": self._get_timestamp(),
                    "updated_at": self._get_timestamp(),
                })
                
                print(f"[UPDATE_ANNUAL_EXPENSE] ✅ Creado correctamente")
                return True, f"Concepto '{concept_name}' creado para {month_str}/{year}."

        except Exception as e:
            print(f"[UPDATE_ANNUAL_EXPENSE] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error al actualizar concepto: {e}"

    def delete_annual_expense_concept(
        self,
        concept_id: str
    ) -> tuple[bool, str]:
        """
        Elimina un concepto anual completo (todos sus meses).
        """
        if not self._db:
            return False, "Base de datos no inicializada."

        try:
            self._db.collection("annual_additional_expenses").document(concept_id).delete()
            return True, "Concepto eliminado correctamente."
        except Exception as e:
            print(f"[DELETE_ANNUAL_CONCEPT] Error: {e}")
            return False, f"Error al eliminar concepto: {e}"

    def get_expense_monthly_history(
        self,
        concept_id: str
    ) -> dict: 
        """
        Obtiene el histórico mensual completo de un concepto.
        
        Returns:
            {
                "concept":  "Depreciación",
                "monthly_values": {"01": 50000, "02": 55000, ... },
                "monthly_notes":  {"01": "Base inicial", ... }
            }
        """
        if not self._db:
            return {}

        try:
            doc = self._db.collection("annual_additional_expenses").document(concept_id).get()
            if doc.exists:
                return doc.to_dict()
            return {}
        except Exception as e: 
            print(f"[GET_HISTORY] Error: {e}")
            return {}

    def get_annual_expense_summary(
        self,
        company_id: int,
        year: int
    ) -> dict:
        """
        Genera un resumen completo del año con valores por mes.
        
        Returns:
            {
                "concepts": [
                    {
                        "name": "Depreciación",
                        "values": [50000, 55000, 53000, ...],  # 12 meses
                        "total_year": 636000
                    },
                    ... 
                ],
                "monthly_totals": [145000, 245000, ... ],  # Total por mes
                "grand_total": 2500000
            }
        """
        concepts = self.get_annual_expense_concepts(company_id, year)
        
        summary = {
            "concepts": [],
            "monthly_totals":  [0.0] * 12,
            "grand_total": 0.0
        }
        
        for concept_data in concepts:
            concept_name = concept_data. get("concept", "")
            monthly_values_dict = concept_data.get("monthly_values", {})
            
            # Crear array de 12 meses
            values = []
            last_value = 0.0
            
            for month in range(1, 13):
                month_str = f"{month:02d}"
                if month_str in monthly_values_dict: 
                    last_value = float(monthly_values_dict[month_str] or 0.0)
                values.append(last_value)
            
            # ✅ CORREGIDO: Calcular total del año como el valor máximo acumulado
            # (buscar el último mes con datos, no asumir diciembre)
            total_year = max(values) if values else 0.0
            
            summary["concepts"].append({
                "name": concept_name,
                "category": concept_data.get("category", ""),
                "values":  values,
                "total_year": total_year
            })
            
            # Sumar a totales mensuales
            for i, val in enumerate(values):
                summary["monthly_totals"][i] += val
        
        # ✅ CORREGIDO: Gran total como máximo acumulado, no solo diciembre
        summary["grand_total"] = max(summary["monthly_totals"]) if summary["monthly_totals"] else 0.0
        
        return summary

    # ========================================================================
    # GESTIÓN DE INGRESOS ADICIONALES (Paralelo a gastos, pero SUMA en lugar de restar)
    # ========================================================================

    def get_annual_income_concepts(
        self, company_id: int, year: int
    ) -> list[dict]:
        """
        Obtiene todos los conceptos de ingresos adicionales del año especificado.
        Similar a get_annual_expense_concepts pero para ingresos.
        """
        if not self._db or not company_id:
            return []

        try:
            concepts_ref = (
                self._db.collection("companies")
                .document(str(company_id))
                .collection("annual_additional_income")
            )
            
            docs = concepts_ref.stream()
            result = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                result.append(data)
            
            return result
        except Exception as e:
            print(f"Error al obtener conceptos de ingresos: {e}")
            return []

    def create_annual_income_concept(
        self,
        company_id: int,
        year: int,
        month_str: str,
        name: str,
        category: str = "",
        description: str = "",
        initial_value: float = 0.0,
    ):
        """
        Crea un nuevo concepto de ingreso adicional.
        Similar a create_annual_expense_concept.
        """
        if not self._db or not company_id:
            raise Exception("Base de datos no disponible")

        concepts_ref = (
            self._db.collection("companies")
            .document(str(company_id))
            .collection("annual_additional_income")
        )

        # Calcular valor acumulado
        current_month_int = int(month_str)
        months_data = {}
        accumulated_value = 0.0
        
        for m in range(1, 13):
            m_str = f"{m:02d}"
            if m <= current_month_int:
                accumulated_value += initial_value
            months_data[m_str] = accumulated_value

        doc_data = {
            "name": name,
            "category": category,
            "description": description,
            "months": {str(year): months_data}
        }

        concepts_ref.add(doc_data)

    def update_annual_income_value(
        self,
        company_id: int,
        year: int,
        month_str: str,
        concept_id: str,
        new_value: float,
    ):
        """
        Actualiza el valor de un ingreso adicional para un mes específico (acumulativo).
        Similar a update_annual_expense_value.
        """
        if not self._db or not company_id:
            raise Exception("Base de datos no disponible")

        concept_ref = (
            self._db.collection("companies")
            .document(str(company_id))
            .collection("annual_additional_income")
            .document(concept_id)
        )

        doc = concept_ref.get()
        if not doc.exists:
            raise Exception("Concepto no encontrado")

        data = doc.to_dict()
        months_data = data.get("months", {}).get(str(year), {})

        # Recalcular acumulados
        current_month_int = int(month_str)
        prev_accumulated = 0.0
        
        if current_month_int > 1:
            prev_month_str = f"{current_month_int - 1:02d}"
            prev_accumulated = months_data.get(prev_month_str, 0.0)

        # Nuevo valor acumulado
        new_accumulated = prev_accumulated + new_value

        # Actualizar meses desde el actual hacia adelante
        for m in range(current_month_int, 13):
            m_str = f"{m:02d}"
            if m == current_month_int:
                months_data[m_str] = new_accumulated
            else:
                # Propagar diferencia
                old_val = months_data.get(m_str, 0.0)
                if old_val > 0:
                    old_base = months_data.get(f"{current_month_int - 1:02d}", 0.0) if current_month_int > 1 else 0.0
                    diff = old_val - old_base
                    months_data[m_str] = new_accumulated + diff
                else:
                    months_data[m_str] = new_accumulated

        # Guardar
        if "months" not in data:
            data["months"] = {}
        data["months"][str(year)] = months_data

        concept_ref.set(data)

    def delete_annual_income_concept(self, company_id: int, concept_id: str):
        """
        Elimina un concepto de ingreso adicional.
        """
        if not self._db or not company_id:
            raise Exception("Base de datos no disponible")

        concept_ref = (
            self._db.collection("companies")
            .document(str(company_id))
            .collection("annual_additional_income")
            .document(concept_id)
        )

        concept_ref.delete()

    def get_annual_income_summary(
        self, company_id: int, year: int
    ) -> dict:
        """
        Obtiene resumen de ingresos adicionales por mes (12 meses + gran total).
        Similar a get_annual_expense_summary.
        """
        if not self._db or not company_id:
            return {
                "concepts": [],
                "monthly_totals": [0.0] * 12,
                "grand_total": 0.0
            }

        concepts = self.get_annual_income_concepts(company_id, year)
        
        summary = {
            "concepts": [],
            "monthly_totals": [0.0] * 12,
            "grand_total": 0.0
        }

        for concept in concepts:
            name = concept.get("name", "")
            monthly_values = concept.get("months", {}).get(str(year), {})
            
            values = []
            for m in range(1, 13):
                m_str = f"{m:02d}"
                val = float(monthly_values.get(m_str, 0.0) or 0.0)
                values.append(val)
            
            # Total año: máximo acumulado (no diciembre que podría ser 0)
            total_year = max(values) if values else 0.0
            
            summary["concepts"].append({
                "name": name,
                "category": concept.get("category", ""),
                "values": values,
                "total_year": total_year
            })
            
            # Sumar a totales mensuales
            for i, val in enumerate(values):
                summary["monthly_totals"][i] += val
        
        # Gran total como máximo acumulado
        summary["grand_total"] = max(summary["monthly_totals"]) if summary["monthly_totals"] else 0.0
        
        return summary

    def get_income_value_for_month(
        self, company_id: int, year: int, month_str: str
    ) -> float:
        """
        Obtiene el total de ingresos adicionales para un mes específico.
        Similar a get_expense_value_for_month.
        """
        if not self._db or not company_id:
            return 0.0

        try:
            concepts = self.get_annual_income_concepts(company_id, year)
            total = 0.0
            
            for concept in concepts:
                monthly_values = concept.get("months", {}).get(str(year), {})
                value = float(monthly_values.get(month_str, 0.0) or 0.0)
                total += value
            
            return total
        except Exception as e:
            print(f"Error al obtener ingresos del mes: {e}")
            return 0.0

    # ========================================================================
    # COMPATIBILIDAD CON SISTEMA ANTERIOR (get_profit_summary)
    # ========================================================================

    def get_profit_summary(
        self,
        company_id: int | None,
        month_str: str | None,
        year_int: int | None,
    ) -> dict:
        """
        Devuelve resumen de utilidades.
        ACTUALIZADO para usar gastos acumulativos.
        """
        # ✅ DEBUG:  Mostrar parámetros de entrada
        print(f"[PROFIT_SUMMARY] ===== INICIO =====")
        print(f"[PROFIT_SUMMARY] company_id: {company_id}")
        print(f"[PROFIT_SUMMARY] month_str: {month_str}")
        print(f"[PROFIT_SUMMARY] year_int: {year_int}")
        
        if not self._db or not company_id: 
            print(f"[PROFIT_SUMMARY] ❌ DB o company_id inválido")
            return {
                "total_income": 0.0,
                "total_expense":  0.0,
                "additional_expenses": 0.0,
                "net_profit":  0.0,
            }

        # Obtener ingresos y gastos de facturas
        invoices = self._query_invoices(
            company_id=company_id,
            month_str=month_str,
            year_int=year_int,
            tx_type=None,
        )
        
        print(f"[PROFIT_SUMMARY] Total facturas encontradas: {len(invoices)}")

        def _fx(inv: dict) -> float:
            try: 
                rate = float(inv. get("exchange_rate", 1.0) or 1.0)
                return rate if rate != 0 else 1.0
            except: 
                return 1.0

        total_income = 0.0
        total_expense = 0.0

        for inv in invoices:
            tipo = inv.get("invoice_type")
            total_rd = float(inv.get("total_amount_rd", 0.0) or 0.0)
            if not total_rd:
                total_rd = float(inv.get("total_amount", 0.0) or 0.0) * _fx(inv)

            if tipo == "emitida": 
                total_income += total_rd
            elif tipo == "gasto":
                total_expense += total_rd
        
        print(f"[PROFIT_SUMMARY] Ingresos facturas: RD$ {total_income:,.2f}")
        print(f"[PROFIT_SUMMARY] Gastos facturas: RD$ {total_expense:,.2f}")

        # ✅ NUEVO: Obtener ingresos adicionales acumulativos
        additional_income = 0.0
        if year_int and month_str:
            additional_income = self.get_income_value_for_month(
                company_id=company_id,
                year=year_int,
                month_str=month_str
            )
        
        print(f"[PROFIT_SUMMARY] Ingresos adicionales acumulativos: RD$ {additional_income:,.2f}")

        # ✅ NUEVO: Obtener gastos acumulativos en lugar de gastos simples
        additional_expenses = 0.0
        if year_int and month_str:
            additional_expenses = self.get_expense_value_for_month(
                company_id=company_id,
                year=year_int,
                month_str=month_str
            )
        
        print(f"[PROFIT_SUMMARY] Gastos adicionales acumulativos: RD$ {additional_expenses:,.2f}")

        # ✅ NUEVA FÓRMULA: (Ingresos Facturados + Ingresos Adicionales) - (Gastos Facturados + Gastos Adicionales)
        net_profit = (total_income + additional_income) - (total_expense + additional_expenses)
        
        print(f"[PROFIT_SUMMARY] Utilidad neta: RD$ {net_profit:,.2f}")
        print(f"[PROFIT_SUMMARY] ===== FIN =====")

        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "additional_income": additional_income,  # ✅ NUEVO
            "additional_expenses": additional_expenses,
            "net_profit": net_profit,
        }


    def _get_additional_expenses_total(
        self,
        company_id: int,
        month_str: str | None,
        year_int:  int | None,
    ) -> float:
        """Helper:  suma total de gastos adicionales para un periodo."""
        expenses = self. get_additional_expenses(company_id, month_str, year_int)
        return sum(float(exp.get("amount", 0.0) or 0.0) for exp in expenses)
    
    # ========================================================================
    # CATÁLOGO MAESTRO DE CONCEPTOS
    # ========================================================================

    def get_concept_catalog(self) -> list[dict]:
        """
        Obtiene todos los conceptos del catálogo maestro.
        
        Returns:
            Lista de conceptos disponibles.
        """
        if not self._db:
            return []

        try:
            docs = self._db.collection("concept_catalog").where("is_active", "==", True).stream()
            
            concepts = []
            for doc in docs:
                data = doc.to_dict()
                data["concept_id"] = doc.id
                concepts.append(data)
            
            return concepts

        except Exception as e:
            print(f"[GET_CATALOG] Error: {e}")
            return []

    def create_concept_in_catalog(
        self,
        concept_id: str,
        display_name: str,
        category: str,
        description: str = ""
    ) -> tuple[bool, str]:
        """
        Crea un nuevo concepto en el catálogo maestro.
        
        Args:
            concept_id: ID único (ej: "depreciation_equipment")
            display_name: Nombre a mostrar (ej: "Depreciación Equipos")
            category:  Categoría (ej: "Depreciación")
            description: Descripción opcional
        """
        if not self._db:
            return False, "Base de datos no inicializada."

        try:
            doc_ref = self._db.collection("concept_catalog").document(concept_id)
            
            # Verificar si ya existe
            if doc_ref.get().exists:
                return False, f"El concepto '{display_name}' ya existe en el catálogo."
            
            doc_ref.set({
                "concept_id": concept_id,
                "display_name": display_name,
                "category":  category,
                "description": description,
                "is_active":  True,
                "created_at": self._get_timestamp(),
                "updated_at": self._get_timestamp(),
            })
            
            return True, f"Concepto '{display_name}' agregado al catálogo."

        except Exception as e:
            print(f"[CREATE_CONCEPT_CATALOG] Error: {e}")
            return False, f"Error al crear concepto: {e}"

    def propagate_concept_to_all_companies(
        self,
        concept_id: str,
        year: int
    ) -> tuple[bool, str]:
        """
        Propaga un concepto del catálogo a TODAS las empresas activas. 
        
        Args:
            concept_id: ID del concepto en el catálogo
            year:  Año para el cual crear las instancias
        
        Returns:
            (success, message)
        """
        if not self._db:
            return False, "Base de datos no inicializada."

        try:
            # Obtener concepto del catálogo
            concept_doc = self._db.collection("concept_catalog").document(concept_id).get()
            
            if not concept_doc.exists:
                return False, f"Concepto '{concept_id}' no existe en el catálogo."
            
            concept_data = concept_doc.to_dict()
            display_name = concept_data.get("display_name")
            category = concept_data. get("category")
            
            # Obtener todas las empresas
            companies = self. list_companies() or []
            
            if not companies:
                return False, "No hay empresas registradas."
            
            # Crear instancia para cada empresa
            count_created = 0
            count_exists = 0
            
            for company_name in companies:
                # Obtener company_id
                company_id = None
                try:
                    if hasattr(self, "get_company_id_by_name"):
                        company_id = self.get_company_id_by_name(company_name)
                    else: 
                        # Fallback:  usar nombre como ID
                        company_id = str(company_name).lower().replace(" ", "_")
                except: 
                    company_id = str(company_name).lower().replace(" ", "_")
                
                # Crear documento
                doc_id = f"{company_id}_{year}_{concept_id}"
                doc_ref = self._db.collection("annual_additional_expenses").document(doc_id)
                
                # Verificar si ya existe
                if doc_ref.get().exists:
                    count_exists += 1
                    continue
                
                # Crear con valores en 0
                monthly_values = {f"{m:02d}": 0.0 for m in range(1, 13)}
                
                doc_ref.set({
                    "company_id": str(company_id),
                    "year": year,
                    "concept_id": concept_id,
                    "concept":  display_name,
                    "category": category,
                    "monthly_values": monthly_values,
                    "monthly_notes":  {},
                    "created_at": self._get_timestamp(),
                    "updated_at": self._get_timestamp(),
                    "auto_propagated": True,
                })
                
                count_created += 1
            
            msg = f"Concepto '{display_name}' propagado:\n"
            msg += f"  • Creado en {count_created} empresa(s)\n"
            if count_exists > 0:
                msg += f"  • Ya existía en {count_exists} empresa(s)"
            
            return True, msg

        except Exception as e:
            print(f"[PROPAGATE_CONCEPT] Error: {e}")
            return False, f"Error al propagar concepto: {e}"

    def create_and_propagate_concept(
        self,
        concept_id:  str,
        display_name:  str,
        category: str,
        year: int,
        description: str = ""
    ) -> tuple[bool, str]:
        """
        Crea un concepto en el catálogo Y lo propaga a todas las empresas.
        
        Este es el método principal que se usa desde la UI.
        """
        # Paso 1: Crear en catálogo
        ok, msg = self.create_concept_in_catalog(
            concept_id, display_name, category, description
        )
        
        if not ok:
            # Si ya existe, solo propagar
            if "ya existe" in msg. lower():
                pass  # Continuar con propagación
            else:
                return False, msg
        
        # Paso 2: Propagar a todas las empresas
        ok2, msg2 = self.propagate_concept_to_all_companies(concept_id, year)
        
        if ok2:
            return True, f"{msg}\n{msg2}"
        else: 
            return False, f"{msg}\n{msg2}"

    def initialize_concepts_for_new_company(
        self,
        company_id: str,
        year: int
    ) -> tuple[bool, str]:
        """
        Inicializa TODOS los conceptos del catálogo para una nueva empresa. 
        
        Usar cuando se crea una empresa nueva.
        """
        if not self._db:
            return False, "Base de datos no inicializada."

        try:
            # Obtener todos los conceptos del catálogo
            concepts = self.get_concept_catalog()
            
            if not concepts:
                return True, "No hay conceptos en el catálogo para inicializar."
            
            count_created = 0
            
            for concept in concepts:
                concept_id = concept. get("concept_id")
                display_name = concept.get("display_name")
                category = concept.get("category")
                
                doc_id = f"{company_id}_{year}_{concept_id}"
                doc_ref = self._db.collection("annual_additional_expenses").document(doc_id)
                
                # Solo crear si no existe
                if not doc_ref.get().exists:
                    monthly_values = {f"{m:02d}": 0.0 for m in range(1, 13)}
                    
                    doc_ref.set({
                        "company_id":  str(company_id),
                        "year": year,
                        "concept_id": concept_id,
                        "concept": display_name,
                        "category": category,
                        "monthly_values": monthly_values,
                        "monthly_notes": {},
                        "created_at":  self._get_timestamp(),
                        "updated_at": self._get_timestamp(),
                        "auto_propagated": True,
                    })
                    
                    count_created += 1
            
            return True, f"Inicializados {count_created} conceptos para la nueva empresa."

        except Exception as e: 
            print(f"[INIT_CONCEPTS] Error: {e}")
            return False, f"Error al inicializar conceptos:  {e}"
        
    # ========================================================================
    # SISTEMA CONTABLE PROFESIONAL
    # ========================================================================

    def get_chart_of_accounts(self, company_id) -> list[dict]:
        """Obtiene el plan de cuentas de una empresa."""
        if not self._db:
            return []

        try:
            from google.cloud. firestore_v1.base_query import FieldFilter
            
            normalized_id = self._normalize_company_id(company_id)
            
            accounts_ref = (
                self._db.collection("chart_of_accounts")
                .where(filter=FieldFilter("company_id", "==", normalized_id))
                .where(filter=FieldFilter("is_active", "==", True))
                .order_by("account_code")
            )
            
            docs = accounts_ref.stream()
            
            accounts = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                accounts.append(data)
            
            return accounts

        except Exception as e:
            print(f"[CHART_ACCOUNTS] Error:  {e}")
            import traceback
            traceback.print_exc()
            return []

    def create_account(
        self,
        company_id,
        account_code:  str,
        account_name:  str,
        account_type:  str,
        category: str,
        parent_account: str = None,
        level: int = 1,
        nature: str = "DEBITO",
        is_detail: bool = True
    ) -> tuple[bool, str]:
        """Crea una nueva cuenta en el plan de cuentas."""
        if not self._db:
            return False, "Base de datos no inicializada."

        try:
            normalized_id = self._normalize_company_id(company_id)
            
            # Verificar que no exista el código
            existing = self._db.collection("chart_of_accounts").where(
                "company_id", "==", normalized_id
            ).where(
                "account_code", "==", account_code
            ).limit(1).stream()
            
            if list(existing):
                return False, f"Ya existe una cuenta con el código {account_code}"
            
            # Crear cuenta
            account_data = {
                "account_code": account_code,
                "account_name": account_name,
                "account_type": account_type,
                "category": category,
                "parent_account": parent_account,
                "level": level,
                "nature": nature,
                "is_detail": is_detail,
                "company_id": normalized_id,
                "currency": "RD$",
                "is_active": True,
                "created_at": self._get_timestamp(),
                "updated_at":  self._get_timestamp(),
            }
            
            self._db.collection("chart_of_accounts").add(account_data)
            
            return True, f"Cuenta {account_code} - {account_name} creada correctamente."

        except Exception as e:
            print(f"[CREATE_ACCOUNT] Error: {e}")
            return False, f"Error al crear cuenta: {e}"

    def initialize_default_chart_of_accounts(self, company_id, year:  int) -> tuple[bool, str]:
        """Inicializa el plan de cuentas estándar para República Dominicana."""
        if not self._db:
            return False, "Base de datos no inicializada."

        try:
            normalized_id = self._normalize_company_id(company_id)
            
            # Plan de cuentas estándar (versión resumida para demo)
            default_accounts = [
                # ACTIVOS
                ("1.0.0.000", "ACTIVOS", "ACTIVO", "GRUPO", None, 1, "DEBITO", False),
                ("1.1.0.000", "ACTIVOS CORRIENTES", "ACTIVO", "ACTIVO_CORRIENTE", "1.0.0.000", 2, "DEBITO", False),
                ("1.1.1.000", "Efectivo y Equivalentes", "ACTIVO", "EFECTIVO", "1.1.0.000", 3, "DEBITO", False),
                ("1.1.1.001", "Caja General", "ACTIVO", "EFECTIVO", "1.1.1.000", 4, "DEBITO", True),
                ("1.1.1.002", "Banco BHD León", "ACTIVO", "EFECTIVO", "1.1.1.000", 4, "DEBITO", True),
                ("1.1.1.003", "Banco Popular", "ACTIVO", "EFECTIVO", "1.1.1.000", 4, "DEBITO", True),
                
                ("1.1.2.000", "Cuentas por Cobrar", "ACTIVO", "CUENTAS_COBRAR", "1.1.0.000", 3, "DEBITO", False),
                ("1.1.2.001", "Clientes Nacionales", "ACTIVO", "CUENTAS_COBRAR", "1.1.2.000", 4, "DEBITO", True),
                ("1.1.2.002", "Clientes Extranjeros", "ACTIVO", "CUENTAS_COBRAR", "1.1.2.000", 4, "DEBITO", True),
                ("1.1.2.003", "(-) Provisión Cuentas Incobrables", "ACTIVO", "CUENTAS_COBRAR", "1.1.2.000", 4, "CREDITO", True),
                
                ("1.1.4.000", "Otros Activos Corrientes", "ACTIVO", "OTROS_CORRIENTES", "1.1.0.000", 3, "DEBITO", False),
                ("1.1.4.001", "ITBIS por Compensar", "ACTIVO", "OTROS_CORRIENTES", "1.1.4.000", 4, "DEBITO", True),
                
                ("1.2.0.000", "ACTIVOS NO CORRIENTES", "ACTIVO", "ACTIVO_NO_CORRIENTE", "1.0.0.000", 2, "DEBITO", False),
                ("1.2.1.000", "Propiedad, Planta y Equipo", "ACTIVO", "PP_E", "1.2.0.000", 3, "DEBITO", False),
                ("1.2.1.001", "Terrenos", "ACTIVO", "PP_E", "1.2.1.000", 4, "DEBITO", True),
                ("1.2.1.002", "Edificios", "ACTIVO", "PP_E", "1.2.1.000", 4, "DEBITO", True),
                ("1.2.1.003", "Equipos de Oficina", "ACTIVO", "PP_E", "1.2.1.000", 4, "DEBITO", True),
                ("1.2.1.004", "Vehículos", "ACTIVO", "PP_E", "1.2.1.000", 4, "DEBITO", True),
                ("1.2.1.005", "(-) Depreciación Acumulada", "ACTIVO", "PP_E", "1.2.1.000", 4, "CREDITO", True),
                
                # PASIVOS
                ("2.0.0.000", "PASIVOS", "PASIVO", "GRUPO", None, 1, "CREDITO", False),
                ("2.1.0.000", "PASIVOS CORRIENTES", "PASIVO", "PASIVO_CORRIENTE", "2.0.0.000", 2, "CREDITO", False),
                ("2.1.1.000", "Cuentas por Pagar", "PASIVO", "CUENTAS_PAGAR", "2.1.0.000", 3, "CREDITO", False),
                ("2.1.1.001", "Proveedores Locales", "PASIVO", "CUENTAS_PAGAR", "2.1.1.000", 4, "CREDITO", True),
                ("2.1.1.002", "Proveedores Extranjeros", "PASIVO", "CUENTAS_PAGAR", "2.1.1.000", 4, "CREDITO", True),
                
                ("2.1.2.000", "Impuestos por Pagar", "PASIVO", "IMPUESTOS_PAGAR", "2.1.0.000", 3, "CREDITO", False),
                ("2.1.2.001", "ITBIS por Pagar", "PASIVO", "IMPUESTOS_PAGAR", "2.1.2.000", 4, "CREDITO", True),
                ("2.1.2.002", "ISR por Pagar", "PASIVO", "IMPUESTOS_PAGAR", "2.1.2.000", 4, "CREDITO", True),
                ("2.1.2.003", "Retenciones por Pagar", "PASIVO", "IMPUESTOS_PAGAR", "2.1.2.000", 4, "CREDITO", True),
                
                ("2.1.4.000", "Otros Pasivos Corrientes", "PASIVO", "OTROS_CORRIENTES", "2.1.0.000", 3, "CREDITO", False),
                ("2.1.4.001", "Nómina por Pagar", "PASIVO", "OTROS_CORRIENTES", "2.1.4.000", 4, "CREDITO", True),
                
                ("2.2.0.000", "PASIVOS NO CORRIENTES", "PASIVO", "PASIVO_NO_CORRIENTE", "2.0.0.000", 2, "CREDITO", False),
                ("2.2.1.000", "Préstamos Largo Plazo", "PASIVO", "PRESTAMOS_LP", "2.2.0.000", 3, "CREDITO", False),
                ("2.2.1.001", "Préstamo Bancario LP", "PASIVO", "PRESTAMOS_LP", "2.2.1.000", 4, "CREDITO", True),
                
                # PATRIMONIO
                ("3.0.0.000", "PATRIMONIO", "PATRIMONIO", "GRUPO", None, 1, "CREDITO", False),
                ("3.1.0.000", "Capital Social", "PATRIMONIO", "CAPITAL", "3.0.0.000", 2, "CREDITO", False),
                ("3.1.1.001", "Capital Inicial", "PATRIMONIO", "CAPITAL", "3.1.0.000", 3, "CREDITO", True),
                
                ("3.2.0.000", "Reservas", "PATRIMONIO", "RESERVAS", "3.0.0.000", 2, "CREDITO", False),
                ("3.2.1.001", "Reserva Legal", "PATRIMONIO", "RESERVAS", "3.2.0.000", 3, "CREDITO", True),
                
                ("3.3.0.000", "Resultados", "PATRIMONIO", "RESULTADOS", "3.0.0.000", 2, "CREDITO", False),
                ("3.3.1.001", "Utilidades Retenidas", "PATRIMONIO", "RESULTADOS", "3.3.0.000", 3, "CREDITO", True),
                ("3.3.1.002", "Utilidad del Ejercicio", "PATRIMONIO", "RESULTADOS", "3.3.0.000", 3, "CREDITO", True),
                
                # INGRESOS
                ("4.0.0.000", "INGRESOS", "INGRESO", "GRUPO", None, 1, "CREDITO", False),
                ("4.1.0.000", "INGRESOS OPERACIONALES", "INGRESO", "INGRESO_OPERACIONAL", "4.0.0.000", 2, "CREDITO", False),
                ("4.1.1.001", "Ventas de Servicios", "INGRESO", "INGRESO_OPERACIONAL", "4.1.0.000", 3, "CREDITO", True),
                ("4.1.1.002", "Ventas de Productos", "INGRESO", "INGRESO_OPERACIONAL", "4.1.0.000", 3, "CREDITO", True),
                
                ("4.2.0.000", "OTROS INGRESOS", "INGRESO", "OTROS_INGRESOS", "4.0.0.000", 2, "CREDITO", False),
                ("4.2.1.001", "Intereses Ganados", "INGRESO", "OTROS_INGRESOS", "4.2.0.000", 3, "CREDITO", True),
                
                # GASTOS
                ("5.0.0.000", "GASTOS", "GASTO", "GRUPO", None, 1, "DEBITO", False),
                ("5.1.0.000", "COSTO DE VENTAS", "GASTO", "COSTO_VENTAS", "5.0.0.000", 2, "DEBITO", False),
                ("5.1.1.001", "Costo de Servicios", "GASTO", "COSTO_VENTAS", "5.1.0.000", 3, "DEBITO", True),
                
                ("5.2.0.000", "GASTOS OPERACIONALES", "GASTO", "GASTO_OPERACIONAL", "5.0.0.000", 2, "DEBITO", False),
                ("5.2.1.000", "Gastos Administrativos", "GASTO", "GASTO_ADMINISTRATIVO", "5.2.0.000", 3, "DEBITO", False),
                ("5.2.1.001", "Sueldos y Salarios", "GASTO", "GASTO_ADMINISTRATIVO", "5.2.1.000", 4, "DEBITO", True),
                ("5.2.1.002", "Alquiler", "GASTO", "GASTO_ADMINISTRATIVO", "5.2.1.000", 4, "DEBITO", True),
                ("5.2.1.003", "Servicios Públicos", "GASTO", "GASTO_ADMINISTRATIVO", "5.2.1.000", 4, "DEBITO", True),
                ("5.2.1.004", "Depreciación", "GASTO", "GASTO_ADMINISTRATIVO", "5.2.1.000", 4, "DEBITO", True),
                
                ("5.3.0.000", "GASTOS FINANCIEROS", "GASTO", "GASTO_FINANCIERO", "5.0.0.000", 2, "DEBITO", False),
                ("5.3.1.001", "Intereses Bancarios", "GASTO", "GASTO_FINANCIERO", "5.3.0.000", 3, "DEBITO", True),
                ("5.3.1.002", "Comisiones Bancarias", "GASTO", "GASTO_FINANCIERO", "5.3.0.000", 3, "DEBITO", True),
            ]
            
            created_count = 0
            for account in default_accounts:
                code, name, acc_type, category, parent, level, nature, is_detail = account
                
                account_data = {
                    "account_code": code,
                    "account_name": name,
                    "account_type":  acc_type,
                    "category": category,
                    "parent_account": parent,
                    "level": level,
                    "nature": nature,
                    "is_detail": is_detail,
                    "company_id": normalized_id,
                    "currency": "RD$",
                    "is_active": True,
                    "created_at": self._get_timestamp(),
                    "updated_at": self._get_timestamp(),
                }
                
                self._db.collection("chart_of_accounts").add(account_data)
                created_count += 1
            
            return True, f"Plan de cuentas inicializado con {created_count} cuentas."

        except Exception as e:
            print(f"[INIT_CHART] Error: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error al inicializar plan de cuentas: {e}"

    def get_account_balance(
        self,
        company_id,
        account_code:  str,
        year: int,
        month: int
    ) -> dict:
        """Obtiene el saldo de una cuenta para un periodo específico."""
        if not self._db:
            return {
                "opening_balance": 0.0,
                "total_debit": 0.0,
                "total_credit": 0.0,
                "closing_balance": 0.0,
            }

        try:
            normalized_id = self._normalize_company_id(company_id)
            
            # Reemplazar puntos por guiones bajos
            account_safe = account_code.replace(".", "_")
            
            # CONSTRUIR ID CON MES FORMATEADO
            month_formatted = str(month).zfill(2)
            balance_id = f"{normalized_id}_{year}_{month_formatted}_{account_safe}"
            
            print(f"[GET_BALANCE] Buscando: {balance_id}")
            
            # Obtener documento
            doc = self._db.collection("account_balances").document(balance_id).get()
            
            if doc.exists:
                data = doc.to_dict()
                closing = data.get('closing_balance', 0.0)
                print(f"[GET_BALANCE] ✅ Encontrado: {account_code} = {closing: ,.2f}")
                return data
            else:
                print(f"[GET_BALANCE] ⚠️ No existe documento:  {balance_id}")
                return {
                    "opening_balance": 0.0,
                    "total_debit": 0.0,
                    "total_credit": 0.0,
                    "closing_balance": 0.0,
                }

        except Exception as e:
            print(f"[GET_BALANCE] ❌ Error:  {e}")
            import traceback
            traceback.print_exc()
            return {
                "opening_balance": 0.0,
                "total_debit": 0.0,
                "total_credit": 0.0,
                "closing_balance": 0.0,
            }


    def recalculate_all_balances(self, company_id, year:  int):
        """
        Recalcula todos los saldos del año basándose en los asientos existentes.  
        
        USAR CON PRECAUCIÓN:  Borra y recrea todos los saldos. 
        """
        if not self._db:
            return False, "BD no inicializada"

        try:
            normalized_id = self._normalize_company_id(company_id)
            
            print(f"[RECALC] Recalculando saldos de {year}...")
            
            # Borrar saldos existentes del año
            from google.cloud. firestore_v1.base_query import FieldFilter
            
            existing_balances = (
                self._db.collection("account_balances")
                .where(filter=FieldFilter("company_id", "==", normalized_id))
                .where(filter=FieldFilter("year", "==", year))
                .stream()
            )
            
            for doc in existing_balances: 
                doc.reference.delete()
            
            print(f"[RECALC] Saldos anteriores borrados")
            
            # Obtener todos los asientos del año, ordenados por fecha
            entries = (
                self._db.collection("journal_entries")
                .where(filter=FieldFilter("company_id", "==", normalized_id))
                .where(filter=FieldFilter("year", "==", year))
                .order_by("entry_date")
                .stream()
            )
            
            count = 0
            for entry_doc in entries:
                entry = entry_doc.to_dict()
                lines = entry.get("lines", [])
                month = entry.get("month")
                
                # Actualizar saldos
                self._update_account_balances(normalized_id, year, month, lines)
                count += 1
            
            print(f"[RECALC] ✅ Recalculados {count} asientos")
            
            return True, f"Saldos recalculados correctamente ({count} asientos procesados)"

        except Exception as e:
            print(f"[RECALC] ❌ Error:  {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error:  {e}"
        

    def generate_journal_entries_from_invoices(
        self,
        company_id,
        year:  int,
        month: int = None
    ) -> tuple[bool, str]:
        """
        Genera asientos contables automáticamente a partir de las facturas del periodo.
        
        Args:
            company_id: ID de la empresa
            year:  Año
            month: Mes (opcional, si es None genera todo el año)
        
        Returns:
            (success, message)
        """
        if not self._db:
            return False, "Base de datos no inicializada."

        try:
            normalized_id = self._normalize_company_id(company_id)
            
            print(f"[AUTO_ENTRIES] Generando asientos para {normalized_id}, {year}-{month or 'TODO'}")
            
            # 1. Obtener facturas del periodo
            if month: 
                month_str = f"{month:02d}"
                invoices = self._query_invoices(
                    company_id=company_id,
                    month_str=month_str,
                    year_int=year,
                    tx_type=None
                )
            else:
                # Todo el año
                invoices = []
                for m in range(1, 13):
                    month_invoices = self._query_invoices(
                        company_id=company_id,
                        month_str=f"{m:02d}",
                        year_int=year,
                        tx_type=None
                    )
                    invoices.extend(month_invoices)
            
            if not invoices:
                return False, "No hay facturas en el periodo seleccionado."
            
            print(f"[AUTO_ENTRIES] Facturas encontradas: {len(invoices)}")
            
            # 2. Generar asientos por cada factura
            entries_created = 0
            errors = []
            
            for invoice in invoices:
                try: 
                    # Verificar si ya existe asiento para esta factura
                    existing = self._check_existing_entry_for_invoice(
                        normalized_id, 
                        invoice. get("invoice_number")
                    )
                    
                    if existing:
                        print(f"[AUTO_ENTRIES] ⏭️ Asiento ya existe para {invoice. get('invoice_number')}")
                        continue
                    
                    # Generar asiento según tipo
                    invoice_type = invoice.get("invoice_type")
                    
                    if invoice_type == "emitida":
                        ok, msg = self._create_entry_for_income_invoice(normalized_id, invoice)
                    elif invoice_type == "gasto": 
                        ok, msg = self._create_entry_for_expense_invoice(normalized_id, invoice)
                    else:
                        continue
                    
                    if ok:
                        entries_created += 1
                        print(f"[AUTO_ENTRIES] ✅ {invoice.get('invoice_number')}")
                    else:
                        errors.append(f"{invoice.get('invoice_number')}: {msg}")
                        print(f"[AUTO_ENTRIES] ❌ {invoice.get('invoice_number')}: {msg}")
                        
                except Exception as e:
                    errors.append(f"{invoice. get('invoice_number', 'UNKNOWN')}: {e}")
                    print(f"[AUTO_ENTRIES] ❌ Error: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 3. Resumen
            result_msg = f"Asientos creados: {entries_created} de {len(invoices)} facturas."
            
            if errors:
                result_msg += f"\n\nErrores ({len(errors)}):\n" + "\n".join(errors[: 5])
                if len(errors) > 5:
                    result_msg += f"\n... y {len(errors) - 5} más."
            
            return True, result_msg
            
        except Exception as e:
            print(f"[AUTO_ENTRIES] ❌ Error general: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error generando asientos: {e}"


    def _check_existing_entry_for_invoice(self, company_id: str, invoice_number: str) -> bool:
        """Verifica si ya existe un asiento para una factura."""
        if not self._db or not invoice_number:
            return False
        
        try:
            from google.cloud. firestore_v1.base_query import FieldFilter
            
            query = (
                self._db.collection("journal_entries")
                .where(filter=FieldFilter("company_id", "==", company_id))
                .where(filter=FieldFilter("reference", "==", invoice_number))
                .limit(1)
            )
            
            docs = list(query.stream())
            return len(docs) > 0
            
        except Exception as e: 
            print(f"[CHECK_ENTRY] Error:  {e}")
            return False


    def _create_entry_for_income_invoice(
        self, 
        company_id: str, 
        invoice: dict
    ) -> tuple[bool, str]: 
        """
        Crea asiento contable para factura de INGRESO.
        
        Asiento tipo: 
        ─────────────────────────────────────────────
        DEBE                        | HABER
        ─────────────────────────────────────────────
        Clientes Nacionales  XXX   |
                                    | Ventas Servicios  XXX
                                    | ITBIS por Pagar   XXX
        ─────────────────────────────────────────────
        """
        try:
            # Extraer datos
            invoice_date = invoice.get("invoice_date")
            if isinstance(invoice_date, str):
                invoice_date = datetime.datetime.strptime(invoice_date[: 10], "%Y-%m-%d")
            elif hasattr(invoice_date, "date") and callable(invoice_date.date):
                invoice_date = datetime.datetime.combine(invoice_date.date(), datetime.time())
            
            invoice_number = invoice.get("invoice_number", "")
            third_party = invoice.get("third_party_name", "")
            
            # Calcular montos en RD$
            rate = float(invoice.get("exchange_rate", 1.0) or 1.0)
            total = float(invoice.get("total_amount", 0.0) or 0.0)
            itbis = float(invoice.get("itbis", 0.0) or 0.0)
            
            total_rd = total * rate
            itbis_rd = itbis * rate
            base_rd = total_rd  # Ya incluye ITBIS (total con impuesto)
            
            # Líneas del asiento
            lines = [
                {
                    "account_id": "1. 1.2.001",  # Clientes Nacionales
                    "account_name": "Clientes Nacionales",
                    "debit": total_rd,
                    "credit": 0.0,
                    "description": f"Por venta a {third_party}"
                },
                {
                    "account_id": "4.1.1.001",  # Ventas de Servicios
                    "account_name": "Ventas de Servicios",
                    "debit": 0.0,
                    "credit": base_rd - itbis_rd,
                    "description": f"Venta factura {invoice_number}"
                },
                {
                    "account_id": "2.1.2.001",  # ITBIS por Pagar
                    "account_name": "ITBIS por Pagar",
                    "debit": 0.0,
                    "credit": itbis_rd,
                    "description": f"ITBIS factura {invoice_number}"
                }
            ]
            
            # Crear asiento
            return self. create_journal_entry(
                company_id=company_id,
                entry_date=invoice_date,
                reference=invoice_number,
                description=f"Factura de venta a {third_party}",
                lines=lines
            )
            
        except Exception as e: 
            return False, f"Error creando asiento de ingreso: {e}"


    def _create_entry_for_expense_invoice(
        self, 
        company_id: str, 
        invoice: dict
    ) -> tuple[bool, str]: 
        """
        Crea asiento contable para factura de GASTO.
        
        Asiento tipo:
        ─────────────────────────────────────────────
        DEBE                        | HABER
        ─────────────────────────────────────────────
        Costo de Servicios   XXX   |
        ITBIS por Compensar  XXX   |
                                    | Proveedores       XXX
        ─────────────────────────────────────────────
        """
        try: 
            # Extraer datos
            invoice_date = invoice.get("invoice_date")
            if isinstance(invoice_date, str):
                invoice_date = datetime. datetime.strptime(invoice_date[:10], "%Y-%m-%d")
            elif hasattr(invoice_date, "date") and callable(invoice_date.date):
                invoice_date = datetime.datetime.combine(invoice_date.date(), datetime.time())
            
            invoice_number = invoice.get("invoice_number", "")
            third_party = invoice.get("third_party_name", "")
            
            # Calcular montos en RD$
            rate = float(invoice.get("exchange_rate", 1.0) or 1.0)
            total = float(invoice.get("total_amount", 0.0) or 0.0)
            itbis = float(invoice.get("itbis", 0.0) or 0.0)
            
            total_rd = total * rate
            itbis_rd = itbis * rate
            base_rd = total_rd - itbis_rd  # Base sin impuesto
            
            # Líneas del asiento
            lines = [
                {
                    "account_id": "5.1.1.001",  # Costo de Servicios
                    "account_name": "Costo de Servicios",
                    "debit": base_rd,
                    "credit": 0.0,
                    "description": f"Compra a {third_party}"
                },
                {
                    "account_id": "1.1.4.001",  # ITBIS por Compensar
                    "account_name": "ITBIS por Compensar",
                    "debit": itbis_rd,
                    "credit": 0.0,
                    "description": f"ITBIS factura {invoice_number}"
                },
                {
                    "account_id": "2.1.1.001",  # Proveedores Locales
                    "account_name":  "Proveedores Locales",
                    "debit": 0.0,
                    "credit": total_rd,
                    "description": f"Por compra a {third_party}"
                }
            ]
            
            # Crear asiento
            return self.create_journal_entry(
                company_id=company_id,
                entry_date=invoice_date,
                reference=invoice_number,
                description=f"Factura de compra de {third_party}",
                lines=lines
            )
            
        except Exception as e:
            return False, f"Error creando asiento de gasto: {e}"


    def create_journal_entry(
        self,
        company_id,
        entry_date,
        reference:  str,
        description: str,
        lines: list[dict],
        source_type: str = "MANUAL",  # ✅ NUEVO: Tipo de origen
        source_id: str = None,  # ✅ NUEVO:  ID del documento origen (invoice_id)
    ) -> tuple[bool, str]: 
        """
        Crea un asiento contable y actualiza los saldos de las cuentas.
        
        ✅ NUEVO: Soporta asientos automáticos desde facturas (source_type="INVOICE")
        """
        if not self._db:
            return False, "Base de datos no inicializada."

        try:
            normalized_id = self._normalize_company_id(company_id)
            
            # Convertir fecha a datetime. datetime
            if isinstance(entry_date, str):
                entry_date = datetime.datetime.strptime(entry_date, "%Y-%m-%d")
            elif isinstance(entry_date, datetime.date) and not isinstance(entry_date, datetime.datetime):
                entry_date = datetime.datetime.combine(entry_date, datetime.time())
            
            if not lines or len(lines) < 2:
                return False, "El asiento debe tener al menos 2 líneas."
            
            total_debit = sum(float(line.get("debit", 0)) for line in lines)
            total_credit = sum(float(line.get("credit", 0)) for line in lines)
            
            if abs(total_debit - total_credit) >= 0.01:
                return False, f"Asiento descuadrado: Débito={total_debit: ,.2f}, Crédito={total_credit:,.2f}"
            
            import uuid
            entry_id = f"JE-{entry_date.year}-{str(uuid.uuid4())[:8].upper()}"
            period = f"{entry_date.year}-{entry_date. month:02d}"
            
            entry_data = {
                "entry_id": entry_id,
                "company_id":  normalized_id,
                "entry_date": entry_date,
                "period": period,
                "year": entry_date.year,
                "month": entry_date.month,
                "reference": reference or "",
                "description": description,
                "source_type": source_type,  # ✅ MANUAL / INVOICE / PAYMENT
                "source_id": source_id,  # ✅ ID de la factura origen
                "lines": [
                    {
                        "line_number": idx + 1,
                        "account_id": line. get("account_id", ""),
                        "account_name":  line.get("account_name", ""),
                        "debit": float(line.get("debit", 0)),
                        "credit": float(line.get("credit", 0)),
                        "description": line.get("description", ""),
                    }
                    for idx, line in enumerate(lines)
                ],
                "total_debit": total_debit,
                "total_credit": total_credit,
                "is_balanced": True,
                "status": "POSTED",
                "created_by": "system",
                "created_at":  self._get_timestamp(),
                "posted_at": self._get_timestamp(),
            }
            
            # Guardar asiento
            self._db.collection("journal_entries").add(entry_data)
            print(f"[JOURNAL_ENTRY] ✅ Asiento {entry_id} creado")
            
            # ✅ ACTUALIZAR SALDOS DE CUENTAS
            self._update_account_balances(normalized_id, entry_date.year, entry_date.month, lines)
            
            return True, f"Asiento {entry_id} creado correctamente."

        except Exception as e:
            print(f"[JOURNAL_ENTRY] ❌ Error:  {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error al crear asiento: {e}"

    def create_journal_entry_from_invoice(
        self,
        invoice_data: dict
    ) -> tuple[bool, str]: 
        """
        Crea un asiento contable automático desde una factura.
        
        ✅ NUEVO:  Sistema de contabilización automática de facturas. 
        
        INGRESOS (Factura Emitida):
            DÉBITO:    Cuentas por Cobrar (Cliente)
            CRÉDITO:  Ingresos por Ventas
            CRÉDITO:  ITBIS por Pagar
        
        GASTOS (Factura de Compra):
            DÉBITO:   Gastos Operacionales
            DÉBITO:   ITBIS por Compensar
            CRÉDITO:   Cuentas por Pagar (Proveedor)
        """
        if not self._db:
            return False, "Base de datos no inicializada."

        try:
            company_id = invoice_data.get("company_id")
            invoice_type = invoice_data.get("invoice_type")
            invoice_number = invoice_data.get("invoice_number", "SIN-NCF")
            invoice_date = invoice_data.get("invoice_date")
            third_party = invoice_data.get("third_party_name", "Cliente/Proveedor")
            
            # Montos
            total_amount = float(invoice_data.get("total_amount", 0.0))
            itbis = float(invoice_data.get("itbis", 0.0))
            exchange_rate = float(invoice_data.get("exchange_rate", 1.0))
            
            # Calcular monto en RD$
            total_rd = total_amount * exchange_rate
            itbis_rd = itbis * exchange_rate
            subtotal_rd = total_rd - itbis_rd
            
            # Normalizar fecha
            if isinstance(invoice_date, str):
                invoice_date = datetime.datetime.strptime(invoice_date[: 10], "%Y-%m-%d")
            elif isinstance(invoice_date, datetime.date) and not isinstance(invoice_date, datetime.datetime):
                invoice_date = datetime.datetime.combine(invoice_date, datetime.time())
            
            lines = []
            
            if invoice_type == "emitida":
                # ✅ FACTURA EMITIDA (INGRESO)
                description = f"Factura de venta {invoice_number} - {third_party}"
                
                # DÉBITO: Cuentas por Cobrar
                lines.append({
                    "account_id": "1. 1.2.001",
                    "account_name":  "Clientes Nacionales",
                    "debit":  total_rd,
                    "credit": 0.0,
                    "description": f"Por venta según {invoice_number}"
                })
                
                # CRÉDITO: Ingresos por Ventas
                lines.append({
                    "account_id": "4.1.1.001",
                    "account_name": "Ventas de Servicios",
                    "debit":  0.0,
                    "credit": subtotal_rd,
                    "description": f"Ingreso por servicios {invoice_number}"
                })
                
                # CRÉDITO: ITBIS por Pagar
                if itbis_rd > 0:
                    lines.append({
                        "account_id": "2.1.2.001",
                        "account_name": "ITBIS por Pagar",
                        "debit": 0.0,
                        "credit": itbis_rd,
                        "description": f"ITBIS factura {invoice_number}"
                    })
            
            elif invoice_type == "gasto":
                # ✅ FACTURA DE GASTO (COMPRA)
                description = f"Factura de compra {invoice_number} - {third_party}"
                
                # DÉBITO: Gastos Operacionales
                lines.append({
                    "account_id": "5.2.1.003",
                    "account_name":  "Servicios Públicos",
                    "debit":  subtotal_rd,
                    "credit": 0.0,
                    "description": f"Gasto según {invoice_number}"
                })
                
                # DÉBITO: ITBIS por Compensar
                if itbis_rd > 0:
                    lines.append({
                        "account_id": "1.1.4.001",
                        "account_name": "ITBIS por Compensar",
                        "debit": itbis_rd,
                        "credit":  0.0,
                        "description": f"ITBIS adelantado {invoice_number}"
                    })
                
                # CRÉDITO: Cuentas por Pagar
                lines.append({
                    "account_id": "2.1.1.001",
                    "account_name": "Proveedores Locales",
                    "debit":  0.0,
                    "credit": total_rd,
                    "description": f"Por compra a {third_party}"
                })
            
            else:
                return False, f"Tipo de factura no reconocido: {invoice_type}"
            
            # Crear asiento
            return self. create_journal_entry(
                company_id=company_id,
                entry_date=invoice_date,
                reference=invoice_number,
                description=description,
                lines=lines,
                source_type="INVOICE",
                source_id=invoice_data.get("id")
            )

        except Exception as e: 
            print(f"[AUTO_ENTRY] ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error creando asiento automático: {e}"


    def generate_test_journal_entries_from_invoices(
        self,
        company_id,
        year: int = None,
        month: int = None,
        overwrite: bool = False
    ) -> tuple[bool, str]:
        """
        Genera asientos contables de prueba desde las facturas existentes.
        
        ✅ NUEVO:  Herramienta para migración/demo del sistema contable.
        
        Args:
            company_id: ID de la empresa
            year:  Año a procesar (None = todos)
            month: Mes a procesar (None = todos)
            overwrite: Si True, elimina asientos existentes de facturas
        
        Returns: 
            (success, message)
        """
        if not self._db:
            return False, "Base de datos no inicializada."

        try:
            normalized_id = self._normalize_company_id(company_id)
            
            print(f"[TEST_ENTRIES] ===== INICIO =====")
            print(f"[TEST_ENTRIES] Empresa: {normalized_id}")
            print(f"[TEST_ENTRIES] Periodo: {year}/{month}")
            
            # 1. Si overwrite, eliminar asientos existentes de facturas
            if overwrite: 
                print(f"[TEST_ENTRIES] Eliminando asientos existentes...")
                existing = (
                    self._db.collection("journal_entries")
                    .where("company_id", "==", normalized_id)
                    .where("source_type", "==", "INVOICE")
                    .stream()
                )
                
                deleted_count = 0
                for entry in existing:
                    entry.reference. delete()
                    deleted_count += 1
                
                print(f"[TEST_ENTRIES] Eliminados {deleted_count} asientos anteriores")
            
            # 2. Obtener facturas del periodo
            invoices = self._query_invoices(
                company_id=company_id,
                month_str=f"{month:02d}" if month else None,
                year_int=year,
                tx_type=None
            )
            
            print(f"[TEST_ENTRIES] Facturas encontradas:  {len(invoices)}")
            
            if not invoices: 
                return False, "No hay facturas en el periodo seleccionado."
            
            # 3. Crear asientos para cada factura
            created_count = 0
            failed_count = 0
            
            for invoice in invoices: 
                try:
                    ok, msg = self.create_journal_entry_from_invoice(invoice)
                    
                    if ok:
                        created_count += 1
                        print(f"  ✅ {invoice.get('invoice_number')}")
                    else:
                        failed_count += 1
                        print(f"  ❌ {invoice.get('invoice_number')}: {msg}")
                
                except Exception as e: 
                    failed_count += 1
                    print(f"  ❌ {invoice.get('invoice_number')}: {e}")
            
            print(f"[TEST_ENTRIES] ===== RESULTADO =====")
            print(f"[TEST_ENTRIES] Creados: {created_count}")
            print(f"[TEST_ENTRIES] Fallidos:  {failed_count}")
            
            result_msg = (
                f"Asientos generados correctamente:\n\n"
                f"✅ Creados: {created_count}\n"
                f"❌ Fallidos: {failed_count}\n\n"
                f"Total procesado: {len(invoices)} facturas"
            )
            
            return True, result_msg

        except Exception as e:
            print(f"[TEST_ENTRIES] ❌ Error general: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error generando asientos: {e}"


    def _update_account_balances(
        self,
        company_id:  str,
        year: int,
        month: int,
        lines: list[dict]
    ):
        """
        Actualiza los saldos de las cuentas afectadas por un asiento.
        
        Actualiza tanto el mes actual como el acumulado del año (YTD).
        """
        try: 
            print(f"[UPDATE_BALANCES] Actualizando saldos para {year}-{month:02d}")
            
            for line in lines:
                account_id = line.get("account_id", "")
                if not account_id:
                    continue
                
                debit = float(line.get("debit", 0))
                credit = float(line.get("credit", 0))
                
                # ✅ CORRECCIÓN:  Reemplazar puntos ANTES de construir el ID
                account_safe = account_id.replace(".", "_")
                balance_id = f"{company_id}_{year}_{month:02d}_{account_safe}"
                
                balance_ref = self._db.collection("account_balances").document(balance_id)
                
                # Obtener saldo actual
                balance_doc = balance_ref.get()
                
                if balance_doc.exists:
                    # Actualizar existente
                    balance_data = balance_doc. to_dict()
                    
                    new_total_debit = balance_data. get("total_debit", 0.0) + debit
                    new_total_credit = balance_data.get("total_credit", 0.0) + credit
                    
                    # Calcular nuevo saldo
                    opening = balance_data.get("opening_balance", 0.0)
                    new_closing = opening + new_total_debit - new_total_credit
                    
                    balance_ref.update({
                        "total_debit": new_total_debit,
                        "total_credit": new_total_credit,
                        "closing_balance": new_closing,
                        "last_updated": self._get_timestamp(),
                    })
                    
                    print(f"  ✅ {account_id}:  Saldo actualizado = {new_closing: ,.2f}")
                else:
                    # Crear nuevo
                    # Obtener saldo inicial (del mes anterior o 0)
                    opening_balance = self._get_previous_month_closing_balance(
                        company_id, account_id, year, month
                    )
                    
                    new_closing = opening_balance + debit - credit
                    
                    balance_ref.set({
                        "balance_id": balance_id,
                        "company_id":  company_id,
                        "account_id": account_id,
                        "period": f"{year}-{month:02d}",
                        "year": year,
                        "month": month,
                        "opening_balance": opening_balance,
                        "total_debit": debit,
                        "total_credit": credit,
                        "closing_balance": new_closing,
                        "last_updated": self._get_timestamp(),
                    })
                    
                    print(f"  ✅ {account_id}:  Saldo creado = {new_closing:,.2f}")
                
                # Actualizar saldos de meses posteriores si existen
                self._propagate_balance_to_future_months(company_id, account_id, year, month)

        except Exception as e:
            print(f"[UPDATE_BALANCES] ❌ Error: {e}")
            import traceback
            traceback.print_exc()

    def _get_previous_month_closing_balance(
        self,
        company_id: str,
        account_id: str,
        year: int,
        month: int
    ) -> float:
        """Obtiene el saldo de cierre del mes anterior."""
        try:
            # Calcular mes anterior
            if month == 1:
                prev_year = year - 1
                prev_month = 12
            else:
                prev_year = year
                prev_month = month - 1
            
            # ✅ CORRECCIÓN:  Reemplazar puntos ANTES de construir el ID
            account_safe = account_id.replace(".", "_")
            balance_id = f"{company_id}_{prev_year}_{prev_month:02d}_{account_safe}"
            
            balance_doc = self._db.collection("account_balances").document(balance_id).get()
            
            if balance_doc.exists:
                closing = float(balance_doc.to_dict().get("closing_balance", 0.0))
                print(f"  📋 Saldo anterior {account_id} ({prev_year}-{prev_month:02d}): {closing:,.2f}")
                return closing
            
            print(f"  📋 Sin saldo anterior para {account_id}")
            return 0.0

        except Exception as e:
            print(f"  ❌ Error obteniendo saldo anterior: {e}")
            return 0.0

    def _propagate_balance_to_future_months(
        self,
        company_id:   str,
        account_id:   str,
        year: int,
        month: int
    ):
        """
        Propaga el cambio de saldo a los meses posteriores del mismo año.
        
        Si ya existen saldos en meses futuros, actualiza sus opening_balance.
        """
        try:
            from google.cloud. firestore_v1.base_query import FieldFilter
            
            # ✅ CORRECCIÓN:  Buscar por account_id original (con puntos)
            # Firestore almacena el campo como "1. 1.1.001", no "1_1_1_001"
            
            # Buscar saldos de meses posteriores en el mismo año
            future_balances = (
                self._db.collection("account_balances")
                .where(filter=FieldFilter("company_id", "==", company_id))
                .where(filter=FieldFilter("account_id", "==", account_id))
                .where(filter=FieldFilter("year", "==", year))
                .where(filter=FieldFilter("month", ">", month))
                .stream()
            )
            
            for balance_doc in future_balances:  
                balance_data = balance_doc.to_dict()
                future_month = balance_data.get("month")
                
                # Obtener saldo de cierre del mes anterior
                new_opening = self._get_previous_month_closing_balance(
                    company_id, account_id, year, future_month
                )
                
                # Recalcular saldo de cierre
                total_debit = balance_data. get("total_debit", 0.0)
                total_credit = balance_data.get("total_credit", 0.0)
                new_closing = new_opening + total_debit - total_credit
                
                # Actualizar
                balance_doc.reference.update({
                    "opening_balance": new_opening,
                    "closing_balance": new_closing,
                    "last_updated": self._get_timestamp(),
                })
                
                print(f"  🔄 Propagado a mes {future_month}: {new_closing:,.2f}")

        except Exception as e:
            print(f"[PROPAGATE] Error:  {e}")
            import traceback
            traceback.print_exc()



    def get_journal_entries(
        self,
        company_id,
        year:  int = None,
        month: int = None,
        limit: int = 100
    ) -> list[dict]:
        """Obtiene los asientos contables de una empresa."""
        if not self._db:
            return []

        try: 
            from google.cloud. firestore_v1.base_query import FieldFilter
            
            normalized_id = self._normalize_company_id(company_id)
            
            # Base query
            query = self._db. collection("journal_entries").where(
                filter=FieldFilter("company_id", "==", normalized_id)
            )
            
            # Filtros opcionales
            if year: 
                query = query.where(filter=FieldFilter("year", "==", year))
            
            if month:
                query = query.where(filter=FieldFilter("month", "==", month))
            
            # Ordenar por fecha descendente
            query = query.order_by("entry_date", direction="DESCENDING").limit(limit)
            
            docs = query.stream()
            
            entries = []
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                entries.append(data)
            
            print(f"[JOURNAL_ENTRIES] Obtenidos {len(entries)} asientos")
            
            return entries

        except Exception as e:
            print(f"[JOURNAL_ENTRIES] Error: {e}")
            import traceback
            traceback. print_exc()
            return []

    def reverse_journal_entry(
        self,
        entry_id: str,
        reversal_date,
        reason: str
    ) -> tuple[bool, str]:
        """
        Anula un asiento contable creando un asiento inverso.
        
        Args:
            entry_id: ID del asiento a anular
            reversal_date: Fecha del asiento de anulación
            reason: Motivo de la anulación
            
        Returns:
            (success, message) tuple
        """
        if not self._db:
            return False, "Base de datos no inicializada."

        try:
            from google.cloud.firestore_v1.base_query import FieldFilter
            
            # Buscar el asiento original
            query = self._db.collection("journal_entries").where(
                filter=FieldFilter("entry_id", "==", entry_id)
            ).limit(1)
            
            docs = list(query.stream())
            if not docs:
                return False, f"Asiento {entry_id} no encontrado."
            
            original_entry = docs[0].to_dict()
            
            # Verificar que no esté ya anulado
            if original_entry.get("reversed_by"):
                return False, f"El asiento {entry_id} ya fue anulado."
            
            # Crear líneas inversas (intercambiar débito y crédito)
            reversed_lines = []
            for line in original_entry.get("lines", []):
                reversed_lines.append({
                    "account_id": line["account_id"],
                    "account_name": line["account_name"],
                    "debit": line["credit"],  # Invertir
                    "credit": line["debit"],   # Invertir
                    "description": f"Anulación: {line.get('description', '')}"
                })
            
            # Crear asiento de anulación
            success, msg = self.create_journal_entry(
                company_id=original_entry["company_id"],
                entry_date=reversal_date,
                reference=f"REV-{original_entry.get('reference', '')}",
                description=f"ANULACIÓN: {reason}",
                lines=reversed_lines,
                source_type="REVERSAL",
                source_id=entry_id
            )
            
            if not success:
                return False, f"Error al crear asiento de anulación: {msg}"
            
            # Marcar el asiento original como anulado
            docs[0].reference.update({
                "reversed_by": reason,
                "reversal_date": reversal_date,
                "status": "REVERSED"
            })
            
            return True, f"Asiento {entry_id} anulado correctamente."

        except Exception as e:
            print(f"[REVERSE_ENTRY] Error: {e}")
            import traceback
            traceback.print_exc()
            return False, f"Error al anular asiento: {e}"

    def get_general_ledger(
        self,
        company_id,
        account_id: str,
        start_date,
        end_date
    ) -> list[dict]:
        """
        Obtiene el libro mayor (movimientos) de una cuenta específica.
        
        Args:
            company_id: ID de la empresa
            account_id: Código de la cuenta (ej: "1.1.1.001")
            start_date: Fecha inicial
            end_date: Fecha final
            
        Returns:
            Lista de movimientos con débito, crédito y saldo
        """
        if not self._db:
            return []

        try:
            from google.cloud.firestore_v1.base_query import FieldFilter
            
            normalized_id = self._normalize_company_id(company_id)
            
            # Convertir fechas a datetime
            if isinstance(start_date, str):
                start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            elif isinstance(start_date, datetime.date) and not isinstance(start_date, datetime.datetime):
                start_date = datetime.datetime.combine(start_date, datetime.time())
            
            if isinstance(end_date, str):
                end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            elif isinstance(end_date, datetime.date) and not isinstance(end_date, datetime.datetime):
                end_date = datetime.datetime.combine(end_date, datetime.time(23, 59, 59))
            
            # Obtener asientos en el rango de fechas
            query = (
                self._db.collection("journal_entries")
                .where(filter=FieldFilter("company_id", "==", normalized_id))
                .where(filter=FieldFilter("entry_date", ">=", start_date))
                .where(filter=FieldFilter("entry_date", "<=", end_date))
                .order_by("entry_date")
            )
            
            docs = query.stream()
            
            # Filtrar líneas que correspondan a esta cuenta
            movements = []
            for doc in docs:
                entry_data = doc.to_dict()
                
                # Buscar líneas de esta cuenta
                for line in entry_data.get("lines", []):
                    if line.get("account_id") == account_id:
                        movements.append({
                            "date": entry_data["entry_date"],
                            "entry_id": entry_data["entry_id"],
                            "reference": entry_data.get("reference", ""),
                            "description": line.get("description", entry_data.get("description", "")),
                            "debit": line.get("debit", 0.0),
                            "credit": line.get("credit", 0.0),
                            "status": entry_data.get("status", ""),
                        })
            
            print(f"[GENERAL_LEDGER] {len(movements)} movimientos para cuenta {account_id}")
            
            return movements

        except Exception as e:
            print(f"[GENERAL_LEDGER] Error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def calculate_income_statement(
        self,
        company_id,
        year: int,
        month: int
    ) -> dict:
        """
        Calcula el Estado de Resultados (P&L) para un periodo.
        
        Returns:
            {
                'ingresos_operacionales': float,
                'costo_ventas': float,
                'utilidad_bruta': float,
                'gastos_operacionales': float,
                'gastos_financieros': float,
                'otros_ingresos': float,
                'otros_gastos': float,
                'utilidad_neta': float
            }
        """
        if not self._db:
            return {}

        try:
            from google.cloud.firestore_v1.base_query import FieldFilter
            
            normalized_id = self._normalize_company_id(company_id)
            
            # Obtener saldos del periodo
            period = f"{year}-{month:02d}"
            query = (
                self._db.collection("account_balances")
                .where(filter=FieldFilter("company_id", "==", normalized_id))
                .where(filter=FieldFilter("period", "==", period))
            )
            
            docs = query.stream()
            
            # Obtener plan de cuentas para clasificar
            accounts = self.get_chart_of_accounts(company_id)
            accounts_dict = {acc["account_code"]: acc for acc in accounts}
            
            # Inicializar totales
            ingresos_operacionales = 0.0
            costo_ventas = 0.0
            gastos_operacionales = 0.0
            gastos_financieros = 0.0
            otros_ingresos = 0.0
            otros_gastos = 0.0
            
            # Sumar saldos por categoría
            for doc in docs:
                balance_data = doc.to_dict()
                account_id = balance_data.get("account_id", "")
                
                # Obtener info de la cuenta
                account = accounts_dict.get(account_id, {})
                account_type = account.get("account_type", "")
                category = account.get("category", "")
                
                # Calcular movimiento neto del periodo
                total_debit = balance_data.get("total_debit", 0.0)
                total_credit = balance_data.get("total_credit", 0.0)
                net_movement = total_credit - total_debit  # Para cuentas de ingreso
                
                if account_type == "INGRESO":
                    category_upper = category.upper()
                    if "OPERACIONAL" in category_upper or "VENTA" in category_upper or "SERVICIO" in category_upper:
                        ingresos_operacionales += net_movement
                    else:
                        otros_ingresos += net_movement
                
                elif account_type == "GASTO":
                    net_movement_gasto = total_debit - total_credit  # Para gastos
                    category_upper = category.upper()
                    
                    if "COSTO" in category_upper or "VENTA" in category_upper:
                        costo_ventas += net_movement_gasto
                    elif "FINANCIERO" in category_upper or "INTERES" in category_upper:
                        gastos_financieros += net_movement_gasto
                    elif "OPERACIONAL" in category_upper or "ADMINISTRATIVO" in category_upper:
                        gastos_operacionales += net_movement_gasto
                    else:
                        otros_gastos += net_movement_gasto
            
            # Calcular utilidades
            utilidad_bruta = ingresos_operacionales - costo_ventas
            utilidad_operacional = utilidad_bruta - gastos_operacionales
            utilidad_antes_impuestos = utilidad_operacional - gastos_financieros + otros_ingresos - otros_gastos
            utilidad_neta = utilidad_antes_impuestos  # Sin impuestos por ahora
            
            result = {
                'ingresos_operacionales': round(ingresos_operacionales, 2),
                'costo_ventas': round(costo_ventas, 2),
                'utilidad_bruta': round(utilidad_bruta, 2),
                'gastos_operacionales': round(gastos_operacionales, 2),
                'gastos_financieros': round(gastos_financieros, 2),
                'otros_ingresos': round(otros_ingresos, 2),
                'otros_gastos': round(otros_gastos, 2),
                'utilidad_operacional': round(utilidad_operacional, 2),
                'utilidad_antes_impuestos': round(utilidad_antes_impuestos, 2),
                'utilidad_neta': round(utilidad_neta, 2)
            }
            
            print(f"[INCOME_STATEMENT] Calculado para {period}: Utilidad Neta = {utilidad_neta:,.2f}")
            
            return result

        except Exception as e:
            print(f"[INCOME_STATEMENT] Error: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_balance_sheet_for_optimizer(
        self,
        company_id,
        year: int,
        month: int
    ) -> dict:
        """
        Exporta balance contable al optimizador financiero.
        
        Returns:
            {
                'has_real_data': bool,
                'current_assets': float,
                'non_current_assets': float,
                'current_liabilities': float,
                'non_current_liabilities': float,
                'equity': float,
                'revenue': float,
                'cogs': float,
                'operating_expenses': float,
                'financial_expenses': float,
                'net_income': float,
                'ebit': float,
                'cash': float,
                'accounts_receivable': float,
                'inventory': float,
                'accounts_payable': float
            }
        """
        if not self._db:
            return {'has_real_data': False}

        try:
            from google.cloud.firestore_v1.base_query import FieldFilter
            
            normalized_id = self._normalize_company_id(company_id)
            
            # Obtener saldos del periodo
            period = f"{year}-{month:02d}"
            query = (
                self._db.collection("account_balances")
                .where(filter=FieldFilter("company_id", "==", normalized_id))
                .where(filter=FieldFilter("period", "==", period))
            )
            
            docs = list(query.stream())
            
            if not docs:
                return {'has_real_data': False}
            
            # Obtener plan de cuentas
            accounts = self.get_chart_of_accounts(company_id)
            accounts_dict = {acc["account_code"]: acc for acc in accounts}
            
            # Inicializar categorías
            current_assets = 0.0
            non_current_assets = 0.0
            current_liabilities = 0.0
            non_current_liabilities = 0.0
            equity = 0.0
            cash = 0.0
            accounts_receivable = 0.0
            inventory = 0.0
            accounts_payable = 0.0
            
            # Clasificar saldos
            for doc in docs:
                balance_data = doc.to_dict()
                account_id = balance_data.get("account_id", "")
                closing_balance = balance_data.get("closing_balance", 0.0)
                
                account = accounts_dict.get(account_id, {})
                account_type = account.get("account_type", "")
                category = account.get("category", "").upper()
                
                if account_type == "ACTIVO":
                    # Consistent approach: check for substring or exact match
                    if "CORRIENTE" in category or category in ["EFECTIVO", "CUENTAS_COBRAR", "INVENTARIO"]:
                        current_assets += closing_balance
                        
                        # Detalles
                        if category == "EFECTIVO":
                            cash += closing_balance
                        elif category == "CUENTAS_COBRAR":
                            accounts_receivable += closing_balance
                        elif category == "INVENTARIO":
                            inventory += closing_balance
                    else:
                        non_current_assets += closing_balance
                
                elif account_type == "PASIVO":
                    # Consistent approach: check for substring or exact match
                    if "CORRIENTE" in category or category == "CUENTAS_PAGAR":
                        current_liabilities += abs(closing_balance)
                        
                        if category == "CUENTAS_PAGAR":
                            accounts_payable += abs(closing_balance)
                    else:
                        non_current_liabilities += abs(closing_balance)
                
                elif account_type == "PATRIMONIO":
                    equity += abs(closing_balance)
            
            # Obtener datos del estado de resultados
            income_statement = self.calculate_income_statement(company_id, year, month)
            
            result = {
                'has_real_data': True,
                'current_assets': round(current_assets, 2),
                'non_current_assets': round(non_current_assets, 2),
                'current_liabilities': round(current_liabilities, 2),
                'non_current_liabilities': round(non_current_liabilities, 2),
                'equity': round(equity, 2),
                'revenue': income_statement.get('ingresos_operacionales', 0.0),
                'cogs': income_statement.get('costo_ventas', 0.0),
                'operating_expenses': income_statement.get('gastos_operacionales', 0.0),
                'financial_expenses': income_statement.get('gastos_financieros', 0.0),
                'net_income': income_statement.get('utilidad_neta', 0.0),
                'ebit': income_statement.get('utilidad_operacional', 0.0),
                'cash': round(cash, 2),
                'accounts_receivable': round(accounts_receivable, 2),
                'inventory': round(inventory, 2),
                'accounts_payable': round(accounts_payable, 2),
                'total_assets': round(current_assets + non_current_assets, 2),
                'total_liabilities': round(current_liabilities + non_current_liabilities, 2),
            }
            
            print(f"[BALANCE_SHEET_OPTIMIZER] Datos exportados para {period}")
            
            return result

        except Exception as e:
            print(f"[BALANCE_SHEET_OPTIMIZER] Error: {e}")
            import traceback
            traceback.print_exc()
            return {'has_real_data': False}