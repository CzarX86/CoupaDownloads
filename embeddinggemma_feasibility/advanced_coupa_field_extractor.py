"""
Advanced PDF Field Extractor with Multiple NLP Libraries
Extrator avançado de campos PDF com múltiplas bibliotecas NLP
"""

import os
import json
import time
import csv
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

# NLP Libraries - Progressive Loading
NLP_LIBRARIES = {}

# spaCy for NER
try:
    import spacy
    NLP_LIBRARIES['spacy'] = True
except ImportError:
    NLP_LIBRARIES['spacy'] = False

# Transformers/BERT
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
    NLP_LIBRARIES['transformers'] = True
except ImportError:
    NLP_LIBRARIES['transformers'] = False

# LangChain
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.embeddings import HuggingFaceEmbeddings
    from langchain.llms import Ollama
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    NLP_LIBRARIES['langchain'] = True
except ImportError:
    NLP_LIBRARIES['langchain'] = False

# Sentence Transformers
try:
    from sentence_transformers import SentenceTransformer
    NLP_LIBRARIES['sentence_transformers'] = True
except ImportError:
    NLP_LIBRARIES['sentence_transformers'] = False

# Ollama (local models)
try:
    import ollama
    NLP_LIBRARIES['ollama'] = True
except ImportError:
    NLP_LIBRARIES['ollama'] = False

# Configuration
from .config import get_config
from .entity_parsing import ContractEntityParser, parse_numeric_amount


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
    nlp_libraries_used: List[str] = None


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


class AdvancedCoupaPDFFieldExtractor:
    """Extrator avançado para campos do Coupa usando múltiplas bibliotecas NLP."""
    
    def __init__(self, pdf_directory: str = "/Users/juliocezar/Dev/work/CoupaDownloads/src/data/P2", *, use_rag: bool = False, use_validations: bool = False):
        self.config = get_config()
        self.pdf_directory = Path(pdf_directory)
        self.logger = self._setup_logger()
        self.use_rag = use_rag
        self.use_validations = use_validations

        # Inicializar bibliotecas NLP disponíveis
        self.nlp_models = {}
        self.available_libraries = []
        self._initialize_nlp_libraries()
        self.entity_parser = ContractEntityParser()
        
        # Campos para extração
        self.target_fields = [
            "remarks", "supporting_information", "procurement_negotiation_strategy",
            "opportunity_available", "inflation_percent", "minimum_commitment_value",
            "contractual_commercial_model", "user_based_license", "type_of_contract_l2",
            "type_of_contract_l1", "sow_value_eur", "fx", "sow_currency",
            "sow_value_lc", "managed_by", "contract_end_date", "contract_start_date",
            "contract_type", "contract_name", "high_level_scope", "platform_technology", "pwo_number"
        ]
    
    def _setup_logger(self) -> logging.Logger:
        """Configurar logger para extração."""
        logger = logging.getLogger("advanced_coupa_extractor")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _initialize_nlp_libraries(self):
        """Inicializar bibliotecas NLP disponíveis."""
        self.logger.info("🔧 Inicializando bibliotecas NLP...")
        
        # spaCy para NER
        if NLP_LIBRARIES.get('spacy'):
            try:
                # Tentar carregar modelo em inglês primeiro (mais comum para documentos corporativos)
                try:
                    self.nlp_models['spacy'] = spacy.load("en_core_web_sm")
                    self.logger.info("✅ spaCy modelo inglês carregado")
                except OSError:
                    try:
                        self.nlp_models['spacy'] = spacy.load("pt_core_news_sm")
                        self.logger.info("✅ spaCy modelo português carregado")
                    except OSError:
                        self.logger.warning("⚠️ Modelos spaCy não encontrados. Instale com: python -m spacy download en_core_web_sm")
                        NLP_LIBRARIES['spacy'] = False
                self.available_libraries.append('spacy')
            except Exception as e:
                self.logger.error(f"❌ Erro ao carregar spaCy: {e}")
                NLP_LIBRARIES['spacy'] = False
        
        # Transformers/BERT para NER
        if NLP_LIBRARIES.get('transformers'):
            try:
                # Usar modelo BERT para NER
                self.nlp_models['bert_ner'] = pipeline(
                    "ner",
                    model="dbmdz/bert-large-cased-finetuned-conll03-english",
                    aggregation_strategy="simple"
                )
                self.logger.info("✅ BERT NER pipeline carregado")
                self.available_libraries.append('transformers')
            except Exception as e:
                self.logger.error(f"❌ Erro ao carregar BERT: {e}")
                NLP_LIBRARIES['transformers'] = False
        
        # Sentence Transformers para embeddings
        if NLP_LIBRARIES.get('sentence_transformers'):
            try:
                # Prefer custom path or configured model, then fall back
                model_name = self.config.embed_model_custom_path or getattr(self.config, 'embed_model', None) or "all-MiniLM-L6-v2"
                try:
                    self.nlp_models['sentence_transformer'] = SentenceTransformer(
                        model_name,
                        cache_folder=self.config.model_cache_dir
                    )
                    self.logger.info(f"✅ SentenceTransformer carregado: {model_name}")
                except Exception:
                    # Fallback to MiniLM if custom/configured fails
                    self.nlp_models['sentence_transformer'] = SentenceTransformer("all-MiniLM-L6-v2")
                    self.logger.info("✅ SentenceTransformer fallback carregado: all-MiniLM-L6-v2")
                self.available_libraries.append('sentence_transformers')
            except Exception as e:
                self.logger.error(f"❌ Erro ao carregar SentenceTransformer: {e}")
                NLP_LIBRARIES['sentence_transformers'] = False
        
        # LangChain
        if NLP_LIBRARIES.get('langchain'):
            try:
                self.nlp_models['text_splitter'] = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200
                )
                self.logger.info("✅ LangChain text splitter carregado")
                self.available_libraries.append('langchain')
            except Exception as e:
                self.logger.error(f"❌ Erro ao carregar LangChain: {e}")
                NLP_LIBRARIES['langchain'] = False
        
        # Ollama (modelos locais)
        if NLP_LIBRARIES.get('ollama'):
            try:
                # Verificar se Ollama está rodando
                models = ollama.list()
                self.logger.info(f"✅ Ollama disponível com {len(models['models'])} modelos")
                self.available_libraries.append('ollama')
            except Exception as e:
                self.logger.warning(f"⚠️ Ollama não disponível: {e}")
                self.logger.info("🔄 Tentando iniciar Ollama...")
                try:
                    import subprocess
                    subprocess.Popen(['ollama', 'serve'], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    import time
                    time.sleep(3)  # Aguardar inicialização
                    models = ollama.list()
                    self.logger.info(f"✅ Ollama iniciado com {len(models['models'])} modelos")
                    self.available_libraries.append('ollama')
                except Exception as e2:
                    self.logger.error(f"❌ Falha ao iniciar Ollama: {e2}")
                    NLP_LIBRARIES['ollama'] = False
        
        self.logger.info(f"📚 Bibliotecas NLP disponíveis: {', '.join(self.available_libraries)}")
        
        # Verificar se Ollama está disponível (obrigatório)
        if 'ollama' not in self.available_libraries:
            raise Exception("❌ Ollama não está disponível. Sistema requer conectividade com Ollama para funcionar.")
    
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

    def find_supported_files(self) -> List[Path]:
        """Encontrar todos os arquivos suportados (PDF/DOCX/TXT/HTML/MSG/EML/IMG)."""
        patterns = [
            "*.pdf", "*.docx", "*.txt", "*.md", "*.markdown", "*.html", "*.htm",
            "*.msg", "*.eml", "*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff"
        ]
        files: List[Path] = []
        if not self.pdf_directory.exists():
            self.logger.warning(f"⚠️ Diretório não encontrado: {self.pdf_directory}")
            return files
        for pat in patterns:
            for f in self.pdf_directory.rglob(pat):
                if f.is_file():
                    files.append(f)
        self.logger.info(f"📄 Encontrados {len(files)} arquivos suportados")
        return files

    def _document_from_text(self, path: Path, text: str) -> PDFDocument:
        try:
            size = path.stat().st_size
        except Exception:
            size = 0
        return PDFDocument(
            file_path=str(path),
            filename=path.name,
            file_size=size,
            page_count=0,
            text_content=(text or "").strip(),
            extracted_metadata={},
            processing_time=0.0
        )

    def extract_text_from_any(self, path: Path) -> PDFDocument:
        """Extrair texto de qualquer arquivo suportado usando content_loader (ou PDF)."""
        if path.suffix.lower() == ".pdf":
            return self.extract_text_from_pdf(path)
        try:
            from .content_loader import load_text_from_path
            loaded = load_text_from_path(str(path))
            doc = self._document_from_text(path, loaded.get("text", ""))
            md = loaded.get("metadata", {}) or {}
            doc.extracted_metadata = md
            return doc
        except Exception as e:
            self.logger.warning(f"⚠️ Falha ao extrair texto de {path.name}: {e}")
            return self._document_from_text(path, "")
    
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
    
    def extract_fields_with_spacy(self, text: str) -> Dict[str, str]:
        """Extrair campos usando spaCy NER."""
        if 'spacy' not in self.nlp_models:
            return {}
        
        try:
            doc = self.nlp_models['spacy'](text)
            extracted = {}
            
            # Extrair entidades nomeadas
            entities = {}
            for ent in doc.ents:
                entities[ent.label_] = entities.get(ent.label_, [])
                entities[ent.label_].append(ent.text)
            
            # Mapear entidades para campos específicos
            if 'MONEY' in entities:
                extracted['minimum_commitment_value'] = entities['MONEY'][0]
                extracted['sow_value_eur'] = entities['MONEY'][0]
            
            if 'DATE' in entities:
                dates = entities['DATE']
                if len(dates) >= 2:
                    extracted['contract_start_date'] = dates[0]
                    extracted['contract_end_date'] = dates[1]
                elif len(dates) == 1:
                    extracted['contract_start_date'] = dates[0]
            
            if 'ORG' in entities:
                extracted['managed_by'] = entities['ORG'][0]
            
            if 'PRODUCT' in entities:
                extracted['platform_technology'] = entities['PRODUCT'][0]
            
            return extracted
            
        except Exception as e:
            self.logger.error(f"❌ Erro no spaCy NER: {e}")
            return {}
    
    def extract_fields_with_bert(self, text: str) -> Dict[str, str]:
        """Extrair campos usando BERT NER."""
        if 'bert_ner' not in self.nlp_models:
            return {}
        
        try:
            # Limitar texto para evitar problemas de memória
            text_chunks = [text[i:i+512] for i in range(0, len(text), 512)]
            all_entities = []
            
            for chunk in text_chunks[:3]:  # Processar apenas os primeiros 3 chunks
                entities = self.nlp_models['bert_ner'](chunk)
                all_entities.extend(entities)
            
            extracted = {}
            
            # Agrupar entidades por tipo
            entity_groups = {}
            for entity in all_entities:
                label = entity['entity_group']
                if label not in entity_groups:
                    entity_groups[label] = []
                entity_groups[label].append(entity['word'])
            
            # Mapear para campos específicos
            if 'MISC' in entity_groups:
                extracted['platform_technology'] = entity_groups['MISC'][0]
            
            if 'ORG' in entity_groups:
                extracted['managed_by'] = entity_groups['ORG'][0]
            
            return extracted
            
        except Exception as e:
            self.logger.error(f"❌ Erro no BERT NER: {e}")
            return {}
    
    def extract_fields_with_llm(self, text: str) -> Dict[str, str]:
        """Extrair campos usando apenas phi3:mini (modelo mais básico)."""
        if 'ollama' not in self.available_libraries:
            return {}
        
        try:
            # Usar apenas o primeiro chunk para velocidade
            text_chunk = self._get_first_chunk(text, max_size=1500)
            
            # Prompt otimizado e estruturado para contratos
            prompt = f"""
            You are a contract analysis expert. Extract specific information from this contract document.

            IMPORTANT: Return ONLY valid JSON format. No explanations, no markdown, just JSON.

            Required fields (use exact field names):
            {{
                "remarks": "General observations or notes about the contract",
                "supporting_information": "Supporting documentation or references",
                "procurement_negotiation_strategy": "Negotiation strategy mentioned",
                "opportunity_available": "Yes or No - if opportunity is mentioned",
                "inflation_percent": "Inflation percentage (0-100) if mentioned",
                "minimum_commitment_value": "Minimum commitment amount in numbers",
                "contractual_commercial_model": "Fixed, Consumption, or other model type",
                "user_based_license": "Yes or No - if user-based licensing is mentioned",
                "type_of_contract_l2": "Contract type level 2 classification",
                "type_of_contract_l1": "Contract type level 1 classification", 
                "sow_value_eur": "SOW value in EUR (numbers only)",
                "fx": "Exchange rate if mentioned",
                "sow_currency": "Currency code (EUR, USD, etc.)",
                "sow_value_lc": "SOW value in local currency",
                "managed_by": "VMO, SL, SAM, or Business",
                "contract_end_date": "End date in YYYY-MM-DD format",
                "contract_start_date": "Start date in YYYY-MM-DD format",
                "contract_type": "SOW, CR, or Subs Order form",
                "contract_name": "Full contract name/title",
                "high_level_scope": "High-level scope description",
                "platform_technology": "Platform or technology mentioned",
                "pwo_number": "PWO number if found"
            }}

            Contract text:
            {text_chunk}

            Extract information and return valid JSON:
            """
            
            # Usar apenas phi3:mini com timeout curto
            response = ollama.generate(
                model='phi3:mini',
                prompt=prompt,
                options={
                    'temperature': 0.1,
                    'timeout': 3000  # 3 segundos
                }
            )
            
            # Extrair JSON da resposta
            response_text = response['response']
            extracted = self._extract_json_from_response(response_text)
            
            if extracted:
                self.logger.debug(f"✅ phi3:mini extraiu {len(extracted)} campos")
                return extracted
            else:
                self.logger.debug("⚠️ phi3:mini não conseguiu extrair campos válidos")
                return {}
            
        except Exception as e:
            self.logger.warning(f"⚠️ phi3:mini falhou: {e}")
            return {}
    
    def _get_first_chunk(self, text: str, max_size: int = 1500) -> str:
        """Obter apenas o primeiro chunk do texto para velocidade."""
        if len(text) <= max_size:
            return text
        
        # Pegar apenas o início do texto
        return text[:max_size] + "..."
    
    def _chunk_text_intelligently(self, text: str, max_chunk_size: int = 2000) -> List[str]:
        """Dividir texto em chunks inteligentes."""
        if len(text) <= max_chunk_size:
            return [text]
        
        # Dividir por parágrafos primeiro
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= max_chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, str]:
        """Extrair JSON válido da resposta do LLM."""
        try:
            # Procurar por JSON na resposta
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                extracted = json.loads(json_text)
                
                # Filtrar apenas campos válidos
                valid_fields = {}
                for key, value in extracted.items():
                    if isinstance(value, str) and value.strip():
                        valid_fields[key] = value.strip()
                
                return valid_fields
            
        except json.JSONDecodeError:
            pass
        
        return {}
    
    def _calculate_extraction_confidence(self, extracted: Dict[str, str]) -> float:
        """Calcular confiança da extração baseada em campos críticos."""
        critical_fields = [
            'contract_name', 'contract_type', 'contract_start_date', 
            'sow_value_eur', 'managed_by', 'pwo_number'
        ]
        
        total_fields = len(self.target_fields)
        found_fields = len([f for f in extracted.keys() if f in self.target_fields])
        
        # Bonus para campos críticos
        critical_found = len([f for f in critical_fields if f in extracted])
        critical_bonus = critical_found * 0.1
        
        base_confidence = found_fields / total_fields
        return min(base_confidence + critical_bonus, 1.0)
    
    def extract_fields_with_semantic_search(self, text: str) -> Dict[str, str]:
        """Extrair campos usando busca semântica com embeddings."""
        if 'sentence_transformer' not in self.nlp_models:
            return {}
        
        try:
            # Dividir texto em chunks
            chunks = self.nlp_models.get('text_splitter', None)
            if chunks:
                text_chunks = chunks.split_text(text)
            else:
                text_chunks = [text[i:i+500] for i in range(0, len(text), 500)]
            
            # Definir queries semânticas para cada campo
            field_queries = {
                'contract_name': ['nome do contrato', 'contract name', 'título', 'title'],
                'contract_type': ['tipo de contrato', 'contract type', 'SOW', 'CR', 'subs order'],
                'contract_start_date': ['data de início', 'start date', 'effective date', 'início'],
                'contract_end_date': ['data de fim', 'end date', 'expiration', 'fim'],
                'sow_value_eur': ['valor em EUR', 'value in EUR', 'euros', '€'],
                'managed_by': ['gerenciado por', 'managed by', 'VMO', 'SL', 'SAM'],
                'platform_technology': ['plataforma', 'technology', 'tecnologia', 'software'],
                'pwo_number': ['PWO', 'número PWO', 'PWO number', 'project work order']
            }
            
            extracted = {}
            
            # Gerar embeddings para chunks
            chunk_embeddings = self.nlp_models['sentence_transformer'].encode(text_chunks)
            
            for field, queries in field_queries.items():
                best_match = None
                best_score = 0
                
                for query in queries:
                    query_embedding = self.nlp_models['sentence_transformer'].encode([query])
                    
                    # Calcular similaridade
                    from sklearn.metrics.pairwise import cosine_similarity
                    similarities = cosine_similarity(query_embedding, chunk_embeddings)[0]
                    
                    max_similarity = max(similarities)
                    if max_similarity > best_score and max_similarity > 0.3:
                        best_score = max_similarity
                        best_match = text_chunks[similarities.argmax()]
                
                if best_match:
                    # Extrair valor específico do chunk
                    extracted[field] = self._extract_value_from_chunk(field, best_match)
            
            return extracted
            
        except Exception as e:
            self.logger.error(f"❌ Erro na busca semântica: {e}")
            return {}
    
    def _extract_value_from_chunk(self, field: str, chunk: str) -> str:
        """Extrair valor específico de um chunk de texto."""
        entities = self.entity_parser.extract_entities(chunk, target_field=field)
        value = getattr(entities, field, None)
        if value:
            return value

        # Para outros campos, retornar o chunk completo (limitado)
        return chunk[:100] + "..." if len(chunk) > 100 else chunk
    
    def extract_coupa_fields_from_file(self, pdf_path: str) -> CoupaFieldExtraction:
        """Extrair campos específicos do Coupa de um arquivo PDF."""
        try:
            # Extrair texto do PDF
            pdf_doc = self.extract_text_from_pdf(Path(pdf_path))
            text = pdf_doc.text_content
            if not text:
                return CoupaFieldExtraction(
                    source_file=os.path.basename(pdf_path),
                    extraction_method="no_text",
                    extraction_confidence=0.0,
                    nlp_libraries_used=[]
                )
            
            # Usar o método principal de extração
            return self._extract_fields_from_text(text, os.path.basename(pdf_path))
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao extrair campos do arquivo {pdf_path}: {e}")
            return CoupaFieldExtraction(
                source_file=os.path.basename(pdf_path),
                extraction_method="error",
                extraction_confidence=0.0,
                nlp_libraries_used=[]
            )
    
    def _calculate_overall_confidence(self, all_extractions: Dict[str, str]) -> float:
        """Calcular confiança geral da extração."""
        try:
            if not all_extractions:
                return 0.0
            
            # Contar campos com valores válidos
            valid_fields = len([v for v in all_extractions.values() if v and str(v).strip()])
            total_fields = len(self.target_fields)
            
            # Confiança baseada na proporção de campos extraídos
            base_confidence = valid_fields / total_fields if total_fields > 0 else 0.0
            
            # Bonus para campos críticos
            critical_fields = ['contract_name', 'contract_type', 'sow_value_eur', 'pwo_number']
            critical_found = len([f for f in critical_fields if f in all_extractions and all_extractions[f]])
            critical_bonus = critical_found * 0.1
            
            return min(base_confidence + critical_bonus, 1.0)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao calcular confiança: {e}")
            return 0.0
    
    def _extract_fields_from_text(self, text: str, filename: str) -> CoupaFieldExtraction:
        """Extrair campos do texto usando múltiplas técnicas NLP."""
        try:
            # Combinar resultados de diferentes técnicas
            all_extractions = {}
            libraries_used = []
            
            # 1. spaCy NER
            if 'spacy' in self.available_libraries:
                spacy_results = self.extract_fields_with_spacy(text)
                all_extractions.update(spacy_results)
                libraries_used.append('spacy')
            
            # 2. BERT NER
            if 'transformers' in self.available_libraries:
                bert_results = self.extract_fields_with_bert(text)
                all_extractions.update(bert_results)
                libraries_used.append('bert')
            
            # 3. LLM (Ollama) - OBRIGATÓRIO
            if 'ollama' not in self.available_libraries:
                raise Exception("❌ Ollama não está disponível. Sistema requer conectividade com Ollama para funcionar.")
            
            llm_results = self.extract_fields_with_llm(text)
            all_extractions.update(llm_results)
            libraries_used.append('ollama')
            
            # 4. Busca semântica
            if 'sentence_transformer' in self.available_libraries:
                semantic_results = self.extract_fields_with_semantic_search(text)
                all_extractions.update(semantic_results)
                libraries_used.append('semantic_search')
            
            # Calcular confiança geral
            confidence = self._calculate_overall_confidence(all_extractions)
            
            # Normalizar nomes dos campos (remover hífens)
            normalized_extractions = {}
            for key, value in all_extractions.items():
                normalized_key = key.replace('-', '_')
                normalized_extractions[normalized_key] = value
            
            return CoupaFieldExtraction(
                source_file=filename,
                extraction_method="advanced_nlp",
                extraction_confidence=confidence,
                nlp_libraries_used=libraries_used,
                **normalized_extractions
            )
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao extrair campos do texto: {e}")
            return CoupaFieldExtraction(
                source_file=filename,
                extraction_method="error",
                extraction_confidence=0.0,
                nlp_libraries_used=[]
            )
    
    def extract_coupa_fields(self, document: PDFDocument) -> CoupaFieldExtraction:
        """Extrair campos específicos do Coupa usando múltiplas técnicas NLP.

        Quando `use_rag` está ativo, reduz o contexto aplicando uma recuperação
        de trechos candidatos (RAG) antes das técnicas NLP, para maior precisão.
        """
        try:
            text = document.text_content
            # Opcional: RAG assistido para reduzir contexto antes das técnicas NLP
            if self.use_rag and text:
                try:
                    from .rag_assisted_extraction import retrieve_candidates_for_fields
                    cands_map = retrieve_candidates_for_fields(text, self.target_fields, top_k=3)
                    unique_snippets: list[str] = []
                    seen: set[str] = set()
                    for lst in cands_map.values():
                        for sn in lst:
                            s = (sn or "").strip()
                            if s and s not in seen:
                                seen.add(s)
                                unique_snippets.append(s)
                    if unique_snippets:
                        text = "\n\n".join(unique_snippets)
                        self.logger.info("🔎 RAG assistido: contexto reduzido para extração")
                except Exception as e:
                    self.logger.warning(f"⚠️ RAG assistido indisponível: {e}")
            if not text:
                return CoupaFieldExtraction(
                    source_file=document.filename,
                    extraction_method="no_text",
                    extraction_confidence=0.0,
                    nlp_libraries_used=[]
                )
            
            # Inicializar extração
            extraction = CoupaFieldExtraction(
                source_file=document.filename,
                extraction_method="multi_nlp",
                nlp_libraries_used=self.available_libraries.copy()
            )
            
            # Aplicar diferentes técnicas de extração
            all_extractions = {}
            
            # 1. spaCy NER
            if 'spacy' in self.available_libraries:
                spacy_results = self.extract_fields_with_spacy(text)
                all_extractions.update(spacy_results)
                self.logger.debug(f"spaCy extraiu: {len(spacy_results)} campos")
            
            # 2. BERT NER
            if 'transformers' in self.available_libraries:
                bert_results = self.extract_fields_with_bert(text)
                all_extractions.update(bert_results)
                self.logger.debug(f"BERT extraiu: {len(bert_results)} campos")
            
            # 3. Busca semântica
            if 'sentence_transformers' in self.available_libraries:
                semantic_results = self.extract_fields_with_semantic_search(text)
                all_extractions.update(semantic_results)
                self.logger.debug(f"Semantic search extraiu: {len(semantic_results)} campos")
            
            # 4. LLM local (Ollama)
            if 'ollama' in self.available_libraries:
                llm_results = self.extract_fields_with_llm(text)
                all_extractions.update(llm_results)
                self.logger.debug(f"LLM extraiu: {len(llm_results)} campos")
            
            # Aplicar resultados à extração
            for field_name in self.target_fields:
                if field_name in all_extractions:
                    setattr(extraction, field_name, all_extractions[field_name])
            
            # Validações opcionais e normalização
            if self.use_validations:
                try:
                    self._apply_validations(extraction)
                except Exception as e:
                    self.logger.warning(f"⚠️ Validações extras falharam: {e}")

            # Calcular confiança baseada no número de campos encontrados
            fields_found = sum(1 for field_name in self.target_fields 
                             if getattr(extraction, field_name, "").strip())
            extraction.extraction_confidence = fields_found / len(self.target_fields)
            
            return extraction
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao extrair campos: {e}")
            return CoupaFieldExtraction(
                source_file=document.filename,
                extraction_method="error",
                extraction_confidence=0.0,
                nlp_libraries_used=[]
            )
    
    def process_all_pdfs(self) -> List[CoupaFieldExtraction]:
        """Processar todos os documentos suportados no diretório base."""
        start_time = time.time()
        
        self.logger.info("🚀 Iniciando extração avançada de campos do Coupa")
        self.logger.info(f"📚 Usando bibliotecas: {', '.join(self.available_libraries)}")
        
        # Encontrar arquivos suportados
        files = self.find_supported_files()
        
        if not files:
            self.logger.warning("⚠️ Nenhum arquivo PDF encontrado")
            return []
        
        extractions = []
        
        # Processar cada arquivo
        for i, file_path in enumerate(files):
            self.logger.info(f"📄 Processando {i+1}/{len(files)}: {file_path.name}")
            
            try:
                # Extrair texto
                document = self.extract_text_from_any(file_path)
                
                if document.error_message:
                    self.logger.error(f"❌ Erro ao extrair texto de {file_path.name}: {document.error_message}")
                    continue
                
                # Extrair campos usando NLP avançado
                extraction = self.extract_coupa_fields(document)
                extractions.append(extraction)
                
                self.logger.info(f"✅ Processado: {file_path.name} (confiança: {extraction.extraction_confidence:.2f})")
                
            except Exception as e:
                self.logger.error(f"❌ Erro ao processar {file_path.name}: {e}")
        
        total_time = time.time() - start_time
        self.logger.info(f"✅ Processamento concluído: {len(extractions)} documentos em {total_time:.2f}s")
        
        # Agregar por PO se habilitado
        try:
            if getattr(self.config, 'aggregate_by_po', False):
                from .po_aggregator import aggregate_extractions_by_po
                extractions = aggregate_extractions_by_po(
                    extractions, use_filename_clues=getattr(self.config, 'enable_filename_clues', True)
                )
        except Exception as e:
            self.logger.warning(f"⚠️ Agregação por PO falhou: {e}")
        
        return extractions

    # -------------------- Validations (optional) --------------------
    def _apply_validations(self, extraction: 'CoupaFieldExtraction') -> None:
        """Apply lightweight validations/normalizations where possible.

        Uses optional libs if available; falls back gracefully.
        """
        # Dates normalization
        for key in ("contract_start_date", "contract_end_date"):
            val = getattr(extraction, key, "")
            norm = self._validate_date(val)
            if norm is not None:
                setattr(extraction, key, norm)

        # Amounts coherence (best-effort)
        eur = getattr(extraction, "sow_value_eur", "")
        lc = getattr(extraction, "sow_value_lc", "")
        fx = getattr(extraction, "fx", "")
        _ = self._validate_amounts(eur, lc, fx)  # currently informational/log-only

    def _validate_date(self, v: str) -> str | None:
        v = (v or "").strip()
        if not v:
            return None
        try:
            import dateparser  # type: ignore
        except Exception:
            return None
        try:
            dt = dateparser.parse(v, languages=["en", "pt"])  # best-effort
            if dt:
                return dt.strftime("%Y-%m-%d")
        except Exception:
            return None
        return None

    def _validate_amounts(self, eur: str, lc: str, fx: str) -> bool:
        def to_num(s: str) -> float | None:
            s = (s or "").strip()
            if not s:
                return None
            numeric = parse_numeric_amount(s)
            return numeric
        eur_v = to_num(eur)
        lc_v = to_num(lc)
        fx_v = to_num(fx)
        if eur_v is not None and fx_v is not None and lc_v is not None:
            # Within 5% tolerance
            expected_lc = eur_v * fx_v
            ok = abs(expected_lc - lc_v) <= 0.05 * max(1.0, expected_lc)
            if not ok:
                self.logger.debug(f"Amounts coherence check failed: EUR*FX={expected_lc:.2f} vs LC={lc_v:.2f}")
            return ok
        return True
    
    def save_to_csv(self, extractions: List[CoupaFieldExtraction], output_file: str = None) -> str:
        """Salvar extrações em arquivo CSV."""
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"reports/advanced_coupa_fields_extraction_{timestamp}.csv"
        
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
            "Extraction Method",
            "NLP Libraries Used"
        ]
        
        # Escrever CSV (SOP: UTF-8 BOM, \n, QUOTE_MINIMAL)
        with open(output_path, 'w', newline='\n', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
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
                    extraction.extraction_method,
                    ', '.join(extraction.nlp_libraries_used or [])
                ]
                writer.writerow(row)
        
        self.logger.info(f"💾 CSV salvo em: {output_path}")
        return str(output_path)
    
    def generate_extraction_report(self, extractions: List[CoupaFieldExtraction]) -> str:
        """Gerar relatório da extração."""
        report_lines = []
        
        report_lines.append("# Relatório de Extração Avançada de Campos do Coupa")
        report_lines.append("=" * 70)
        report_lines.append("")
        
        # Resumo geral
        report_lines.append("## Resumo Geral")
        report_lines.append(f"- **Documentos processados**: {len(extractions)}")
        report_lines.append(f"- **Campos extraídos**: {len(self.target_fields)}")
        report_lines.append(f"- **Bibliotecas NLP utilizadas**: {', '.join(self.available_libraries)}")
        
        if extractions:
            avg_confidence = sum(e.extraction_confidence for e in extractions) / len(extractions)
            report_lines.append(f"- **Confiança média**: {avg_confidence:.2f}")
        
        report_lines.append("")
        
        # Estatísticas por campo
        report_lines.append("## Estatísticas por Campo")
        field_stats = {}
        
        for field_name in self.target_fields:
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
        
        # Estatísticas por biblioteca NLP
        report_lines.append("## Estatísticas por Biblioteca NLP")
        library_stats = {}
        
        for extraction in extractions:
            for lib in extraction.nlp_libraries_used or []:
                if lib not in library_stats:
                    library_stats[lib] = 0
                library_stats[lib] += 1
        
        for lib, count in library_stats.items():
            report_lines.append(f"- **{lib}**: {count} documentos")
        
        report_lines.append("")
        
        # Detalhes por documento
        report_lines.append("## Detalhes por Documento")
        for i, extraction in enumerate(extractions, 1):
            report_lines.append(f"### {i}. {extraction.source_file}")
            report_lines.append(f"- **Confiança**: {extraction.extraction_confidence:.2f}")
            report_lines.append(f"- **Método**: {extraction.extraction_method}")
            report_lines.append(f"- **Bibliotecas NLP**: {', '.join(extraction.nlp_libraries_used or [])}")
            
            # Mostrar campos encontrados
            found_fields = []
            for field_name in self.target_fields:
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
    """Função principal para extração avançada de campos."""
    print("📄 Extrator Avançado de Campos do Coupa com NLP")
    print("=" * 60)
    
    # Verificar dependências
    if not PDF_LIBRARIES_AVAILABLE:
        print("❌ Bibliotecas de PDF não disponíveis")
        print("Instale com: pip install PyPDF2 pdfplumber")
        return
    
    print(f"📚 Bibliotecas NLP disponíveis: {', '.join([lib for lib, available in NLP_LIBRARIES.items() if available])}")
    
    # Criar extrator
    extractor = AdvancedCoupaPDFFieldExtractor()
    
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
            for field_name in extractor.target_fields:
                count = sum(1 for e in extractions if getattr(e, field_name, "").strip())
                field_counts[field_name] = count
            
            print(f"\n🔍 Campos mais encontrados:")
            sorted_fields = sorted(field_counts.items(), key=lambda x: x[1], reverse=True)
            for field_name, count in sorted_fields[:10]:
                if count > 0:
                    print(f"  - {field_name.replace('_', ' ').title()}: {count} documentos")
        
    else:
        print(f"\n❌ Nenhum documento processado com sucesso")


if __name__ == "__main__":
    main()
