#!/bin/bash
# Script para rodar o Hunt-Analyzer usando o ambiente virtual correto (venv312)
# Isso evita erros caso o Python do sistema/Homebrew seja atualizado.

# Garante que o script rode a partir do diretório onde ele está salvo
cd "$(dirname "$0")"

# Executa o app usando o Python do venv
./venv312/bin/python3 main.py

