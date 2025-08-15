# Hunt Analyzer

Projeto de estudo em Python voltado à análise de sessões de caça do MMORPG Tibia. O aplicativo persiste estatísticas em SQLite e oferece uma interface gráfica em Tkinter para importar logs, consultar métricas e gerenciar registros.

## Principais funcionalidades
- Importação de logs `.txt`/`.log` gerados na janela de sessão do Tibia.
- Extração automatizada de duração, XP, loot, supplies, balance, dano, cura e monstros derrotados via expressões regulares.
- Persistência local em banco SQLite (`tibia_hunts.db`), com tabelas normalizadas para personagens, locais, hunts e criaturas.
- Interface gráfica em **Tkinter/ttk**, com abas para Inserção, Análises e gerenciamento de Hunts.
- Filtros de período (hoje, semana, mês, ano) usando utilitários de `datetime` e geração de métricas como XP/h e Balance/h.
- Visualização gráfica das hunts comparando Raw XP/h e Balance/h com apoio do `matplotlib`.
- Operações de batch: importação de múltiplos arquivos, edição em lote e exclusão simultânea de registros.

## Requisitos técnicos
- Python 3.x com módulos padrão `sqlite3` e `tkinter`.
- `matplotlib` para geração dos gráficos comparativos.

## Execução
```bash
python Hunt-Analizer.py
```
O script cria ou reutiliza automaticamente o banco `tibia_hunts.db` no diretório raiz.

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
