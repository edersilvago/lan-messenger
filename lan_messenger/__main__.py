"""Ponto de entrada: python -m lan_messenger (equivale a app_gui).

Import absoluto de propósito: o PyInstaller executa este arquivo como
script top-level, onde import relativo falharia.
"""
from lan_messenger.app_gui import main

if __name__ == "__main__":
    main()
