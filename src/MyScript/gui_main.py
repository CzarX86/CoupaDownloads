"""
Interface Gráfica CustomTkinter para Sistema MyScript
Interface moderna e intuitiva para controle do sistema CoupaDownloads
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import json
from pathlib import Path

# Adicionar o diretório atual ao sys.path para importações locais
import sys
from pathlib import Path
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Importações do sistema
try:
    from coupa_inventory_collector import manage_inventory_system
    from coupa_workflow_orchestrator import AdvancedCoupaSystem
    from config import config_manager
    from config_advanced import get_config, validate_all_configs
    # NOVO: Importação do progress tracker avançado
    from execution_progress_tracker import IntelligentProgressTracker
except ImportError as e:
    print(f"⚠️ Erro ao importar módulos: {e}")
    print("   Certifique-se de que está executando do diretório correto")


class MyScriptGUI:
    """Interface gráfica principal do sistema MyScript."""
    
    def __init__(self):
        # Configurar tema do CustomTkinter
        ctk.set_appearance_mode("dark")  # "dark" ou "light"
        ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"
        
        # Criar janela principal
        self.root = ctk.CTk()
        self.root.title("🚀 MyScript - Sistema CoupaDownloads")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Variáveis de estado
        self.is_running = False
        self.current_system = None
        self.log_thread = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        
        # NOVO: Progress tracker avançado
        self.progress_tracker = IntelligentProgressTracker("gui_system")
        
        # Configurações padrão (sem batch_size)
        self.config = {
            'excel_path': 'src/MyScript/data/input.csv',
            'csv_path': 'src/MyScript/download_inventory.csv',
            'download_dir': '~/Downloads/CoupaDownloads',
            'num_windows': 2,
            'max_tabs_per_window': 3,
            'max_workers': 4,
            'headless': False,
            'profile_mode': 'minimal'
        }
        
        # Criar interface
        self.create_widgets()
        self.load_config()
        
        # Configurar fechamento da janela
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        """Cria todos os widgets da interface."""
        # Frame principal
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Criar notebook para abas
        self.notebook = ctk.CTkTabview(self.main_frame)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Abas
        self.create_dashboard_tab()
        self.create_configuration_tab()
        self.create_logs_tab()
    
    def create_dashboard_tab(self):
        """Cria a aba do dashboard principal."""
        self.notebook.add("📊 Dashboard")
        dashboard_frame = self.notebook.tab("📊 Dashboard")
        
        # Título
        title_label = ctk.CTkLabel(
            dashboard_frame, 
            text="🚀 Sistema CoupaDownloads - Avançado",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=20)
        
        # Frame de status
        status_frame = ctk.CTkFrame(dashboard_frame)
        status_frame.pack(fill="x", padx=20, pady=10)
        
        # Status do sistema
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="🔴 Sistema Parado",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.status_label.pack(pady=10)
        
        # Frame de opções de execução
        execution_frame = ctk.CTkFrame(dashboard_frame)
        execution_frame.pack(fill="x", padx=20, pady=20)
        
        execution_title = ctk.CTkLabel(
            execution_frame,
            text="⚙️ Opções de Execução",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        execution_title.pack(pady=10)
        
        # Radio buttons para modo de execução - CORREÇÃO: Layout horizontal
        self.execution_mode = ctk.StringVar(value="inventory_only")
        
        # Frame para organizar os radio buttons horizontalmente
        radio_frame = ctk.CTkFrame(execution_frame)
        radio_frame.pack(fill="x", padx=10, pady=10)
        
        # Radio button 1: Apenas Inventário
        inventory_radio = ctk.CTkRadioButton(
            radio_frame,
            text="📋 Apenas Inventário",
            variable=self.execution_mode,
            value="inventory_only",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        inventory_radio.pack(side="left", padx=15, pady=10, fill="x", expand=True)
        
        # Radio button 2: Apenas Download
        download_radio = ctk.CTkRadioButton(
            radio_frame,
            text="⬇️ Apenas Download",
            variable=self.execution_mode,
            value="download_only",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        download_radio.pack(side="left", padx=15, pady=10, fill="x", expand=True)
        
        # Radio button 3: Inventário + Download
        both_radio = ctk.CTkRadioButton(
            radio_frame,
            text="🔄 Inventário + Download",
            variable=self.execution_mode,
            value="both",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        both_radio.pack(side="left", padx=15, pady=10, fill="x", expand=True)
        
        # Tooltips para opções de execução
        self.create_execution_tooltips(inventory_radio, download_radio, both_radio)
        
        # Botões de controle
        control_frame = ctk.CTkFrame(dashboard_frame)
        control_frame.pack(fill="x", padx=20, pady=20)
        
        # Botão Executar
        self.execute_btn = ctk.CTkButton(
            control_frame,
            text="🚀 Executar Sistema",
            command=self.run_advanced_system,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        self.execute_btn.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        
        # Botão Pausar
        self.pause_btn = ctk.CTkButton(
            control_frame,
            text="⏸️ Pausar",
            command=self.pause_system,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="orange",
            hover_color="darkorange",
            state="disabled"
        )
        self.pause_btn.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        
        # Botão Parar
        self.stop_btn = ctk.CTkButton(
            control_frame,
            text="⏹️ Parar Sistema",
            command=self.stop_system,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="red",
            hover_color="darkred",
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        
        # Tooltips para os botões
        self.create_tooltips()
    
    def create_execution_tooltips(self, inventory_radio, download_radio, both_radio):
        """Cria tooltips para as opções de execução."""
        # Tooltip para Apenas Inventário
        self.create_tooltip(
            inventory_radio,
            "📋 APENAS INVENTÁRIO\n\n"
            "Coleta URLs dos anexos das POs sem baixar os arquivos.\n"
            "• Navega pelas páginas das POs\n"
            "• Identifica links de anexos\n"
            "• Salva URLs no arquivo CSV\n"
            "• Não executa downloads\n\n"
            "💡 Use quando quiser apenas mapear os arquivos disponíveis."
        )

        # Tooltip para Apenas Download
        self.create_tooltip(
            download_radio,
            "⬇️ APENAS DOWNLOAD\n\n"
            "Baixa arquivos baseado no inventário existente.\n"
            "• Lê URLs do arquivo CSV\n"
            "• Executa downloads dos arquivos\n"
            "• Organiza arquivos por PO\n"
            "• Não faz novo inventário\n\n"
            "💡 Use quando já tem um inventário pronto."
        )

        # Tooltip para Inventário + Download
        self.create_tooltip(
            both_radio,
            "🔄 INVENTÁRIO + DOWNLOAD\n\n"
            "Executa ambos os processos em sequência.\n"
            "• Primeiro: Coleta URLs (Inventário)\n"
            "• Segundo: Baixa arquivos (Download)\n"
            "• Processo completo automatizado\n"
            "• Ideal para uso único\n\n"
            "💡 Use quando quiser fazer tudo de uma vez."
        )
    
    def create_tooltips(self):
        """Cria tooltips para os botões."""
        # Tooltip para botão Executar
        self.create_tooltip(
            self.execute_btn,
            "🚀 Executar Sistema Avançado\n\n"
            "Executa o sistema baseado na opção selecionada:\n"
            "• Apenas Inventário: Coleta URLs dos anexos sem baixar\n"
            "• Apenas Download: Baixa arquivos do inventário existente\n"
            "• Inventário + Download: Executa ambos os processos\n\n"
            "O sistema usa Playwright com Edge para máxima compatibilidade."
        )
        
        # Tooltip para botão Pausar
        self.create_tooltip(
            self.pause_btn,
            "⏸️ Pausar Sistema\n\n"
            "Pausa temporariamente a execução do sistema.\n"
            "O sistema manterá o estado atual e poderá ser\n"
            "retomado posteriormente sem perder progresso."
        )
        
        # Tooltip para botão Parar
        self.create_tooltip(
            self.stop_btn,
            "⏹️ Parar Sistema\n\n"
            "Para completamente a execução do sistema.\n"
            "Todos os processos serão interrompidos e\n"
            "os recursos serão liberados imediatamente."
        )
    
    def create_tooltip(self, widget, text):
        """Cria um tooltip para um widget."""
        def show_tooltip(event):
            # Destruir tooltip existente se houver
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
            
            tooltip = ctk.CTkToplevel()
            tooltip.wm_overrideredirect(True)
            
            # Calcular posição para evitar sobreposição
            x = event.x_root + 15
            y = event.y_root + 15
            
            # Ajustar posição se sair da tela
            screen_width = tooltip.winfo_screenwidth()
            screen_height = tooltip.winfo_screenheight()
            
            if x + 350 > screen_width:  # 350 é o tamanho estimado do tooltip
                x = event.x_root - 360
            if y + 200 > screen_height:  # 200 é a altura estimada do tooltip
                y = event.y_root - 210
            
            tooltip.wm_geometry(f"+{x}+{y}")
            
            # Criar frame com borda
            tooltip_frame = ctk.CTkFrame(tooltip, corner_radius=8)
            tooltip_frame.pack(fill="both", expand=True, padx=2, pady=2)
            
            label = ctk.CTkLabel(
                tooltip_frame,
                text=text,
                font=ctk.CTkFont(size=12),
                justify="left",
                wraplength=320,
                anchor="w"
            )
            label.pack(padx=12, pady=8)
            
            widget.tooltip = tooltip
        
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)
        return widget
    
    def create_configuration_tab(self):
        """Cria a aba de configuração."""
        self.notebook.add("⚙️ Configuração")
        config_frame = self.notebook.tab("⚙️ Configuração")
        
        # Título
        title_label = ctk.CTkLabel(
            config_frame,
            text="⚙️ Configurações do Sistema",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=20)
        
        # Frame principal de configuração
        main_config_frame = ctk.CTkScrollableFrame(config_frame)
        main_config_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Configurações de arquivos
        files_frame = ctk.CTkFrame(main_config_frame)
        files_frame.pack(fill="x", padx=10, pady=10)
        
        files_title = ctk.CTkLabel(
            files_frame,
            text="📁 Arquivos",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        files_title.pack(pady=10)
        
        # Excel Path
        excel_frame = ctk.CTkFrame(files_frame)
        excel_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(excel_frame, text="Arquivo Excel:").pack(side="left", padx=10)
        self.excel_path_var = ctk.StringVar(value=self.config['excel_path'])
        excel_entry = ctk.CTkEntry(excel_frame, textvariable=self.excel_path_var, width=400)
        excel_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        excel_btn = ctk.CTkButton(
            excel_frame,
            text="📂",
            command=self.browse_excel_file,
            width=50
        )
        excel_btn.pack(side="right", padx=10)
        
        # CSV Path
        csv_frame = ctk.CTkFrame(files_frame)
        csv_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(csv_frame, text="Arquivo CSV:").pack(side="left", padx=10)
        self.csv_path_var = ctk.StringVar(value=self.config['csv_path'])
        csv_entry = ctk.CTkEntry(csv_frame, textvariable=self.csv_path_var, width=400)
        csv_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        csv_btn = ctk.CTkButton(
            csv_frame,
            text="📂",
            command=self.browse_csv_file,
            width=50
        )
        csv_btn.pack(side="right", padx=10)
        
        # Download Directory
        download_frame = ctk.CTkFrame(files_frame)
        download_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(download_frame, text="Diretório Download:").pack(side="left", padx=10)
        self.download_dir_var = ctk.StringVar(value=self.config['download_dir'])
        download_entry = ctk.CTkEntry(download_frame, textvariable=self.download_dir_var, width=400)
        download_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        download_btn = ctk.CTkButton(
            download_frame,
            text="📂",
            command=self.browse_download_dir,
            width=50
        )
        download_btn.pack(side="right", padx=10)
        
        # Configurações de performance
        performance_frame = ctk.CTkFrame(main_config_frame)
        performance_frame.pack(fill="x", padx=10, pady=10)
        
        perf_title = ctk.CTkLabel(
            performance_frame,
            text="⚡ Performance",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        perf_title.pack(pady=10)
        
        # Número de janelas
        windows_frame = ctk.CTkFrame(performance_frame)
        windows_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(windows_frame, text="Número de Janelas:").pack(side="left", padx=10)
        self.num_windows_var = ctk.IntVar(value=self.config['num_windows'])
        windows_slider = ctk.CTkSlider(
            windows_frame,
            from_=1,
            to=8,
            number_of_steps=7,
            variable=self.num_windows_var
        )
        windows_slider.pack(side="left", padx=10, fill="x", expand=True)
        
        windows_label = ctk.CTkLabel(windows_frame, textvariable=self.num_windows_var)
        windows_label.pack(side="right", padx=10)
        
        # Abas por janela
        tabs_frame = ctk.CTkFrame(performance_frame)
        tabs_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(tabs_frame, text="Abas por Janela:").pack(side="left", padx=10)
        self.max_tabs_var = ctk.IntVar(value=self.config['max_tabs_per_window'])
        tabs_slider = ctk.CTkSlider(
            tabs_frame,
            from_=1,
            to=10,
            number_of_steps=9,
            variable=self.max_tabs_var
        )
        tabs_slider.pack(side="left", padx=10, fill="x", expand=True)
        
        tabs_label = ctk.CTkLabel(tabs_frame, textvariable=self.max_tabs_var)
        tabs_label.pack(side="right", padx=10)
        
        # Workers
        workers_frame = ctk.CTkFrame(performance_frame)
        workers_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(workers_frame, text="Workers Paralelos:").pack(side="left", padx=10)
        self.max_workers_var = ctk.IntVar(value=self.config['max_workers'])
        workers_slider = ctk.CTkSlider(
            workers_frame,
            from_=1,
            to=10,
            number_of_steps=9,
            variable=self.max_workers_var
        )
        workers_slider.pack(side="left", padx=10, fill="x", expand=True)
        
        workers_label = ctk.CTkLabel(workers_frame, textvariable=self.max_workers_var)
        workers_label.pack(side="right", padx=10)
        
        # Configurações avançadas
        advanced_frame = ctk.CTkFrame(main_config_frame)
        advanced_frame.pack(fill="x", padx=10, pady=10)
        
        adv_title = ctk.CTkLabel(
            advanced_frame,
            text="🔧 Configurações Avançadas",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        adv_title.pack(pady=10)
        
        # Modo headless
        headless_frame = ctk.CTkFrame(advanced_frame)
        headless_frame.pack(fill="x", padx=10, pady=5)
        
        self.headless_var = ctk.BooleanVar(value=self.config['headless'])
        headless_check = ctk.CTkCheckBox(
            headless_frame,
            text="Modo Headless (sem interface gráfica)",
            variable=self.headless_var
        )
        headless_check.pack(side="left", padx=10)
        
        # Modo do perfil
        profile_frame = ctk.CTkFrame(advanced_frame)
        profile_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(profile_frame, text="Modo do Perfil:").pack(side="left", padx=10)
        self.profile_mode_var = ctk.StringVar(value=self.config['profile_mode'])
        profile_combo = ctk.CTkComboBox(
            profile_frame,
            values=["none", "minimal", "full"],
            variable=self.profile_mode_var
        )
        profile_combo.pack(side="left", padx=10)
        
        # Botões de ação
        action_frame = ctk.CTkFrame(main_config_frame)
        action_frame.pack(fill="x", padx=10, pady=20)
        
        save_btn = ctk.CTkButton(
            action_frame,
            text="💾 Salvar Configuração",
            command=self.save_config,
            height=40
        )
        save_btn.pack(side="left", padx=10)
        
        load_btn = ctk.CTkButton(
            action_frame,
            text="📂 Carregar Configuração",
            command=self.load_config_file,
            height=40
        )
        load_btn.pack(side="left", padx=10)
        
        reset_btn = ctk.CTkButton(
            action_frame,
            text="🔄 Resetar Padrões",
            command=self.reset_config,
            height=40,
            fg_color="orange",
            hover_color="darkorange"
        )
        reset_btn.pack(side="left", padx=10)
    
    def create_logs_tab(self):
        """Cria a aba de logs."""
        self.notebook.add("📝 Logs")
        logs_frame = self.notebook.tab("📝 Logs")
        
        # Título
        title_label = ctk.CTkLabel(
            logs_frame,
            text="📝 Logs do Sistema",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=20)
        
        # Frame de controles de log
        log_controls_frame = ctk.CTkFrame(logs_frame)
        log_controls_frame.pack(fill="x", padx=20, pady=10)
        
        # Botões de controle
        clear_btn = ctk.CTkButton(
            log_controls_frame,
            text="🗑️ Limpar Logs",
            command=self.clear_logs,
            width=120
        )
        clear_btn.pack(side="left", padx=10, pady=10)
        
        save_logs_btn = ctk.CTkButton(
            log_controls_frame,
            text="💾 Salvar Logs",
            command=self.save_logs,
            width=120
        )
        save_logs_btn.pack(side="left", padx=10, pady=10)
        
        # Checkbox para auto-scroll
        self.auto_scroll_var = ctk.BooleanVar(value=True)
        auto_scroll_check = ctk.CTkCheckBox(
            log_controls_frame,
            text="Auto-scroll",
            variable=self.auto_scroll_var
        )
        auto_scroll_check.pack(side="right", padx=10, pady=10)
        
        # Frame do texto de log
        log_text_frame = ctk.CTkFrame(logs_frame)
        log_text_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Text widget para logs
        self.log_text = tk.Text(
            log_text_frame,
            wrap="word",
            font=("Consolas", 10),
            bg="#2b2b2b",
            fg="#ffffff",
            insertbackground="#ffffff"
        )
        
        # Scrollbar para logs
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        log_scrollbar.pack(side="right", fill="y", pady=10)
        
        # Adicionar logs iniciais
        self.add_log("🚀 Sistema MyScript GUI iniciado")
        self.add_log("📋 Interface carregada com sucesso")
    
    # Métodos de funcionalidade
    
    def browse_excel_file(self):
        """Abre diálogo para selecionar planilha (CSV ou Excel)."""
        filename = filedialog.askopenfilename(
            title="Selecionar planilha",
            filetypes=[
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx *.xls"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.excel_path_var.set(filename)
    
    def browse_csv_file(self):
        """Abre diálogo para selecionar arquivo CSV."""
        filename = filedialog.asksaveasfilename(
            title="Salvar arquivo CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.csv_path_var.set(filename)
    
    def browse_download_dir(self):
        """Abre diálogo para selecionar diretório de download."""
        directory = filedialog.askdirectory(title="Selecionar diretório de download")
        if directory:
            self.download_dir_var.set(directory)
    
    def save_config(self):
        """Salva configurações atuais."""
        self.update_config_from_ui()
        
        config_file = "myscript_config.json"
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.add_log(f"✅ Configuração salva em {config_file}")
            messagebox.showinfo("Sucesso", f"Configuração salva em {config_file}")
        except Exception as e:
            self.add_log(f"❌ Erro ao salvar configuração: {e}")
            messagebox.showerror("Erro", f"Erro ao salvar configuração: {e}")
    
    def load_config_file(self):
        """Carrega configurações de arquivo."""
        filename = filedialog.askopenfilename(
            title="Carregar configuração",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    loaded_config = json.load(f)
                self.config.update(loaded_config)
                self.update_ui_from_config()
                self.add_log(f"✅ Configuração carregada de {filename}")
                messagebox.showinfo("Sucesso", f"Configuração carregada de {filename}")
            except Exception as e:
                self.add_log(f"❌ Erro ao carregar configuração: {e}")
                messagebox.showerror("Erro", f"Erro ao carregar configuração: {e}")
    
    def load_config(self):
        """Carrega configurações padrão."""
        config_file = "myscript_config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                self.config.update(loaded_config)
                self.add_log(f"✅ Configuração carregada de {config_file}")
            except Exception as e:
                self.add_log(f"⚠️ Erro ao carregar configuração: {e}")
        
        self.update_ui_from_config()
    
    def reset_config(self):
        """Reseta configurações para padrões."""
        self.config = {
            'excel_path': 'src/MyScript/data/input.xlsx',
            'csv_path': 'src/MyScript/download_inventory.csv',
            'download_dir': '~/Downloads/CoupaDownloads',
            'num_windows': 2,
            'max_tabs_per_window': 3,
            'max_workers': 4,
            'headless': False,
            'profile_mode': 'minimal'
        }
        self.update_ui_from_config()
        self.add_log("🔄 Configurações resetadas para padrões")
    
    def update_config_from_ui(self):
        """Atualiza configurações a partir da UI."""
        self.config.update({
            'excel_path': self.excel_path_var.get(),
            'csv_path': self.csv_path_var.get(),
            'download_dir': self.download_dir_var.get(),
            'num_windows': self.num_windows_var.get(),
            'max_tabs_per_window': self.max_tabs_var.get(),
            'max_workers': self.max_workers_var.get(),
            'headless': self.headless_var.get(),
            'profile_mode': self.profile_mode_var.get()
        })
    
    def update_ui_from_config(self):
        """Atualiza UI a partir das configurações."""
        self.excel_path_var.set(self.config['excel_path'])
        self.csv_path_var.set(self.config['csv_path'])
        self.download_dir_var.set(self.config['download_dir'])
        self.num_windows_var.set(self.config['num_windows'])
        self.max_tabs_var.set(self.config['max_tabs_per_window'])
        self.max_workers_var.set(self.config['max_workers'])
        self.headless_var.set(self.config['headless'])
        self.profile_mode_var.set(self.config['profile_mode'])
    
    def run_advanced_system(self):
        """Executa o sistema avançado baseado no modo selecionado."""
        if self.is_running:
            messagebox.showwarning("Aviso", "Sistema já está em execução!")
            return
        
        self.update_config_from_ui()
        mode = self.execution_mode.get()
        
        mode_text = {
            "inventory_only": "📋 Apenas Inventário",
            "download_only": "⬇️ Apenas Download", 
            "both": "🔄 Inventário + Download"
        }
        
        self.add_log(f"⚡ Iniciando Sistema Avançado - {mode_text[mode]}")
        
        # Desabilitar botões durante execução
        self.execute_btn.configure(state="disabled", text="🔄 Executando...")
        self.pause_btn.configure(state="normal")
        self.stop_btn.configure(state="normal")
        
        def run_advanced():
            try:
                self.is_running = True
                self.update_status(f"🟡 Sistema Avançado Executando - {mode_text[mode]}")
                
                # Executar sistema avançado com stop_event, modo e configurações da UI
                import asyncio
                from coupa_workflow_orchestrator import run_advanced_coupa_system
                
                # CORREÇÃO: Passar configurações da UI para o sistema avançado
                ui_config = {
                    'num_windows': self.config['num_windows'],
                    'max_tabs_per_window': self.config['max_tabs_per_window'],
                    'max_workers': self.config['max_workers'],
                    'headless': self.config['headless'],
                    'profile_mode': self.config['profile_mode']
                }
                
                # Executar em loop assíncrono com stop_event, modo e configurações da UI
                asyncio.run(run_advanced_coupa_system(
                    stop_event=self.stop_event,
                    execution_mode=mode,
                    ui_config=ui_config
                ))
                
                self.add_log("✅ Sistema Avançado concluído!")
                self.update_status("🟢 Sistema Avançado Concluído")
                
            except Exception as e:
                self.add_log(f"❌ Erro no Sistema Avançado: {e}")
                self.update_status("🔴 Erro no Sistema Avançado")
            finally:
                self.is_running = False
                # Reabilitar botões
                self.execute_btn.configure(state="normal", text="🚀 Executar Sistema")
                self.pause_btn.configure(state="disabled")
                self.stop_btn.configure(state="disabled")
        
        # Executar em thread separada
        thread = threading.Thread(target=run_advanced, daemon=True)
        thread.start()
    
    def pause_system(self):
        """Pausa o sistema em execução."""
        if not self.is_running:
            messagebox.showinfo("Info", "Nenhum sistema está em execução!")
            return
        
        # Implementar lógica de pausa
        self.pause_event.set()
        self.update_status("⏸️ Sistema Pausado")
        self.add_log("⏸️ Sistema pausado pelo usuário")
        
        # Alterar botão para Retomar
        self.pause_btn.configure(text="▶️ Retomar", command=self.resume_system)
    
    def resume_system(self):
        """Retoma o sistema pausado."""
        self.pause_event.clear()
        self.update_status("🟡 Sistema Retomado")
        self.add_log("▶️ Sistema retomado pelo usuário")
        
        # Alterar botão para Pausar
        self.pause_btn.configure(text="⏸️ Pausar", command=self.pause_system)
    
    def stop_system(self):
        """Para o sistema em execução."""
        if not self.is_running:
            messagebox.showinfo("Info", "Nenhum sistema está em execução!")
            return
        
        self.stop_event.set()
        self.is_running = False
        self.update_status("🔴 Sistema Parado")
        self.add_log("⏹️ Sistema parado pelo usuário")
    
    def update_status(self, status_text, metrics=None):
        """Atualiza o status do sistema com métricas avançadas."""
        # LÓGICA EXISTENTE PRESERVADA
        self.status_label.configure(text=status_text)
        
        # NOVO: Adicionar métricas se disponíveis
        if metrics:
            throughput = metrics.get('throughput', 0)
            remaining_time = metrics.get('remaining_time', 0)
            progress = metrics.get('progress', 0)
            
            advanced_status = f"{status_text} | Velocidade: {throughput:.2f} items/s | Tempo restante: {remaining_time:.0f}s | Progresso: {progress:.1f}%"
            self.status_label.configure(text=advanced_status)
    
    def update_status_advanced(self, status_text):
        """Atualiza status com métricas do progress tracker."""
        # Obter métricas do progress tracker
        summary = self.progress_tracker.get_progress_summary()
        
        throughput = summary['timing']['current_throughput']
        remaining_time = summary['timing']['estimated_remaining']
        progress = summary['progress']['percent']
        
        metrics = {
            'throughput': throughput,
            'remaining_time': remaining_time,
            'progress': progress
        }
        
        self.update_status(status_text, metrics)
    
    def add_log(self, message):
        """Adiciona mensagem ao log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert("end", log_message)
        
        if self.auto_scroll_var.get():
            self.log_text.see("end")
    
    def clear_logs(self):
        """Limpa os logs."""
        self.log_text.delete("1.0", "end")
        self.add_log("🗑️ Logs limpos")
    
    def save_logs(self):
        """Salva logs em arquivo."""
        filename = filedialog.asksaveasfilename(
            title="Salvar logs",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.log_text.get("1.0", "end"))
                self.add_log(f"💾 Logs salvos em {filename}")
                messagebox.showinfo("Sucesso", f"Logs salvos em {filename}")
            except Exception as e:
                self.add_log(f"❌ Erro ao salvar logs: {e}")
                messagebox.showerror("Erro", f"Erro ao salvar logs: {e}")
    
    def on_closing(self):
        """Manipula o fechamento da janela."""
        if self.is_running:
            if messagebox.askokcancel("Sair", "Sistema está em execução. Deseja realmente sair?"):
                self.stop_system()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """Inicia a interface gráfica."""
        self.root.mainloop()


def main():
    """Função principal."""
    print("🚀 Iniciando MyScript GUI...")
    
    try:
        app = MyScriptGUI()
        app.run()
    except Exception as e:
        print(f"❌ Erro ao iniciar GUI: {e}")
        messagebox.showerror("Erro", f"Erro ao iniciar GUI: {e}")


if __name__ == "__main__":
    main()
