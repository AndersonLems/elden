"""Controladores de puzzle: verificam o estado dos objetos e aplicam a recompensa ao resolver.

Tipos:
  combination  mostradores devem mostrar a combinação certa (símbolos lunares, diagramas...)
  all_on       todos os objetos ativos ao mesmo tempo (alavancas, placas, cristais)
  sequence     botões na ordem certa (erro reinicia)
  beam         todos os receptores iluminados por feixes de luz (espelhos)
  network      rede de nós/tubos: a fonte deve alcançar os destinos sem alcançar os proibidos
               (distribuição de energia, direcionamento de vapor)
  gears        todos os encaixes com engrenagem e na rotação correta
  kill         todos os inimigos do grupo derrotados (salas de emboscada)
"""
from collections import defaultdict, deque


class Puzzle:
    def __init__(self, world, spec):
        self.world = world
        self.spec = spec
        self.id = spec["id"]
        self.type = spec["type"]
        self.solved = False
        self.progress = []
        s = world.session
        if s is not None and s.has_flag(self.flag):
            self.solved = True
            self.apply(silent=True)
        if self.type == "sequence":
            world.bus.on("sequence_input", self._on_seq)

    @property
    def flag(self):
        return f"puzzle:{self.id}"

    def props(self, key="props"):
        out = []
        for pid in self.spec.get(key, []):
            p = self.world.find_prop(pid)
            if p is not None:
                out.append(p)
        return out

    # ------------------------------------------------------------------ verificação
    def check(self):
        t = self.type
        if t == "combination":
            props = self.props()
            sol = self.spec["solution"]
            if len(props) != len(sol):
                return False
            for p, want in zip(props, sol):
                cur = p.symbol if isinstance(want, str) else p.state
                if cur != want:
                    return False
            return True
        if t == "all_on":
            return all(bool(p.state) or getattr(p, "pressed", False) for p in self.props())
        if t == "beam":
            return all(p.state for p in self.props())
        if t == "gears":
            sol = self.spec.get("solution")
            for i, p in enumerate(self.props()):
                if not p.has_gear:
                    return False
                if sol is not None and p.rotation != sol[i]:
                    return False
            return True
        if t == "network":
            return self.network_ok()
        if t == "kill":
            g = self.spec["group"]
            alive = [e for e in self.world.enemies() if getattr(e, "group", None) == g]
            spawned = getattr(self.world, "_groups_spawned", set())
            return g in spawned and not alive
        return False

    def reachable(self):
        """Nós alcançados a partir da fonte na rede, dado o estado das chaves/válvulas."""
        edges = defaultdict(list)
        for e in self.spec["edges"]:
            a, b = e[0], e[1]
            switch = e[2] if len(e) > 2 else None
            need = e[3] if len(e) > 3 else 1
            if switch is not None:
                p = self.world.find_prop(switch)
                if p is None or p.state != need:
                    continue
            edges[a].append(b)
            edges[b].append(a)
        seen = {self.spec["source"]}
        q = deque([self.spec["source"]])
        while q:
            n = q.popleft()
            for m in edges[n]:
                if m not in seen:
                    seen.add(m)
                    q.append(m)
        return seen

    def network_ok(self):
        seen = self.reachable()
        if any(s not in seen for s in self.spec["sinks"]):
            return False
        if any(f in seen for f in self.spec.get("forbidden", [])):
            return False
        return True

    def update(self, dt):
        if self.type == "network":
            seen = self.reachable()
            for node, pid in self.spec.get("indicators", {}).items():
                p = self.world.find_prop(pid)
                if p is not None:
                    p.powered = node in seen
            overload = [f for f in self.spec.get("forbidden", []) if f in seen]
            if overload and not getattr(self, "_warned", False):
                self._warned = True
                self.world.message(self.spec.get("overload_text", "A pressão vaza pelo caminho errado!"), "warn")
            elif not overload:
                self._warned = False
        if not self.solved and self.check():
            self.solve()

    # ------------------------------------------------------------------ sequência
    def _on_seq(self, prop):
        if self.solved or prop.pid not in self.spec.get("props", []):
            return
        self.progress.append(prop.symbol)
        sol = self.spec["solution"]
        n = len(self.progress)
        if self.progress != sol[:n]:
            self.progress = []
            self.world.fx.push("puzzle_fail", x=prop.x, y=prop.y, z=prop.z)
            self.world.message(self.spec.get("fail_text", "A sequência se desfaz. Recomece."), "warn")
            return
        if n == len(sol):
            self.solve()

    # ------------------------------------------------------------------ resolução
    def solve(self):
        self.solved = True
        s = self.world.session
        if s is not None:
            s.set_flag(self.flag)
            s.on_puzzle_solved(self)
        self.world.fx.push("puzzle_solved", puzzle=self.id)
        msg = self.spec.get("message")
        if msg:
            self.world.message(msg, "puzzle")
        self.apply(silent=False)

    def apply(self, silent):
        w = self.world
        for pid in self.spec.get("open", []):
            p = w.find_prop(pid)
            if p is not None and hasattr(p, "set_open"):
                p.set_open(True, silent=silent)
        for pid in self.spec.get("activate", []):
            p = w.find_prop(pid)
            if p is not None:
                p.on_signal("activate", p)
        for pid in self.spec.get("lock", []):
            p = w.find_prop(pid)
            if p is not None:
                p.locked = True
        if not silent and w.session is not None:
            for entry in self.spec.get("reward", []):
                w.session.grant(entry, None)
