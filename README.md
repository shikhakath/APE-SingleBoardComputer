# APE-SingleBoardComputer

A Linux single-board computer built around the Octavo **OSD6254** System-in-Package (TI AM6254 + 1 GB DDR4), designed in Altium Designer.

**Start here:** [DESIGN_PROPOSAL.md](DESIGN_PROPOSAL.md)

## Repository layout

| Path | Contents |
|---|---|
| `DESIGN_PROPOSAL.md` | Architecture proposal, open decisions and design plan |
| `docs/research/` | Page-referenced notes on the OSD62x-PM SiP, the TI SK-AM62B reference design, and AM625/TPS65219 design constraints |
| `datasheets/` | AM625 datasheet, AM62x TRM, TPS65219 datasheet, OSD62x-PM overview |
| `reference/` | TI SK-AM62B-P1 design packages (PROC142B and PROC142A): schematics, BOM, board files, Gerbers, stackup, power sequence |
| `hardware/` | Altium project (not created yet) |

Files over GitHub's 100 MB limit (`*.brd`, `*.alg`, `*.STEP`, the TRM PDF) are stored with **Git LFS**. Run `git lfs install` before cloning.

## Altium MCP server

`.mcp.json` registers the [altium-mcp](https://github.com/coffeenmusic/altium-mcp) server for Claude Code. It expects:

- the server cloned to `%USERPROFILE%\mcp-servers\altium-mcp`;
- Python 3.10 or newer on `PATH`;
- Altium Designer installed under `C:\Program Files\Altium\AD*`.

On first start the server builds its virtual environment in `%USERPROFILE%\.altium-mcp\venvs\`. If it fails with a pydantic `ImportError`, install the repo's pinned dependencies into that environment:

```bash
"$USERPROFILE/.altium-mcp/venvs/<id>/Scripts/python.exe" -m pip install -r "$USERPROFILE/mcp-servers/altium-mcp/requirements.txt"
```
