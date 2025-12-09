import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QGraphicsView, QGraphicsScene
)
from PyQt5.QtCore import Qt, QMimeData, QPointF, QByteArray
from PyQt5.QtGui import (
    QDrag, QBrush, QPen, QFont, QColor,
    QPainter
)

from session import LadderSession, BlockState  # <- NUEVO


MIME_BLOCK_TYPE = "application/x-plc-block"


class DraggableButton(QPushButton):
    """
    Botón que inicia un QDrag con el tipo de bloque (block_type)
    cuando el usuario arrastra con el mouse.
    """
    def __init__(self, text, block_type, parent=None):
        super().__init__(text, parent)
        self.block_type = block_type
        self._drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return

        if self._drag_start_pos is None:
            return

        # Distancia mínima para considerar que es un drag
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return

        # Iniciar el drag
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData(MIME_BLOCK_TYPE, QByteArray(self.block_type.encode("utf-8")))
        drag.setMimeData(mime_data)

        drag.exec_(Qt.CopyAction)


class WorkspaceView(QGraphicsView):
    """
    Vista del espacio de trabajo tipo ladder.
    - Usa LadderSession para manejar posiciones y tipos.
    - 4 filas (rungs).
    - Máx N columnas; la barra vertical derecha es el límite.
    - Bloques de izquierda a derecha, sin superposición.
    - Reordenamiento arrastrando bloques.
    - Borrado de bloques seleccionados (botón o tecla Delete/Backspace).
    """

    def __init__(self, session: LadderSession, parent=None):
        super().__init__(parent)

        self.session = session  # <- sesión lógica

        scene = QGraphicsScene(self)
        self.setScene(scene)

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setAcceptDrops(True)
        self.setBackgroundBrush(QColor("#1e1e1e"))
        self.setFocusPolicy(Qt.ClickFocus)  # para recibir teclas al hacer click

        # Parámetros de la grilla lógica (coherentes con LadderSession)
        self.num_rows = self.session.max_rows
        self.max_cols = self.session.max_cols
        self.base_y = 80        # centro del primer renglón
        self.row_height = 80    # distancia entre renglones

        self.base_x = 140       # centro de la primera columna
        self.col_width = 140    # distancia entre columnas

        # Mapa id -> QGraphicsItem
        self.items_by_id: dict[int, object] = {}

        # Dibujar los rieles y renglones tipo ladder
        self._create_ladder_rungs()

        # Ajustar vista inicial al contenido
        self._fit_to_view()

    # ------------------------------------------------------------------
    # Dibujar ladder: rieles y rungs
    # ------------------------------------------------------------------
    def _create_ladder_rungs(self):
        """
        Dibuja:
        - Dos rieles verticales (izquierdo y derecho).
        - Un rung horizontal por cada fila.
        Y define el rectángulo de escena para poder hacer zoom automático.
        """
        scene = self.scene()

        # Posición de los rieles en X en función de las columnas
        self.rail_x_left = self.base_x - 80
        # El rail derecho queda un poco después de la última columna
        self.rail_x_right = self.base_x + (self.max_cols - 1) * self.col_width + 80

        # Y de inicio/fin de los rieles verticales
        top_y = self.base_y - self.row_height
        bottom_y = self.base_y + (self.num_rows) * self.row_height

        pen_rail = QPen(QColor("#bbbbbb"))
        pen_rail.setWidth(2)

        # Riel izquierdo
        left_rail = scene.addLine(
            self.rail_x_left, top_y,
            self.rail_x_left, bottom_y,
            pen_rail
        )
        left_rail.setZValue(-10)
        left_rail.setFlag(left_rail.ItemIsSelectable, False)
        left_rail.setFlag(left_rail.ItemIsMovable, False)

        # Riel derecho
        right_rail = scene.addLine(
            self.rail_x_right, top_y,
            self.rail_x_right, bottom_y,
            pen_rail
        )
        right_rail.setZValue(-10)
        right_rail.setFlag(right_rail.ItemIsSelectable, False)
        right_rail.setFlag(right_rail.ItemIsMovable, False)

        # Rungs horizontales (uno por fila)
        pen_rung = QPen(QColor("#888888"))
        pen_rung.setWidth(1)

        for r in range(self.num_rows):
            cy = self.base_y + r * self.row_height
            rung = scene.addLine(
                self.rail_x_left, cy,
                self.rail_x_right, cy,
                pen_rung
            )
            rung.setZValue(-10)
            rung.setFlag(rung.ItemIsSelectable, False)
            rung.setFlag(rung.ItemIsMovable, False)

        # Definir rectángulo de escena para que el fitInView sepa qué mostrar
        margin = 40
        scene.setSceneRect(
            self.rail_x_left - margin,
            top_y - margin,
            (self.rail_x_right - self.rail_x_left) + 2 * margin,
            (bottom_y - top_y) + 2 * margin
        )

    # ------------------------------------------------------------------
    # Zoom automático al contenido
    # ------------------------------------------------------------------
    def _fit_to_view(self):
        rect = self.scene().sceneRect()
        if not rect.isNull():
            self.fitInView(rect, Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        """Cuando la vista cambia de tamaño, reencuadra el ladder."""
        super().resizeEvent(event)
        self._fit_to_view()

    # ------------------------------------------------------------------
    # Utilidades de grilla
    # ------------------------------------------------------------------
    def row_from_y(self, y: float) -> int:
        """Determina el índice de fila (0..num_rows-1) a partir de una coordenada Y."""
        r = round((y - self.base_y) / self.row_height)
        r = max(0, min(self.num_rows - 1, r))
        return r

    def grid_center(self, row: int, index: int) -> QPointF:
        """Devuelve el punto centro (cx, cy) de un slot (row, index)."""
        cx = self.base_x + index * self.col_width
        cy = self.base_y + row * self.row_height
        return QPointF(cx, cy)

    def set_block_center(self, item, center: QPointF):
        """Posiciona un item para que su centro quede en 'center'."""
        br = item.boundingRect()
        x = center.x() - (br.width() / 2 + br.x())
        y = center.y() - (br.height() / 2 + br.y())
        item.setPos(x, y)

    # ------------------------------------------------------------------
    # Drag & Drop desde los botones
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_BLOCK_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_BLOCK_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(MIME_BLOCK_TYPE):
            event.ignore()
            return

        block_type_bytes = event.mimeData().data(MIME_BLOCK_TYPE)
        block_type = bytes(block_type_bytes).decode("utf-8")

        pos_in_scene = self.mapToScene(event.pos())
        row = self.row_from_y(pos_in_scene.y())

        # Pedimos a la sesión que agregue al final de la fila
        state = self.session.add_block_end_of_row(row, block_type)
        if state is None:
            # fila llena
            event.ignore()
            return

        # Crear gráficamente el bloque
        item = self._create_graphics_block(block_type)
        item.setData(0, "BLOCK")
        item.setData(1, state.id)  # ID de sesión
        item.setZValue(0)

        self.items_by_id[state.id] = item

        # Ubicar todos los bloques de esa fila
        self.layout_row(row)

        event.acceptProposedAction()

    # ------------------------------------------------------------------
    # Crear bloque gráfico segun tipo (símbolos ladder)
    # ------------------------------------------------------------------
    def _create_graphics_block(self, block_type: str):
        """
        Crea el QGraphicsItem del símbolo ladder.
        Aquí solo construimos el shape, no manejamos posiciones lógicas.
        """
        if block_type == "XIC":
            return self._create_contact_no_block()
        elif block_type == "XIO":
            return self._create_contact_nc_block()
        elif block_type in ("OTE", "OTL", "OTU"):
            return self._create_coil_block(block_type)
        elif block_type == "TON":
            return self._create_timer_block()
        else:
            return self._create_contact_no_block()

    # --- Constructores de símbolos ladder (gráficos) ---
    def _create_contact_no_block(self):
        """
        XIC - Contacto normalmente abierto:
        Rectángulo base + dos líneas verticales internas.
        """
        scene = self.scene()
        width = 120
        height = 50

        rect = scene.addRect(
            0, 0, width, height,
            QPen(QColor("#ffffff")),
            QBrush(QColor("#2d2d30"))
        )
        rect.setFlag(rect.ItemIsMovable, True)
        rect.setFlag(rect.ItemIsSelectable, True)

        # Líneas del contacto
        pen = QPen(QColor("#ffffff"))
        pen.setWidth(2)
        cx = width / 2
        y1 = height * 0.2
        y2 = height * 0.8
        offset = 20

        left_line = scene.addLine(cx - offset, y1, cx - offset, y2, pen)
        right_line = scene.addLine(cx + offset, y1, cx + offset, y2, pen)

        left_line.setParentItem(rect)
        right_line.setParentItem(rect)

        return rect

    def _create_contact_nc_block(self):
        """
        XIO - Contacto normalmente cerrado:
        Igual que NO pero con una línea diagonal cruzando.
        """
        rect = self._create_contact_no_block()
        scene = self.scene()
        br = rect.boundingRect()
        width = br.width()
        height = br.height()

        pen = QPen(QColor("#ffffff"))
        pen.setWidth(2)
        cx = width / 2
        y1 = height * 0.2
        y2 = height * 0.8
        offset = 20

        diag = scene.addLine(
            cx - offset, y1,
            cx + offset, y2,
            pen
        )
        diag.setParentItem(rect)

        return rect

    def _create_coil_block(self, coil_type="OTE"):
        """
        OTE/OTL/OTU - Bobina:
        Rectángulo base + círculo interno + etiqueta pequeña.
        """
        scene = self.scene()
        width = 120
        height = 50

        rect = scene.addRect(
            0, 0, width, height,
            QPen(QColor("#ffffff")),
            QBrush(QColor("#2d2d30"))
        )
        rect.setFlag(rect.ItemIsMovable, True)
        rect.setFlag(rect.ItemIsSelectable, True)

        # Círculo central
        radius = 14
        cx = width / 2
        cy = height / 2
        circ = scene.addEllipse(
            cx - radius, cy - radius,
            2 * radius, 2 * radius,
            QPen(QColor("#ffffff")),
            QBrush(Qt.NoBrush)
        )
        circ.setParentItem(rect)

        inner_text = self.scene().addText(coil_type, QFont("Segoe UI", 7, QFont.Bold))
        inner_text.setDefaultTextColor(QColor("#ffffff"))
        tr = inner_text.boundingRect()
        inner_text.setPos(
            cx - tr.width() / 2,
            cy - tr.height() / 2
        )
        inner_text.setParentItem(rect)

        return rect

    def _create_timer_block(self):
        """
        TON - Timer:
        Rectángulo base + recuadro interno y texto TON.
        """
        scene = self.scene()
        width = 120
        height = 50

        rect = scene.addRect(
            0, 0, width, height,
            QPen(QColor("#ffffff")),
            QBrush(QColor("#2d2d30"))
        )
        rect.setFlag(rect.ItemIsMovable, True)
        rect.setFlag(rect.ItemIsSelectable, True)

        margin = 10
        inner = scene.addRect(
            margin, margin,
            width - 2 * margin, height - 2 * margin,
            QPen(QColor("#ffffff")),
            QBrush(Qt.NoBrush)
        )
        inner.setParentItem(rect)

        inner_text = scene.addText("TON", QFont("Segoe UI", 9, QFont.Bold))
        inner_text.setDefaultTextColor(QColor("#ffffff"))
        br = rect.boundingRect()
        tr = inner_text.boundingRect()
        inner_text.setPos(
            br.center().x() - tr.width() / 2,
            br.center().y() - tr.height() / 2
        )
        inner_text.setParentItem(rect)

        return rect

    # ------------------------------------------------------------------
    # Layout de filas en función de la sesión
    # ------------------------------------------------------------------
    def layout_row(self, row: int):
        """Reposiciona gráficamente todos los bloques de una fila según el orden de la sesión."""
        if not (0 <= row < self.num_rows):
            return

        row_ids = self.session.rows[row]  # lista de IDs en esa fila
        for index, block_id in enumerate(row_ids):
            item = self.items_by_id.get(block_id)
            if item is None:
                continue
            center = self.grid_center(row, index)
            self.set_block_center(item, center)

    # ------------------------------------------------------------------
    # Reordenamiento al soltar el mouse
    # ------------------------------------------------------------------
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

        item = self.itemAt(event.pos())
        if item is None:
            return

        # Si el item es hijo (línea, texto), subimos al padre
        block_item = self._get_block_from_item(item)
        if block_item is None:
            return

        block_id = block_item.data(1)
        if block_id is None:
            return

        # Centro en coordenadas de escena
        center_scene = block_item.mapToScene(block_item.boundingRect().center())
        new_row = self.row_from_y(center_scene.y())

        # Cálculo de índice destino aproximado por X
        row_list = self.session.rows[new_row]
        if not row_list:
            new_index = 0
        else:
            rel = (center_scene.x() - self.base_x) / self.col_width
            new_index = round(rel)
            if new_index < 0:
                new_index = 0
            if new_index > len(row_list):
                new_index = len(row_list)

        # Pedir a la sesión el movimiento
        moved = self.session.move_block(int(block_id), new_row, new_index)
        if moved is None:
            # Movimiento inválido (por ejemplo fila destino llena): re-layout fila original
            state = self.session.get_block_state(int(block_id))
            if state:
                self.layout_row(state.row)
            return

        old_row, final_row = moved
        self.layout_row(old_row)
        if final_row != old_row:
            self.layout_row(final_row)

    def _get_block_from_item(self, item):
        """Si el item es un bloque o un hijo de bloque, devuelve el bloque principal."""
        it = item
        while it is not None:
            if it.data(0) == "BLOCK":
                return it
            it = it.parentItem()
        return None

    # ------------------------------------------------------------------
    # Borrado de bloques
    # ------------------------------------------------------------------
    def delete_block(self, block_item):
        """Elimina un bloque de la escena y de la sesión."""
        block_id = block_item.data(1)
        if block_id is None:
            return

        block_id = int(block_id)
        row = self.session.delete_block(block_id)
        # Eliminar el item y sus hijos gráficos
        self.scene().removeItem(block_item)
        self.items_by_id.pop(block_id, None)

        if row is not None:
            self.layout_row(row)

    def delete_selected(self):
        """Elimina todos los bloques seleccionados."""
        selected = self.scene().selectedItems()
        processed = set()
        for item in selected:
            block = self._get_block_from_item(item)
            if block is not None and block not in processed:
                processed.add(block)
                self.delete_block(block)

    def keyPressEvent(self, event):
        """Permite borrar con Delete o Backspace."""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected()
        else:
            super().keyPressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PLC Designer - Ladder con sesión")
        self.resize(1000, 600)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)

        # Crear la sesión lógica
        self.session = LadderSession(max_rows=4, max_cols=6)

        # ---------- Panel izquierdo: Toolbox ----------
        toolbox = QWidget()
        toolbox_layout = QVBoxLayout(toolbox)
        toolbox_layout.setContentsMargins(10, 10, 10, 10)
        toolbox_layout.setSpacing(10)

        label = QLabel("Símbolos ladder")
        label.setStyleSheet("font-size: 14px; font-weight: bold;")
        toolbox_layout.addWidget(label)

        # 6 símbolos
        btn_xic = DraggableButton("XIC (NO)", "XIC")
        btn_xio = DraggableButton("XIO (NC)", "XIO")
        btn_ote = DraggableButton("OTE (Coil)", "OTE")
        btn_otl = DraggableButton("OTL (Latch)", "OTL")
        btn_otu = DraggableButton("OTU (Unlatch)", "OTU")
        btn_ton = DraggableButton("TON (Timer)", "TON")

        for btn in (btn_xic, btn_xio, btn_ote, btn_otl, btn_otu, btn_ton):
            btn.setMinimumHeight(30)
            toolbox_layout.addWidget(btn)

        # Botón para eliminar el bloque seleccionado
        delete_btn = QPushButton("Eliminar seleccionado")
        delete_btn.clicked.connect(self.on_delete_clicked)
        toolbox_layout.addWidget(delete_btn)

        toolbox_layout.addStretch()

        # ---------- Panel derecho: Workspace ----------
        workspace_container = QWidget()
        workspace_layout = QVBoxLayout(workspace_container)
        workspace_layout.setContentsMargins(10, 10, 10, 10)
        workspace_layout.setSpacing(5)

        workspace_label = QLabel("Espacio de trabajo (4 rungs)")
        workspace_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        workspace_layout.addWidget(workspace_label)

        self.workspace_view = WorkspaceView(self.session)
        workspace_layout.addWidget(self.workspace_view)

        # ---------- Layout principal ----------
        main_layout.addWidget(toolbox, 0)
        main_layout.addWidget(workspace_container, 1)

    def on_delete_clicked(self):
        """Conecta el botón 'Eliminar seleccionado' con el workspace."""
        self.workspace_view.delete_selected()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()