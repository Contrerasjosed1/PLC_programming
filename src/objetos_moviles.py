import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QGraphicsView, QGraphicsScene
)
from PyQt5.QtCore import Qt, QMimeData, QPoint, QByteArray
from PyQt5.QtGui import QDrag, QBrush, QPen, QFont, QColor


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
        # Metemos el tipo de bloque como bytes en el mime
        mime_data.setData(MIME_BLOCK_TYPE, QByteArray(self.block_type.encode("utf-8")))
        drag.setMimeData(mime_data)

        # Opcional: setear un pixmap para que se vea algo en el cursor
        # aquí solo usamos el texto del botón
        drag.exec_(Qt.CopyAction)


class WorkspaceView(QGraphicsView):
    """
    Vista del espacio de trabajo. Acepta drops de bloques
    y crea elementos gráficos en la escena.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        scene = QGraphicsScene(self)
        self.setScene(scene)
        # self.setRenderHint(self.renderHints())
        self.setAcceptDrops(True)

        # Estilo básico
        self.setBackgroundBrush(QColor("#1e1e1e"))
        self.setDragMode(QGraphicsView.RubberBandDrag)  # seleccionar varios, etc.

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

        # Coordenadas de drop en el sistema de la escena
        pos_in_view = event.pos()
        pos_in_scene = self.mapToScene(pos_in_view)

        self.create_block(pos_in_scene, block_type)
        event.acceptProposedAction()

    # -------- Crear un bloque en la escena --------
    def create_block(self, pos, block_type: str):
        """
        Crea un bloque rectangular con texto en la posición 'pos'
        dentro de la escena. El bloque es movable y selectable.
        """
        scene = self.scene()

        width = 120
        height = 40
        x = pos.x() - width / 2
        y = pos.y() - height / 2

        # Rectángulo
        rect_item = scene.addRect(
            x, y, width, height,
            QPen(QColor("#ffffff")),
            QBrush(QColor("#2d2d30"))
        )
        rect_item.setFlag(rect_item.ItemIsMovable, True)
        rect_item.setFlag(rect_item.ItemIsSelectable, True)

        # Texto
        text_item = scene.addText(f"Bloque {block_type}", QFont("Segoe UI", 9, QFont.Bold))
        text_item.setDefaultTextColor(QColor("#ffffff"))
        # Centrar el texto en el rectángulo
        text_rect = text_item.boundingRect()
        text_item.setPos(
            x + (width - text_rect.width()) / 2,
            y + (height - text_rect.height()) / 2
        )

        # Hacemos que el texto se mueva junto con el rectángulo usando "parent"
        text_item.setParentItem(rect_item)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PLC Designer - PyQt5 Prototype")
        self.resize(1000, 600)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)

        # ---------- Panel izquierdo: Toolbox ----------
        toolbox = QWidget()
        toolbox_layout = QVBoxLayout(toolbox)
        toolbox_layout.setContentsMargins(10, 10, 10, 10)
        toolbox_layout.setSpacing(10)

        label = QLabel("Elementos PLC")
        label.setStyleSheet("font-size: 14px; font-weight: bold;")
        toolbox_layout.addWidget(label)

        # Botones arrastrables
        btn_a = DraggableButton("Bloque A", "A")
        btn_b = DraggableButton("Bloque B", "B")
        btn_c = DraggableButton("Bloque C", "C")

        for btn in (btn_a, btn_b, btn_c):
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

        # ---------- Añadir a layout principal ----------
        main_layout.addWidget(toolbox, 0)
        main_layout.addWidget(workspace_container, 1)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()