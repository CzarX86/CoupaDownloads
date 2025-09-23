"""
PDF Information Extraction using EmbeddingGemma
Extração de informações de documentos PDF usando EmbeddingGemma
"""

import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

from src.server.pdf_training_app.models import Entity

# PDF processing libraries
from src.server.pdf_training_app.models import Entity

# ...

@dataclass
class ExtractedInformation:
    """Informações extraídas de um documento PDF."""
    document: PDFDocument
    key_phrases: List[str]
    entities: List[Entity]
    summary: str
    categories: List[str]
    relevance_score: float
    embedding: Optional[List[float]] = None


@dataclass
class ExtractionResult:
    """Resultado da extração de informações."""
    success: bool
    documents_processed: int
    total_processing_time: float
    extracted_info: List[ExtractedInformation]
    errors: List[str]
    statistics: Dict[str, Any]


class PDFInformationExtractor:
    """Extrator de informações de PDFs usando EmbeddingGemma."""
    
    def __init__(self, pdf_directory: str = "/Users/juliocezar/Dev/work/CoupaDownloads/src/data/P2"):
        self.config = get_config()
        self.pdf_directory = Path(pdf_directory)
        self.model = None
        self.logger = self._setup_logger()
        
        # Templates para extração de informações específicas
        self.information_templates = {
            "purchase_order": [
                "PO Number", "Purchase Order", "Order Number", "PO#",
                "Vendor", "Supplier", "Company", "Contractor",
                "Amount", "Total", "Cost", "Price", "Value",
                "Date", "Delivery", "Shipment", "Due Date"
            ],
            "invoice": [
                "Invoice Number", "Invoice", "Bill", "Receipt",
                "Amount Due", "Total Amount", "Payment", "Billing",
                "Tax", "VAT", "Discount", "Subtotal"
            ],
            "contract": [
                "Contract", "Agreement", "Terms", "Conditions",
                "Parties", "Effective Date", "Expiration", "Renewal",
                "Obligations", "Responsibilities", "Penalties"
            ],
            "technical_spec": [
                "Specifications", "Technical", "Requirements", "Standards",
                "Materials", "Components", "Dimensions", "Performance",
                "Testing", "Quality", "Compliance"
            ]
        }
        
        # Inicializar modelo se disponível
        self._initialize_model()
    
    def _setup_logger(self) -> logging.Logger:
        """Configurar logger para extração."""
        logger = logging.getLogger("pdf_extractor")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _initialize_model(self):
        """Inicializar modelo EmbeddingGemma."""
        try:
            if ML_LIBRARIES_AVAILABLE:
                self.model = SentenceTransformer(
                    self.config.model_name,
                    cache_folder=self.config.model_cache_dir,
                    device=self.config.device
                )
                self.logger.info("✅ Modelo EmbeddingGemma carregado com sucesso")
            else:
                self.logger.warning("⚠️ Bibliotecas ML não disponíveis - usando extração básica")
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar modelo: {e}")
    
    def find_pdf_files(self) -> List[Path]:
        """Encontrar todos os arquivos PDF na pasta P2 e subpastas."""
        pdf_files = []
        
        if not self.pdf_directory.exists():
            self.logger.warning(f"⚠️ Diretório não encontrado: {self.pdf_directory}")
            return pdf_files
        
        # Buscar PDFs recursivamente
        for pdf_file in self.pdf_directory.rglob("*.pdf"):
            if pdf_file.is_file():
                pdf_files.append(pdf_file)
        
        self.logger.info(f"📄 Encontrados {len(pdf_files)} arquivos PDF")
        return pdf_files
    
    def extract_text_from_pdf(self, pdf_path: Path) -> PDFDocument:
        """Extrair texto de um arquivo PDF."""
        start_time = time.time()
        
        try:
            # Obter informações básicas do arquivo
            file_size = pdf_path.stat().st_size
            filename = pdf_path.name
            
            # Tentar diferentes métodos de extração
            text_content = ""
            page_count = 0
            metadata = {}
            
            # Método 1: pdfplumber (melhor para PDFs com texto)
            if PDF_LIBRARIES_AVAILABLE:
                try:
                    with pdfplumber.open(pdf_path) as pdf:
                        page_count = len(pdf.pages)
                        metadata = pdf.metadata or {}
                        
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_content += page_text + "\n"
                        
                        if text_content.strip():
                            self.logger.info(f"✅ Texto extraído com pdfplumber: {filename}")
                        else:
                            # Método 2: PyPDF2 (fallback)
                            text_content = self._extract_with_pypdf2(pdf_path)
                            if text_content.strip():
                                self.logger.info(f"✅ Texto extraído com PyPDF2: {filename}")
                            else:
                                # Método 3: OCR (para PDFs escaneados)
                                text_content = self._extract_with_ocr(pdf_path)
                                if text_content.strip():
                                    self.logger.info(f"✅ Texto extraído com OCR: {filename}")
                except Exception as e:
                    self.logger.warning(f"⚠️ Erro com pdfplumber: {e}")
                    text_content = self._extract_with_pypdf2(pdf_path)
            
            processing_time = time.time() - start_time
            
            return PDFDocument(
                file_path=str(pdf_path),
                filename=filename,
                file_size=file_size,
                page_count=page_count,
                text_content=text_content.strip(),
                extracted_metadata=metadata,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"❌ Erro ao extrair texto de {pdf_path}: {e}")
            
            return PDFDocument(
                file_path=str(pdf_path),
                filename=pdf_path.name,
                file_size=pdf_path.stat().st_size if pdf_path.exists() else 0,
                page_count=0,
                text_content="",
                extracted_metadata={},
                processing_time=processing_time,
                error_message=str(e)
            )
    
    def _extract_with_pypdf2(self, pdf_path: Path) -> str:
        """Extrair texto usando PyPDF2."""
        try:
            text_content = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
            return text_content
        except Exception as e:
            self.logger.warning(f"⚠️ Erro com PyPDF2: {e}")
            return ""
    
    def _extract_with_ocr(self, pdf_path: Path) -> str:
        """Extrair texto usando OCR (para PDFs escaneados)."""
        if not OCR_LIBRARIES_AVAILABLE:
            return ""
        
        try:
            text_content = ""
            pdf_document = fitz.open(pdf_path)
            
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                
                # Converter para PIL Image
                image = Image.open(io.BytesIO(img_data))
                
                # OCR com Tesseract
                page_text = pytesseract.image_to_string(image)
                text_content += page_text + "\n"
            
            pdf_document.close()
            return text_content
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erro com OCR: {e}")
            return ""
    
    def extract_key_information(self, document: PDFDocument) -> ExtractedInformation:
        """Extrair informações-chave de um documento PDF."""
        start_time = time.time()
        
        try:
            text = document.text_content.lower()
            
            # Extrair frases-chave baseadas em templates
            key_phrases = []
            entities = {
                "dates": [],
                "amounts": [],
                "numbers": [],
                "companies": [],
                "addresses": []
            }
            
            # Buscar informações específicas
            for category, templates in self.information_templates.items():
                for template in templates:
                    if template.lower() in text:
                        key_phrases.append(template)
            
            # Extrair entidades usando regex simples
            import re
            
            # Datas
            date_patterns = [
                r'\d{1,2}/\d{1,2}/\d{4}',
                r'\d{1,2}-\d{1,2}-\d{4}',
                r'\d{4}-\d{1,2}-\d{1,2}',
                r'\d{1,2}\s+\w+\s+\d{4}'
            ]
            for pattern in date_patterns:
                entities["dates"].extend(re.findall(pattern, document.text_content))
            
            # Valores monetários
            amount_patterns = [
                r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
                r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|BRL|EUR)',
                r'R\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
            ]
            for pattern in amount_patterns:
                entities["amounts"].extend(re.findall(pattern, document.text_content))
            
            # Números de PO, contratos, etc.
            number_patterns = [
                r'PO\s*#?\s*\d+',
                r'Contract\s*#?\s*\d+',
                r'Invoice\s*#?\s*\d+',
                r'Order\s*#?\s*\d+'
            ]
            for pattern in number_patterns:
                entities["numbers"].extend(re.findall(pattern, document.text_content, re.IGNORECASE))
            
            # Gerar resumo usando EmbeddingGemma se disponível
            summary = self._generate_summary(document.text_content)
            
            # Categorizar documento
            categories = self._categorize_document(document.text_content)
            
            # Calcular score de relevância
            relevance_score = self._calculate_relevance_score(document.text_content)
            
            # Gerar embedding se modelo disponível
            embedding = None
            if self.model and document.text_content:
                try:
                    embedding = self.model.encode([document.text_content])[0].tolist()
                except Exception as e:
                    self.logger.warning(f"⚠️ Erro ao gerar embedding: {e}")
            
            return ExtractedInformation(
                document=document,
                key_phrases=list(set(key_phrases)),
                entities=entities,
                summary=summary,
                categories=categories,
                relevance_score=relevance_score,
                embedding=embedding
            )
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao extrair informações: {e}")
            return ExtractedInformation(
                document=document,
                key_phrases=[],
                entities=[],
                summary="Erro na extração",
                categories=[],
                relevance_score=0.0,
                embedding=None
            )
    
    def _generate_summary(self, text: str) -> str:
        """Gerar resumo do texto."""
        if not text or len(text) < 100:
            return "Documento muito curto para resumo"
        
        # Resumo simples baseado nas primeiras frases
        sentences = text.split('.')
        if len(sentences) > 3:
            summary = '. '.join(sentences[:3]) + '.'
        else:
            summary = text[:200] + "..." if len(text) > 200 else text
        
        return summary
    
    def _categorize_document(self, text: str) -> List[str]:
        """Categorizar documento baseado no conteúdo."""
        text_lower = text.lower()
        categories = []
        
        # Categorias baseadas em palavras-chave
        if any(word in text_lower for word in ['purchase order', 'po', 'compra', 'pedido']):
            categories.append("Purchase Order")
        
        if any(word in text_lower for word in ['invoice', 'fatura', 'bill', 'receipt']):
            categories.append("Invoice")
        
        if any(word in text_lower for word in ['contract', 'contrato', 'agreement', 'acordo']):
            categories.append("Contract")
        
        if any(word in text_lower for word in ['specification', 'especificação', 'technical', 'técnico']):
            categories.append("Technical Specification")
        
        if any(word in text_lower for word in ['report', 'relatório', 'analysis', 'análise']):
            categories.append("Report")
        
        return categories if categories else ["Uncategorized"]
    
    def _calculate_relevance_score(self, text: str) -> float:
        """Calcular score de relevância do documento."""
        if not text:
            return 0.0
        
        # Score baseado em densidade de informações importantes
        important_keywords = [
            'purchase order', 'invoice', 'contract', 'amount', 'date',
            'vendor', 'supplier', 'delivery', 'payment', 'terms'
        ]
        
        text_lower = text.lower()
        keyword_count = sum(1 for keyword in important_keywords if keyword in text_lower)
        
        # Normalizar score (0-1)
        max_possible_score = len(important_keywords)
        score = keyword_count / max_possible_score
        
        return min(score, 1.0)
    
    def process_all_pdfs(self) -> ExtractionResult:
        """Processar todos os PDFs na pasta P2."""
        start_time = time.time()
        
        self.logger.info("🚀 Iniciando extração de informações de PDFs")
        
        # Encontrar arquivos PDF
        pdf_files = self.find_pdf_files()
        
        if not pdf_files:
            self.logger.warning("⚠️ Nenhum arquivo PDF encontrado")
            return ExtractionResult(
                success=False,
                documents_processed=0,
                total_processing_time=time.time() - start_time,
                extracted_info=[],
                errors=["Nenhum arquivo PDF encontrado"],
                statistics={}
            )
        
        extracted_info = []
        errors = []
        
        # Processar cada PDF
        for i, pdf_file in enumerate(pdf_files):
            self.logger.info(f"📄 Processando {i+1}/{len(pdf_files)}: {pdf_file.name}")
            
            try:
                # Extrair texto
                document = self.extract_text_from_pdf(pdf_file)
                
                if document.error_message:
                    errors.append(f"Erro em {pdf_file.name}: {document.error_message}")
                    continue
                
                # Extrair informações
                info = self.extract_key_information(document)
                extracted_info.append(info)
                
                self.logger.info(f"✅ Processado: {pdf_file.name} ({len(document.text_content)} caracteres)")
                
            except Exception as e:
                error_msg = f"Erro ao processar {pdf_file.name}: {e}"
                errors.append(error_msg)
                self.logger.error(f"❌ {error_msg}")
        
        total_time = time.time() - start_time
        
        # Calcular estatísticas
        statistics = self._calculate_statistics(extracted_info)
        
        self.logger.info(f"✅ Processamento concluído: {len(extracted_info)} documentos em {total_time:.2f}s")
        
        return ExtractionResult(
            success=len(extracted_info) > 0,
            documents_processed=len(extracted_info),
            total_processing_time=total_time,
            extracted_info=extracted_info,
            errors=errors,
            statistics=statistics
        )
    
    def _calculate_statistics(self, extracted_info: List[ExtractedInformation]) -> Dict[str, Any]:
        """Calcular estatísticas da extração."""
        if not extracted_info:
            return {}
        
        total_docs = len(extracted_info)
        total_text_length = sum(len(info.document.text_content) for info in extracted_info)
        total_pages = sum(info.document.page_count for info in extracted_info)
        
        # Categorias mais comuns
        all_categories = []
        for info in extracted_info:
            all_categories.extend(info.categories)
        
        category_counts = {}
        for category in all_categories:
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Score médio de relevância
        avg_relevance = sum(info.relevance_score for info in extracted_info) / total_docs
        
        return {
            "total_documents": total_docs,
            "total_text_length": total_text_length,
            "total_pages": total_pages,
            "average_text_length": total_text_length / total_docs,
            "average_pages_per_document": total_pages / total_docs,
            "average_relevance_score": avg_relevance,
            "category_distribution": category_counts,
            "documents_with_embeddings": sum(1 for info in extracted_info if info.embedding is not None)
        }
    
    def save_results(self, result: ExtractionResult, output_file: str = None) -> str:
        """Salvar resultados da extração."""
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"reports/pdf_extraction_{timestamp}.json"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Converter para formato serializável
        serializable_result = {
            "success": result.success,
            "documents_processed": result.documents_processed,
            "total_processing_time": result.total_processing_time,
            "extracted_info": [
                {
                    "document": {
                        "file_path": info.document.file_path,
                        "filename": info.document.filename,
                        "file_size": info.document.file_size,
                        "page_count": info.document.page_count,
                        "text_content": info.document.text_content,
                        "extracted_metadata": info.document.extracted_metadata,
                        "processing_time": info.document.processing_time
                    },
                    "key_phrases": info.key_phrases,
                    "entities": info.entities,
                    "summary": info.summary,
                    "categories": info.categories,
                    "relevance_score": info.relevance_score,
                    "embedding": info.embedding
                }
                for info in result.extracted_info
            ],
            "errors": result.errors,
            "statistics": result.statistics,
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_result, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"💾 Resultados salvos em: {output_path}")
        return str(output_path)
    
    def generate_report(self, result: ExtractionResult) -> str:
        """Gerar relatório em texto da extração."""
        report_lines = []
        
        report_lines.append("# Relatório de Extração de Informações de PDFs")
        report_lines.append("=" * 60)
        report_lines.append("")
        
        # Resumo geral
        report_lines.append("## Resumo Geral")
        report_lines.append(f"- **Documentos processados**: {result.documents_processed}")
        report_lines.append(f"- **Tempo total**: {result.total_processing_time:.2f} segundos")
        report_lines.append(f"- **Taxa de sucesso**: {(result.documents_processed / (result.documents_processed + len(result.errors))) * 100:.1f}%")
        report_lines.append("")
        
        # Estatísticas
        if result.statistics:
            report_lines.append("## Estatísticas")
            stats = result.statistics
            report_lines.append(f"- **Total de páginas**: {stats.get('total_pages', 0)}")
            report_lines.append(f"- **Comprimento médio do texto**: {stats.get('average_text_length', 0):.0f} caracteres")
            report_lines.append(f"- **Score médio de relevância**: {stats.get('average_relevance_score', 0):.2f}")
            report_lines.append("")
            
            # Distribuição de categorias
            if stats.get('category_distribution'):
                report_lines.append("### Distribuição por Categoria")
                for category, count in stats['category_distribution'].items():
                    report_lines.append(f"- **{category}**: {count} documentos")
                report_lines.append("")
        
        # Documentos processados
        report_lines.append("## Documentos Processados")
        for i, info in enumerate(result.extracted_info, 1):
            report_lines.append(f"### {i}. {info.document.filename}")
            report_lines.append(f"- **Categorias**: {', '.join(info.categories)}")
            report_lines.append(f"- **Score de relevância**: {info.relevance_score:.2f}")
            report_lines.append(f"- **Páginas**: {info.document.page_count}")
            report_lines.append(f"- **Frases-chave**: {', '.join(info.key_phrases[:5])}")
            report_lines.append(f"- **Resumo**: {info.summary[:200]}...")
            report_lines.append("")
        
        # Erros
        if result.errors:
            report_lines.append("## Erros Encontrados")
            for error in result.errors:
                report_lines.append(f"- {error}")
            report_lines.append("")
        
        return "\n".join(report_lines)


def main():
    """Função principal para extração de PDFs."""
    print("📄 Extrator de Informações de PDFs com EmbeddingGemma")
    print("=" * 60)
    
    # Verificar dependências
    if not PDF_LIBRARIES_AVAILABLE:
        print("❌ Bibliotecas de PDF não disponíveis")
        print("Instale com: pip install PyPDF2 pdfplumber")
        return
    
    if not ML_LIBRARIES_AVAILABLE:
        print("⚠️ Bibliotecas ML não disponíveis - usando extração básica")
        print("Instale com: pip install sentence-transformers torch numpy scikit-learn")
    
    # Criar extrator
    extractor = PDFInformationExtractor()
    
    # Processar PDFs
    result = extractor.process_all_pdfs()
    
    if result.success:
        print(f"\n✅ Processamento concluído!")
        print(f"📊 Documentos processados: {result.documents_processed}")
        print(f"⏱️ Tempo total: {result.total_processing_time:.2f}s")
        
        # Salvar resultados
        output_file = extractor.save_results(result)
        print(f"💾 Resultados salvos em: {output_file}")
        
        # Gerar relatório
        report = extractor.generate_report(result)
        report_file = output_file.replace('.json', '_report.md')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📋 Relatório salvo em: {report_file}")
        
    else:
        print(f"\n❌ Processamento falhou")
        print(f"Erros: {len(result.errors)}")
        for error in result.errors:
            print(f"  - {error}")


if __name__ == "__main__":
    main()
