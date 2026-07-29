# Documento de Design: Motor de Download Turbo e Sintonizador Genético de Rede

## 1. Contexto
No processamento de downloads do Coupa, o modo `direct_http` foi concebido para alta velocidade, porém falhava devido à mudança no layout DOM da página de detalhes das ordens de compra (`order_headers`). Os anexos agora são renderizados como elementos com o atributo `data-url` contendo a URL de download criptografada/protegida (em vez de tags `<a>` simples com `href`).

Este design document detalha as mudanças necessárias em `src/lib/direct_http_downloader.py` para corrigir o parser BeautifulSoup e injetar hiperparâmetros de rede ideais descobertos através de nossa pesquisa evolutiva baseada em Algoritmo Genético.

## 2. Decisão Técnica
1. **Parser Unificado do BeautifulSoup**:
   Expandir o loop de busca de anexos para realizar duas passagens complementares na árvore DOM do HTML:
   - Passagem 1: Buscar elementos com o atributo `data-url` contendo termos-chave como `attachment` ou `download`. Capturar seus títulos associados a partir de sub-elementos ou atributos nativos.
   - Passagem 2: Buscar âncoras tradicionais baseadas no `Config.ATTACHMENT_SELECTOR` ou termos-chave globais.
   - Deduplicar links encontrados preservando a ordem original.

2. **Parametrização Dinâmica do Timeout de Rede**:
   - Ajustar o construtor da classe `DirectHTTPDownloader` para receber um parâmetro opcional `timeout` com o padrão de `11.7` segundos (a configuração mais rápida e estável identificada pela sintonização genética evolutiva).

## 3. Alterações Planejadas

### 3.1 `src/lib/direct_http_downloader.py`

#### Construtor Modificado:
```python
    def __init__(
        self,
        cookies: Dict[str, str],
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        timeout: float = 11.7,
    ):
        self.cookies = cookies
        self._progress_callback = progress_callback
        self.client = httpx.Client(
            cookies=cookies,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
            follow_redirects=True,
            timeout=timeout
        )
```

#### Extração de Anexos Unificada:
```python
        # Find attachments using both data-url attribute (modern DOM) and standard anchors (legacy DOM)
        attachment_links = []
        
        # 1. Search for any elements with data-url containing attachment or download
        for el in soup.find_all(attrs={"data-url": True}):
            data_url = el.get("data-url")
            if "attachment" in data_url.lower() or "download" in data_url.lower():
                title_el = el.select_one("[title], [aria-label]")
                title = ""
                if title_el:
                    title = title_el.get("title") or title_el.get("aria-label")
                if not title:
                    title = el.get_text(strip=True) or os.path.basename(data_url.split("?")[0])
                attachment_links.append({
                    'url': urljoin(url, data_url),
                    'name': title
                })

        # 2. Search for standard anchor tags matching selector or fallback keywords
        selector = Config.ATTACHMENT_SELECTOR
        if selector:
            try:
                anchors = soup.select(selector)
            except Exception:
                anchors = soup.select("a[href*='attachment'], a[href*='download'], a[download]")
        else:
            anchors = soup.select("a[href*='attachment'], a[href*='download'], a[download]")

        for a in anchors:
            href = a.get('href')
            if href and href not in ('#', ''):
                title = a.get('title') or a.get('aria-label') or a.get_text(strip=True) or os.path.basename(href.split("?")[0])
                attachment_links.append({
                    'url': urljoin(url, href),
                    'name': title
                })
```

## 4. Fluxo de Dados e Controle
1. O `WorkerPool` inicia workers paralelos no modo `direct_http`.
2. Cada worker extrai os cookies ativos uma vez e instancia o `DirectHTTPDownloader`.
3. O downloader executa requisições HTTP seguras e extremamente leves diretamente nos servidores do Coupa.
4. O parser unificado analisa a resposta HTML capturando anexos em qualquer uma das estruturas DOM.
5. Arquivos de anexos correspondentes são gravados assincronamente em disco na pasta de destino final.

## 5. Testes e Validação
- **Validação de Produção**: Usar os POs ativos conhecidos como válidos para confirmar a identificação de 100% dos anexos.
- **Teste de Regressão**: Garantir que ordens antigas sem `data-url` mas com âncoras normais continuem sendo processadas sem falhas.
