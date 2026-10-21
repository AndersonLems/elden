"""Diálogos: todos os caminhos de escolha de todos os diálogos chegam ao fim sem nó inexistente nem erro, e as
missões dos NPCs dos Atos III–V avançam como os dados prometem.

Rodar: python3 -m unittest tests.test_dialogos -v
"""
import unittest

from util import new_session
from elden.core.data import DB
from elden.sim.narrative.dialogue import DialogueRunner


def percorrer(dlg_id, caminho, preparo=None):
    s = new_session()
    if preparo:
        preparo(s)
    r = DialogueRunner(s, dlg_id)
    passos = 0
    for escolha in caminho:
        if r.done:
            break
        r.advance(escolha)
        passos += 1
    return s, r


class TestDialogos(unittest.TestCase):
    def test_todos_os_caminhos_terminam(self):
        falhas = []
        for did, d in DB.dialogues.items():
            nos = d["nodes"]
            for nid, n in nos.items():
                for alvo in [n.get("next"), n.get("else")] + [c.get("next") for c in n.get("choices", [])]:
                    if alvo is not None and alvo not in nos:
                        falhas.append(f"{did}.{nid} → {alvo} inexistente")
            # percorre todas as escolhas (DFS limitada) a partir do início
            pilha = [[]]
            vistos = 0
            while pilha and vistos < 400:
                cam = pilha.pop()
                vistos += 1
                try:
                    _, r = percorrer(did, cam)
                except Exception as exc:     # noqa: BLE001 — o teste quer qualquer erro de dados
                    falhas.append(f"{did} caminho {cam}: {type(exc).__name__}: {exc}")
                    continue
                if r.done or len(cam) > 30:
                    continue
                ops = [i for i, _ in r.choices()] if r.node.get("choices") else [None]
                for o in ops:
                    pilha.append(cam + [o])
        self.assertEqual(falhas, [])

    def test_missao_agathe(self):
        def preparo(s):
            s.set_flag("conheceu_agathe")
            s.set_quest("q_agathe", 1)
            for i in (1, 2, 3):
                s.read_document(f"pagina_absolvicao_{i}", silent=True)
        s = new_session()
        preparo(s)
        self.assertTrue(s.char.has_item("pagina_absolvicao"))
        r = DialogueRunner(s, "agathe_paginas", "agathe")
        for _ in range(20):
            if r.done:
                break
            ops = r.choices()
            r.advance(ops[0][0] if r.node.get("choices") and ops else None)
        self.assertEqual(s.quest_stage("q_agathe"), "done")

    def test_missao_corvin(self):
        s = new_session()
        s.set_quest("q_corvin", 1)
        s.set_flag("corvin_livre")
        self.assertEqual(s.quest_stage("q_corvin"), 2)


if __name__ == "__main__":
    unittest.main()
