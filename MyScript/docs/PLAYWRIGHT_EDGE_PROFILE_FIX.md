# Correção: Playwright Edge Profile Loading

## Problema Identificado

O Playwright não estava carregando o perfil do Edge corretamente, diferentemente do sistema monolítico que funcionava bem.

## Causa Raiz

- Playwright não estava usando argumentos específicos do Edge
- User-Agent desatualizado (Windows em macOS)
- Argumentos de linha de comando insuficientes para Edge

## Solução Implementada

### 1. Argumentos Específicos do Edge

```python
edge_args = [
    '--user-data-dir=' + profile_path,
    '--profile-directory=Default',
    '--disable-web-security',
    '--disable-features=VizDisplayCompositor',
    '--disable-extensions-except',
    '--disable-plugins-discovery',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-default-apps'
]
```

### 2. User-Agent Correto para macOS

- **Antes**: `Mozilla/5.0 (Windows NT 10.0; Win64; x64)...`
- **Depois**: `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...`

### 3. Configuração Completa do Playwright

```python
self.context = await self.playwright.chromium.launch_persistent_context(
    profile_path,
    headless=self.headless,
    slow_mo=self.slow_mo,
    timeout=self.timeout,
    viewport=self.viewport,
    args=edge_args,  # Argumentos específicos do Edge
    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...'
)
```

### 4. Aplicado em Ambos os Caminhos

- Caminho principal (`browser_type in ['chromium', 'msedge']`)
- Fallback para chromium

## Resultado Esperado

- ✅ Playwright carrega perfil Edge corretamente
- ✅ Cookies e logins preservados
- ✅ Extensões funcionando (se configuradas)
- ✅ Comportamento idêntico ao sistema monolítico
- ✅ Compatibilidade com macOS

## Arquivos Modificados

1. `src/MyScript/playwright_system.py` - Argumentos Edge específicos

## Teste Recomendado

1. Executar sistema avançado
2. Verificar logs: "Perfil Edge configurado"
3. Confirmar que login é preservado
4. Validar que extensões funcionam
5. Comparar comportamento com sistema monolítico
