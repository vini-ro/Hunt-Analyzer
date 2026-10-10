# Hunt Analyzer

Projeto de estudo em Python voltado à análise de sessões de caça do MMORPG Tibia. O aplicativo persiste estatísticas em SQLite e oferece uma interface gráfica em Tkinter para importar logs, consultar métricas e gerenciar registros.

## Principais funcionalidades
- Importação de logs `.txt`/`.log` gerados na janela de sessão do Tibia.
- Verificação automática de uma pasta de logs predefinida, importando apenas arquivos `Hunting_Session_` ainda não presentes no banco.
- Extração automatizada de duração, XP, loot, supplies, balance, dano, cura e monstros derrotados via expressões regulares.
- Persistência local em banco SQLite (`tibia_hunts.db`), com tabelas normalizadas para personagens, locais, hunts e criaturas, guardado na pasta de dados do sistema.
- Interface gráfica em **Tkinter/ttk**, com abas para Inserção, Análises e gerenciamento de Hunts.
- Filtros de período (hoje, semana, mês, ano) usando utilitários de `datetime` e geração de métricas como XP/h e Balance/h.
- Visualização gráfica das hunts comparando Raw XP/h e Balance/h com apoio do `matplotlib`.
- Operações de batch: importação de múltiplos arquivos, edição em lote e exclusão simultânea de registros.

## Requisitos técnicos
- Python 3.x com módulos padrão `sqlite3` e `tkinter`.
- Dependências em `requirements.txt` (customtkinter, matplotlib, pandas, mplcursors…).

## Execução
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

### Experimente sem logs próprios
```bash
python3 main.py --demo
```
Abre uma cópia temporária de `samples/sample_hunts.db`, com 60 hunts fictícias de dois personagens de demonstração. O banco de exemplo pode ser recriado com `python3 samples/generate_sample_db.py`.

Também é possível abrir um banco específico com `python3 main.py --db caminho/para/arquivo.db`.

## Onde ficam os seus dados
O banco (`tibia_hunts.db`) e a configuração (`config.json`) ficam **fora da pasta do projeto**, na pasta de dados do sistema:

| Sistema | Pasta |
|---|---|
| macOS | `~/Library/Application Support/HuntAnalyzer` |
| Windows | `%APPDATA%\HuntAnalyzer` |
| Linux | `~/.local/share/HuntAnalyzer` |

Assim, atualizar o projeto com `git pull` não afeta as suas hunts, e os seus dados não vão para o GitHub. Para usar outra pasta, defina a variável de ambiente `HUNT_ANALYZER_DATA_DIR`.

**Migração automática:** se você usava uma versão antiga, com o banco na pasta do projeto, o app **copia** `tibia_hunts.db` e `config.json` para a pasta nova na primeira execução. Os arquivos originais não são apagados.

## Empacotando como aplicativo macOS

Para gerar um pacote `.app` utilize o [py2app](https://py2app.readthedocs.io/):

```bash
pip install py2app
python setup.py py2app
```

O resultado será criado em `dist/Hunt-Analizer.app`.

## Empacotando com PyInstaller

Para gerar um executável standalone utilize o [PyInstaller](https://pyinstaller.org/):

```bash
pip install pyinstaller
pyinstaller Hunt-Analizer.spec
```

O binário será criado em `dist/Hunt-Analizer/` já configurado com um ícone temático de Tibia gerado automaticamente.

## Estrutura do banco de dados
- `Characters`: personagens cadastrados e personagem padrão.
- `Locations`: locais de caça.
- `Hunts`: sessões de caça com métricas e saldos.
- `Hunts_Monstros`: criaturas abatidas por hunt (relacionamento 1:N).

## Competências demonstradas
- Modelagem e persistência com SQLite e chaves estrangeiras.
- Criação de GUI com Tkinter/ttk e widgets como `Notebook`, `Treeview` e diálogos.
- Manipulação de arquivos e tratamento de codificações (`utf-8` e `latin-1`).
- Uso extensivo de expressões regulares para parsing de texto.
- Controle de datas e períodos com `datetime`.
- Gerenciamento de recursos com `contextlib.closing` e consultas parametrizadas em SQL.
