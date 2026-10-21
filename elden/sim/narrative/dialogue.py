"""Diálogos ramificados com condições e efeitos (data/dialogues/*.json)."""
from ...core.data import DB


class DialogueRunner:
    def __init__(self, session, dlg_id, npc_id=None):
        self.session = session
        self.dlg_id = dlg_id
        self.npc_id = npc_id
        self.d = DB.dialogues[dlg_id]
        self.speaker = self.d.get("speaker", DB.npcs.get(npc_id, {}).get("name", ""))
        self.node_id = self.d.get("start", "start")
        self.done = False
        self.outputs = []
        self._enter(self.node_id)

    def _fmt(self, text):
        c = self.session.char
        return text.replace("{nome}", c.name).replace("{classe}", DB.classes[c.class_id]["name"])

    def _enter(self, nid):
        while nid is not None:
            node = self.d["nodes"].get(nid)
            if node is None:
                self.done = True
                return
            if node.get("if") and not self.session.check(node["if"]):
                nid = node.get("else")
                continue
            self.node_id = nid
            self.node = node
            self.outputs.extend(self.session.apply_effects(node.get("do")))
            return
        self.done = True

    @property
    def text(self):
        return self._fmt(self.node.get("text", ""))

    @property
    def who(self):
        return self.node.get("speaker", self.speaker)

    def choices(self):
        return [ (i, self._fmt(c["text"])) for i, c in enumerate(self.node.get("choices", []))
                 if self.session.check(c.get("if")) ]

    def advance(self, choice=None):
        """Avança; se houver escolhas, 'choice' é o índice original da escolha."""
        node = self.node
        if node.get("choices"):
            if choice is None:
                return
            c = node["choices"][choice]
            self.outputs.extend(self.session.apply_effects(c.get("do")))
            nxt = c.get("next")
        else:
            nxt = node.get("next")
        if nxt is None:
            self.done = True
            return
        self._enter(nxt)

    def take_outputs(self):
        out, self.outputs = self.outputs, []
        return out
