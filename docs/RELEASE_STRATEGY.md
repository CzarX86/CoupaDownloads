<!-- Moved from repository root: RELEASE_STRATEGY.md -->

# Estratégia de Releases — CoupaDownloads

## Visão Geral
Esta estratégia define o roadmap de releases do CoupaDownloads, priorizando estabilidade, usabilidade e distribuição simplificada.

## Releases Atuais
- **v1.x**: Versões baseadas em Poetry/Python, requerem instalação manual
- **Distribuição**: ZIP com setup scripts para Windows

## Próximos Releases (Roadmap)

### v2.0 - Executável Standalone (Q1 2026)
**Objetivo**: Eliminar necessidade de instalação Python, fornecer executáveis nativos.

**Características**:
- ✅ Executáveis standalone (.exe para Windows, .app para macOS)
- ✅ Zero dependências externas (Python runtime embutido)
- ✅ Instalação drag-and-drop
- ✅ Configuração persistente em diretórios padrão do usuário
- ✅ Interface Tkinter integrada (GUI opcional)

**Tecnologias de Empacotamento**:
- **PyInstaller**: Ferramenta principal para criação de executáveis
- **cx_Freeze**: Alternativa para validação cross-platform
- **Dependências**: Apenas bibliotecas built-in (Tkinter, threading, queue, json)

**Benefícios para Usuários**:
- Sem necessidade de instalar Python
- Sem conflitos de versão de dependências
- Distribuição simplificada (arquivo único)
- Compatibilidade garantida entre plataformas

**Considerações Técnicas**:
- UI em Tkinter (built-in, cross-platform)
- Processos isolados para evitar conflitos
- Configurações em diretórios padrão do SO
- Testes de compatibilidade com ambiente empacotado

### v2.x - Melhorias Incrementais
- Performance e estabilidade
- Novos recursos baseados em feedback
- Manutenção da compatibilidade com executáveis

## Critérios de Release
- ✅ Testes automatizados passando (pytest)
- ✅ Validação manual em Windows/macOS
- ✅ Documentação atualizada
- ✅ Sem regressões críticas

## Distribuição
- **GitHub Releases**: Executáveis standalone + código fonte
- **Documentação**: README atualizado com instruções de instalação zero
- **Suporte**: Issues no GitHub para report de bugs
