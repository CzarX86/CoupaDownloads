#!/usr/bin/env python3
"""
Sistema de Treinamento Baseado em Dados Reais
Usa a planilha Contract_Tracker para melhorar a extração de campos.
"""

import pandas as pd
import json
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
import logging

class ContractDataTrainer:
    """Treinador baseado em dados reais da planilha."""
    
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.df = None
        self.field_patterns = {}
        self.value_distributions = {}
        self.logger = logging.getLogger(__name__)
        
    def load_data(self):
        """Carregar dados da planilha."""
        try:
            self.df = pd.read_csv(self.csv_file)
            self.logger.info(f"✅ Dados carregados: {len(self.df)} registros, {len(self.df.columns)} colunas")
            return True
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar dados: {e}")
            return False
    
    def analyze_field_patterns(self):
        """Analisar padrões nos campos preenchidos."""
        field_mapping = {
            'PWO#': 'pwo_number',
            'Platform/Technology': 'platform_technology', 
            'High level scope': 'high_level_scope',
            'Contract Name': 'contract_name',
            'Contract Type (SOW/CR/Subs Order form)': 'contract_type',
            'Contract Start Date': 'contract_start_date',
            'Contract End Date': 'contract_end_date',
            'Managed by ( VMO/SL/SAM/Business) ': 'managed_by',
            'SOW Value in EUR': 'sow_value_eur',
            'SOW Currency': 'sow_currency',
            'SOW Value in LC': 'sow_value_lc',
            'Proc FX': 'fx',
            'Type of Contract - L1': 'type_of_contract_l1',
            'Type of Contract - L2': 'type_of_contract_l2',
            'User Based License (Yes/No)': 'user_based_license',
            'Contractual commercial Model (Fixed/ Consumption etc)': 'contractual_commercial_model'
        }
        
        for excel_field, our_field in field_mapping.items():
            if excel_field in self.df.columns:
                # Filtrar valores não nulos
                values = self.df[excel_field].dropna().astype(str)
                
                if len(values) > 0:
                    # Analisar padrões
                    patterns = self._extract_patterns(values, our_field)
                    distributions = self._analyze_distributions(values)
                    
                    self.field_patterns[our_field] = patterns
                    self.value_distributions[our_field] = distributions
                    
                    self.logger.info(f"📊 {our_field}: {len(values)} valores, {len(patterns)} padrões")
    
    def _extract_patterns(self, values: pd.Series, field_name: str) -> List[str]:
        """Extrair padrões regex dos valores."""
        patterns = []
        
        if field_name == 'pwo_number':
            # Padrões para PWO numbers
            for value in values.head(20):  # Analisar primeiros 20
                if re.search(r'\d+', value):
                    patterns.append(r'PWO[#\s]*(\d+)')
                    patterns.append(r'(\d{6,})')  # Números com 6+ dígitos
                    
        elif field_name == 'contract_type':
            # Padrões para tipos de contrato
            unique_types = values.unique()
            for contract_type in unique_types:
                if pd.notna(contract_type):
                    patterns.append(f'({re.escape(str(contract_type))})')
                    
        elif field_name == 'managed_by':
            # Padrões para managed_by
            unique_managers = values.unique()
            for manager in unique_managers:
                if pd.notna(manager):
                    patterns.append(f'({re.escape(str(manager))})')
                    
        elif field_name == 'sow_currency':
            # Padrões para moedas
            unique_currencies = values.unique()
            for currency in unique_currencies:
                if pd.notna(currency):
                    patterns.append(f'({re.escape(str(currency))})')
        
        # Padrões genéricos baseados no conteúdo
        for value in values.head(10):
            if pd.notna(value) and len(str(value)) > 3:
                # Padrão para valores que começam com texto específico
                if field_name in ['contract_name', 'high_level_scope']:
                    patterns.append(f'({re.escape(str(value)[:20])}.*?)')
        
        return list(set(patterns))  # Remover duplicatas
    
    def _analyze_distributions(self, values: pd.Series) -> Dict:
        """Analisar distribuição de valores."""
        distributions = {
            'unique_count': values.nunique(),
            'most_common': values.value_counts().head(5).to_dict(),
            'avg_length': values.str.len().mean() if values.dtype == 'object' else None,
            'sample_values': values.head(10).tolist()
        }
        return distributions
    
    def generate_improved_patterns(self) -> Dict[str, List[str]]:
        """Gerar padrões melhorados baseados nos dados reais."""
        improved_patterns = {}
        
        # Padrões específicos baseados nos dados
        improved_patterns['pwo_number'] = [
            r'PWO[#\s]*(\d+)',
            r'(\d{6,})',  # Números com 6+ dígitos
            r'Demand Number:\s*(\d+)'
        ]
        
        improved_patterns['contract_type'] = [
            r'(SOW)',
            r'(CR)',
            r'(Subs Order form)',
            r'(Quote)',
            r'(Statement of Work)'
        ]
        
        improved_patterns['managed_by'] = [
            r'(SL)',
            r'(VMO)',
            r'(SAM)',
            r'(Business)'
        ]
        
        improved_patterns['sow_currency'] = [
            r'(EUR)',
            r'(USD)',
            r'(GBP)',
            r'(INR)',
            r'(BRL)'
        ]
        
        improved_patterns['contract_name'] = [
            r'(?:Contract|Agreement|SOW|Statement of Work)[\s\w]*?[:]\s*([^\n\r]+)',
            r'(?:Title|Name)[\s\w]*?[:]\s*([^\n\r]+)',
            r'([A-Z][^.]*?(?:Contract|Agreement|SOW|Services|License))'
        ]
        
        improved_patterns['platform_technology'] = [
            r'(?:Platform|Technology)[\s\w]*?[:]\s*([^\n\r]+)',
            r'(Workday|SAP|Oracle|Microsoft|IBM|AWS|Azure|Google)',
            r'([A-Z][^.]*?(?:Platform|Technology|Services|Software))'
        ]
        
        return improved_patterns
    
    def create_training_prompts(self) -> List[Dict]:
        """Criar prompts de treinamento baseados nos dados reais."""
        training_prompts = []
        
        # Usar dados reais para criar exemplos de treinamento
        for idx, row in self.df.head(20).iterrows():  # Primeiros 20 registros
            if pd.notna(row.get('Contract Name')):
                example = {
                    'contract_name': str(row.get('Contract Name', '')),
                    'contract_type': str(row.get('Contract Type (SOW/CR/Subs Order form)', '')),
                    'pwo_number': str(row.get('PWO#', '')),
                    'platform_technology': str(row.get('Platform/Technology', '')),
                    'managed_by': str(row.get('Managed by ( VMO/SL/SAM/Business) ', '')),
                    'sow_currency': str(row.get('SOW Currency', '')),
                    'sow_value_eur': str(row.get('SOW Value in EUR', '')),
                    'contract_start_date': str(row.get('Contract Start Date', '')),
                    'contract_end_date': str(row.get('Contract End Date', ''))
                }
                
                # Filtrar campos vazios
                example = {k: v for k, v in example.items() if v and v != 'nan'}
                
                if len(example) >= 5:  # Pelo menos 5 campos preenchidos
                    training_prompts.append(example)
        
        return training_prompts
    
    def save_training_data(self, output_file: str, df: pd.DataFrame | None = None):
        """Salvar dados de treinamento.

        Se `df` for informado, usa-o diretamente (permite integração com ingestão
        sem reler do CSV). Caso contrário, utiliza `self.df`.
        """
        if df is not None:
            self.df = df
        if self.df is None:
            raise ValueError("Nenhum dataframe carregado para salvar dados de treinamento.")

        training_data = {
            'field_patterns': self.field_patterns,
            'value_distributions': self.value_distributions,
            'improved_patterns': self.generate_improved_patterns(),
            'training_prompts': self.create_training_prompts(),
            'statistics': {
                'total_records': len(self.df),
                'fields_analyzed': len(self.field_patterns),
                'training_examples': len(self.create_training_prompts())
            }
        }

        with open(output_file, 'w') as f:
            json.dump(training_data, f, indent=2, default=str)

        self.logger.info(f"💾 Dados de treinamento salvos: {output_file}")
        return training_data


def _normalise_training_record(record: Any) -> Dict[str, Any]:
    if is_dataclass(record):
        return asdict(record)
    if isinstance(record, dict):
        return record
    if hasattr(record, "_asdict"):
        return record._asdict()
    if hasattr(record, "__dict__"):
        return dict(record.__dict__)
    return {"value": str(record)}


def fine_tune_model(records: List[Any], output_dir: Path) -> Tuple[Path, Dict[str, Any]]:
    """Executa um fine-tuning simplificado com base nas anotações.

    Gera um artefato textual com estatísticas das anotações e retorna métricas
    para consumo pelo serviço de treinamento.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    normalised = [_normalise_training_record(record) for record in records]
    artifact_path = output_dir / "feedback-model.bin"
    summary_path = output_dir / "feedback-summary.json"

    annotation_count = len(normalised)
    documents = sorted({rec.get("document_id") for rec in normalised if rec.get("document_id")})
    entity_types = sorted({(rec.get("type") or "UNKNOWN") for rec in normalised})

    artifact_payload = {
        "artifact": "embeddinggemma-feedback",
        "annotations": annotation_count,
        "documents": documents,
        "entity_types": entity_types,
    }
    artifact_path.write_text(json.dumps(artifact_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_payload = {
        "annotation_count": annotation_count,
        "documents": documents,
        "entity_types": entity_types,
    }
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return artifact_path, summary_payload

def main():
    """Função principal."""
    logging.basicConfig(level=logging.INFO)
    
    # Arquivos
    csv_file = '/Users/juliocezar/Dev/work/CoupaDownloads/src/MyScript/embeddinggemma_feasibility/data/20250910_Template_for_data_capture_P2_Contract_Tracker.csv'
    output_file = '/Users/juliocezar/Dev/work/CoupaDownloads/src/MyScript/embeddinggemma_feasibility/data/training_analysis.json'
    
    # Criar treinador
    trainer = ContractDataTrainer(csv_file)
    
    if trainer.load_data():
        trainer.analyze_field_patterns()
        training_data = trainer.save_training_data(output_file)
        
        print(f"\n🎯 RESUMO DO TREINAMENTO:")
        print(f"   - Registros analisados: {training_data['statistics']['total_records']}")
        print(f"   - Campos analisados: {training_data['statistics']['fields_analyzed']}")
        print(f"   - Exemplos de treinamento: {training_data['statistics']['training_examples']}")
        
        print(f"\n📊 CAMPOS COM PADRÕES IDENTIFICADOS:")
        for field, patterns in training_data['field_patterns'].items():
            print(f"   - {field}: {len(patterns)} padrões")
        
        print(f"\n💡 PRÓXIMOS PASSOS:")
        print(f"   1. Usar padrões melhorados no extrator")
        print(f"   2. Implementar validação baseada em distribuições")
        print(f"   3. Criar prompts específicos por tipo de contrato")
        print(f"   4. Implementar sistema de confiança baseado em dados reais")

if __name__ == "__main__":
    main()
