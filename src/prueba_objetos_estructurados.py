import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QGraphicsView, QGraphicsScene
)
from PyQt5.QtCore import Qt, QMimeData, QPointF, QByteArray
from PyQt5.QtGui import (
    QDrag, QBrush, QPen, QFont, QColor,
    QPainter, QPolygonF
)


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
    Vista del espacio de trabajo estructurada en renglones.
    - 4 filas.
    - Los bloques se agregan de izquierda a derecha.
    - No hay superposición: cada slot es una posición en la fila.
    - Al mover un bloque se reordenan las posiciones (tipo lista).
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        scene = QGraphicsScene(self)
        self.setScene(scene)

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setAcceptDrops(True)
        self.setBackgroundBrush(QColor("#1e1e1e"))

        # Parámetros de la grilla
        self.num_rows = 4
        self.base_y = 80        # centro del primer renglón
        self.row_height = 80    # distancia entre renglones

        self.base_x = 80        # centro de la primera columna
        self.col_width = 140    # distancia entre columnas

        # Estructura lógica: lista de filas, cada fila es lista de items (bloques)
        self.rows = [[] for _ in range(self.num_rows)]

    # ------------------------------------------------------------------
    # Utilidades de grilla
    # ------------------------------------------------------------------
    def row_from_y(self, y: float) -> int:
        """Determina el índice de fila (0..3) a partir de una coordenada Y."""
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
        # boundingRect está en coordenadas locales del item
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
        index = len(self.rows[row])  # se agrega al final de la fila

        self.create_block(row, index, block_type)
        event.acceptProposedAction()

    # ------------------------------------------------------------------
    # Crear bloques según tipo
    # ------------------------------------------------------------------
    def create_block(self, row: int, index: int, block_type: str):
        """
        Crea un bloque en (row, index) según el tipo:
        - "RECT": rectángulo
        - "TRI":  triángulo
        - "CIRC": círculo
        """
        if block_type == "RECT":
            item = self.create_rectangle_block()
            label_text = "Rectángulo"
        elif block_type == "TRI":
            item = self.create_triangle_block()
            label_text = "Triángulo"
        elif block_type == "CIRC":
            item = self.create_circle_block()
            label_text = "Círculo"
        else:
            item = self.create_rectangle_block()
            label_text = "Bloque"

        # Marcar el item como "bloque" y guardar su posición lógica
        item.setData(0, "BLOCK")
        item.setData(1, row)
        item.setData(2, index)

        # Etiqueta de texto (hija del item para moverse con él)
        scene = self.scene()
        text_item = scene.addText(label_text, QFont("Segoe UI", 9, QFont.Bold))
        text_item.setDefaultTextColor(QColor("#ffffff"))
        text_item.setParentItem(item)

        # Centrar texto en el boundingRect del item
        br = item.boundingRect()
        tr = text_item.boundingRect()
        text_item.setPos(
            br.center().x() - tr.width() / 2,
            br.center().y() - tr.height() / 2
        )

        # Insertar en la estructura de filas
        self.rows[row].insert(index, item)

        # Reacomodar la fila completa
        self.layout_row(row)

    def create_rectangle_block(self):
        scene = self.scene()
        width = 120
        height = 50
        # Creamos el rectángulo en coordenadas locales (0,0,width,height)
        rect_item = scene.addRect(
            0, 0, width, height,
            QPen(QColor("#ffffff")),
            QBrush(QColor("#2d2d30"))
        )
        rect_item.setFlag(rect_item.ItemIsMovable, True)
        rect_item.setFlag(rect_item.ItemIsSelectable, True)
        return rect_item

    def create_triangle_block(self):
        scene = self.scene()
        size = 60
        # Triángulo en coordenadas locales, centrado alrededor de (0,0)
        p_top = QPointF(0, -size / 2)
        p_left = QPointF(-size / 2, size / 2)
        p_right = QPointF(size / 2, size / 2)
        polygon = QPolygonF([p_top, p_left, p_right])

        tri_item = scene.addPolygon(
            polygon,
            QPen(QColor("#ffffff")),
            QBrush(QColor("#2d2d30"))
        )
        tri_item.setFlag(tri_item.ItemIsMovable, True)
        tri_item.setFlag(tri_item.ItemIsSelectable, True)
        return tri_item

    def create_circle_block(self):
        scene = self.scene()
        radius = 30
        # Círculo en coordenadas locales (0,0, 2r, 2r)
        circ_item = scene.addEllipse(
            0, 0, 2 * radius, 2 * radius,
            QPen(QColor("#ffffff")),
            QBrush(QColor("#2d2d30"))
        )
        circ_item.setFlag(circ_item.ItemIsMovable, True)
        circ_item.setFlag(circ_item.ItemIsSelectable, True)
        return circ_item

    # ------------------------------------------------------------------
    # Layout de filas y reordenamiento
    # ------------------------------------------------------------------
    def layout_row(self, row: int):
        """Reposiciona todos los bloques de una fila según su índice."""
        items = self.rows[row]
        for i, item in enumerate(items):
            # actualizar índice guardado en el item
            item.setData(1, row)
            item.setData(2, i)
            center = self.grid_center(row, i)
            self.set_block_center(item, center)

    def mouseReleaseEvent(self, event):
        """
        Cuando se suelta el mouse dentro del workspace:
        - Si se soltó sobre un bloque, se calcula la nueva posición (fila, índice)
          y se reordena la lista de esa fila.
        """
        super().mouseReleaseEvent(event)

        # Buscar el item bajo el cursor
        item = self.itemAt(event.pos())
        if item is None:
            return

        # Si el item es texto hijo, subimos al padre
        block = self._get_block_from_item(item)
        if block is None:
            return

        # Centro del bloque en coordenadas de escena
        center_scene = block.mapToScene(block.boundingRect().center())
        new_row = self.row_from_y(center_scene.y())

        # Determinar índice destino aproximando por la X
        # Número de elementos actuales en la fila destino
        row_items = self.rows[new_row]
        if not row_items:
            new_index = 0
        else:
            # índice aproximado desde X
            rel = (center_scene.x() - self.base_x) / self.col_width
            new_index = round(rel)
            new_index = max(0, min(len(row_items), new_index))

        self.move_block_to(block, new_row, new_index)

    def _get_block_from_item(self, item):
        """Si el item es un bloque o un hijo de bloque, devuelve el bloque."""
        it = item
        while it is not None:
            if it.data(0) == "BLOCK":
                return it
            it = it.parentItem()
        return None

    def move_block_to(self, block, new_row: int, new_index: int):
        """Reubica un bloque a (new_row, new_index) reordenando filas."""
        old_row = block.data(1)
        if old_row is None:
            return
        old_row = int(old_row)

        # Sacar el bloque de su fila anterior
        old_list = self.rows[old_row]
        if block in old_list:
            old_list.remove(block)
            # Reacomodar fila anterior
            self.layout_row(old_row)

        # Insertar en la nueva fila
        row_list = self.rows[new_row]
        # clamp del índice
        if new_index < 0:
            new_index = 0
        if new_index > len(row_list):
            new_index = len(row_list)

        row_list.insert(new_index, block)
        self.layout_row(new_row)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PLC Designer - Renglones estructurados")
        self.resize(1000, 600)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)

        # ---------- Panel izquierdo: Toolbox ----------
        toolbox = QWidget()
        toolbox_layout = QVBoxLayout(toolbox)
        toolbox_layout.setContentsMargins(10, 10, 10, 10)
        toolbox_layout.setSpacing(10)

        label = QLabel("Formas disponibles")
        label.setStyleSheet("font-size: 14px; font-weight: bold;")
        toolbox_layout.addWidget(label)

        btn_rect = DraggableButton("Rectángulo", "RECT")
        btn_tri = DraggableButton("Triángulo", "TRI")
        btn_circ = DraggableButton("Círculo", "CIRC")

        for btn in (btn_rect, btn_tri, btn_circ):
            btn.setMinimumHeight(32)
            toolbox_layout.addWidget(btn)

        toolbox_layout.addStretch()

        # ---------- Panel derecho: Workspace ----------
        workspace_container = QWidget()
        workspace_layout = QVBoxLayout(workspace_container)
        workspace_layout.setContentsMargins(10, 10, 10, 10)
        workspace_layout.setSpacing(5)

        workspace_label = QLabel("Espacio de trabajo (4 renglones)")
        workspace_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        workspace_layout.addWidget(workspace_label)

        self.workspace_view = WorkspaceView()
        workspace_layout.addWidget(self.workspace_view)

        # ---------- Layout principal ----------
        main_layout.addWidget(toolbox, 0)
        main_layout.addWidget(workspace_container, 1)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()