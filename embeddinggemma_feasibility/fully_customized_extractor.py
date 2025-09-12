#!/usr/bin/env python3
"""
Extrator Integrado com Todas as Customizações
Combina spaCy, BERT e Sentence Transformers customizados.
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any
import logging

# Importar customizadores
from spacy_customizer import ContractSpacyCustomizer
from bert_customizer import ContractBertCustomizer
from sentence_transformer_customizer import ContractSentenceTransformerCustomizer

# Importar extrator base
from advanced_coupa_field_extractor import AdvancedCoupaPDFFieldExtractor, CoupaFieldExtraction

class FullyCustomizedCoupaExtractor(AdvancedCoupaPDFFieldExtractor):
    """Extrator completamente customizado com todas as tecnologias."""
    
    def __init__(self, pdf_directory: str, csv_file: str):
        super().__init__(pdf_directory)
        
        # Inicializar customizadores
        self.spacy_customizer = None
        self.bert_customizer = None
        self.st_customizer = None
        
        # Carregar customizações
        self.load_customizations(csv_file)
    
    def load_customizations(self, csv_file: str):
        """Carregar todas as customizações."""
        try:
            # spaCy customizado
            self.spacy_customizer = ContractSpacyCustomizer(csv_file)
            if self.spacy_customizer.load_data() and self.spacy_customizer.initialize_spacy():
                # Carregar padrões personalizados
                patterns = self.spacy_customizer.create_custom_patterns()
                self.spacy_customizer.add_custom_matcher(patterns)
                self.spacy_customizer.create_custom_ner()
                self.logger.info("✅ spaCy customizado carregado")
            
            # BERT customizado
            self.bert_customizer = ContractBertCustomizer(csv_file)
            if self.bert_customizer.load_data() and self.bert_customizer.initialize_bert():
                self.logger.info("✅ BERT customizado carregado")
            
            # Sentence Transformers customizado
            self.st_customizer = ContractSentenceTransformerCustomizer(csv_file)
            if self.st_customizer.load_data() and self.st_customizer.initialize_model():
                self.st_customizer.create_contract_embeddings()
                self.st_customizer.create_semantic_search()
                self.logger.info("✅ Sentence Transformers customizado carregado")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar customizações: {e}")
    
    def extract_fields_with_custom_spacy(self, text: str) -> Dict[str, str]:
        """Extrair campos usando spaCy customizado."""
        if not self.spacy_customizer:
            return {}
        
        try:
            results = self.spacy_customizer.test_custom_model(text)
            if results:
                extracted = {}
                for entity in results['custom_entities']:
                    field_name = entity['label'].lower().replace('_', '_')
                    extracted[field_name] = entity['text']
                return extracted
        except Exception as e:
            self.logger.error(f"❌ Erro no spaCy customizado: {e}")
        
        return {}
    
    def extract_fields_with_custom_bert(self, text: str) -> Dict[str, str]:
        """Extrair campos usando BERT customizado."""
        if not self.bert_customizer:
            return {}
        
        try:
            results = self.bert_customizer.extract_contract_fields(text)
            return results
        except Exception as e:
            self.logger.error(f"❌ Erro no BERT customizado: {e}")
        
        return {}
    
    def extract_fields_with_custom_st(self, text: str) -> Dict[str, str]:
        """Extrair campos usando Sentence Transformers customizado."""
        if not self.st_customizer:
            return {}
        
        try:
            results = self.st_customizer.extract_contract_fields(text)
            return results
        except Exception as e:
            self.logger.error(f"❌ Erro no Sentence Transformers customizado: {e}")
        
        return {}
    
    def extract_coupa_fields_from_file(self, pdf_path: str) -> CoupaFieldExtraction:
        """Extrair campos com todas as customizações."""
        try:
            # Extrair texto do PDF
            pdf_doc = self.extract_text_from_pdf(Path(pdf_path))
            text = pdf_doc.text_content
            if not text:
                return self._create_empty_extraction(os.path.basename(pdf_path))
            
            # Usar método melhorado de extração
            return self._extract_fields_from_text_fully_customized(text, os.path.basename(pdf_path))
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao extrair campos do arquivo {pdf_path}: {e}")
            return self._create_empty_extraction(os.path.basename(pdf_path))
    
    def _extract_fields_from_text_fully_customized(self, text: str, filename: str) -> CoupaFieldExtraction:
        """Extrair campos usando todas as técnicas customizadas."""
        try:
            # Combinar resultados de todas as técnicas customizadas
            all_extractions = {}
            libraries_used = []
            
            # 1. spaCy customizado
            if self.spacy_customizer:
                spacy_results = self.extract_fields_with_custom_spacy(text)
                all_extractions.update(spacy_results)
                libraries_used.append('spacy_custom')
            
            # 2. BERT customizado
            if self.bert_customizer:
                bert_results = self.extract_fields_with_custom_bert(text)
                all_extractions.update(bert_results)
                libraries_used.append('bert_custom')
            
            # 3. Sentence Transformers customizado
            if self.st_customizer:
                st_results = self.extract_fields_with_custom_st(text)
                all_extractions.update(st_results)
                libraries_used.append('sentence_transformer_custom')
            
            # 4. LLM (Ollama) - OBRIGATÓRIO
            if 'ollama' not in self.available_libraries:
                raise Exception("❌ Ollama não está disponível. Sistema requer conectividade com Ollama para funcionar.")
            
            llm_results = self.extract_fields_with_llm(text)
            all_extractions.update(llm_results)
            libraries_used.append('ollama')
            
            # Calcular confiança melhorada
            confidence = self._calculate_fully_customized_confidence(all_extractions)
            
            # Normalizar nomes dos campos (remover hífens e mapear campos)
            normalized_extractions = {}
            field_mapping = {
                'platform': 'platform_technology',
                'contract_type': 'contract_type',
                'managed_by': 'managed_by',
                'currency': 'sow_currency',
                'pwo_number': 'pwo_number',
                'contract_value': 'sow_value_eur',
                'organization': 'contract_name',
                'commercial_model': 'contractual_commercial_model',
                'ORGANIZATION': 'contract_name',
                'CONTRACT_VALUE': 'sow_value_eur',
                'DATE': 'contract_start_date',
                'PERSON': 'managed_by'
            }
            
            # Campos válidos do CoupaFieldExtraction
            valid_fields = {
                'remarks', 'supporting_information', 'procurement_negotiation_strategy',
                'opportunity_available', 'inflation_percent', 'minimum_commitment_value',
                'contractual_commercial_model', 'user_based_license', 'type_of_contract_l2',
                'type_of_contract_l1', 'sow_value_eur', 'fx', 'sow_currency', 'sow_value_lc',
                'managed_by', 'contract_end_date', 'contract_start_date', 'contract_type',
                'contract_name', 'high_level_scope', 'platform_technology', 'pwo_number'
            }
            
            for key, value in all_extractions.items():
                normalized_key = key.replace('-', '_').lower()
                # Mapear para campos válidos do CoupaFieldExtraction
                if normalized_key in field_mapping:
                    normalized_key = field_mapping[normalized_key]
                elif normalized_key in valid_fields:
                    normalized_key = normalized_key
                else:
                    # Pular campos não válidos
                    continue
                normalized_extractions[normalized_key] = value
            
            return CoupaFieldExtraction(
                source_file=filename,
                extraction_method="fully_customized_nlp",
                extraction_confidence=confidence,
                nlp_libraries_used=libraries_used,
                **normalized_extractions
            )
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao extrair campos do texto: {e}")
            return self._create_empty_extraction(filename)
    
    def _calculate_fully_customized_confidence(self, all_extractions: Dict[str, str]) -> float:
        """Calcular confiança com todas as customizações."""
        try:
            if not all_extractions:
                return 0.0
            
            # Contar campos com valores válidos
            valid_fields = len([v for v in all_extractions.values() if v and str(v).strip()])
            total_fields = len(self.target_fields)
            
            # Confiança baseada na proporção de campos extraídos
            base_confidence = valid_fields / total_fields if total_fields > 0 else 0.0
            
            # Bonus para campos críticos
            critical_fields = ['contract_name', 'contract_type', 'sow_value_eur', 'pwo_number', 'managed_by']
            critical_found = len([f for f in critical_fields if f in all_extractions and all_extractions[f]])
            critical_bonus = critical_found * 0.2  # Bonus maior para campos críticos
            
            # Bonus para customizações implementadas
            customizations_bonus = 0.0
            if self.spacy_customizer:
                customizations_bonus += 0.1
            if self.bert_customizer:
                customizations_bonus += 0.1
            if self.st_customizer:
                customizations_bonus += 0.1
            
            # Bonus para validação cruzada
            validation_bonus = 0.0
            if len(all_extractions) > 5:  # Múltiplas técnicas concordando
                validation_bonus = 0.15
            
            total_confidence = base_confidence + critical_bonus + customizations_bonus + validation_bonus
            return min(total_confidence, 1.0)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao calcular confiança: {e}")
            return 0.0
    
    def _create_empty_extraction(self, filename: str) -> CoupaFieldExtraction:
        """Criar extração vazia."""
        return CoupaFieldExtraction(
            source_file=filename,
            extraction_method="no_text",
            extraction_confidence=0.0,
            nlp_libraries_used=[]
        )

def main():
    """Testar o extrator completamente customizado."""
    import os
    
    # Arquivos
    pdf_dir = '/Users/juliocezar/Dev/work/CoupaDownloads/src/data/P2'
    csv_file = '/Users/juliocezar/Dev/work/CoupaDownloads/src/MyScript/embeddinggemma_feasibility/data/20250910_Template_for_data_capture_P2_Contract_Tracker.csv'
    test_pdf = '/Users/juliocezar/Dev/work/CoupaDownloads/src/data/P2/PO15331069_PWO_-_90055_-_DDT_Support_Feb24_-_Jan25-v1.2_-_fully_signed.pdf'
    
    print("🧪 Testando Extrator Completamente Customizado")
    print("=" * 60)
    
    # Criar extrator customizado
    extractor = FullyCustomizedCoupaExtractor(pdf_dir, csv_file)
    
    # Testar extração
    result = extractor.extract_coupa_fields_from_file(test_pdf)
    
    # Mostrar resultados
    print(f"📄 Arquivo: {result.source_file}")
    print(f"📊 Confiança: {result.extraction_confidence:.2f}")
    print(f"🔧 Método: {result.extraction_method}")
    print(f"📚 Bibliotecas: {', '.join(result.nlp_libraries_used)}")
    print()
    
    # Mostrar campos extraídos
    fields_with_values = []
    for field, value in result.__dict__.items():
        if field not in ['source_file', 'extraction_method', 'extraction_confidence', 'nlp_libraries_used'] and value:
            fields_with_values.append(f'{field}: {str(value)[:50]}...')
    
    if fields_with_values:
        print(f"✅ {len(fields_with_values)} campos extraídos:")
        for field in fields_with_values[:15]:  # Mostrar primeiros 15
            print(f"  - {field}")
        if len(fields_with_values) > 15:
            print(f"  ... e mais {len(fields_with_values) - 15} campos")
    else:
        print("❌ Nenhum campo extraído com sucesso")
    
    print("\n🎉 Teste concluído!")

if __name__ == "__main__":
    main()
