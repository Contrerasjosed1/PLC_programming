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
    - index: columna dentro de la fila (0..max_cols-1)
    - position: posición global secuencial (1,2,3,...)
    """
    id: int
    block_type: str
    row: int
    index: int
    position: int


class LadderSession:
    """
    Maneja el "programa" lógico en forma de GRILLA:
    - grid[row][col] = None -> celda vacía
    - grid[row][col] = id   -> bloque ocupando ese slot

    Permite:
    - Agregar bloques (en el primer slot libre o en un slot dado).
    - Mover bloques a una celda (con lógica de desplazamiento izquierda/derecha).
    - Borrar bloques.
    """

    def __init__(self, max_rows: int, max_cols: int):
        self.max_rows = max_rows
        self.max_cols = max_cols

        # grid[row][col] = id de bloque o None
        self.grid: List[List[Optional[int]]] = [
            [None for _ in range(max_cols)] for _ in range(max_rows)
        ]

        # Mapa id -> tipo de bloque (XIC, XIO, etc.)
        self.block_types: Dict[int, str] = {}

        # Contador incremental para IDs
        self._next_id: int = 1

    # ------------------- Helpers internos -------------------

    def _new_id(self) -> int:
        bid = self._next_id
        self._next_id += 1
        return bid

    def _find_block(self, block_id: int) -> Optional[Tuple[int, int]]:
        """Devuelve (row, col) donde está el bloque, o None si no existe."""
        for r in range(self.max_rows):
            for c in range(self.max_cols):
                if self.grid[r][c] == block_id:
                    return r, c
        return None

    def _global_position(self, row: int, index: int) -> int:
        """
        Posición global secuencial (1-based).
        Si hay 6 columnas:
        - fila 0, col 0..5 -> pos 1..6
        - fila 1, col 0..5 -> pos 7..12
        etc.
        """
        return row * self.max_cols + index + 1

    # ------------------- API pública -------------------
    # ALTAS
    # ------------------------------------------

    def add_block_first_free(self, row: int, block_type: str) -> Optional[BlockState]:
        """
        Agrega un bloque en el PRIMER slot libre de la fila 'row'.
        Devuelve el estado del bloque o None si la fila está llena / row inválida.
        """
        if not (0 <= row < self.max_rows):
            return None

        # Buscar primera celda vacía (None)
        free_col = None
        for c in range(self.max_cols):
            if self.grid[row][c] is None:
                free_col = c
                break

        if free_col is None:
            # fila llena
            return None

        block_id = self._new_id()
        self.block_types[block_id] = block_type
        self.grid[row][free_col] = block_id

        pos = self._global_position(row, free_col)
        return BlockState(
            id=block_id,
            block_type=block_type,
            row=row,
            index=free_col,
            position=pos,
        )

    def add_block_at(
        self, row: int, col: int, block_type: str, direction: int = 0
    ) -> Optional[BlockState]:
        """
        Agrega un bloque en una fila y columna específicas.

        - Si la celda está libre -> lo coloca ahí.
        - Si está ocupada -> desplaza en la fila usando 'direction':
            direction > 0 -> desplaza hacia la DERECHA (intenta abrir hueco)
            direction < 0 -> desplaza hacia la IZQUIERDA
            direction = 0 -> modo AUTO: intenta derecha y luego izquierda.

        Devuelve el estado resultante o None si no se pudo insertar (no hay espacio).
        """
        if not (0 <= row < self.max_rows):
            return None
        if col < 0 or col >= self.max_cols:
            return None

        block_id = self._new_id()
        self.block_types[block_id] = block_type

        # Si la celda está vacía, fácil
        if self.grid[row][col] is None:
            self.grid[row][col] = block_id
            pos = self._global_position(row, col)
            return BlockState(block_id, block_type, row, col, pos)

        # La celda está ocupada -> desplazamiento
        placed = self._insert_with_shift(row, col, block_id, direction)
        if not placed:
            # no se pudo insertar, revertimos el registro del tipo
            self.block_types.pop(block_id, None)
            return None

        final_col = placed
        pos = self._global_position(row, final_col)
        return BlockState(block_id, block_type, row, final_col, pos)

    # ------------------------------------------
    # MOVIMIENTOS
    # ------------------------------------------

    def _insert_with_shift(
        self, row: int, col: int, block_id: int, direction: int
    ) -> Optional[int]:
        """
        Inserta block_id en grid[row][col], desplazando otros bloques si hace falta.
        direction:
            > 0 -> desplazar hacia la derecha
            < 0 -> desplazar hacia la izquierda
            = 0 -> modo AUTO (primero intenta derecha, luego izquierda)

        Devuelve la columna final donde quedó block_id o None si fue imposible.
        """

        def shift_right(start_col: int) -> Optional[int]:
            """
            Intenta abrir espacio en 'start_col' desplazando hacia la derecha
            dentro de la fila. Devuelve la col final donde se insertó el bloque
            o None si no hay espacio.
            """
            # Buscar un hueco libre hacia la derecha
            free = None
            for c in range(self.max_cols - 1, start_col - 1, -1):
                if self.grid[row][c] is None:
                    free = c
                    break
            if free is None:
                return None

            # Desplazar todo a la derecha entre start_col..free-1
            # (de derecha a izquierda para no pisar)
            for c in range(free, start_col, -1):
                self.grid[row][c] = self.grid[row][c - 1]

            # Insertar en start_col
            self.grid[row][start_col] = block_id
            return start_col

        def shift_left(start_col: int) -> Optional[int]:
            """
            Intenta abrir espacio en 'start_col' desplazando hacia la izquierda.
            Devuelve la col donde se inserta el bloque o None si no hay espacio.
            """
            free = None
            for c in range(0, start_col + 1):
                if self.grid[row][c] is None:
                    free = c
                    break
            if free is None:
                return None

            # Desplazar todo a la izquierda entre free+1..start_col
            for c in range(free, start_col):
                self.grid[row][c] = self.grid[row][c + 1]

            self.grid[row][start_col] = block_id
            return start_col

        if direction > 0:  # derecha
            return shift_right(col)
        elif direction < 0:  # izquierda
            return shift_left(col)
        else:
            # Modo AUTO: primero intenta derecha, si no se puede intenta izquierda
            placed = shift_right(col)
            if placed is not None:
                return placed
            return shift_left(col)

    def move_block(
        self,
        block_id: int,
        new_row: int,
        target_col: int,
        direction: int = 0,
    ) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Mueve un bloque a la celda (new_row, target_col).
        - Si la celda está libre: solo se cambia de posición.
        - Si está ocupada: se aplica desplazamiento en la fila (como insert).

        direction:
            > 0 -> intentar abrir hueco hacia la derecha
            < 0 -> hacia la izquierda
            = 0 -> AUTO: intenta derecha, luego izquierda.

        Devuelve ((old_row, old_col), (new_row, new_col)) o None si el movimiento
        no se pudo realizar (por falta de espacio).
        """
        found = self._find_block(block_id)
        if found is None:
            return None
        old_row, old_col = found

        if not (0 <= new_row < self.max_rows):
            new_row = old_row

        if target_col < 0:
            target_col = 0
        if target_col >= self.max_cols:
            target_col = self.max_cols - 1

        # Si se queda en la misma celda, nada que hacer
        if old_row == new_row and old_col == target_col:
            return ( (old_row, old_col), (new_row, target_col) )

        # Quitamos el bloque de su posición actual
        self.grid[old_row][old_col] = None

        # Caso 1: celda destino libre -> se pone ahí
        if self.grid[new_row][target_col] is None:
            self.grid[new_row][target_col] = block_id
            return ( (old_row, old_col), (new_row, target_col) )

        # Caso 2: hay algo en ese slot -> insert con desplazamiento
        placed_col = self._insert_with_shift(new_row, target_col, block_id, direction)
        if placed_col is None:
            # No se pudo insertar -> devolvemos el bloque a su lugar original
            self.grid[old_row][old_col] = block_id
            return None

        return ( (old_row, old_col), (new_row, placed_col) )

    # ------------------------------------------
    # BAJAS
    # ------------------------------------------

    def delete_block(self, block_id: int) -> Optional[Tuple[int, int]]:
        """
        Elimina un bloque de la sesión.
        Devuelve (row, col) donde estaba o None si no se encontró.
        """
        found = self._find_block(block_id)
        if found is None:
            return None

        row, col = found
        self.grid[row][col] = None
        self.block_types.pop(block_id, None)
        return row, col

    # ------------------------------------------
    # CONSULTAS
    # ------------------------------------------

    def get_block_state(self, block_id: int) -> Optional[BlockState]:
        """Devuelve el estado actual de un bloque."""
        found = self._find_block(block_id)
        if found is None:
            return None

        row, col = found
        btype = self.block_types.get(block_id, "UNKNOWN")
        pos = self._global_position(row, col)
        return BlockState(block_id, btype, row, col, pos)

    def get_snapshot(self) -> List[BlockState]:
        """
        Devuelve una lista con el estado de TODOS los bloques.
        Útil para exportar el "programa".
        """
        snapshot: List[BlockState] = []
        for r in range(self.max_rows):
            for c in range(self.max_cols):
                bid = self.grid[r][c]
                if bid is None:
                    continue
                btype = self.block_types.get(bid, "UNKNOWN")
                pos = self._global_position(r, c)
                snapshot.append(
                    BlockState(
                        id=bid,
                        block_type=btype,
                        row=r,
                        index=c,
                        position=pos,
                    )
                )
        return snapshot