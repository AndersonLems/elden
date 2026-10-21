"""Barramento de eventos simples (publicar/assinar) e fila de eventos da simulação para a apresentação."""
from collections import defaultdict


class EventBus:
    def __init__(self):
        self._subs = defaultdict(list)

    def on(self, name, fn):
        self._subs[name].append(fn)
        return fn

    def off(self, name, fn):
        if fn in self._subs.get(name, ()):
            self._subs[name].remove(fn)

    def emit(self, name, **data):
        for fn in list(self._subs.get(name, ())):
            fn(**data)


class FxQueue:
    """A simulação empilha eventos visuais/sonoros (faíscas, sons, tremores); a camada de
    renderização consome a cada quadro. Sem janela (testes), a fila é simplesmente descartada."""

    def __init__(self):
        self.items = []

    def push(self, _kind, **data):
        data["kind"] = _kind
        self.items.append(data)

    def drain(self):
        items, self.items = self.items, []
        return items
