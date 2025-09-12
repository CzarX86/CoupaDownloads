"""
PDF Information Extractor for Specific Coupa Fields
Extrator específico para campos específicos dos PDFs do Coupa
"""

import os
import json
import time
import csv
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# PDF processing libraries
try:
    import PyPDF2
    import pdfplumber
    PDF_LIBRARIES_AVAILABLE = True
except ImportError:
    PDF_LIBRARIES_AVAILABLE = False

# OCR libraries (for scanned PDFs)
try:
    import pytesseract
    from PIL import Image
    import fitz  # PyMuPDF
    OCR_LIBRARIES_AVAILABLE = True
except ImportError:
    OCR_LIBRARIES_AVAILABLE = False

# ML libraries
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    ML_LIBRARIES_AVAILABLE = True
except ImportError:
    ML_LIBRARIES_AVAILABLE = False

# Configuration
from config import get_config


@dataclass
class CoupaFieldExtraction:
    """Campos específicos para extração dos PDFs do Coupa."""
    # Campos obrigatórios
    remarks: str = ""
    supporting_information: str = ""
    procurement_negotiation_strategy: str = ""
    opportunity_available: str = ""  # Yes/No
    inflation_percent: str = ""
    minimum_commitment_value: str = ""
    contractual_commercial_model: str = ""  # Fixed/Consumption etc
    user_based_license: str = ""  # Yes/No
    type_of_contract_l2: str = ""
    type_of_contract_l1: str = ""
    sow_value_eur: str = ""
    fx: str = ""
    sow_currency: str = ""
    sow_value_lc: str = ""
    managed_by: str = ""  # VMO/SL/SAM/Business
    contract_end_date: str = ""
    contract_start_date: str = ""
    contract_type: str = ""  # SOW/CR/Subs Order form
    contract_name: str = ""
    high_level_scope: str = ""
    platform_technology: str = ""
    pwo_number: str = ""
    
    # Metadados
    source_file: str = ""
    extraction_confidence: float = 0.0
    extraction_method: str = ""


@dataclass
class PDFDocument:
    """Representação de um documento PDF."""
    file_path: str
    filename: str
    file_size: int
    page_count: int
    text_content: str
    extracted_metadata: Dict[str, Any]
    processing_time: float
    error_message: Optional[str] = None


class CoupaPDFFieldExtractor:
    """Extrator específico para campos do Coupa."""
    
    def __init__(self, pdf_directory: str = "/Users/juliocezar/Dev/work/CoupaDownloads/src/data/P2"):
        self.config = get_config()
        self.pdf_directory = Path(pdf_directory)
        self.model = None
        self.logger = self._setup_logger()
        
        # Padrões de regex para extração de campos específicos
        self.field_patterns = {
            "remarks": [
                r"remarks?\s*:?\s*(.+?)(?:\n|$)",
                r"comments?\s*:?\s*(.+?)(?:\n|$)",
                r"notes?\s*:?\s*(.+?)(?:\n|$)"
            ],
            "supporting_information": [
                r"supporting\s+information\s*:?\s*(.+?)(?:\n|$)",
                r"additional\s+information\s*:?\s*(.+?)(?:\n|$)",
                r"background\s*:?\s*(.+?)(?:\n|$)"
            ],
            "procurement_negotiation_strategy": [
                r"procurement\s+negotiation\s+strategy\s*:?\s*(.+?)(?:\n|$)",
                r"negotiation\s+strategy\s*:?\s*(.+?)(?:\n|$)",
                r"procurement\s+strategy\s*:?\s*(.+?)(?:\n|$)"
            ],
            "opportunity_available": [
                r"opportunity\s+available\s*:?\s*(yes|no|y|n)",
                r"opportunity\s*:?\s*(yes|no|y|n)",
                r"available\s*:?\s*(yes|no|y|n)"
            ],
            "inflation_percent": [
                r"inflation\s*:?\s*(\d+(?:\.\d+)?)\s*%",
                r"inflation\s+%\s*:?\s*(\d+(?:\.\d+)?)",
                r"inflation\s+rate\s*:?\s*(\d+(?:\.\d+)?)\s*%"
            ],
            "minimum_commitment_value": [
                r"minimum\s+commitment\s+value\s*:?\s*([€$£]\s*\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"min\s+commitment\s*:?\s*([€$£]\s*\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"commitment\s+value\s*:?\s*([€$£]\s*\d+(?:,\d{3})*(?:\.\d{2})?)"
            ],
            "contractual_commercial_model": [
                r"contractual\s+commercial\s+model\s*:?\s*(fixed|consumption|subscription|perpetual)",
                r"commercial\s+model\s*:?\s*(fixed|consumption|subscription|perpetual)",
                r"pricing\s+model\s*:?\s*(fixed|consumption|subscription|perpetual)"
            ],
            "user_based_license": [
                r"user\s+based\s+license\s*:?\s*(yes|no|y|n)",
                r"user\s+license\s*:?\s*(yes|no|y|n)",
                r"license\s+type\s*:?\s*(user|seat|concurrent)"
            ],
            "type_of_contract_l2": [
                r"type\s+of\s+contract\s+l2\s*:?\s*(.+?)(?:\n|$)",
                r"contract\s+type\s+l2\s*:?\s*(.+?)(?:\n|$)",
                r"l2\s+contract\s+type\s*:?\s*(.+?)(?:\n|$)"
            ],
            "type_of_contract_l1": [
                r"type\s+of\s+contract\s+l1\s*:?\s*(.+?)(?:\n|$)",
                r"contract\s+type\s+l1\s*:?\s*(.+?)(?:\n|$)",
                r"l1\s+contract\s+type\s*:?\s*(.+?)(?:\n|$)"
            ],
            "sow_value_eur": [
                r"sow\s+value\s+in\s+eur\s*:?\s*([€]\s*\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"sow\s+value\s+eur\s*:?\s*([€]\s*\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"value\s+eur\s*:?\s*([€]\s*\d+(?:,\d{3})*(?:\.\d{2})?)"
            ],
            "fx": [
                r"fx\s*:?\s*(\d+(?:\.\d+)?)",
                r"exchange\s+rate\s*:?\s*(\d+(?:\.\d+)?)",
                r"currency\s+rate\s*:?\s*(\d+(?:\.\d+)?)"
            ],
            "sow_currency": [
                r"sow\s+currency\s*:?\s*([A-Z]{3})",
                r"currency\s*:?\s*([A-Z]{3})",
                r"base\s+currency\s*:?\s*([A-Z]{3})"
            ],
            "sow_value_lc": [
                r"sow\s+value\s+in\s+lc\s*:?\s*([€$£]\s*\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"sow\s+value\s+lc\s*:?\s*([€$£]\s*\d+(?:,\d{3})*(?:\.\d{2})?)",
                r"value\s+lc\s*:?\s*([€$£]\s*\d+(?:,\d{3})*(?:\.\d{2})?)"
            ],
            "managed_by": [
                r"managed\s+by\s*:?\s*(vmo|sl|sam|business)",
                r"management\s*:?\s*(vmo|sl|sam|business)",
                r"owner\s*:?\s*(vmo|sl|sam|business)"
            ],
            "contract_end_date": [
                r"contract\s+end\s+date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
                r"end\s+date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
                r"expiration\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})"
            ],
            "contract_start_date": [
                r"contract\s+start\s+date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
                r"start\s+date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
                r"effective\s+date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})"
            ],
            "contract_type": [
                r"contract\s+type\s*:?\s*(sow|cr|subs\s+order\s+form)",
                r"type\s*:?\s*(sow|cr|subs\s+order\s+form)",
                r"agreement\s+type\s*:?\s*(sow|cr|subs\s+order\s+form)"
            ],
            "contract_name": [
                r"contract\s+name\s*:?\s*(.+?)(?:\n|$)",
                r"agreement\s+name\s*:?\s*(.+?)(?:\n|$)",
                r"title\s*:?\s*(.+?)(?:\n|$)"
            ],
            "high_level_scope": [
                r"high\s+level\s+scope\s*:?\s*(.+?)(?:\n|$)",
                r"scope\s*:?\s*(.+?)(?:\n|$)",
                r"description\s*:?\s*(.+?)(?:\n|$)"
            ],
            "platform_technology": [
                r"platform\s*:?\s*(.+?)(?:\n|$)",
                r"technology\s*:?\s*(.+?)(?:\n|$)",
                r"platform/technology\s*:?\s*(.+?)(?:\n|$)"
            ],
            "pwo_number": [
                r"pwo\s*#?\s*:?\s*(\d+)",
                r"pwo\s+number\s*:?\s*(\d+)",
                r"project\s+work\s+order\s*#?\s*:?\s*(\d+)"
            ]
        }
        
        # Inicializar modelo se disponível
        self._initialize_model()
    
    def _setup_logger(self) -> logging.Logger:
        """Configurar logger para extração."""
        logger = logging.getLogger("coupa_pdf_extractor")
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
    
    def extract_coupa_fields(self, document: PDFDocument) -> CoupaFieldExtraction:
        """Extrair campos específicos do Coupa de um documento PDF."""
        try:
            text = document.text_content
            text_lower = text.lower()
            
            # Inicializar extração
            extraction = CoupaFieldExtraction(
                source_file=document.filename,
                extraction_method="regex_patterns"
            )
            
            # Extrair cada campo usando padrões regex
            for field_name, patterns in self.field_patterns.items():
                field_value = self._extract_field_value(text, text_lower, patterns)
                setattr(extraction, field_name, field_value)
            
            # Calcular confiança da extração
            extraction.extraction_confidence = self._calculate_extraction_confidence(extraction)
            
            return extraction
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao extrair campos: {e}")
            return CoupaFieldExtraction(
                source_file=document.filename,
                extraction_method="error",
                extraction_confidence=0.0
            )
    
    def _extract_field_value(self, text: str, text_lower: str, patterns: List[str]) -> str:
        """Extrair valor de um campo usando padrões regex."""
        for pattern in patterns:
            try:
                matches = re.findall(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
                if matches:
                    # Retornar o primeiro match encontrado
                    match = matches[0]
                    if isinstance(match, tuple):
                        match = match[0]
                    return match.strip()
            except Exception as e:
                self.logger.warning(f"⚠️ Erro no padrão regex {pattern}: {e}")
                continue
        
        return ""
    
    def _calculate_extraction_confidence(self, extraction: CoupaFieldExtraction) -> float:
        """Calcular confiança da extração baseada nos campos encontrados."""
        fields_found = 0
        total_fields = len(self.field_patterns)
        
        for field_name in self.field_patterns.keys():
            field_value = getattr(extraction, field_name, "")
            if field_value and field_value.strip():
                fields_found += 1
        
        confidence = fields_found / total_fields
        return confidence
    
    def process_all_pdfs(self) -> List[CoupaFieldExtraction]:
        """Processar todos os PDFs na pasta P2."""
        start_time = time.time()
        
        self.logger.info("🚀 Iniciando extração de campos específicos do Coupa")
        
        # Encontrar arquivos PDF
        pdf_files = self.find_pdf_files()
        
        if not pdf_files:
            self.logger.warning("⚠️ Nenhum arquivo PDF encontrado")
            return []
        
        extractions = []
        
        # Processar cada PDF
        for i, pdf_file in enumerate(pdf_files):
            self.logger.info(f"📄 Processando {i+1}/{len(pdf_files)}: {pdf_file.name}")
            
            try:
                # Extrair texto
                document = self.extract_text_from_pdf(pdf_file)
                
                if document.error_message:
                    self.logger.error(f"❌ Erro ao extrair texto de {pdf_file.name}: {document.error_message}")
                    continue
                
                # Extrair campos específicos
                extraction = self.extract_coupa_fields(document)
                extractions.append(extraction)
                
                self.logger.info(f"✅ Processado: {pdf_file.name} (confiança: {extraction.extraction_confidence:.2f})")
                
            except Exception as e:
                self.logger.error(f"❌ Erro ao processar {pdf_file.name}: {e}")
        
        total_time = time.time() - start_time
        self.logger.info(f"✅ Processamento concluído: {len(extractions)} documentos em {total_time:.2f}s")
        
        return extractions
    
    def save_to_csv(self, extractions: List[CoupaFieldExtraction], output_file: str = None) -> str:
        """Salvar extrações em arquivo CSV."""
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"reports/coupa_fields_extraction_{timestamp}.csv"
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Definir cabeçalhos do CSV
        headers = [
            "Source File",
            "Remarks",
            "Supporting Information",
            "Procurement Negotiation Strategy",
            "Opportunity Available",
            "Inflation %",
            "Minimum Commitment Value",
            "Contractual Commercial Model",
            "User Based License",
            "Type of Contract - L2",
            "Type of Contract - L1",
            "SOW Value in EUR",
            "FX",
            "SOW Currency",
            "SOW Value in LC",
            "Managed By",
            "Contract End Date",
            "Contract Start Date",
            "Contract Type",
            "Contract Name",
            "High Level Scope",
            "Platform/Technology",
            "PWO#",
            "Extraction Confidence",
            "Extraction Method"
        ]
        
        # Escrever CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for extraction in extractions:
                row = [
                    extraction.source_file,
                    extraction.remarks,
                    extraction.supporting_information,
                    extraction.procurement_negotiation_strategy,
                    extraction.opportunity_available,
                    extraction.inflation_percent,
                    extraction.minimum_commitment_value,
                    extraction.contractual_commercial_model,
                    extraction.user_based_license,
                    extraction.type_of_contract_l2,
                    extraction.type_of_contract_l1,
                    extraction.sow_value_eur,
                    extraction.fx,
                    extraction.sow_currency,
                    extraction.sow_value_lc,
                    extraction.managed_by,
                    extraction.contract_end_date,
                    extraction.contract_start_date,
                    extraction.contract_type,
                    extraction.contract_name,
                    extraction.high_level_scope,
                    extraction.platform_technology,
                    extraction.pwo_number,
                    extraction.extraction_confidence,
                    extraction.extraction_method
                ]
                writer.writerow(row)
        
        self.logger.info(f"💾 CSV salvo em: {output_path}")
        return str(output_path)
    
    def generate_extraction_report(self, extractions: List[CoupaFieldExtraction]) -> str:
        """Gerar relatório da extração."""
        report_lines = []
        
        report_lines.append("# Relatório de Extração de Campos do Coupa")
        report_lines.append("=" * 60)
        report_lines.append("")
        
        # Resumo geral
        report_lines.append("## Resumo Geral")
        report_lines.append(f"- **Documentos processados**: {len(extractions)}")
        report_lines.append(f"- **Campos extraídos**: {len(self.field_patterns)}")
        
        if extractions:
            avg_confidence = sum(e.extraction_confidence for e in extractions) / len(extractions)
            report_lines.append(f"- **Confiança média**: {avg_confidence:.2f}")
        
        report_lines.append("")
        
        # Estatísticas por campo
        report_lines.append("## Estatísticas por Campo")
        field_stats = {}
        
        for field_name in self.field_patterns.keys():
            field_values = [getattr(e, field_name, "") for e in extractions]
            non_empty_count = sum(1 for v in field_values if v and v.strip())
            field_stats[field_name] = {
                "total": len(extractions),
                "found": non_empty_count,
                "percentage": (non_empty_count / len(extractions)) * 100 if extractions else 0
            }
        
        for field_name, stats in field_stats.items():
            report_lines.append(f"- **{field_name.replace('_', ' ').title()}**: {stats['found']}/{stats['total']} ({stats['percentage']:.1f}%)")
        
        report_lines.append("")
        
        # Detalhes por documento
        report_lines.append("## Detalhes por Documento")
        for i, extraction in enumerate(extractions, 1):
            report_lines.append(f"### {i}. {extraction.source_file}")
            report_lines.append(f"- **Confiança**: {extraction.extraction_confidence:.2f}")
            report_lines.append(f"- **Método**: {extraction.extraction_method}")
            
            # Mostrar campos encontrados
            found_fields = []
            for field_name in self.field_patterns.keys():
                field_value = getattr(extraction, field_name, "")
                if field_value and field_value.strip():
                    found_fields.append(f"{field_name.replace('_', ' ').title()}: {field_value}")
            
            if found_fields:
                report_lines.append("- **Campos encontrados**:")
                for field in found_fields[:5]:  # Mostrar apenas os primeiros 5
                    report_lines.append(f"  - {field}")
                if len(found_fields) > 5:
                    report_lines.append(f"  - ... e mais {len(found_fields) - 5} campos")
            else:
                report_lines.append("- **Nenhum campo encontrado**")
            
            report_lines.append("")
        
        return "\n".join(report_lines)


def main():
    """Função principal para extração de campos específicos."""
    print("📄 Extrator de Campos Específicos do Coupa")
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
    extractor = CoupaPDFFieldExtractor()
    
    # Processar PDFs
    extractions = extractor.process_all_pdfs()
    
    if extractions:
        print(f"\n✅ Processamento concluído!")
        print(f"📊 Documentos processados: {len(extractions)}")
        
        # Salvar CSV
        csv_file = extractor.save_to_csv(extractions)
        print(f"💾 CSV salvo em: {csv_file}")
        
        # Gerar relatório
        report = extractor.generate_extraction_report(extractions)
        report_file = csv_file.replace('.csv', '_report.md')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"📋 Relatório salvo em: {report_file}")
        
        # Mostrar estatísticas
        if extractions:
            avg_confidence = sum(e.extraction_confidence for e in extractions) / len(extractions)
            print(f"📈 Confiança média: {avg_confidence:.2f}")
            
            # Mostrar campos mais encontrados
            field_counts = {}
            for field_name in extractor.field_patterns.keys():
                count = sum(1 for e in extractions if getattr(e, field_name, "").strip())
                field_counts[field_name] = count
            
            print(f"\n🔍 Campos mais encontrados:")
            sorted_fields = sorted(field_counts.items(), key=lambda x: x[1], reverse=True)
            for field_name, count in sorted_fields[:5]:
                if count > 0:
                    print(f"  - {field_name.replace('_', ' ').title()}: {count} documentos")
        
    else:
        print(f"\n❌ Nenhum documento processado com sucesso")


if __name__ == "__main__":
    main()
