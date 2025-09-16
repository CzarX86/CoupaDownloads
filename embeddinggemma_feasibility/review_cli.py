from __future__ import annotations

"""
Human-in-the-loop (HITL) CLI utilities for review → retrain → evaluate.

Commands:
  - generate: create a small review bundle from extraction CSVs
  - ingest:   store a corrected CSV into a curated training folder
  - train:    run a simple ST fine-tuning using curated data (optional)
  - eval:     compare predictions vs ground-truth with NA-aware metrics
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import random


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _write_csv(path: Path, rows: List[Dict[str, Any]]):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def cmd_generate(args: argparse.Namespace) -> int:
    src = Path(args.source)
    size = int(args.size)
    # Accept single CSV or a dir with CSVs
    csv_files: List[Path] = []
    if src.is_file():
        csv_files = [src]
    elif src.is_dir():
        csv_files = sorted(src.glob("*.csv"))
    else:
        print(f"Invalid source: {src}")
        return 2

    rows: List[Dict[str, Any]] = []
    for f in csv_files:
        rows.extend(_read_csv(f))

    # Group by PWO# if present
    key = "PWO#"
    by_key: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        k = (r.get(key) or "").strip()
        if k:
            by_key.setdefault(k, []).append(r)

    # Sample POs
    keys = list(by_key.keys())
    random.shuffle(keys)
    keys = keys[:size]
    bundle: List[Dict[str, Any]] = []
    for k in keys:
        # Take first row per PWO for review bundle
        bundle.append(by_key[k][0])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path(args.output or f"reports/review_bundle_{ts}.csv")
    _write_csv(out, bundle)
    print(f"✅ Review bundle salvo em: {out}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    corrected = Path(args.corrected)
    if not corrected.exists():
        print(f"Arquivo não encontrado: {corrected}")
        return 2
    rows = _read_csv(corrected)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = Path(args.dest or f"training_data/curated/reviewed_{ts}.csv")
    _write_csv(dest, rows)
    print(f"✅ Correções ingeridas em: {dest}")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    gt = _read_csv(Path(args.groundtruth))
    pred = _read_csv(Path(args.predictions))

    # Index by PWO#
    def index(rows):
        by = {}
        for r in rows:
            k = (r.get("PWO#") or "").strip()
            if k:
                by[k] = r
        return by

    gt_i = index(gt)
    pd_i = index(pred)
    common = sorted(set(gt_i.keys()) & set(pd_i.keys()))
    if not common:
        print("Sem chaves comuns (PWO#).")
        return 0

    fields = [
        "Contract Name","Contract Type","Contract Start Date","Contract End Date",
        "SOW Value in EUR","SOW Value in LC","FX","Managed By","Platform/Technology","PWO#"
    ]
    totals = {f: {"tp": 0, "fn": 0} for f in fields}
    for k in common:
        g = gt_i[k]
        p = pd_i[k]
        for f in fields:
            gval = (g.get(f) or "").strip()
            pval = (p.get(f) or "").strip()
            if not gval:
                # NA in ground-truth: ignore
                continue
            if gval.lower() == pval.lower():
                totals[f]["tp"] += 1
            else:
                totals[f]["fn"] += 1

    print("\n📊 Avaliação (acurácia por campo; NA ignorado no GT):")
    for f, t in totals.items():
        denom = t["tp"] + t["fn"]
        if denom == 0:
            acc = "NA"
        else:
            acc = f"{(t['tp']/denom)*100:.1f}%"
        print(f" - {f}: {acc} (n={denom})")
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    # Minimal hook to existing customizer; expects a CSV similar to XLSX export
    try:
        from .sentence_transformer_customizer import ContractSentenceTransformerCustomizer as CSTC
    except Exception as e:
        print(f"Falha ao importar customizador: {e}")
        return 2
    csv_path = Path(args.csv)
    out_dir = Path(args.output or "embeddinggemma_feasibility/models/st_custom_v1")
    c = CSTC(str(csv_path))
    if not (c.load_data() and c.initialize_model()):
        print("Falha ao inicializar dados/modelo")
        return 2
    c.create_contract_embeddings()
    training_examples = c.create_training_data()
    if training_examples:
        c.fine_tune_model(training_examples, str(out_dir))
    c.save_custom_model(str(out_dir))
    print(f"✅ Modelo ST salvo em: {out_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="review-cli", description="Ferramentas de revisão HITL")
    sp = p.add_subparsers(dest="cmd")

    g = sp.add_parser("generate", help="Gerar pacote de revisão")
    g.add_argument("--source", required=True, help="Arquivo CSV ou diretório com CSVs")
    g.add_argument("--size", default=20, help="Tamanho da amostra (POs)")
    g.add_argument("--output", default=None, help="Caminho de saída do bundle")
    g.set_defaults(func=cmd_generate)

    i = sp.add_parser("ingest", help="Ingerir CSV corrigido")
    i.add_argument("--corrected", required=True)
    i.add_argument("--dest", default=None)
    i.set_defaults(func=cmd_ingest)

    t = sp.add_parser("train", help="Treinar modelo ST customizado")
    t.add_argument("--csv", required=True, help="CSV (XLSX convertido) com colunas mapeadas")
    t.add_argument("--output", default=None)
    t.set_defaults(func=cmd_train)

    e = sp.add_parser("eval", help="Avaliar predições vs. ground truth")
    e.add_argument("--groundtruth", required=True)
    e.add_argument("--predictions", required=True)
    e.set_defaults(func=cmd_eval)
    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    if not hasattr(ns, "func"):
        parser.print_help()
        return 1
    return ns.func(ns)


if __name__ == "__main__":
    sys.exit(main())

