from __future__ import annotations

"""
CLI interativo para o subprojeto embeddinggemma_feasibility.

Ajuda a executar operações de RAG sem precisar lembrar os parâmetros.
Opções:
  1) Build index
  2) Query index
  3) Mostrar configurações
  0) Sair

Requisitos: módulos em embeddinggemma_feasibility.rag.* já instalados.
"""

import json
from pathlib import Path
from typing import Optional

from embeddinggemma_feasibility.rag.config import RAGConfig
from embeddinggemma_feasibility.rag.ingest import load_documents
from embeddinggemma_feasibility.rag.index import build_index, load_index
from embeddinggemma_feasibility.rag.retrieve import query_index
from embeddinggemma_feasibility.rag.rerank import rerank_candidates
import os


SUBPROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_DIR = SUBPROJECT_ROOT / "data" / "sample_documents"


def _ask(prompt: str, default: Optional[str] = None) -> str:
    if default is None:
        return input(f"{prompt}: ").strip()
    val = input(f"{prompt} [{default}]: ").strip()
    return val or str(default)


def _ask_int(prompt: str, default: int) -> int:
    raw = input(f"{prompt} [{default}]: ").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except Exception:
        print("Valor inválido. Mantendo padrão.")
        return default


def _ask_bool(prompt: str, default: bool) -> bool:
    d = "Y/n" if default else "y/N"
    raw = input(f"{prompt} [{d}]: ").strip().lower()
    if not raw:
        return default
    if raw in ("y", "yes", "s", "sim"):
        return True
    if raw in ("n", "no", "nao", "não"):
        return False
    print("Entrada inválida. Mantendo padrão.")
    return default


def action_build() -> None:
    print("\n=== Build do índice (RAG) ===")
    cfg = RAGConfig()

    source_dir = Path(_ask("Diretório de documentos (txt/md/pdf)", str(DEFAULT_SOURCE_DIR)))
    persist_dir = Path(_ask("Diretório de persistência do índice", str(cfg.index_dir)))
    embed_model = _ask("Modelo de embeddings (HuggingFace)", cfg.embed_model)
    max_chars = _ask_int("Tamanho dos chunks (caracteres)", 1200)
    overlap = _ask_int("Overlap entre chunks (caracteres)", 120)

    try:
        print("Carregando documentos...")
        texts, metas = load_documents(source_dir, max_chars=max_chars, overlap=overlap)
        print(f"Encontrados {len(texts)} chunks. Construindo índice...")
        build_index(texts, metas, persist_dir=persist_dir, embed_model_name=embed_model)
        print(f"✅ Índice criado em: {persist_dir}")
    except Exception as e:
        print(f"❌ Erro no build: {e}")

    input("\nPressione Enter para voltar ao menu...")


def action_query() -> None:
    print("\n=== Consulta ao índice (RAG) ===")
    cfg = RAGConfig()

    index_dir = Path(_ask("Diretório do índice", str(cfg.index_dir)))
    q = _ask("Pergunta", "termos de entrega")
    top_k = _ask_int("Top-k (itens para recuperar)", cfg.top_k)
    return_k = _ask_int("Return-k (itens para exibir)", cfg.return_k)
    use_rerank = _ask_bool("Usar reranker (melhor ordenação, pode baixar modelo)", cfg.use_reranker)

    try:
        index = load_index(index_dir)
        results = query_index(index, q, top_k=top_k)
        if use_rerank:
            results = rerank_candidates(q, results, top_k=return_k)
        else:
            results = results[: return_k]
        print("\nResultados:\n" + json.dumps([r.model_dump() for r in results], indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Erro na consulta: {e}")

    input("\nPressione Enter para voltar ao menu...")


def action_show_config() -> None:
    print("\n=== Configurações atuais (RAGConfig) ===")
    cfg = RAGConfig()
    data = {
        "index_dir": str(cfg.index_dir),
        "embed_model": cfg.embed_model,
        "use_reranker": cfg.use_reranker,
        "top_k": cfg.top_k,
        "return_k": cfg.return_k,
        "default_source_dir": str(DEFAULT_SOURCE_DIR),
    }
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("\nDicas:")
    print("- Use 'Build index' após adicionar/alterar documentos.")
    print("- Use 'Query index' para perguntas rápidas sobre o conteúdo indexado.")
    print("- Desative o reranker em ambientes totalmente offline.")

    input("\nPressione Enter para voltar ao menu...")


def action_run_advanced_extractor() -> None:
    """Run the advanced Coupa field extractor end-to-end from the menu."""
    print("\n=== Extrator Avançado (PDF → CSV) ===")

    try:
        from .advanced_coupa_field_extractor import AdvancedCoupaPDFFieldExtractor
    except Exception as e:
        print("❌ Não foi possível importar o extrator avançado.")
        print("   Verifique dependências: pdfplumber, PyMuPDF, sentence-transformers/transformers, etc.")
        print(f"   Detalhes: {e}")
        input("\nPressione Enter para voltar ao menu...")
        return

    pdf_dir = Path(_ask("Diretório com PDFs", str(DEFAULT_SOURCE_DIR)))
    if not pdf_dir.exists() or not pdf_dir.is_dir():
        print(f"❌ Diretório inválido: {pdf_dir}")
        input("\nPressione Enter para voltar ao menu...")
        return

    use_rag = _ask_bool("Usar RAG para recuperar trechos?", False)
    use_valid = _ask_bool("Ativar validações extras?", False)

    try:
        extractor = AdvancedCoupaPDFFieldExtractor(str(pdf_dir), use_rag=use_rag, use_validations=use_valid)
        extractions = extractor.process_all_pdfs()
        if not extractions:
            print("⚠️ Nenhum documento processado com sucesso.")
            input("\nPressione Enter para voltar ao menu...")
            return

        csv_path = extractor.save_to_csv(extractions)
        # Also create a simple markdown report alongside CSV
        try:
            report_md = extractor.generate_extraction_report(extractions)
            report_file = Path(csv_path).with_suffix('').as_posix() + "_report.md"
            Path(report_file).write_text(report_md, encoding='utf-8')
            print(f"📋 Relatório salvo em: {report_file}")
        except Exception as e:
            print(f"⚠️ Não foi possível gerar relatório: {e}")

        print(f"✅ CSV salvo em: {csv_path}")
    except Exception as e:
        print(f"❌ Erro no processamento: {e}")

    input("\nPressione Enter para voltar ao menu...")


def action_review_tools() -> None:
    print("\n=== Ferramentas de Feedback (HITL) ===")
    print("1) Preparar CSV de revisão (triplets *_pred/_gold/_status)")
    print("2) Ingerir CSV revisado (gerar datasets e análise)")
    print("3) Avaliar métricas (pred vs gold)")
    print("4) Treinar ST (pares)")
    print("5) Exportar tarefas para Label Studio")
    print("0) Voltar")
    choice = input("> ").strip()

    if choice == "1":
        pred_glob = _ask("Arquivo(s) CSV do pipeline (glob)", str(SUBPROJECT_ROOT / "reports" / "advanced_coupa_fields_extraction_*.csv"))
        out_csv = _ask("Arquivo de saída (review.csv)", str(SUBPROJECT_ROOT / "reports" / "feedback" / "review.csv"))
        fields = _ask("Campos (normalizados, separados por vírgula)", "contract_name,contract_type,sow_value_eur,pwo_number,managed_by")
        sample = _ask_int("Amostra (linhas)", 30)
        os.system(f"python tools/legacy/feedback_cli.py prepare --pred-csv '{pred_glob}' --out '{out_csv}' --fields '{fields}' --sample {sample}")
    elif choice == "2":
        review_csv = _ask("CSV revisado (review.csv)", str(SUBPROJECT_ROOT / "reports" / "feedback" / "review.csv"))
        out_dir = _ask("Diretório de saída (datasets)", str(SUBPROJECT_ROOT / "datasets"))
        os.system(f"python tools/legacy/feedback_cli.py ingest --review-csv '{review_csv}' --out-dir '{out_dir}'")
    elif choice == "3":
        review_csv = _ask("CSV revisado (review.csv)", str(SUBPROJECT_ROOT / "reports" / "feedback" / "review.csv"))
        report_dir = _ask("Diretório de relatórios", str(SUBPROJECT_ROOT / "reports" / "feedback"))
        os.system(f"python tools/legacy/feedback_cli.py eval --review-csv '{review_csv}' --report-dir '{report_dir}'")
    elif choice == "4":
        dataset = _ask("Dataset de pares (st_pairs.jsonl)", str(SUBPROJECT_ROOT / "datasets" / "st_pairs.jsonl"))
        output = _ask("Saída do modelo ST", str(SUBPROJECT_ROOT / "models" / "st_custom_v1"))
        epochs = _ask_int("Épocas", 2)
        bs = _ask_int("Batch size", 16)
        os.system(f"python tools/legacy/feedback_cli.py train-st --dataset '{dataset}' --output '{output}' --epochs {epochs} --batch-size {bs}")
    elif choice == "5":
        review_csv = _ask("CSV revisado (review.csv)", str(SUBPROJECT_ROOT / "reports" / "feedback" / "review.csv"))
        out_json = _ask("Saída (tasks.json)", str(SUBPROJECT_ROOT / "reports" / "feedback" / "tasks.json"))
        os.system(f"python tools/legacy/feedback_cli.py export-labelstudio --review-csv '{review_csv}' --out '{out_json}'")
    input("\nPressione Enter para voltar ao menu...")


def main() -> None:
    while True:
        print("\n=== Menu RAG — embeddinggemma_feasibility ===")
        print("1) Build index")
        print("2) Query index")
        print("3) Mostrar configurações")
        print("4) Executar Extrator Avançado (PDF → CSV)")
        print("5) Ferramentas de Revisão (HITL)")
        print("6) Model Manager (listar/selecionar/comparar)")
        print("0) Sair")
        choice = input("> ").strip()

        if choice == "1":
            action_build()
        elif choice == "2":
            action_query()
        elif choice == "3":
            action_show_config()
        elif choice == "4":
            try:
                action_run_advanced_extractor()
            except Exception as e:
                print(f"❌ Erro ao executar extrator avançado: {e}")
        elif choice == "5":
            action_review_tools()
        elif choice == "6":
            action_model_manager()
        elif choice == "0":
            print("Até logo!")
            break
        else:
            print("Opção inválida. Tente novamente.")


if __name__ == "__main__":
    main()

def action_model_manager() -> None:
    print("\n=== Model Manager ===")
    print("1) Listar modelos")
    print("2) Selecionar modelo ativo")
    print("3) Mostrar modelo ativo")
    print("4) A/B compare (lado a lado, via CSVs)")
    print("0) Voltar")
    choice = input("> ").strip()
    if choice == "1":
        os.system("python tools/model_select.py list")
    elif choice == "2":
        path = _ask("Caminho do modelo (dir)")
        os.system(f"python tools/model_select.py set-active --path '{path}'")
    elif choice == "3":
        os.system("python tools/model_select.py show-active")
    elif choice == "4":
        pred_a = _ask("CSV predições - run A", str(SUBPROJECT_ROOT / "reports" / "runA.csv"))
        pred_b = _ask("CSV predições - run B", str(SUBPROJECT_ROOT / "reports" / "runB.csv"))
        sample = _ask_int("Amostra (linhas)", 10)
        out = _ask("Saída preferences.jsonl", str(SUBPROJECT_ROOT / "datasets" / "preferences.jsonl"))
        os.system(f"python tools/ab_compare_cli.py --pred-a '{pred_a}' --pred-b '{pred_b}' --sample {sample} --out '{out}'")
    input("\nPressione Enter para voltar ao menu...")
