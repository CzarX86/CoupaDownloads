"""
Sistema de Rastreamento de Progresso com Tempo Restante Inteligente
Implementa métricas detalhadas de progresso com estimativas adaptativas baseadas em performance real
"""

import time
import statistics
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import math

# Importação condicional
try:
    from logging_advanced import get_logger
except ImportError:
    pass


@dataclass
class PerformanceMetrics:
    """Métricas de performance para análise adaptativa."""
    item_times: deque = field(default_factory=lambda: deque(maxlen=20))  # Últimos 20 itens
    phase_times: deque = field(default_factory=lambda: deque(maxlen=10))  # Últimas 10 fases
    success_rate_history: deque = field(default_factory=lambda: deque(maxlen=15))  # Histórico de sucesso
    throughput_history: deque = field(default_factory=lambda: deque(maxlen=10))  # Histórico de throughput
    
    # Métricas calculadas
    average_time_per_item: float = 0.0
    median_time_per_item: float = 0.0
    std_deviation: float = 0.0
    trend_factor: float = 1.0  # Fator de tendência (aceleração/desaceleração)
    confidence_level: float = 0.5  # Nível de confiança na estimativa
    
    def update_item_time(self, item_time: float):
        """Atualiza tempo de processamento de um item."""
        self.item_times.append(item_time)
        self._recalculate_metrics()
    
    def update_phase_time(self, phase_time: float):
        """Atualiza tempo de uma fase completa."""
        self.phase_times.append(phase_time)
    
    def update_success_rate(self, success_rate: float):
        """Atualiza taxa de sucesso."""
        self.success_rate_history.append(success_rate)
    
    def update_throughput(self, throughput: float):
        """Atualiza throughput (itens por segundo)."""
        self.throughput_history.append(throughput)
    
    def _recalculate_metrics(self):
        """Recalcula métricas baseadas nos dados históricos."""
        if len(self.item_times) < 2:
            return
        
        times = list(self.item_times)
        self.average_time_per_item = statistics.mean(times)
        self.median_time_per_item = statistics.median(times)
        self.std_deviation = statistics.stdev(times) if len(times) > 1 else 0.0
        
        # Calcular tendência (aceleração/desaceleração)
        if len(times) >= 5:
            recent_avg = statistics.mean(times[-5:])  # Últimos 5
            older_avg = statistics.mean(times[-10:-5]) if len(times) >= 10 else statistics.mean(times[:-5]) if len(times) > 5 else recent_avg
            self.trend_factor = recent_avg / older_avg if older_avg > 0 else 1.0
        
        # Calcular nível de confiança baseado na consistência
        if self.std_deviation > 0:
            cv = self.std_deviation / self.average_time_per_item  # Coeficiente de variação
            self.confidence_level = max(0.1, min(0.95, 1.0 - cv))  # Confiança inversamente proporcional à variação


@dataclass
class ProgressMetrics:
    """Métricas de progresso para uma operação."""
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    start_time: Optional[float] = None
    last_update_time: Optional[float] = None
    current_phase: str = ""
    
    # Métricas de performance
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    
    # Estimativas inteligentes
    estimated_remaining_time: float = 0.0
    estimated_remaining_time_conservative: float = 0.0  # Estimativa conservadora
    estimated_remaining_time_optimistic: float = 0.0     # Estimativa otimista
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = time.time()
        if self.last_update_time is None:
            self.last_update_time = self.start_time


class IntelligentProgressTracker:
    """Rastreador de progresso com estimativas inteligentes baseadas em performance real."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.logger = get_logger("intelligent_progress_tracker")
        self.metrics = ProgressMetrics()
        self.phase_start_times: Dict[str, float] = {}
        self.phase_performance: Dict[str, PerformanceMetrics] = {}
        
        # Configurações para estimativas
        self.confidence_threshold = 0.7  # Limiar de confiança para usar estimativas
        self.min_samples_for_prediction = 3  # Mínimo de amostras para fazer predições
        
    def start_operation(self, total_items: int, phase: str = "inicialização"):
        """Inicia uma nova operação."""
        self.metrics = ProgressMetrics(
            total_items=total_items,
            start_time=time.time(),
            current_phase=phase
        )
        self.phase_start_times[phase] = time.time()
        self.phase_performance[phase] = PerformanceMetrics()
        
        self.logger.info("Operação iniciada", 
                        operation=self.operation_name,
                        total_items=total_items,
                        phase=phase)
    
    def update_phase(self, phase: str):
        """Atualiza a fase atual da operação."""
        if self.metrics.current_phase:
            phase_duration = time.time() - self.phase_start_times.get(self.metrics.current_phase, time.time())
            
            # Atualizar métricas da fase anterior
            if self.metrics.current_phase in self.phase_performance:
                self.phase_performance[self.metrics.current_phase].update_phase_time(phase_duration)
            
            self.logger.info("Fase concluída", 
                           phase=self.metrics.current_phase,
                           duration=phase_duration)
        
        self.metrics.current_phase = phase
        self.phase_start_times[phase] = time.time()
        
        # Inicializar métricas da nova fase se não existir
        if phase not in self.phase_performance:
            self.phase_performance[phase] = PerformanceMetrics()
        
        self.logger.info("Nova fase iniciada", phase=phase)
    
    def update_progress(self, processed: int, successful: int = None, failed: int = None, item_duration: float = None):
        """Atualiza o progresso da operação com análise inteligente."""
        current_time = time.time()
        
        # Atualizar métricas básicas
        self.metrics.processed_items = processed
        if successful is not None:
            self.metrics.successful_items = successful
        if failed is not None:
            self.metrics.failed_items = failed
        
        # Atualizar métricas de performance se item_duration fornecido
        if item_duration is not None:
            self.metrics.performance.update_item_time(item_duration)
            
            # Atualizar métricas da fase atual
            if self.metrics.current_phase in self.phase_performance:
                self.phase_performance[self.metrics.current_phase].update_item_time(item_duration)
        
        # Calcular estimativas inteligentes
        self._calculate_intelligent_estimates()
        
        # Calcular percentual de progresso
        progress_percent = (processed / self.metrics.total_items) * 100 if self.metrics.total_items > 0 else 0
        
        # Calcular tempo decorrido
        elapsed_time = current_time - self.metrics.start_time
        
        # Calcular throughput atual
        current_throughput = processed / elapsed_time if elapsed_time > 0 else 0
        self.metrics.performance.update_throughput(current_throughput)
        
        # Calcular taxa de sucesso
        success_rate = (self.metrics.successful_items / processed * 100) if processed > 0 else 0
        self.metrics.performance.update_success_rate(success_rate)
        
        # Log de progresso detalhado com estimativas inteligentes
        self.logger.info("Progresso atualizado",
                        operation=self.operation_name,
                        processed=processed,
                        total=self.metrics.total_items,
                        progress_percent=f"{progress_percent:.1f}%",
                        successful=self.metrics.successful_items,
                        failed=self.metrics.failed_items,
                        elapsed_time=f"{elapsed_time:.1f}s",
                        estimated_remaining=f"{self.metrics.estimated_remaining_time:.1f}s",
                        estimated_remaining_conservative=f"{self.metrics.estimated_remaining_time_conservative:.1f}s",
                        estimated_remaining_optimistic=f"{self.metrics.estimated_remaining_time_optimistic:.1f}s",
                        confidence_level=f"{self.metrics.performance.confidence_level:.2f}",
                        trend_factor=f"{self.metrics.performance.trend_factor:.2f}",
                        average_time_per_item=f"{self.metrics.performance.average_time_per_item:.2f}s",
                        current_throughput=f"{current_throughput:.2f} items/s",
                        current_phase=self.metrics.current_phase)
        
        self.metrics.last_update_time = current_time
    
    def _calculate_intelligent_estimates(self):
        """Calcula estimativas inteligentes baseadas em performance real."""
        remaining_items = self.metrics.total_items - self.metrics.processed_items
        
        if remaining_items <= 0:
            self.metrics.estimated_remaining_time = 0
            self.metrics.estimated_remaining_time_conservative = 0
            self.metrics.estimated_remaining_time_optimistic = 0
            return
        
        # Usar métricas da fase atual se disponível, senão usar métricas gerais
        current_performance = self.phase_performance.get(self.metrics.current_phase, self.metrics.performance)
        
        if len(current_performance.item_times) < self.min_samples_for_prediction:
            # Não há dados suficientes, usar estimativa simples
            if self.metrics.performance.average_time_per_item > 0:
                base_time = self.metrics.performance.average_time_per_item
            else:
                # Estimativa baseada no throughput atual
                elapsed = time.time() - self.metrics.start_time
                base_time = elapsed / self.metrics.processed_items if self.metrics.processed_items > 0 else 1.0
            
            self.metrics.estimated_remaining_time = remaining_items * base_time
            self.metrics.estimated_remaining_time_conservative = remaining_items * base_time * 1.5
            self.metrics.estimated_remaining_time_optimistic = remaining_items * base_time * 0.7
            return
        
        # Estimativa baseada na mediana (mais robusta que média)
        base_time = current_performance.median_time_per_item
        
        # Aplicar fator de tendência
        trend_adjusted_time = base_time * current_performance.trend_factor
        
        # Estimativa principal (mediana ajustada pela tendência)
        self.metrics.estimated_remaining_time = remaining_items * trend_adjusted_time
        
        # Estimativa conservadora (inclui variação e margem de segurança)
        conservative_factor = 1.0 + (current_performance.std_deviation / base_time) if base_time > 0 else 1.5
        self.metrics.estimated_remaining_time_conservative = remaining_items * trend_adjusted_time * conservative_factor
        
        # Estimativa otimista (assume melhoria de performance)
        optimistic_factor = max(0.5, 1.0 - (current_performance.std_deviation / base_time * 0.5)) if base_time > 0 else 0.7
        self.metrics.estimated_remaining_time_optimistic = remaining_items * trend_adjusted_time * optimistic_factor
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Retorna um resumo detalhado do progresso atual."""
        current_time = time.time()
        elapsed_time = current_time - self.metrics.start_time
        
        # Calcular taxa de sucesso
        success_rate = (self.metrics.successful_items / self.metrics.processed_items * 100) if self.metrics.processed_items > 0 else 0
        
        # Calcular throughput atual e médio
        current_throughput = self.metrics.processed_items / elapsed_time if elapsed_time > 0 else 0
        avg_throughput = statistics.mean(self.metrics.performance.throughput_history) if len(self.metrics.performance.throughput_history) > 0 else current_throughput
        
        # Determinar estimativa recomendada baseada na confiança
        recommended_estimate = self.metrics.estimated_remaining_time
        if self.metrics.performance.confidence_level < self.confidence_threshold:
            # Baixa confiança, usar estimativa conservadora
            recommended_estimate = self.metrics.estimated_remaining_time_conservative
        
        return {
            'operation': self.operation_name,
            'phase': self.metrics.current_phase,
            'progress': {
                'processed': self.metrics.processed_items,
                'total': self.metrics.total_items,
                'percent': (self.metrics.processed_items / self.metrics.total_items * 100) if self.metrics.total_items > 0 else 0,
                'successful': self.metrics.successful_items,
                'failed': self.metrics.failed_items,
                'success_rate': success_rate
            },
            'timing': {
                'elapsed_time': elapsed_time,
                'estimated_remaining': recommended_estimate,
                'estimated_remaining_conservative': self.metrics.estimated_remaining_time_conservative,
                'estimated_remaining_optimistic': self.metrics.estimated_remaining_time_optimistic,
                'estimated_total': elapsed_time + recommended_estimate,
                'average_time_per_item': self.metrics.performance.average_time_per_item,
                'median_time_per_item': self.metrics.performance.median_time_per_item,
                'current_throughput': current_throughput,
                'average_throughput': avg_throughput
            },
            'intelligence': {
                'confidence_level': self.metrics.performance.confidence_level,
                'trend_factor': self.metrics.performance.trend_factor,
                'std_deviation': self.metrics.performance.std_deviation,
                'samples_count': len(self.metrics.performance.item_times),
                'prediction_quality': 'high' if self.metrics.performance.confidence_level > 0.8 else 'medium' if self.metrics.performance.confidence_level > 0.5 else 'low'
            },
            'formatted': {
                'elapsed': self._format_duration(elapsed_time),
                'remaining': self._format_duration(recommended_estimate),
                'remaining_conservative': self._format_duration(self.metrics.estimated_remaining_time_conservative),
                'remaining_optimistic': self._format_duration(self.metrics.estimated_remaining_time_optimistic),
                'eta': self._format_eta(current_time + recommended_estimate)
            }
        }
    
    def _format_duration(self, seconds: float) -> str:
        """Formata duração em formato legível."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def _format_eta(self, eta_timestamp: float) -> str:
        """Formata ETA em formato legível."""
        eta_datetime = datetime.fromtimestamp(eta_timestamp)
        return eta_datetime.strftime("%H:%M:%S")
    
    def finish_operation(self):
        """Finaliza a operação e gera relatório final."""
        current_time = time.time()
        total_duration = current_time - self.metrics.start_time
        
        # Calcular métricas finais
        success_rate = (self.metrics.successful_items / self.metrics.processed_items * 100) if self.metrics.processed_items > 0 else 0
        final_throughput = self.metrics.processed_items / total_duration if total_duration > 0 else 0
        
        # Calcular precisão das estimativas (se houver dados suficientes)
        estimation_accuracy = "N/A"
        if len(self.metrics.performance.item_times) >= 5:
            # Comparar estimativa final com tempo real
            final_estimate = self.metrics.estimated_remaining_time
            actual_remaining = 0  # Operação terminou
            estimation_accuracy = f"{abs(final_estimate - actual_remaining) / max(final_estimate, 0.1) * 100:.1f}%"
        
        self.logger.info("Operação concluída",
                        operation=self.operation_name,
                        total_duration=f"{total_duration:.1f}s",
                        total_processed=self.metrics.processed_items,
                        successful=self.metrics.successful_items,
                        failed=self.metrics.failed_items,
                        success_rate=f"{success_rate:.1f}%",
                        final_throughput=f"{final_throughput:.2f} items/s",
                        estimation_accuracy=estimation_accuracy,
                        confidence_level=f"{self.metrics.performance.confidence_level:.2f}")
        
        return {
            'operation': self.operation_name,
            'total_duration': total_duration,
            'total_processed': self.metrics.processed_items,
            'successful': self.metrics.successful_items,
            'failed': self.metrics.failed_items,
            'success_rate': success_rate,
            'final_throughput': final_throughput,
            'estimation_accuracy': estimation_accuracy,
            'confidence_level': self.metrics.performance.confidence_level
        }


# Manter compatibilidade com versão anterior
ProgressTracker = IntelligentProgressTracker
MultiPhaseProgressTracker = IntelligentProgressTracker
