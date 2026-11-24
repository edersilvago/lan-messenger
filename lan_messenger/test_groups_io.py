"""Teste da v1.40: exportar/importar grupos e seleção para F2.
Roda: python -m lan_messenger.test_groups_io
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from lan_messenger import app_gui, profile


def main() -> None:
    td = Path(tempfile.mkdtemp(prefix="lm_groups_"))
    exp = td / "grupos.json"

    # exporta formato esperado
    app = SimpleNamespace(settings=profile.Settings(
        group_aliases={"TI": "Tecnologia"},
        hidden_groups=["RH"],
        custom_groups=["Projetos"],
        peer_groups={"u1": "TI"},
        group_order=["TI", "RH"],
    ))
    app.root = None
    old_save = app_gui.filedialog.asksaveasfilename
    old_info = app_gui.messagebox.showinfo
    old_err = app_gui.messagebox.showerror
    try:
        app_gui.filedialog.asksaveasfilename = lambda **k: str(exp)
        app_gui.messagebox.showinfo = lambda *a, **k: None
        app_gui.messagebox.showerror = lambda *a, **k: (_ for _ in ()).throw(AssertionError(a))
        app_gui.App.export_groups(app, None)
    finally:
        app_gui.filedialog.asksaveasfilename = old_save
        app_gui.messagebox.showinfo = old_info
        app_gui.messagebox.showerror = old_err
    data = json.loads(exp.read_text(encoding="utf-8"))
    assert data["kind"] == "lan-messenger-groups"
    assert data["group_aliases"] == {"TI": "Tecnologia"}
    assert data["hidden_groups"] == ["RH"]
    assert data["custom_groups"] == ["Projetos"]
    assert data["peer_groups"] == {"u1": "TI"}
    assert data["group_order"] == ["TI", "RH"]
    print("OK exporta grupos")

    # importa e substitui organização
    app2 = SimpleNamespace(settings=profile.Settings(), profile=profile.Profile())
    app2.root = None
    app2.refresh = lambda: setattr(app2, "refreshed", True)
    old_open = app_gui.filedialog.askopenfilename
    old_ask = app_gui.messagebox.askyesno
    try:
        app_gui.filedialog.askopenfilename = lambda **k: str(exp)
        app_gui.messagebox.askyesno = lambda *a, **k: True
        app_gui.messagebox.showinfo = lambda *a, **k: None
        app_gui.messagebox.showerror = lambda *a, **k: (_ for _ in ()).throw(AssertionError(a))
        old_psave = profile.save
        profile.save = lambda *a, **k: setattr(app2, "saved", True)
        try:
            ok = app_gui.App.import_groups(app2, None)
        finally:
            profile.save = old_psave
    finally:
        app_gui.filedialog.askopenfilename = old_open
        app_gui.messagebox.askyesno = old_ask
        app_gui.messagebox.showinfo = old_info
        app_gui.messagebox.showerror = old_err
    assert ok is True
    assert app2.settings.group_aliases == {"TI": "Tecnologia"}
    assert app2.settings.hidden_groups == ["RH"]
    assert app2.settings.custom_groups == ["Projetos"]
    assert app2.settings.peer_groups == {"u1": "TI"}
    assert app2.settings.group_order == ["TI", "RH"]
    assert app2.refreshed is True and app2.saved is True
    print("OK importa grupos")

    # rejeita arquivo inválido
    bad = td / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    app3 = SimpleNamespace(settings=profile.Settings(), profile=profile.Profile(), root=None)
    called = {"err": 0}
    try:
        app_gui.filedialog.askopenfilename = lambda **k: str(bad)
        app_gui.messagebox.showerror = lambda *a, **k: called.__setitem__("err", called["err"] + 1)
        ok = app_gui.App.import_groups(app3, None)
    finally:
        app_gui.filedialog.askopenfilename = old_open
        app_gui.messagebox.showerror = old_err
    assert ok is False and called["err"] == 1
    print("OK rejeita arquivo inválido")

    # toggle_group seleciona grupo para F2
    tg = SimpleNamespace(_selected_group="", _selected_ip="x",
                         _collapsed_groups=set(), _roster_sig=("x",))
    tg.refresh = lambda: None
    app_gui.App._toggle_group(tg, "TI")
    assert tg._selected_group == "TI"
    assert tg._selected_ip == ""
    print("OK clique no grupo seleciona para F2")

    print("TESTE GROUPS IO: PASSOU")


if __name__ == "__main__":
    main()
