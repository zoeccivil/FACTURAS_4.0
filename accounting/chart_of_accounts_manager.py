from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QTreeWidgetItemIterator,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor


class ChartOfAccountsManager(QDialog):
    """
    Gestor del Plan de Cuentas Contable.  
    
    Características:
    - Vista jerárquica en árbol
    - CRUD completo de cuentas
    - Inicialización con plan estándar
    - Validaciones contables
    - Búsqueda y filtros
    """

    ACCOUNT_TYPES = {
        "ACTIVO": {"icon": "💰", "color": "#15803D"},
        "PASIVO": {"icon": "📋", "color": "#DC2626"},
        "PATRIMONIO": {"icon": "💎", "color": "#3B82F6"},
        "INGRESO": {"icon": "📈", "color": "#059669"},
        "GASTO": {"icon": "📉", "color": "#EA580C"},
    }

    def __init__(self, parent, controller, company_id, company_name:  str):
        super().__init__(parent)
        self.controller = controller
        self.company_id = company_id
        self.company_name = company_name
        
        self.setWindowTitle(f"Plan de Cuentas - {company_name}")
        self.resize(1200, 700)
        self.setModal(True)
        
        self._build_ui()
        self._load_accounts()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # === HEADER ===
        header_card = QFrame()
        header_card.setObjectName("headerCard")
        header_layout = QVBoxLayout(header_card)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        title = QLabel("📊 Plan de Cuentas Contable")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")
        title_row.addWidget(title)
        title_row.addStretch()

        # Botones de acción
        self.btn_new = QPushButton("➕ Nueva Cuenta")
        self.btn_new.setObjectName("primaryButton")
        self.btn_new.clicked.connect(self._new_account)

        self.btn_init = QPushButton("🔄 Inicializar Plan Estándar")
        self.btn_init.setObjectName("secondaryButton")
        self.btn_init.clicked.connect(self._initialize_standard_plan)

        self.btn_refresh = QPushButton("🔃 Refrescar")
        self.btn_refresh.setObjectName("refreshButton")
        self.btn_refresh.clicked.connect(self._load_accounts)

        title_row.addWidget(self.btn_new)
        title_row.addWidget(self.btn_init)
        title_row.addWidget(self.btn_refresh)

        header_layout.addLayout(title_row)

        subtitle = QLabel(f"{self.company_name}")
        subtitle.setStyleSheet("font-size: 12px; color: #64748B;")
        header_layout.addWidget(subtitle)

        root.addWidget(header_card)

        # === BÚSQUEDA ===
        search_row = QHBoxLayout()
        search_row.setSpacing(12)

        lbl_search = QLabel("🔍 Buscar:")
        lbl_search.setStyleSheet("font-weight: 600; color: #475569;")
        search_row.addWidget(lbl_search)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("modernInput")
        self.search_input.setPlaceholderText("Buscar por código o nombre...")
        self.search_input.textChanged.connect(self._filter_accounts)
        search_row.addWidget(self.search_input, 1)

        lbl_type = QLabel("Tipo:")
        lbl_type.setStyleSheet("font-weight: 600; color: #475569;")
        search_row.addWidget(lbl_type)

        self.filter_type = QComboBox()
        self.filter_type.setObjectName("modernCombo")
        self.filter_type.addItems(["Todos", "ACTIVO", "PASIVO", "PATRIMONIO", "INGRESO", "GASTO"])
        self.filter_type.currentIndexChanged.connect(self._filter_accounts)
        search_row.addWidget(self.filter_type)

        root.addLayout(search_row)

        # === ÁRBOL DE CUENTAS ===
        self.tree = QTreeWidget()
        self.tree.setObjectName("accountTree")
        self.tree.setHeaderLabels([
            "Código", "Nombre de Cuenta", "Tipo", "Naturaleza", "Detalle", "Acciones"
        ])
        self.tree.setColumnWidth(0, 150)
        self.tree.setColumnWidth(1, 350)
        self.tree.setColumnWidth(2, 120)
        self.tree.setColumnWidth(3, 100)
        self.tree.setColumnWidth(4, 80)
        self.tree.setColumnWidth(5, 180)
        
        self.tree.setAlternatingRowColors(True)
        self.tree.setAnimated(True)
        
        root.addWidget(self.tree)

        # === ESTADÍSTICAS ===
        stats_card = QFrame()
        stats_card.setObjectName("statsCard")
        stats_layout = QHBoxLayout(stats_card)
        stats_layout.setContentsMargins(20, 12, 20, 12)
        stats_layout.setSpacing(20)

        self.lbl_total = QLabel("Total:  0 cuentas")
        self.lbl_total.setStyleSheet("font-weight: 600; color: #1E293B;")
        stats_layout.addWidget(self.lbl_total)

        self.lbl_activo = QLabel("💰 Activos: 0")
        self.lbl_activo.setStyleSheet("color: #15803D;")
        stats_layout.addWidget(self.lbl_activo)

        self.lbl_pasivo = QLabel("📋 Pasivos: 0")
        self.lbl_pasivo.setStyleSheet("color: #DC2626;")
        stats_layout.addWidget(self.lbl_pasivo)

        self.lbl_patrimonio = QLabel("💎 Patrimonio: 0")
        self.lbl_patrimonio.setStyleSheet("color: #3B82F6;")
        stats_layout.addWidget(self.lbl_patrimonio)

        self.lbl_ingreso = QLabel("📈 Ingresos: 0")
        self.lbl_ingreso.setStyleSheet("color: #059669;")
        stats_layout.addWidget(self.lbl_ingreso)

        self.lbl_gasto = QLabel("📉 Gastos:  0")
        self.lbl_gasto.setStyleSheet("color: #EA580C;")
        stats_layout.addWidget(self.lbl_gasto)

        stats_layout.addStretch()

        root.addWidget(stats_card)

        # === ESTILOS ===
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }
            
            QFrame#headerCard, QFrame#statsCard {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E5E7EB;
            }
            
            QLineEdit#modernInput {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 12px;
                color: #0F172A;
                font-size: 13px;
            }
            
            QLineEdit#modernInput:focus {
                border-color: #3B82F6;
                border-width: 2px;
            }
            
            QComboBox#modernCombo {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 8px 12px;
                color: #0F172A;
                font-size: 13px;
                min-width: 150px;
            }
            
            QComboBox#modernCombo:hover { border-color: #3B82F6; }
            
            QTreeWidget#accountTree {
                background-color: #FFFFFF;
                alternate-background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                color: #0F172A;
                font-size: 13px;
            }
            
            QTreeWidget#accountTree::item {
                padding: 6px;
                border:  none;
            }
            
            QTreeWidget#accountTree::item:selected {
                background-color: #EFF6FF;
                color: #1E293B;
            }
            
            QHeaderView::section {
                background-color: #F1F5F9;
                border: none;
                padding: 10px 8px;
                color: #475569;
                font-weight:  700;
                font-size: 12px;
            }
            
            QPushButton#primaryButton {
                background-color: #15803D;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0px 20px;
                font-weight: 600;
                font-size: 14px;
                min-width: 150px;
                height: 36px;
            }
            QPushButton#primaryButton:hover { background-color: #166534; }
            
            QPushButton#secondaryButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0px 20px;
                font-weight: 600;
                font-size: 14px;
                min-width: 180px;
                height: 36px;
            }
            QPushButton#secondaryButton:hover { background-color: #2563EB; }
            
            QPushButton#refreshButton {
                background-color: #64748B;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0px 16px;
                font-weight:  600;
                font-size: 14px;
                height: 36px;
            }
            QPushButton#refreshButton:hover { background-color: #475569; }
            
            QPushButton#editButton, QPushButton#deleteButton {
                border: none;
                border-radius: 6px;
                font-size: 16px;
                width: 32px;
                height: 28px;
            }
            
            QPushButton#editButton {
                background-color: #3B82F6;
                color: #FFFFFF;
            }
            QPushButton#editButton:hover { background-color:  #2563EB; }
            
            QPushButton#deleteButton {
                background-color:  #EF4444;
                color:  #FFFFFF;
            }
            QPushButton#deleteButton:hover { background-color: #DC2626; }
            
            /* === ARREGLO PARA QMESSAGEBOX === */
            QMessageBox {
                background-color:  #FFFFFF;
            }
            QMessageBox QLabel {
                color: #0F172A;
                font-size: 13px;
                background-color: transparent;
                min-width: 300px;
            }
            QMessageBox QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 600;
                font-size: 13px;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #2563EB;
            }
        """)

    def _load_accounts(self):
        """Carga las cuentas desde Firebase."""
        self.tree.clear()
        
        try:
            if not hasattr(self.controller, "get_chart_of_accounts"):
                QMessageBox.critical(
                    self,
                    "Error",
                    "El método get_chart_of_accounts no está implementado en el controller."
                )
                return

            accounts = self.controller.get_chart_of_accounts(self.company_id) or []
            
            if not accounts:
                QMessageBox.information(
                    self,
                    "Plan de Cuentas Vacío",
                    "No hay cuentas registradas.\n\n"
                    "Puedes inicializar el plan de cuentas estándar con el botón "
                    "'🔄 Inicializar Plan Estándar'."
                )
                return

            # Organizar cuentas por jerarquía
            accounts_dict = {acc["account_code"]: acc for acc in accounts}
            root_accounts = [acc for acc in accounts if not acc.get("parent_account")]
            
            # Construir árbol
            for root_acc in sorted(root_accounts, key=lambda x: x["account_code"]):
                root_item = self._create_tree_item(root_acc, accounts_dict)
                self.tree.addTopLevelItem(root_item)
            
            self.tree.expandAll()
            self._update_statistics(accounts)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error cargando cuentas:\n{e}")
            import traceback
            traceback.print_exc()

    def _create_tree_item(self, account: dict, accounts_dict: dict) -> QTreeWidgetItem: 
        """Crea un item del árbol para una cuenta."""
        item = QTreeWidgetItem()
        
        # Código
        code = account.get("account_code", "")
        item.setText(0, code)
        
        # Nombre
        name = account.get("account_name", "")
        item.setText(1, name)
        
        # Tipo con icono
        acc_type = account.get("account_type", "")
        icon = self.ACCOUNT_TYPES.get(acc_type, {}).get("icon", "📄")
        item.setText(2, f"{icon} {acc_type}")
        
        # Naturaleza
        nature = account.get("nature", "")
        item.setText(3, nature)
        
        # Es detalle
        is_detail = "✓" if account.get("is_detail", False) else "✗"
        item.setText(4, is_detail)
        
        # Color según tipo
        color = self.ACCOUNT_TYPES.get(acc_type, {}).get("color", "#000000")
        item.setForeground(0, QColor(color))
        item.setForeground(1, QColor(color))
        
        # Negrita para cuentas grupo
        if not account.get("is_detail", True):
            font = QFont()
            font.setBold(True)
            item.setFont(1, font)
        
        # Guardar datos de la cuenta
        item.setData(0, Qt.ItemDataRole.UserRole, account)
        
        # Botones de acción (solo para cuentas detalle)
        if account.get("is_detail", False):
            self.tree.setItemWidget(item, 5, self._create_action_buttons(account))
        
        # Agregar hijos recursivamente
        children = [
            acc for acc in accounts_dict.values()
            if acc.get("parent_account") == code
        ]
        
        for child in sorted(children, key=lambda x:  x["account_code"]):
            child_item = self._create_tree_item(child, accounts_dict)
            item.addChild(child_item)
        
        return item

    def _create_action_buttons(self, account: dict):
        """Crea botones de acción para una cuenta."""
        widget = QFrame()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        btn_edit = QPushButton("✏️")
        btn_edit.setObjectName("editButton")
        btn_edit.setToolTip("Editar cuenta")
        btn_edit.clicked.connect(lambda: self._edit_account(account))

        btn_delete = QPushButton("🗑️")
        btn_delete.setObjectName("deleteButton")
        btn_delete.setToolTip("Eliminar cuenta")
        btn_delete.clicked.connect(lambda: self._delete_account(account))

        layout.addWidget(btn_edit)
        layout.addWidget(btn_delete)
        layout.addStretch()

        return widget

    def _update_statistics(self, accounts: list):
        """Actualiza las estadísticas."""
        total = len(accounts)
        activo = len([a for a in accounts if a.get("account_type") == "ACTIVO"])
        pasivo = len([a for a in accounts if a.get("account_type") == "PASIVO"])
        patrimonio = len([a for a in accounts if a.get("account_type") == "PATRIMONIO"])
        ingreso = len([a for a in accounts if a.get("account_type") == "INGRESO"])
        gasto = len([a for a in accounts if a.get("account_type") == "GASTO"])

        self.lbl_total.setText(f"Total: {total} cuentas")
        self.lbl_activo.setText(f"💰 Activos: {activo}")
        self.lbl_pasivo.setText(f"📋 Pasivos: {pasivo}")
        self.lbl_patrimonio.setText(f"💎 Patrimonio:  {patrimonio}")
        self.lbl_ingreso.setText(f"📈 Ingresos: {ingreso}")
        self.lbl_gasto.setText(f"📉 Gastos: {gasto}")

    def _filter_accounts(self):
        """Filtra cuentas por texto y tipo."""
        search_text = self.search_input.text().lower()
        filter_type = self.filter_type.currentText()

        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            account = item.data(0, Qt.ItemDataRole.UserRole)
            
            if account:
                code = account.get("account_code", "").lower()
                name = account.get("account_name", "").lower()
                acc_type = account.get("account_type", "")
                
                text_match = search_text in code or search_text in name
                type_match = filter_type == "Todos" or acc_type == filter_type
                
                item.setHidden(not (text_match and type_match))
            
            iterator += 1

    def _new_account(self):
        """Abre diálogo para crear nueva cuenta."""
        dlg = AccountFormDialog(self, self.controller, self.company_id, None)
        if dlg.exec():
            self._load_accounts()

    def _edit_account(self, account: dict):
        """Abre diálogo para editar cuenta."""
        dlg = AccountFormDialog(self, self.controller, self.company_id, account)
        if dlg.exec():
            self._load_accounts()

    def _delete_account(self, account: dict):
        """Elimina una cuenta."""
        reply = QMessageBox.question(
            self,
            "Confirmar Eliminación",
            f"¿Está seguro de eliminar la cuenta?\n\n"
            f"{account.get('account_code')} - {account.get('account_name')}\n\n"
            f"ADVERTENCIA: Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Implementar delete_account en controller
            QMessageBox.information(self, "Pendiente", "Función de eliminación pendiente de implementar.")

    def _initialize_standard_plan(self):
        """Inicializa el plan de cuentas estándar."""
        reply = QMessageBox.question(
            self,
            "Inicializar Plan de Cuentas",
            f"¿Desea inicializar el plan de cuentas estándar para República Dominicana?\n\n"
            f"Se crearán aproximadamente 50+ cuentas básicas.\n\n"
            f"Empresa: {self.company_name}\n"
            f"Año: 2025",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                if hasattr(self.controller, "initialize_default_chart_of_accounts"):
                    ok, msg = self.controller.initialize_default_chart_of_accounts(
                        self.company_id,
                        2025
                    )

                    if ok:
                        QMessageBox.information(self, "Éxito", msg)
                        self._load_accounts()
                    else:
                        QMessageBox.warning(self, "Error", msg)
                else:
                    QMessageBox.critical(
                        self,
                        "Error",
                        "Método initialize_default_chart_of_accounts no implementado."
                    )

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al inicializar:\n{e}")


class AccountFormDialog(QDialog):
    """Diálogo para crear/editar cuentas."""

    def __init__(self, parent, controller, company_id, account:  dict = None):
        super().__init__(parent)
        self.controller = controller
        self.company_id = company_id
        self.account = account
        self.is_edit = account is not None
        
        title = "Editar Cuenta" if self.is_edit else "Nueva Cuenta"
        self.setWindowTitle(title)
        self.resize(600, 500)
        self.setModal(True)
        
        self._build_ui()
        
        if self.is_edit:
            self._load_account_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Título
        title = QLabel("📝 " + ("Editar Cuenta" if self.is_edit else "Nueva Cuenta"))
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A;")
        root.addWidget(title)

        # Código
        lbl_code = QLabel("Código de Cuenta:  *")
        lbl_code.setStyleSheet("font-weight: 600; color: #475569;")
        root.addWidget(lbl_code)

        self.edit_code = QLineEdit()
        self.edit_code.setPlaceholderText("Ej: 1.1.1.001")
        root.addWidget(self.edit_code)

        # Nombre
        lbl_name = QLabel("Nombre de Cuenta: *")
        lbl_name.setStyleSheet("font-weight:  600; color: #475569;")
        root.addWidget(lbl_name)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("Ej: Caja General")
        root.addWidget(self.edit_name)

        # Tipo
        lbl_type = QLabel("Tipo de Cuenta: *")
        lbl_type.setStyleSheet("font-weight: 600; color: #475569;")
        root.addWidget(lbl_type)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["ACTIVO", "PASIVO", "PATRIMONIO", "INGRESO", "GASTO"])
        root.addWidget(self.combo_type)

        # Naturaleza
        lbl_nature = QLabel("Naturaleza: *")
        lbl_nature.setStyleSheet("font-weight: 600; color: #475569;")
        root.addWidget(lbl_nature)

        self.combo_nature = QComboBox()
        self.combo_nature.addItems(["DEBITO", "CREDITO"])
        root.addWidget(self.combo_nature)

        # Es cuenta detalle
        self.check_detail = QCheckBox("Esta cuenta acepta movimientos (cuenta detalle)")
        self.check_detail.setChecked(True)
        root.addWidget(self.check_detail)

        # Nivel
        lbl_level = QLabel("Nivel Jerárquico:")
        lbl_level.setStyleSheet("font-weight: 600; color: #475569;")
        root.addWidget(lbl_level)

        self.spin_level = QSpinBox()
        self.spin_level.setRange(1, 10)
        self.spin_level.setValue(4)
        root.addWidget(self.spin_level)

        root.addStretch()

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_cancel = QPushButton("❌ Cancelar")
        btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("💾 Guardar")
        self.btn_save.clicked.connect(self._save)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_save)

        root.addLayout(btn_layout)

        # Estilos
        self.setStyleSheet("""
            QDialog { background-color: #F8F9FA; }
            
            QLabel {
                color: #0F172A;
            }
            
            QLineEdit, QComboBox, QSpinBox {
                padding: 8px 12px;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                background-color: #FFFFFF;
                color: #0F172A;
                font-size: 13px;
            }
            
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border-color: #3B82F6;
                border-width: 2px;
            }
            
            QCheckBox {
                color: #0F172A;
                font-size: 13px;
            }
            
            QPushButton {
                padding: 10px 24px;
                border-radius: 8px;
                font-weight:  600;
                font-size: 14px;
                min-width: 120px;
                color: #FFFFFF;
                background-color:  #3B82F6;
            }
            
            QPushButton:hover {
                background-color: #2563EB;
            }
            
            /* === ARREGLO PARA QMESSAGEBOX === */
            QMessageBox {
                background-color:  #FFFFFF;
            }
            QMessageBox QLabel {
                color: #0F172A;
                font-size: 13px;
                background-color: transparent;
                min-width: 300px;
            }
            QMessageBox QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 600;
                font-size: 13px;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #2563EB;
            }
        """)

    def _load_account_data(self):
        """Carga datos de la cuenta para edición."""
        if not self.account:
            return

        self.edit_code.setText(self.account.get("account_code", ""))
        self.edit_code.setEnabled(False)  # No se puede cambiar el código
        
        self.edit_name.setText(self.account.get("account_name", ""))
        
        acc_type = self.account.get("account_type", "ACTIVO")
        self.combo_type.setCurrentText(acc_type)
        
        nature = self.account.get("nature", "DEBITO")
        self.combo_nature.setCurrentText(nature)
        
        is_detail = self.account.get("is_detail", True)
        self.check_detail.setChecked(is_detail)
        
        level = self.account.get("level", 1)
        self.spin_level.setValue(level)

    def _save(self):
        """Guarda la cuenta."""
        code = self.edit_code.text().strip()
        name = self.edit_name.text().strip()
        
        if not code or not name:
            QMessageBox.warning(self, "Validación", "Código y nombre son obligatorios.")
            return

        # TODO: Implementar update_account en controller si es edición
        if self.is_edit:
            QMessageBox.information(self, "Pendiente", "Función de edición pendiente de implementar.")
            return

        try:
            if hasattr(self.controller, "create_account"):
                ok, msg = self.controller.create_account(
                    self.company_id,
                    code,
                    name,
                    self.combo_type.currentText(),
                    "DEFAULT",  # Categoría
                    None,  # Parent
                    self.spin_level.value(),
                    self.combo_nature.currentText(),
                    self.check_detail.isChecked()
                )

                if ok: 
                    QMessageBox.information(self, "Éxito", msg)
                    self.accept()
                else:
                    QMessageBox.warning(self, "Error", msg)
            else:
                QMessageBox.critical(self, "Error", "Método create_account no implementado.")

        except Exception as e: 
            QMessageBox.critical(self, "Error", f"Error al guardar:\n{e}")