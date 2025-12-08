import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QGraphicsView, QGraphicsScene
)
from PyQt5.QtCore import Qt, QMimeData, QPoint, QPointF, QByteArray
from PyQt5.QtGui import QDrag, QBrush, QPen, QFont, QColor, QPainter, QPolygonF


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
        # Guardamos el tipo de bloque como bytes
        mime_data.setData(MIME_BLOCK_TYPE, QByteArray(self.block_type.encode("utf-8")))
        drag.setMimeData(mime_data)

        drag.exec_(Qt.CopyAction)


class WorkspaceView(QGraphicsView):
    """
    Vista del espacio de trabajo. Acepta drops de bloques
    y crea formas (rectángulo, triángulo, círculo).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        scene = QGraphicsScene(self)
        self.setScene(scene)

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setAcceptDrops(True)

        self.setBackgroundBrush(QColor("#1e1e1e"))
        self.setDragMode(QGraphicsView.RubberBandDrag)

    # -------- Drag & Drop desde los botones --------
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

        # Coordenadas del drop en la escena
        pos_in_view = event.pos()
        pos_in_scene = self.mapToScene(pos_in_view)

        self.create_block(pos_in_scene, block_type)
        event.acceptProposedAction()

    # -------- Dispatcher de formas --------
    def create_block(self, pos, block_type: str):
        """
        Según el tipo de bloque, crea la forma correspondiente.
        block_type puede ser: "RECT", "TRI", "CIRC".
        """
        if block_type == "RECT":
            self.create_rectangle_block(pos)
        elif block_type == "TRI":
            self.create_triangle_block(pos)
        elif block_type == "CIRC":
            self.create_circle_block(pos)
        else:
            # Por si en algún momento llega algo inesperado
            self.create_rectangle_block(pos)

    # -------- Formas individuales --------
    def create_rectangle_block(self, pos: QPointF):
        scene = self.scene()
        width = 120
        height = 60
        x = pos.x() - width / 2
        y = pos.y() - height / 2

        rect_item = scene.addRect(
            x, y, width, height,
            QPen(QColor("#ffffff")),
            QBrush(QColor("#2d2d30"))
        )
        rect_item.setFlag(rect_item.ItemIsMovable, True)
        rect_item.setFlag(rect_item.ItemIsSelectable, True)

        # Etiqueta de texto dentro del rectángulo
        text_item = scene.addText("Rectángulo", QFont("Segoe UI", 9, QFont.Bold))
        text_item.setDefaultTextColor(QColor("#ffffff"))
        text_rect = text_item.boundingRect()
        text_item.setPos(
            x + (width - text_rect.width()) / 2,
            y + (height - text_rect.height()) / 2
        )
        text_item.setParentItem(rect_item)

    def create_triangle_block(self, pos: QPointF):
        scene = self.scene()

        # Triángulo isósceles centrado en pos
        size = 60
        p_top = QPointF(pos.x(), pos.y() - size / 2)
        p_left = QPointF(pos.x() - size / 2, pos.y() + size / 2)
        p_right = QPointF(pos.x() + size / 2, pos.y() + size / 2)

        polygon = QPolygonF([p_top, p_left, p_right])

        tri_item = scene.addPolygon(
            polygon,
            QPen(QColor("#ffffff")),
            QBrush(QColor("#2d2d30"))
        )
        tri_item.setFlag(tri_item.ItemIsMovable, True)
        tri_item.setFlag(tri_item.ItemIsSelectable, True)

        # Texto debajo del triángulo
        text_item = scene.addText("Triángulo", QFont("Segoe UI", 9, QFont.Bold))
        text_item.setDefaultTextColor(QColor("#ffffff"))
        text_rect = text_item.boundingRect()
        text_item.setPos(
            pos.x() - text_rect.width() / 2,
            pos.y() + size / 2 + 4  # un poquito por debajo
        )
        text_item.setParentItem(tri_item)

    def create_circle_block(self, pos: QPointF):
        scene = self.scene()
        radius = 35
        x = pos.x() - radius
        y = pos.y() - radius

        circ_item = scene.addEllipse(
            x, y, 2 * radius, 2 * radius,
            QPen(QColor("#ffffff")),
            QBrush(QColor("#2d2d30"))
        )
        circ_item.setFlag(circ_item.ItemIsMovable, True)
        circ_item.setFlag(circ_item.ItemIsSelectable, True)

        # Etiqueta de texto en el centro
        text_item = scene.addText("Círculo", QFont("Segoe UI", 9, QFont.Bold))
        text_item.setDefaultTextColor(QColor("#ffffff"))
        text_rect = text_item.boundingRect()
        text_item.setPos(
            pos.x() - text_rect.width() / 2,
            pos.y() - text_rect.height() / 2
        )
        text_item.setParentItem(circ_item)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PLC Designer - Formas básicas")
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

        # 3 botones -> 3 tipos de figuras
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

        workspace_label = QLabel("Espacio de trabajo")
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