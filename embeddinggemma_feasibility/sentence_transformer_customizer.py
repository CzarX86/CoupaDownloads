#!/usr/bin/env python3
"""
Sistema de Customização Sentence Transformers para Contratos
Cria embeddings personalizados para termos específicos de contratos.
"""

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
import json
from pathlib import Path
import logging
import re
from sklearn.metrics.pairwise import cosine_similarity

class ContractSentenceTransformerCustomizer:
    """Customizador Sentence Transformers para contratos."""
    
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.df = None
        self.model = None
        self.contract_embeddings = {}
        self.logger = logging.getLogger(__name__)
        
        # Termos específicos de contratos
        self.contract_terms = {
            'contract_types': ['SOW', 'CR', 'Subs Order form', 'Quote', 'Statement of Work'],
            'managed_by': ['SL', 'VMO', 'SAM', 'Business'],
            'currencies': ['EUR', 'USD', 'GBP', 'INR', 'BRL'],
            'commercial_models': ['Fixed', 'Consumption', 'Subscription', 'Pay-per-use'],
            'platforms': ['Workday', 'SAP', 'Oracle', 'Microsoft', 'IBM', 'AWS', 'Azure'],
            'contract_levels': ['L1', 'L2', 'L3', 'Level 1', 'Level 2', 'Level 3']
        }
    
    def load_data(self):
        """Carregar dados da planilha."""
        try:
            self.df = pd.read_csv(self.csv_file)
            self.logger.info(f"✅ Dados carregados: {len(self.df)} registros")
            return True
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar dados: {e}")
            return False
    
    def initialize_model(self):
        """Inicializar modelo Sentence Transformers."""
        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.logger.info("✅ Sentence Transformers inicializado")
            return True
        except Exception as e:
            self.logger.error(f"❌ Erro ao inicializar modelo: {e}")
            return False
    
    def create_contract_embeddings(self):
        """Criar embeddings para termos específicos de contratos."""
        try:
            # Extrair termos únicos dos dados
            unique_terms = {}
            
            # Contract Types
            contract_types = self.df['Contract Type (SOW/CR/Subs Order form)'].dropna().unique()
            unique_terms['contract_types'] = [str(ct) for ct in contract_types if pd.notna(ct)]
            
            # Managed By
            managed_by = self.df['Managed by ( VMO/SL/SAM/Business) '].dropna().unique()
            unique_terms['managed_by'] = [str(mb) for mb in managed_by if pd.notna(mb)]
            
            # Currencies
            currencies = self.df['SOW Currency'].dropna().unique()
            unique_terms['currencies'] = [str(c) for c in currencies if pd.notna(c)]
            
            # Platforms
            platforms = self.df['Platform/Technology'].dropna().unique()
            unique_terms['platforms'] = [str(p) for p in platforms if pd.notna(p)]
            
            # Commercial Models
            commercial_models = self.df['Contractual commercial Model (Fixed/ Consumption etc)'].dropna().unique()
            unique_terms['commercial_models'] = [str(cm) for cm in commercial_models if pd.notna(cm)]
            
            # Contract Levels
            l1_types = self.df['Type of Contract - L1'].dropna().unique()
            l2_types = self.df['Type of Contract - L2'].dropna().unique()
            unique_terms['contract_levels'] = list(set([str(l) for l in l1_types if pd.notna(l)] + [str(l) for l in l2_types if pd.notna(l)]))
            
            # Criar embeddings para cada categoria
            for category, terms in unique_terms.items():
                if terms:
                    embeddings = self.model.encode(terms)
                    self.contract_embeddings[category] = {
                        'terms': terms,
                        'embeddings': embeddings
                    }
                    self.logger.info(f"✅ {len(terms)} embeddings criados para {category}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao criar embeddings: {e}")
            return False
    
    def create_training_data(self, pairs_jsonl: str | None = None):
        """Criar dados de treinamento para fine-tuning.

        Se `pairs_jsonl` for informado, carrega pares pré-gerados (JSONL com
        chaves text1, text2, label). Caso contrário, deriva pares dos
        embeddings criados a partir do CSV carregado.
        """
        training_examples = []
        # Caminho alternativo: carregar pares prontos
        if pairs_jsonl:
            try:
                from sentence_transformers import InputExample
                import json
                with open(pairs_jsonl, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            obj = json.loads(line)
                        except Exception:
                            continue
                        t1 = str(obj.get('text1', '')).strip()
                        t2 = str(obj.get('text2', '')).strip()
                        if not t1 or not t2:
                            continue
                        label = float(obj.get('label', 0.0))
                        training_examples.append(InputExample(texts=[t1, t2], label=label))
                self.logger.info(f"✅ {len(training_examples)} exemplos carregados de pares_jsonl")
                return training_examples
            except Exception as e:
                self.logger.error(f"❌ Erro ao carregar pairs_jsonl: {e}")
                # Cai para o modo derivado se falhar
        
        # Criar pares positivos (termos similares)
        for category, data in self.contract_embeddings.items():
            terms = data['terms']
            embeddings = data['embeddings']
            
            # Calcular similaridade entre termos
            similarity_matrix = cosine_similarity(embeddings)
            
            for i, term1 in enumerate(terms):
                for j, term2 in enumerate(terms):
                    if i != j and similarity_matrix[i][j] > 0.7:  # Similaridade alta
                        training_examples.append(
                            InputExample(texts=[term1, term2], label=1.0)
                        )
        
        # Criar pares negativos (termos diferentes)
        categories = list(self.contract_embeddings.keys())
        for i, cat1 in enumerate(categories):
            for j, cat2 in enumerate(categories):
                if i != j:
                    terms1 = self.contract_embeddings[cat1]['terms']
                    terms2 = self.contract_embeddings[cat2]['terms']
                    
                    # Criar alguns pares negativos
                    for term1 in terms1[:5]:  # Limitar para não criar muitos
                        for term2 in terms2[:5]:
                            training_examples.append(
                                InputExample(texts=[term1, term2], label=0.0)
                            )
        
        self.logger.info(f"✅ {len(training_examples)} exemplos de treinamento criados")
        return training_examples
    
    def fine_tune_model(self, training_examples, output_dir: str):
        """Fine-tuning do modelo."""
        try:
            # Criar DataLoader
            train_dataloader = DataLoader(training_examples, shuffle=True, batch_size=16)
            
            # Definir loss function
            train_loss = losses.CosineSimilarityLoss(self.model)
            
            # Configurações de treinamento
            num_epochs = 3
            
            # Treinar modelo
            self.model.fit(
                train_objectives=[(train_dataloader, train_loss)],
                epochs=num_epochs,
                warmup_steps=100,
                output_path=output_dir
            )
            
            self.logger.info(f"✅ Modelo fine-tuned salvo em: {output_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro no fine-tuning: {e}")
            return False
    
    def create_semantic_search(self):
        """Criar sistema de busca semântica."""
        try:
            # Criar índice de busca
            search_index = {}
            
            for category, data in self.contract_embeddings.items():
                for term, embedding in zip(data['terms'], data['embeddings']):
                    search_index[term] = {
                        'category': category,
                        'embedding': embedding
                    }
            
            self.search_index = search_index
            self.logger.info(f"✅ Índice de busca criado com {len(search_index)} termos")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao criar índice de busca: {e}")
            return False
    
    def semantic_search(self, query: str, top_k: int = 5):
        """Busca semântica."""
        try:
            if not hasattr(self, 'search_index'):
                self.create_semantic_search()
            
            # Embedding da query
            query_embedding = self.model.encode([query])
            
            # Calcular similaridade
            similarities = []
            for term, data in self.search_index.items():
                similarity = cosine_similarity(
                    query_embedding, 
                    data['embedding'].reshape(1, -1)
                )[0][0]
                similarities.append({
                    'term': term,
                    'category': data['category'],
                    'similarity': similarity
                })
            
            # Ordenar por similaridade
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            return similarities[:top_k]
            
        except Exception as e:
            self.logger.error(f"❌ Erro na busca semântica: {e}")
            return []
    
    def extract_contract_fields(self, text: str):
        """Extrair campos de contrato usando busca semântica."""
        try:
            results = {}
            
            # Buscar para cada categoria
            for category in self.contract_embeddings.keys():
                search_results = self.semantic_search(text, top_k=3)
                
                # Filtrar resultados da categoria atual
                category_results = [r for r in search_results if r['category'] == category]
                
                if category_results and category_results[0]['similarity'] > 0.7:
                    results[category] = {
                        'value': category_results[0]['term'],
                        'confidence': category_results[0]['similarity']
                    }
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Erro na extração de campos: {e}")
            return {}
    
    def save_custom_model(self, output_dir: str):
        """Salvar modelo customizado."""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Salvar modelo
            self.model.save(output_path)
            
            # Salvar embeddings
            embeddings_data = {}
            for category, data in self.contract_embeddings.items():
                embeddings_data[category] = {
                    'terms': data['terms'],
                    'embeddings': data['embeddings'].tolist()
                }
            
            with open(output_path / 'contract_embeddings.json', 'w') as f:
                json.dump(embeddings_data, f, indent=2)
            
            # Salvar configurações
            config = {
                'contract_terms': self.contract_terms,
                'model_name': 'all-MiniLM-L6-v2',
                'embedding_dimension': 384
            }
            
            with open(output_path / 'contract_config.json', 'w') as f:
                json.dump(config, f, indent=2)
            
            self.logger.info(f"✅ Modelo Sentence Transformers customizado salvo em: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar modelo: {e}")
            return False

def main():
    """Função principal."""
    logging.basicConfig(level=logging.INFO)
    
    # Arquivos
    csv_file = '/Users/juliocezar/Dev/work/CoupaDownloads/src/MyScript/embeddinggemma_feasibility/data/20250910_Template_for_data_capture_P2_Contract_Tracker.csv'
    output_dir = '/Users/juliocezar/Dev/work/CoupaDownloads/src/MyScript/embeddinggemma_feasibility/models/sentence_transformer_custom'
    
    # Criar customizador
    customizer = ContractSentenceTransformerCustomizer(csv_file)
    
    if customizer.load_data() and customizer.initialize_model():
        # Criar embeddings de contratos
        customizer.create_contract_embeddings()
        
        # Criar dados de treinamento
        training_examples = customizer.create_training_data()
        
        if training_examples:
            # Fine-tuning
            customizer.fine_tune_model(training_examples, output_dir)
        
        # Criar sistema de busca semântica
        customizer.create_semantic_search()
        
        # Testar busca semântica
        test_queries = [
            "SOW contract",
            "SL management",
            "EUR currency",
            "Workday platform"
        ]
        
        print(f"\\n🧪 TESTE DE BUSCA SEMÂNTICA:")
        for query in test_queries:
            results = customizer.semantic_search(query, top_k=3)
            print(f"\\n   Query: '{query}'")
            for result in results:
                print(f"     - {result['term']} ({result['category']}): {result['similarity']:.3f}")
        
        # Testar extração de campos
        test_text = "This is a SOW contract managed by SL for Workday platform in EUR currency"
        field_results = customizer.extract_contract_fields(test_text)
        
        print(f"\\n🧪 TESTE DE EXTRAÇÃO DE CAMPOS:")
        for field, data in field_results.items():
            print(f"     - {field}: {data['value']} (confiança: {data['confidence']:.3f})")
        
        # Salvar modelo
        customizer.save_custom_model(output_dir)
        
        print(f"\\n✅ Sentence Transformers customizado com sucesso!")

if __name__ == "__main__":
    main()
