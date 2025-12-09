# session.py
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class BlockState:
    """
    Representa el estado lógico de un bloque en la sesión.
    - id: identificador único del bloque
    - block_type: tipo de símbolo (XIC, XIO, OTE, etc.)
    - row: índice de renglón (0..max_rows-1)
    - index: posición dentro de la fila (0..max_cols-1)
    - position: posición global secuencial (1,2,3,...)
    """
    id: int
    block_type: str
    row: int
    index: int
    position: int


class LadderSession:
    """
    Maneja el "programa" lógico:
    - Controla filas y columnas (num_rows x max_cols).
    - Asigna IDs a cada objeto.
    - Mantiene el orden de los bloques por fila.
    - Expone operaciones para agregar, mover y borrar bloques.
    """

    def __init__(self, max_rows: int, max_cols: int):
        self.max_rows = max_rows
        self.max_cols = max_cols

        # rows[row] = lista de IDs de bloque en esa fila, en orden
        self.rows: List[List[int]] = [[] for _ in range(max_rows)]

        # Mapa id -> tipo de bloque (XIC, XIO, etc.)
        self.block_types: Dict[int, str] = {}

        # Contador incremental para IDs
        self._next_id: int = 1

    # ------------------- Helpers internos -------------------

    def _new_id(self) -> int:
        bid = self._next_id
        self._next_id += 1
        return bid

    def _find_row(self, block_id: int) -> Optional[int]:
        """Devuelve la fila donde está el bloque (o None si no existe)."""
        for r, ids in enumerate(self.rows):
            if block_id in ids:
                return r
        return None

    def _global_position(self, row: int, index: int) -> int:
        """
        Posición global secuencial (1-based).
        Si hay 6 columnas:
        - fila 0, index 0..5 -> pos 1..6
        - fila 1, index 0..5 -> pos 7..12
        """
        return row * self.max_cols + index + 1

    # ------------------- API pública -------------------

    def add_block_end_of_row(self, row: int, block_type: str) -> Optional[BlockState]:
        """
        Agrega un bloque al FINAL de la fila 'row'.
        Devuelve el estado del bloque (con id y posiciones) o None si la fila está llena.
        """
        if not (0 <= row < self.max_rows):
            return None

        row_list = self.rows[row]
        if len(row_list) >= self.max_cols:
            # fila llena
            return None

        block_id = self._new_id()
        self.block_types[block_id] = block_type
        row_list.append(block_id)
        index = len(row_list) - 1
        position = self._global_position(row, index)

        return BlockState(
            id=block_id,
            block_type=block_type,
            row=row,
            index=index,
            position=position,
        )

    def move_block(self, block_id: int, new_row: int, new_index: int) -> Optional[Tuple[int, int]]:
        """
        Mueve el bloque a (new_row, new_index) dentro de la sesión.
        Reordena las listas de filas.
        Si el movimiento no es posible (p.e. fila destino llena), devuelve None.
        Si es exitoso, devuelve (old_row, new_row).
        """
        old_row = self._find_row(block_id)
        if old_row is None:
            return None

        if not (0 <= new_row < self.max_rows):
            new_row = old_row  # por seguridad

        # Lista origen/destino
        src_list = self.rows[old_row]
        dst_list = self.rows[new_row]

        # Si vamos a otra fila y la nueva fila está llena, no movemos
        if new_row != old_row and len(dst_list) >= self.max_cols:
            return None

        # Sacar el bloque de la fila origen
        if block_id in src_list:
            src_list.remove(block_id)
        else:
            return None

        # Normalizar índice en la fila destino
        if new_index < 0:
            new_index = 0
        if new_index > len(dst_list):
            new_index = len(dst_list)

        # Insertar en la fila destino
        dst_list.insert(new_index, block_id)

        return (old_row, new_row)

    def delete_block(self, block_id: int) -> Optional[int]:
        """
        Elimina un bloque de la sesión.
        Devuelve la fila en la que estaba (para re-layout gráfico) o None si no se encontró.
        """
        row = self._find_row(block_id)
        if row is None:
            return None

        row_list = self.rows[row]
        if block_id in row_list:
            row_list.remove(block_id)

        self.block_types.pop(block_id, None)
        return row

    def get_block_state(self, block_id: int) -> Optional[BlockState]:
        """
        Devuelve el estado actual (row, index, position global, tipo) de un bloque.
        """
        row = self._find_row(block_id)
        if row is None:
            return None

        row_list = self.rows[row]
        if block_id not in row_list:
            return None

        index = row_list.index(block_id)
        position = self._global_position(row, index)
        btype = self.block_types.get(block_id, "UNKNOWN")

        return BlockState(
            id=block_id,
            block_type=btype,
            row=row,
            index=index,
            position=position,
        )

    def get_snapshot(self) -> List[BlockState]:
        """
        Devuelve una lista con el estado de TODOS los bloques,
        ya lista para exportar el "programa" si quieres (JSON, etc.).
        """
        snapshot: List[BlockState] = []
        for row, ids in enumerate(self.rows):
            for index, bid in enumerate(ids):
                btype = self.block_types.get(bid, "UNKNOWN")
                pos = self._global_position(row, index)
                snapshot.append(
                    BlockState(
                        id=bid,
                        block_type=btype,
                        row=row,
                        index=index,
                        position=pos,
                    )
                )
        return snapshot