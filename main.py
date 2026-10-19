"""
Sistema CarnitasDB - Menu principal + CRUD de catalogos (PyQt6).

REQUISITO: las clases Conexion_sqlserver y Conexion_psql deben estar en el
archivo conexion.py (misma carpeta). NO se modifican; aqui solo se usan:
    - Conexion_psql.consulta(sql, parametros)      -> devuelve un JSON (str)
    - Conexion_sqlserver.ejecutar(sql, parametros) -> devuelve un JSON (str)
"""
import hashlib
import json
import os
import sys
from decimal import Decimal

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QActionGroup, QIcon
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFrame, QGridLayout, QScrollArea, QWidget,
    QFormLayout, QHBoxLayout, QHeaderView, QAbstractItemView, QInputDialog,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

import qtawesome as qta

from conexion import Conexion_psql, Conexion_sqlserver


# =============================================================================
# 1. CAPA DE BASE DE DATOS  (usa las clases de conexion tal cual)
# =============================================================================
class BaseDatos:
    """Envuelve la clase de conexion elegida y unifica su uso."""

    def __init__(self):
        self.motor = None      # "postgres" | "sqlserver"
        self.conexion = None   # objeto Conexion_psql o Conexion_sqlserver
        self._metodo = None    # consulta (postgres) o ejecutar (sqlserver)
        self.ph = "%s"         # placeholder de parametros segun el motor

    def conectar(self, motor):
        """Cierra la conexion anterior y abre una nueva. True si conecto."""
        nueva = Conexion_psql() if motor == "postgres" else Conexion_sqlserver()
        if nueva.crear_conexion() is None:      # devuelve None si fallo
            return False
        self.cerrar()
        self.motor = motor
        self.conexion = nueva
        if motor == "postgres":
            self._metodo = nueva.consulta
            self.ph = "%s"                      # psycopg2
        else:
            self._metodo = nueva.ejecutar
            self.ph = "?"                       # mssql_python
        return True

    def cerrar(self):
        if self.conexion is not None:
            self.conexion.cerrar_conexion()
        self.conexion = None
        self._metodo = None

    def ejecutar(self, sql, parametros=None):
        """Ejecuta y convierte el JSON de la clase en diccionario Python."""
        if self._metodo is None:
            return {"estado": False, "mensaje": "Sin conexion a la base de datos"}
        return json.loads(self._metodo(sql, parametros))


# =============================================================================
# 2. DEFINICION DE LOS CATALOGOS (tablas maestras)
#    fk = (tabla_referenciada, columna_id, columna_texto_a_mostrar)
# =============================================================================
def F(col, label, tipo="texto", req=False, max=None, fk=None):
    return {"col": col, "label": label, "tipo": tipo, "req": req, "max": max, "fk": fk}


CATALOGOS = {
    "Proveedores": {
        "tabla": "Proveedor", "pk": "Id_Proveedor",
        "campos": [
            F("nombre_empresa", "Nombre de la empresa", req=True, max=150),
            F("telefono", "Telefono", max=20),
            F("direccion", "Direccion", max=200),
        ],
    },
    "Artículos de inventario": {
        "tabla": "ArticuloInventario", "pk": "Id_Articulo",
        "campos": [
            F("nombre", "Nombre", req=True, max=100),
            F("unidad_medida", "Unidad de medida", req=True, max=20),
            F("existencia", "Existencia", tipo="decimal"),
        ],
    },
    "Categorías de abarrotes": {
        "tabla": "CategoriaAbarrotes", "pk": "Id_Categoria",
        "campos": [
            F("nombre", "Nombre", req=True, max=100),
            F("descripcion", "Descripcion", max=200),
        ],
    },
    "Productos de abarrotes": {
        "tabla": "ProductoAbarrotes", "pk": "Id_producto",
        "campos": [
            F("Id_Categoria", "Categoria", tipo="fk", req=True,
              fk=("CategoriaAbarrotes", "Id_Categoria", "nombre")),
            F("Id_Articulo", "Articulo de inventario", tipo="fk", req=True,
              fk=("ArticuloInventario", "Id_Articulo", "nombre")),
            F("nombre", "Nombre", req=True, max=100),
            F("precio_compra", "Precio de compra", tipo="decimal"),
            F("precio_venta", "Precio de venta", tipo="decimal"),
        ],
    },
    "Productos de cocina": {
        "tabla": "ProductoCocina", "pk": "Id_ProductoCocina",
        "campos": [
            F("nombre", "Nombre", req=True, max=100),
            F("precioventa", "Precio de venta", tipo="decimal"),
        ],
    },
    "Tacos": {
        "tabla": "Tacos", "pk": "Id_Tacos",
        "campos": [
            F("tipo", "Tipo", req=True, max=50),
            F("precio", "Precio", tipo="decimal"),
        ],
    },
    "Insumos de cocina": {
        "tabla": "InsumoCocina", "pk": "Id_InsumoCocina",
        "campos": [
            F("Id_Articulo", "Articulo de inventario", tipo="fk", req=True,
              fk=("ArticuloInventario", "Id_Articulo", "nombre")),
            F("nombre_insumo", "Nombre del insumo", req=True, max=100),
            F("tipo_insumo", "Tipo de insumo", max=50),
        ],
    },
    "Métodos de pago": {
        "tabla": "MetodoPago", "pk": "Id_MetodoPago",
        "campos": [F("forma", "Forma de pago", req=True, max=50)],
    },
    "Empleados": {
        "tabla": "Empleado", "pk": "Id_Empleado",
        "campos": [
            F("nombre", "Nombre", req=True, max=100),
            F("apellidos", "Apellidos", req=True, max=100),
            F("telefono", "Telefono", max=20),
            F("puesto", "Puesto", max=50),
            F("salario", "Salario", tipo="decimal"),
        ],
    },
    "Roles": {
        "tabla": "Rol", "pk": "Id_Rol",
        "campos": [
            F("tipo", "Tipo", req=True, max=50),
            F("descripcion", "Descripcion", max=200),
        ],
    },
    "Permisos": {
        "tabla": "Permiso", "pk": "Id_Permiso",
        "campos": [
            F("nombre", "Nombre", req=True, max=100),
            F("descripcion", "Descripcion", max=200),
        ],
    },
    "Usuarios": {
        "tabla": "Usuario", "pk": "Id_Usuario",
        "campos": [
            F("Id_Rol", "Rol", tipo="fk", req=True, fk=("Rol", "Id_Rol", "tipo")),
            F("nombre", "Nombre", req=True, max=100),
            F("apellidos", "Apellidos", req=True, max=100),
            F("correo", "Correo", req=True, max=150),
            F("telefono", "Telefono", max=20),
            F("contrasena", "Contrasena", tipo="password", req=True, max=100),
        ],
    },
}


def hash_password(texto):
    """PBKDF2-SHA256 con sal aleatoria (solo libreria estandar). Cabe en VARCHAR(255)."""
    sal = os.urandom(16)
    iteraciones = 200_000
    dk = hashlib.pbkdf2_hmac("sha256", texto.encode("utf-8"), sal, iteraciones)
    return f"pbkdf2_sha256${iteraciones}${sal.hex()}${dk.hex()}"


# =============================================================================
# 2.1 TEMA VISUAL (iconos + hoja de estilos QSS)
# =============================================================================
ICONOS = {
    "Proveedores": "fa5s.truck",
    "Artículos de inventario": "fa5s.boxes",
    "Categorías de abarrotes": "fa5s.tags",
    "Productos de abarrotes": "fa5s.shopping-basket",
    "Productos de cocina": "fa5s.utensils",
    "Tacos": "fa5s.pepper-hot",
    "Insumos de cocina": "fa5s.carrot",
    "Métodos de pago": "fa5s.credit-card",
    "Empleados": "fa5s.user-tie",
    "Roles": "fa5s.user-shield",
    "Permisos": "fa5s.key",
    "Usuarios": "fa5s.users",
}


def ico(nombre, color="#475569"):
    """Icono vectorial; si algo falla devuelve un icono vacio (nunca rompe la app)."""
    try:
        return qta.icon(nombre, color=color)
    except Exception:
        return QIcon()


STYLE = """
QWidget { font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif; font-size: 14px; color: #1E293B; }
QMainWindow, QDialog { background: #F1F5F9; }

QMenuBar { background: #FFFFFF; border-bottom: 1px solid #E2E8F0; padding: 4px 8px; }
QMenuBar::item { padding: 7px 14px; border-radius: 8px; background: transparent; }
QMenuBar::item:selected { background: #FFEDD5; color: #C2410C; }
QMenu { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 6px; }
QMenu::item { padding: 8px 28px 8px 12px; border-radius: 6px; }
QMenu::item:selected { background: #FFEDD5; color: #C2410C; }
QMenu::separator { height: 1px; background: #E2E8F0; margin: 6px 8px; }
QStatusBar { background: #FFFFFF; border-top: 1px solid #E2E8F0; color: #64748B; }

QLineEdit, QDoubleSpinBox, QComboBox {
    background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px;
    padding: 8px 10px; selection-background-color: #FDBA74; }
QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus { border: 1px solid #EA580C; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView {
    background: #FFFFFF; border: 1px solid #E2E8F0; outline: none;
    selection-background-color: #FFEDD5; selection-color: #C2410C; }

QPushButton { background: #EA580C; color: #FFFFFF; border: none; border-radius: 8px;
              padding: 9px 18px; font-weight: 600; }
QPushButton:hover { background: #C2410C; }
QPushButton:pressed { background: #9A3412; }
QPushButton[rol="secundario"] { background: #FFFFFF; color: #475569; border: 1px solid #CBD5E1; }
QPushButton[rol="secundario"]:hover { background: #F1F5F9; }
QPushButton[rol="peligro"] { background: #DC2626; }
QPushButton[rol="peligro"]:hover { background: #B91C1C; }

QTableWidget { background: #FFFFFF; alternate-background-color: #FFF7ED;
               border: 1px solid #E2E8F0; border-radius: 10px;
               selection-background-color: #FED7AA; selection-color: #7C2D12; }
QTableWidget::item { padding: 6px; border: none; }
QHeaderView::section { background: #FFEDD5; color: #9A3412; padding: 10px;
                       border: none; font-weight: 700; }

QLabel#titulo { font-size: 22px; font-weight: 700; color: #1E293B; }
QLabel#subtitulo { color: #64748B; }

QFrame#tarjeta { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px; }
QFrame#tarjeta:hover { background: #FFF7ED; border: 1px solid #EA580C; }
QFrame#tarjeta QLabel { background: transparent; }
QFrame#banner { border-radius: 16px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #EA580C, stop:1 #F59E0B); }
QFrame#banner QLabel { color: #FFFFFF; background: transparent; }

QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #CBD5E1; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #1E293B; color: #FFFFFF; border: none; padding: 6px; }
"""


# =============================================================================
# 3. CONSULTAS CRUD  (todo el SQL del sistema esta en esta clase)
#    Los datos SIEMPRE viajan como parametros (nunca concatenados) para evitar
#    inyeccion SQL. Los nombres de tabla/columna salen de CATALOGOS (fijos).
#    Nota: PostgreSQL devuelve los nombres de columna en minusculas, por eso
#    todas las claves de los diccionarios se pasan a minusculas.
# =============================================================================
class Crud:
    def __init__(self, db):
        self.db = db

    def listar(self, cat):
        """CONSULTAR: todos los registros ordenados por llave primaria."""
        sql = f"SELECT * FROM {cat['tabla']} ORDER BY {cat['pk']}"
        r = self.db.ejecutar(sql)
        if r.get("estado"):
            filas = [{k.lower(): v for k, v in fila.items()} for fila in r["registros"]]
            return True, filas
        return False, r

    def opciones_fk(self, fk):
        """Lista (id, texto) de una tabla referenciada, para combos."""
        tabla, col_id, col_txt = fk
        r = self.db.ejecutar(f"SELECT {col_id}, {col_txt} FROM {tabla} ORDER BY {col_txt}")
        if not r.get("estado"):
            return []
        salida = []
        for fila in r["registros"]:
            f = {k.lower(): v for k, v in fila.items()}
            salida.append((int(f[col_id.lower()]), str(f[col_txt.lower()])))
        return salida

    def insertar(self, cat, valores):
        """INSERT: el ID se genera solo (SERIAL / IDENTITY), por eso no se envia."""
        cols = list(valores.keys())
        marcas = ", ".join([self.db.ph] * len(cols))
        sql = f"INSERT INTO {cat['tabla']} ({', '.join(cols)}) VALUES ({marcas})"
        return self.db.ejecutar(sql, tuple(valores[c] for c in cols))

    def actualizar(self, cat, id_valor, valores):
        """UPDATE de las columnas indicadas para un registro."""
        cols = list(valores.keys())
        sets = ", ".join(f"{c} = {self.db.ph}" for c in cols)
        sql = f"UPDATE {cat['tabla']} SET {sets} WHERE {cat['pk']} = {self.db.ph}"
        return self.db.ejecutar(sql, tuple(valores[c] for c in cols) + (id_valor,))

    def eliminar(self, cat, id_valor):
        """DELETE fisico por llave primaria."""
        sql = f"DELETE FROM {cat['tabla']} WHERE {cat['pk']} = {self.db.ph}"
        return self.db.ejecutar(sql, (id_valor,))


def mostrar_error(parent, r, titulo="Error"):
    detalle = r.get("mensaje", "Error desconocido")
    if r.get("error"):
        detalle += f"\n\n{r['error']}"
    QMessageBox.critical(parent, titulo, detalle)


# =============================================================================
# 4. FORMULARIO (Insertar / Actualizar)
# =============================================================================
class FormularioDialog(QDialog):
    def __init__(self, crud, cat, titulo, fila=None, parent=None):
        super().__init__(parent)
        self.cat = cat
        self.editando = fila is not None
        self.setWindowTitle(titulo)
        self.setMinimumWidth(420)
        self.widgets = {}

        form = QFormLayout()
        for c in cat["campos"]:
            w = self._crear_widget(crud, c)
            if self.editando:
                self._cargar_valor(w, c, fila.get(c["col"].lower()))
            etiqueta = c["label"] + (" *" if c["req"] else "")
            if c["tipo"] == "password" and self.editando:
                etiqueta += " (vacio = no cambiar)"
            form.addRow(etiqueta, w)
            self.widgets[c["col"]] = w

        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        guardar = QPushButton(" Guardar")
        guardar.setIcon(ico("fa5s.save", "#FFFFFF"))
        guardar.clicked.connect(self._validar)
        cancelar = QPushButton(" Cancelar")
        cancelar.setProperty("rol", "secundario")
        cancelar.setIcon(ico("fa5s.times", "#475569"))
        cancelar.clicked.connect(self.reject)
        botones = QHBoxLayout()
        botones.addStretch()
        botones.addWidget(cancelar)
        botones.addWidget(guardar)

        encabezado = QLabel(titulo)
        encabezado.setObjectName("titulo")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(18)
        lay.addWidget(encabezado)
        lay.addLayout(form)
        lay.addLayout(botones)

    def _crear_widget(self, crud, c):
        if c["tipo"] == "decimal":
            w = QDoubleSpinBox()
            w.setDecimals(2)
            w.setRange(0, 99999999.99)
            return w
        if c["tipo"] == "fk":
            w = QComboBox()
            for id_, texto in crud.opciones_fk(c["fk"]):
                w.addItem(f"{texto}", id_)
            return w
        w = QLineEdit()
        if c["max"]:
            w.setMaxLength(c["max"])
        if c["tipo"] == "password":
            w.setEchoMode(QLineEdit.EchoMode.Password)
        return w

    def _cargar_valor(self, w, c, valor):
        if c["tipo"] == "decimal":
            w.setValue(float(valor or 0))
        elif c["tipo"] == "fk":
            i = w.findData(int(valor)) if valor is not None else -1
            if i >= 0:
                w.setCurrentIndex(i)
        elif c["tipo"] == "password":
            w.clear()
        else:
            w.setText("" if valor is None else str(valor))

    def _validar(self):
        for c in self.cat["campos"]:
            w = self.widgets[c["col"]]
            if c["tipo"] == "fk" and w.currentIndex() < 0:
                QMessageBox.warning(self, "Dato requerido",
                                    f"No hay registros en el catalogo de '{c['label']}'. "
                                    "Captura uno primero.")
                return
            if c["tipo"] in ("texto", "password") and c["req"]:
                # al editar, la contrasena puede quedar vacia (no se cambia)
                if not w.text().strip() and not (c["tipo"] == "password" and self.editando):
                    QMessageBox.warning(self, "Dato requerido", f"'{c['label']}' es obligatorio.")
                    return
        self.accept()

    def valores(self):
        """Devuelve {columna: valor} listo para enviarse como parametros."""
        v = {}
        for c in self.cat["campos"]:
            w = self.widgets[c["col"]]
            if c["tipo"] == "decimal":
                v[c["col"]] = Decimal(f"{w.value():.2f}")
            elif c["tipo"] == "fk":
                v[c["col"]] = int(w.currentData())
            elif c["tipo"] == "password":
                if w.text():                      # vacio al editar = no se modifica
                    v[c["col"]] = hash_password(w.text())
            else:
                texto = w.text().strip()
                v[c["col"]] = texto if texto else None   # vacio -> NULL
        return v


# =============================================================================
# 5. VENTANA DE LISTA (Consultar / Actualizar / Eliminar)
# =============================================================================
class ListaDialog(QDialog):
    def __init__(self, crud, nombre, cat, modo, parent=None):
        super().__init__(parent)
        self.crud, self.cat, self.modo = crud, cat, modo
        self.filas = []
        titulos = {"consultar": "Consultar", "actualizar": "Actualizar",
                   "eliminar": "Eliminar", "todo": "Administrar"}
        self.setWindowTitle(f"{titulos[modo]} - {nombre}")
        self.resize(820, 480)

        # columnas visibles: ID + campos (la contrasena nunca se muestra)
        self.campos = [c for c in cat["campos"] if c["tipo"] != "password"]
        self.fk_texto = {c["col"]: dict(crud.opciones_fk(c["fk"]))
                         for c in self.campos if c["tipo"] == "fk"}

        self.buscar = QLineEdit()
        self.buscar.setPlaceholderText("Buscar...")
        self.buscar.textChanged.connect(self._pintar)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(self.campos) + 1)
        self.tabla.setHorizontalHeaderLabels(["ID"] + [c["label"] for c in self.campos])
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.verticalHeader().setVisible(False)

        self.resize(920, 580)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)
        self.buscar.addAction(ico("fa5s.search", "#94A3B8"),
                              QLineEdit.ActionPosition.LeadingPosition)

        def boton(texto, icono, slot, rol=None):
            b = QPushButton(f" {texto}")
            b.setIcon(ico(icono, "#FFFFFF" if rol != "secundario" else "#475569"))
            if rol:
                b.setProperty("rol", rol)
            b.clicked.connect(slot)
            return b

        botones = QHBoxLayout()
        botones.addStretch()
        if modo == "todo":
            botones.addWidget(boton("Nuevo", "fa5s.plus", self._insertar))
        if modo in ("actualizar", "todo"):
            botones.addWidget(boton("Editar" if modo == "todo" else "Actualizar seleccionado",
                                    "fa5s.edit", self._actualizar))
            self.tabla.doubleClicked.connect(self._actualizar)
        if modo in ("eliminar", "todo"):
            botones.addWidget(boton("Eliminar" if modo == "todo" else "Eliminar seleccionado",
                                    "fa5s.trash-alt", self._eliminar, "peligro"))
        botones.addWidget(boton("Cerrar", "fa5s.times", self.close, "secundario"))

        # encabezado: icono + titulo + contador de registros
        icono = QLabel()
        icono.setPixmap(ico(ICONOS.get(nombre, "fa5s.table"), "#EA580C").pixmap(34, 34))
        titulo = QLabel(nombre)
        titulo.setObjectName("titulo")
        self.lbl_total = QLabel("")
        self.lbl_total.setObjectName("subtitulo")
        textos = QVBoxLayout()
        textos.setSpacing(0)
        textos.addWidget(titulo)
        textos.addWidget(self.lbl_total)
        cab = QHBoxLayout()
        cab.addWidget(icono)
        cab.addLayout(textos)
        cab.addStretch()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)
        lay.addLayout(cab)
        lay.addWidget(self.buscar)
        lay.addWidget(self.tabla)
        lay.addLayout(botones)
        self._cargar()

    def _cargar(self):
        ok, datos = self.crud.listar(self.cat)
        if not ok:
            mostrar_error(self, datos, "No se pudo consultar")
            self.filas = []
        else:
            self.filas = datos
        self._pintar()

    def _texto_celda(self, c, fila):
        valor = fila.get(c["col"].lower())
        if valor is None:
            return ""
        if c["tipo"] == "fk":
            return self.fk_texto.get(c["col"], {}).get(int(valor), str(valor))
        return str(valor)

    def _pintar(self):
        filtro = self.buscar.text().strip().lower()
        self.tabla.setRowCount(0)
        for fila in self.filas:
            textos = [str(fila.get(self.cat["pk"].lower()))] + \
                     [self._texto_celda(c, fila) for c in self.campos]
            if filtro and not any(filtro in t.lower() for t in textos):
                continue
            r = self.tabla.rowCount()
            self.tabla.insertRow(r)
            for i, t in enumerate(textos):
                item = QTableWidgetItem(t)
                if i == 0:  # guardamos la fila completa en la celda del ID
                    item.setData(Qt.ItemDataRole.UserRole, fila)
                self.tabla.setItem(r, i, item)
        self.lbl_total.setText(f"{self.tabla.rowCount()} registro(s)")

    def _seleccionada(self):
        r = self.tabla.currentRow()
        if r < 0:
            QMessageBox.information(self, "Seleccione", "Seleccione un registro de la tabla.")
            return None
        return self.tabla.item(r, 0).data(Qt.ItemDataRole.UserRole)

    def _insertar(self):
        dlg = FormularioDialog(self.crud, self.cat, "Nuevo registro", parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        r = self.crud.insertar(self.cat, dlg.valores())
        if r.get("estado"):
            self._cargar()
        else:
            mostrar_error(self, r, "No se pudo insertar")

    def _actualizar(self, *_):
        fila = self._seleccionada()
        if fila is None:
            return
        dlg = FormularioDialog(self.crud, self.cat, "Actualizar registro", fila, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        id_valor = int(fila[self.cat["pk"].lower()])
        r = self.crud.actualizar(self.cat, id_valor, dlg.valores())
        if r.get("estado"):
            QMessageBox.information(self, "Listo", r.get("mensaje", "Actualizado"))
            self._cargar()
        else:
            mostrar_error(self, r, "No se pudo actualizar")

    def _eliminar(self):
        fila = self._seleccionada()
        if fila is None:
            return
        id_valor = int(fila[self.cat["pk"].lower()])
        resp = QMessageBox.question(
            self, "Confirmar eliminacion",
            f"¿Eliminar definitivamente el registro {id_valor}?\nEsta accion no se puede deshacer.")
        if resp != QMessageBox.StandardButton.Yes:
            return
        r = self.crud.eliminar(self.cat, id_valor)
        if r.get("estado"):
            QMessageBox.information(self, "Listo", r.get("mensaje", "Eliminado"))
            self._cargar()
        elif r.get("tipo") == "IntegrityError":
            QMessageBox.warning(
                self, "No se puede eliminar",
                "El registro esta relacionado con otros datos (compras, ventas, etc.) "
                f"y la base de datos no permite borrarlo.\n\n{r.get('error', '')}")
        else:
            mostrar_error(self, r, "No se pudo eliminar")


# =============================================================================
# 6. MENU PRINCIPAL
# =============================================================================
class Tarjeta(QFrame):
    """Tarjeta clicable de la pantalla de inicio (abre la administracion del catalogo)."""

    def __init__(self, nombre, on_click):
        super().__init__()
        self.setObjectName("tarjeta")
        self.on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(120)
        centro = Qt.AlignmentFlag.AlignCenter
        icono = QLabel()
        icono.setPixmap(ico(ICONOS[nombre], "#EA580C").pixmap(40, 40))
        icono.setAlignment(centro)
        titulo = QLabel(nombre)
        titulo.setAlignment(centro)
        titulo.setWordWrap(True)
        titulo.setStyleSheet("font-weight: 600;")
        lay = QVBoxLayout(self)
        lay.setAlignment(centro)
        lay.setSpacing(8)
        lay.addWidget(icono)
        lay.addWidget(titulo)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.on_click()


class SelectorMotor(QDialog):
    """Pantalla inicial para elegir el motor de base de datos."""

    def __init__(self):
        super().__init__()
        self.clave = None
        self.setWindowTitle("Carnitas")
        self.setMinimumWidth(420)
        titulo = QLabel("Bienvenido")
        titulo.setObjectName("titulo")
        sub = QLabel("Seleccione el motor de base de datos")
        sub.setObjectName("subtitulo")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(14)
        lay.addWidget(titulo)
        lay.addWidget(sub)
        for clave, nombre, icono in (("postgres", "PostgreSQL", "fa5s.database"),
                                     ("sqlserver", "SQL Server", "fa5s.server")):
            b = QPushButton(f"  {nombre}")
            b.setIcon(ico(icono, "#FFFFFF"))
            b.setIconSize(QSize(20, 20))
            b.setMinimumHeight(48)
            b.clicked.connect(lambda _, k=clave: self._elegir(k))
            lay.addWidget(b)
        salir = QPushButton("Salir")
        salir.setProperty("rol", "secundario")
        salir.clicked.connect(self.reject)
        lay.addWidget(salir)

    def _elegir(self, clave):
        self.clave = clave
        self.accept()


class VentanaPrincipal(QMainWindow):
    NOMBRES_MOTOR = {"postgres": "PostgreSQL", "sqlserver": "SQL Server"}

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.crud = Crud(db)
        self.setWindowTitle("Carnitas - Sistema de gestion")
        self.resize(1040, 660)

        self.setCentralWidget(self._crear_inicio())
        self._crear_menu()
        self._actualizar_estado()

    def _crear_inicio(self):
        """Pantalla de inicio: banner + una tarjeta por catalogo."""
        cont = QWidget()
        lay = QVBoxLayout(cont)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(18)

        banner = QFrame()
        banner.setObjectName("banner")
        bl = QVBoxLayout(banner)
        bl.setContentsMargins(28, 22, 28, 22)
        t = QLabel("Carnitas · Sistema de gestión")
        t.setStyleSheet("font-size: 26px; font-weight: 700;")
        self.lbl = QLabel()
        bl.addWidget(t)
        bl.addWidget(self.lbl)
        lay.addWidget(banner)

        seccion = QLabel("Catálogos")
        seccion.setObjectName("titulo")
        lay.addWidget(seccion)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        cuadricula_w = QWidget()
        grid = QGridLayout(cuadricula_w)
        grid.setSpacing(14)
        for i, nombre in enumerate(CATALOGOS):
            grid.addWidget(Tarjeta(nombre, lambda n=nombre: self._abrir(n, "todo")),
                           i // 4, i % 4)
        grid.setRowStretch(grid.rowCount(), 1)
        scroll.setWidget(cuadricula_w)
        lay.addWidget(scroll)
        return cont

    def _crear_menu(self):
        barra = self.menuBar()

        # --- Archivo ---
        m_archivo = barra.addMenu("&Archivo")
        m_motor = m_archivo.addMenu("Motor de base de datos")
        grupo = QActionGroup(self)
        grupo.setExclusive(True)
        self.acc_motor = {}
        for clave, nombre in self.NOMBRES_MOTOR.items():
            a = QAction(nombre, self, checkable=True)
            a.setChecked(clave == self.db.motor)
            a.triggered.connect(lambda _, k=clave: self._cambiar_motor(k))
            grupo.addAction(a)
            m_motor.addAction(a)
            self.acc_motor[clave] = a
        m_archivo.addSeparator()
        salir = QAction("Salir", self)
        salir.triggered.connect(self.close)
        m_archivo.addAction(salir)

        # --- Catalogos: submenu por tabla maestra, con sus 4 operaciones ---
        m_cat = barra.addMenu("&Catálogos")
        for nombre, cat in CATALOGOS.items():
            sub = m_cat.addMenu(ico(ICONOS[nombre], "#C2410C"), nombre)
            for texto, modo, icono in (("Insertar", "insertar", "fa5s.plus"),
                                       ("Actualizar", "actualizar", "fa5s.edit"),
                                       ("Eliminar", "eliminar", "fa5s.trash-alt"),
                                       ("Consultar", "consultar", "fa5s.search")):
                a = QAction(ico(icono, "#475569"), texto, self)
                a.triggered.connect(lambda _, n=nombre, m=modo: self._abrir(n, m))
                sub.addAction(a)

        # --- Ayuda ---
        m_ayuda = barra.addMenu("A&yuda")
        acerca = QAction("Acerca de", self)
        acerca.triggered.connect(lambda: QMessageBox.about(
            self, "Acerca de", "Sistema Carnitas\nPyQt6 + PostgreSQL / SQL Server"))
        m_ayuda.addAction(acerca)

    def _actualizar_estado(self):
        motor = self.NOMBRES_MOTOR.get(self.db.motor, "Sin conexion")
        self.lbl.setText(f"Motor activo: {motor}  ·  Haga clic en un catálogo para administrarlo")
        self.statusBar().showMessage(f"Conectado a: {motor}")

    def _cambiar_motor(self, clave):
        if clave == self.db.motor:
            return
        if self.db.conectar(clave):
            self._actualizar_estado()
        else:
            QMessageBox.critical(self, "Conexion fallida",
                                 f"No fue posible conectar con {self.NOMBRES_MOTOR[clave]}.\n"
                                 "Revise el archivo .env.")
            if self.db.motor in self.acc_motor:   # volver a marcar el motor anterior
                self.acc_motor[self.db.motor].setChecked(True)

    def _abrir(self, nombre, modo):
        cat = CATALOGOS[nombre]
        if modo == "insertar":
            dlg = FormularioDialog(self.crud, cat, f"Insertar - {nombre}", parent=self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            r = self.crud.insertar(cat, dlg.valores())
            if r.get("estado"):
                QMessageBox.information(self, "Listo", r.get("mensaje", "Insertado"))
            else:
                mostrar_error(self, r, "No se pudo insertar")
        else:
            ListaDialog(self.crud, nombre, cat, modo, self).exec()

    def closeEvent(self, e):
        self.db.cerrar()
        e.accept()


# =============================================================================
# 7. ARRANQUE: elegir motor y abrir el menu
# =============================================================================
def main():
    app = QApplication(sys.argv)
    db = BaseDatos()

    app.setStyleSheet(STYLE)
    while True:
        selector = SelectorMotor()
        if selector.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
        if db.conectar(selector.clave):
            break
        QMessageBox.critical(
            None, "Conexion fallida",
            f"No fue posible conectar con {VentanaPrincipal.NOMBRES_MOTOR[selector.clave]}."
            "\nRevise el archivo .env.")

    ventana = VentanaPrincipal(db)
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()