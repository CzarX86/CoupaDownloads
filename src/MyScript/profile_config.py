# ============================================================================
# 🛡️ CONFIGURAÇÃO CRÍTICA DO PERFIL EDGE - NÃO ALTERAR 🛡️
# ============================================================================
# Este arquivo contém configurações ESSENCIAIS para o funcionamento do perfil Edge
# ⚠️  ATENÇÃO: Qualquer alteração pode quebrar a detecção de perfil
# ⚠️  Se você precisa modificar algo aqui, CONSULTE O USUÁRIO PRIMEIRO
# ============================================================================

# Configurações do perfil Edge
EDGE_PROFILE_CONFIG = {
    "macos_profile_path": "~/Library/Application Support/Microsoft Edge",
    "windows_profile_path": "%LOCALAPPDATA%/Microsoft/Edge/User Data",
    "profile_directory": "Default",
    "login_check_url": "https://unilever.coupahost.com",
    "login_check_timeout": 3,
    "login_selectors": [
        "input[type='password']",
        "input[name*='password']", 
        "button[type='submit']"
    ]
}

# Mensagens de status do perfil
PROFILE_STATUS_MESSAGES = {
    "not_logged_in": "⚠️ Perfil carregado mas usuário não está logado no Coupa\n   Será necessário fazer login manualmente se necessário",
    "logged_in": "✅ Perfil carregado e usuário está logado no Coupa!",
    "check_failed": "⚠️ Não foi possível verificar status do login: {error}\n   Continuando com o processamento..."
}

# ============================================================================
# 🛡️ FIM DA CONFIGURAÇÃO CRÍTICA 🛡️
# ============================================================================
