#!/usr/bin/env python3
"""
Extrator Melhorado com Dados de Treinamento
Integra padrões aprendidos da planilha real.
"""

import json
import os
from pathlib import Path
from typing import Dict, List
from .advanced_coupa_field_extractor import AdvancedCoupaPDFFieldExtractor, CoupaFieldExtraction
from .entity_parsing import has_numeric_content

class ImprovedCoupaFieldExtractor(AdvancedCoupaPDFFieldExtractor):
    """Extrator melhorado com padrões aprendidos dos dados reais."""
    
    def __init__(self, pdf_directory: str, training_file: str = None):
        super().__init__(pdf_directory)
        
        # Carregar dados de treinamento
        self.training_patterns = {}
        self.value_distributions = {}
        self.training_examples = []
        
        if training_file and Path(training_file).exists():
            self.load_training_data(training_file)
    
    def load_training_data(self, training_file: str):
        """Carregar dados de treinamento."""
        try:
            with open(training_file, 'r') as f:
                training_data = json.load(f)
            
            self.training_patterns = training_data.get('improved_patterns', {})
            self.value_distributions = training_data.get('value_distributions', {})
            self.training_examples = training_data.get('training_prompts', [])
            
            self.logger.info(f"✅ Dados de treinamento carregados: {len(self.training_patterns)} padrões")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar dados de treinamento: {e}")
    
    def extract_fields_with_trained_patterns(self, text: str) -> Dict[str, str]:
        """Extrair campos usando padrões aprendidos dos dados reais."""
        extracted = {}

        for field, patterns in self.training_patterns.items():
            for pattern in patterns:
                entities = self.entity_parser.extract_entities(
                    text,
                    field_hint=pattern,
                    target_field=field,
                )
                value = getattr(entities, field, None)
                if value and self._validate_value(field, value):
                    extracted[field] = value
                    break

        return extracted
    
    def _validate_value(self, field: str, value: str) -> bool:
        """Validar valor baseado nas distribuições dos dados reais."""
        if field not in self.value_distributions:
            return True  # Sem validação disponível
        
        distribution = self.value_distributions[field]
        
        # Validações específicas por campo
        if field == 'pwo_number':
            # PWO deve ser numérico
            return has_numeric_content(value)
        
        elif field == 'contract_type':
            # Tipos válidos baseados nos dados
            valid_types = ['SOW', 'CR', 'Subs Order form', 'Quote', 'Statement of Work']
            return any(valid_type.lower() in value.lower() for valid_type in valid_types)
        
        elif field == 'managed_by':
            # Valores válidos baseados nos dados
            valid_managers = ['SL', 'VMO', 'SAM', 'Business']
            return any(manager.lower() in value.lower() for manager in valid_managers)
        
        elif field == 'sow_currency':
            # Moedas válidas baseadas nos dados
            valid_currencies = ['EUR', 'USD', 'GBP', 'INR', 'BRL']
            return any(currency.lower() in value.lower() for currency in valid_currencies)
        
        elif field == 'sow_value_eur':
            # Valores monetários devem conter números
            return has_numeric_content(value)
        
        # Validação de comprimento baseada na distribuição
        if distribution.get('avg_length'):
            avg_length = distribution['avg_length']
            if len(value) > avg_length * 3:  # Muito longo
                return False
            if len(value) < 2:  # Muito curto
                return False
        
        return True
    
    def extract_coupa_fields_from_file(self, pdf_path: str) -> 'CoupaFieldExtraction':
        """Extrair campos com padrões treinados."""
        try:
            # Extrair texto do PDF
            pdf_doc = self.extract_text_from_pdf(Path(pdf_path))
            text = pdf_doc.text_content
            if not text:
                return self._create_empty_extraction(os.path.basename(pdf_path))
            
            # Usar método melhorado de extração
            return self._extract_fields_from_text_improved(text, os.path.basename(pdf_path))
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao extrair campos do arquivo {pdf_path}: {e}")
            return self._create_empty_extraction(os.path.basename(pdf_path))
    
    def _extract_fields_from_text_improved(self, text: str, filename: str) -> 'CoupaFieldExtraction':
        """Extrair campos usando técnicas melhoradas."""
        try:
            # Combinar resultados de diferentes técnicas
            all_extractions = {}
            libraries_used = []
            
            # 1. Padrões treinados (prioridade alta)
            if self.training_patterns:
                trained_results = self.extract_fields_with_trained_patterns(text)
                all_extractions.update(trained_results)
                libraries_used.append('trained_patterns')
            
            # 2. spaCy NER
            if 'spacy' in self.available_libraries:
                spacy_results = self.extract_fields_with_spacy(text)
                all_extractions.update(spacy_results)
                libraries_used.append('spacy')
            
            # 3. BERT NER
            if 'transformers' in self.available_libraries:
                bert_results = self.extract_fields_with_bert(text)
                all_extractions.update(bert_results)
                libraries_used.append('bert')
            
            # 4. LLM (Ollama) - OBRIGATÓRIO
            if 'ollama' not in self.available_libraries:
                raise Exception("❌ Ollama não está disponível. Sistema requer conectividade com Ollama para funcionar.")
            
            llm_results = self.extract_fields_with_llm(text)
            all_extractions.update(llm_results)
            libraries_used.append('ollama')
            
            # 5. Busca semântica
            if 'sentence_transformer' in self.available_libraries:
                semantic_results = self.extract_fields_with_semantic_search(text)
                all_extractions.update(semantic_results)
                libraries_used.append('semantic_search')
            
            # Calcular confiança melhorada
            confidence = self._calculate_improved_confidence(all_extractions)
            
            # Normalizar nomes dos campos (remover hífens)
            normalized_extractions = {}
            for key, value in all_extractions.items():
                normalized_key = key.replace('-', '_')
                normalized_extractions[normalized_key] = value
            
            return CoupaFieldExtraction(
                source_file=filename,
                extraction_method="improved_nlp_with_training",
                extraction_confidence=confidence,
                nlp_libraries_used=libraries_used,
                **normalized_extractions
            )
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao extrair campos do texto: {e}")
            return self._create_empty_extraction(filename)
    
    def _calculate_improved_confidence(self, all_extractions: Dict[str, str]) -> float:
        """Calcular confiança melhorada baseada nos dados de treinamento."""
        try:
            if not all_extractions:
                return 0.0
            
            # Contar campos com valores válidos
            valid_fields = len([v for v in all_extractions.values() if v and str(v).strip()])
            total_fields = len(self.target_fields)
            
            # Confiança baseada na proporção de campos extraídos
            base_confidence = valid_fields / total_fields if total_fields > 0 else 0.0
            
            # Bonus para campos críticos (baseado nos dados reais)
            critical_fields = ['contract_name', 'contract_type', 'sow_value_eur', 'pwo_number', 'managed_by']
            critical_found = len([f for f in critical_fields if f in all_extractions and all_extractions[f]])
            critical_bonus = critical_found * 0.15  # Bonus maior para campos críticos
            
            # Bonus para campos com padrões treinados
            trained_fields_found = len([f for f in all_extractions.keys() if f in self.training_patterns])
            training_bonus = trained_fields_found * 0.05
            
            # Bonus para valores validados
            validated_fields = 0
            for field, value in all_extractions.items():
                if self._validate_value(field, value):
                    validated_fields += 1
            
            validation_bonus = (validated_fields / len(all_extractions)) * 0.1 if all_extractions else 0
            
            total_confidence = base_confidence + critical_bonus + training_bonus + validation_bonus
            return min(total_confidence, 1.0)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao calcular confiança: {e}")
            return 0.0
    
    def _create_empty_extraction(self, filename: str) -> 'CoupaFieldExtraction':
        """Criar extração vazia."""
        return CoupaFieldExtraction(
            source_file=filename,
            extraction_method="no_text",
            extraction_confidence=0.0,
            nlp_libraries_used=[]
        )

def main():
    """Testar o extrator melhorado."""
    import os
    
    # Arquivos
    pdf_dir = '/Users/juliocezar/Dev/work/CoupaDownloads/src/data/P2'
    training_file = '/Users/juliocezar/Dev/work/CoupaDownloads/src/MyScript/embeddinggemma_feasibility/data/training_analysis.json'
    test_pdf = '/Users/juliocezar/Dev/work/CoupaDownloads/src/data/P2/PO15331069_PWO_-_90055_-_DDT_Support_Feb24_-_Jan25-v1.2_-_fully_signed.pdf'
    
    print("🧪 Testando Extrator Melhorado com Dados de Treinamento")
    print("=" * 60)
    
    # Criar extrator melhorado
    extractor = ImprovedCoupaFieldExtractor(pdf_dir, training_file)
    
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
        for field in fields_with_values[:10]:  # Mostrar primeiros 10
            print(f"  - {field}")
        if len(fields_with_values) > 10:
            print(f"  ... e mais {len(fields_with_values) - 10} campos")
    else:
        print("❌ Nenhum campo extraído com sucesso")
    
    print("\n🎉 Teste concluído!")

if __name__ == "__main__":
    main()
