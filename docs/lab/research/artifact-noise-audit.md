# Auditoria de ruído nos artifacts

Auditoria somente leitura dos 67 artifacts (`kind = markdown`, `tool = cg-pipeline-archive`)
presentes no banco. Objetivo: medir quanto do corpo markdown que enviamos aos modelos de
extração não é conteúdo instrucional.

## 1. Método

- Todos os 67 bodies foram lidos na íntegra a partir do banco (`artifact.body`), nenhuma amostragem.
- Cada linha foi classificada por regras determinísticas (front-matter, scaffolding de leitor,
  UI de embed, placeholders) e por faixas explícitas de linhas identificadas manualmente nos
  casos de chrome de site, comentários e rodapés.
- As contagens de caracteres incluem o caractere de quebra de linha de cada linha classificada.
- Artefatos inline (dingbats de PDF, entidades HTML, hifenização de quebra de linha) foram
  contados por ocorrência, não por caractere, porque estão embutidos dentro de parágrafos
  legítimos.

Total do corpus: **1.277.614 caracteres** distribuídos em 67 artifacts (menor: 3.484; maior: 95.050).

## 2. Números globais

| Métrica | Valor |
| --- | --- |
| Caracteres totais | 1.277.614 |
| Caracteres de ruído | 179.988 |
| **Percentual global de ruído** | **14,09%** |
| Ruído excluindo front-matter YAML | 114.538 (**8,97%**) |
| Artifacts sem nenhum ruído | 0 |
| Artifacts cujo único ruído é o front-matter | 42 (63%) |
| Artifacts com ruído além do front-matter | 25 (37%) |

O ruído é extremamente concentrado. Três artifacts (`0034`, `0061`, `0082`) concentram
**81,7% de todo o ruído não relacionado a front-matter**. Os outros 22 artifacts com ruído
somam menos de 21 mil caracteres no total.

### Distribuição por categoria

| Categoria | Caracteres | % do corpus | % do ruído | % do ruído sem front-matter |
| --- | ---: | ---: | ---: | ---: |
| Front-matter YAML | 65.450 | 5,12% | 36,4% | - |
| Chrome de site (menu, header, banner de cookie, sidebar, landing page) | 56.426 | 4,42% | 31,3% | 49,3% |
| Comentários de leitores | 20.534 | 1,61% | 11,4% | 17,9% |
| Rodapé | 16.376 | 1,28% | 9,1% | 14,3% |
| Scaffolding de leitor de ebook/PDF | 8.449 | 0,66% | 4,7% | 7,4% |
| Artigos relacionados e cross-sell | 4.760 | 0,37% | 2,6% | 4,2% |
| Boilerplate editorial de PDF | 3.702 | 0,29% | 2,1% | 3,2% |
| Bio de autor e CTA | 2.173 | 0,17% | 1,2% | 1,9% |
| UI de player/embed | 1.670 | 0,13% | 0,9% | 1,5% |
| Placeholder de widget JS | 312 | 0,02% | 0,2% | 0,3% |
| Banner promocional | 136 | 0,01% | 0,1% | 0,1% |

## 3. Por artifact

Todos os 67 artifacts têm front-matter YAML (média de 977 caracteres, entre 310 e 1.542).
Nos artifacts pequenos isso sozinho já representa 20% a 29% do body.

### 3.1 Artifacts com ruído significativo além do front-matter

| ID | Total | Ruído | % | Categorias |
| --- | ---: | ---: | ---: | --- |
| 0082 | 14.079 | 14.080 | 100,0% | chrome de site |
| 0034 | 82.584 | 57.338 | 69,4% | chrome, rodapé, relacionados, bio/CTA, comentários, UI |
| 0075 | 3.839 | 2.226 | 58,0% | chrome de site |
| 0081 | 3.484 | 1.471 | 42,2% | chrome de site |
| 0061 | 70.266 | 25.699 | 36,6% | comentários, chrome de site |
| 0020 | 9.825 | 2.954 | 30,1% | chrome de site |
| 0055 | 10.864 | 1.937 | 17,8% | relacionados, banner promocional |
| 0059 | 18.639 | 3.286 | 17,6% | UI de embed, bio/CTA |
| 0023 | 11.299 | 1.890 | 16,7% | chrome de site, relacionados |
| 0067 | 12.338 | 1.903 | 15,4% | bio/CTA |
| 0008 | 11.257 | 1.646 | 14,6% | placeholder de widget |
| 0048 | 14.660 | 1.351 | 9,2% | chrome de site |
| 0043 | 17.331 | 1.385 | 8,0% | chrome de site (rodapé Sphinx) |
| 0073 | 17.471 | 1.472 | 8,4% | scaffolding de leitor, boilerplate PDF |
| 0062 | 22.904 | 1.571 | 6,9% | scaffolding de leitor, boilerplate PDF |
| 0024 | 21.847 | 1.453 | 6,7% | scaffolding de leitor, boilerplate PDF |
| 0018 | 21.071 | 1.377 | 6,5% | scaffolding de leitor, boilerplate PDF |
| 0016 | 25.426 | 1.568 | 6,2% | scaffolding de leitor, boilerplate PDF |
| 0005 | 17.220 | 977 | 5,7% | scaffolding de leitor |
| 0077 | 24.459 | 1.322 | 5,4% | scaffolding de leitor, boilerplate PDF |
| 0015 | 28.238 | 1.498 | 5,3% | scaffolding de leitor, boilerplate PDF |
| 0042 | 29.308 | 1.464 | 5,0% | scaffolding de leitor, boilerplate PDF |
| 0039 | 49.987 | 2.254 | 4,5% | scaffolding de leitor, boilerplate PDF |
| 0019 | 23.688 | 974 | 4,1% | scaffolding de leitor |
| 0049 | 18.936 | 463 | 2,4% | scaffolding de leitor |

### 3.2 Artifacts cujo único ruído é o front-matter (42)

0003, 0004, 0006, 0007, 0009, 0010, 0011, 0012, 0014, 0017, 0022, 0025, 0026, 0028, 0029, 0030,
0031, 0032, 0035, 0036, 0037, 0038, 0041, 0045, 0046, 0047, 0050, 0051, 0053, 0054, 0056, 0057,
0058, 0063, 0066, 0069, 0071, 0072, 0074, 0078, 0079, 0080.

Atenção: "limpo de chrome" não é o mesmo que "íntegro". Vários desses artifacts têm problemas
graves de conteúdo descritos na seção 5 (0046, 0038, 0031, 0022/0026).

## 4. Casos detalhados com evidência

### 0034 - Naive Bayes Algorithms (analyticsvidhya.com), 69,4% de ruído

O pior caso do corpus. O texto do artigo só começa na linha 240 de 838.

- Linhas 26 a 239 (34.668 caracteres): banner de cookie, faixa promocional com contador
  regressivo e o mega-menu completo do site.
  Evidência: `"We use cookies essential for this site to function well."`,
  `"Accept all cookies"`, seguidos de dezenas de links `.../blog/category/...?ref=category`.
- Linhas 568 a 585 (1.345 caracteres): bio do autor e paywall.
  Evidência: `"UG (PE) @PDEU | 50+ Published Articles on Data Science | Technical Writer (AI/ML/DL) ..."`
  e `"#### Login to continue reading and enjoy expert-curated content."`
- Linhas 586 a 635 (3.646 caracteres): blocos "Free Courses" e "Recommended Articles".
- Linhas 636 a 639: `"### Responses From Readers"` com `"[Cancel reply](...)"`.
- Linhas 666 a 838 (16.376 caracteres): rodapé com "Become an Author", "Flagship Programs",
  "Free Courses", "Popular Categories" e centenas de links `?ref=footer`.

A seção "Frequently Asked Questions" (linhas 640 a 665) foi mantida como conteúdo legítimo:
são perguntas e respostas sobre Naive Bayes, não chrome.

### 0061 - Understanding word vectors (GitHub Gist), 36,6% de ruído

- Linhas 26 a 150 (3.900 caracteres): chrome do Gist.
  Evidência: `"[Skip to content](...)"`, `"{{ message }}"`, `"Instantly share code, notes, and snippets."`,
  `"Show Gist options"`, `"Clone via HTTPS"`, além do bloco "Select an option" repetido três vezes.
- Linhas 1287 a 1746 (20.381 caracteres): 30 comentários de leitores do Gist, cada um com
  avatar órfão, `"Copy link"` e `"Copy Markdown"`.
  Evidência: `"### **[motahher](...)** commented on Dec 10, 2020"` seguido de `"very good explanation"`.
- Encerra com `"[Sign up for free](...) **to join this conversation on GitHub**."` e
  `"You can't perform that action at this time."`

O conteúdo instrucional real (o notebook de Allison Parrish) ocupa as linhas 151 a 1286.

### 0082 - ATIVIDADE: ferramentas de PLN em nuvem, 100% de ruído

O body não contém a atividade. É a homepage de marketing do github.com capturada por inteiro.
Evidência: `"# The future of building happens together"`, `"[Try GitHub Copilot](...)"`,
`"## Millions of developers and businesses call GitHub home"`. Nenhuma linha do body tem
relação com o título do artifact ou com PLN.

### 0020 - ATIVIDADE: Pipeline dinâmico, 30,1% de ruído

Também é uma captura de landing page: a homepage do scikit-learn.org, não o enunciado da
atividade. Os cards de Classification/Regression/Clustering carregam algum conteúdo técnico,
mas as linhas 107 a 132 são puro chrome.
Evidência: `"#### Who uses scikit-learn?"` seguido de
`"[Image: spotify](...) _\"I think it's the most well-designed ML package I've seen so far.\"_"`
e `"[More testimonials...](...)"`.

### 0075 - ATIVIDADE: Estudo de caso, 58,0% de ruído

Página de dataset do Kaggle. O trecho final é telemetria do site: uma tabela de 32 linhas com
o número de visualizações por dia.
Evidência: `"| Date | Views |"` seguido de `"| Apr 12, 2026 | 187 |"`, mais
`"### Expected update frequency"` / `"Annually"` e a lista de tags do Kaggle.

### 0081 - Métricas de Software, 42,2% de ruído

README do GitHub com a sidebar do repositório colada no fim.
Evidência: `"## About"`, `"### Topics"`, `"### License"`, `"### Contributing"`, cada um seguido
apenas de links para `github.com/topics/...`.

### 0059 - Gerenciamento de Memória no TensorFlow, 17,6% de ruído

Artigo do Medium com a barra de assinatura do autor e quatro players de YouTube embutidos que
vazaram a UI para o markdown.
Evidência: bloco `"Follow"` / `"7 min read"` / `"·"` / `"Mar 9, 2021"` logo abaixo do título, e
o padrão repetido `"Tap to unmute"` / `"1x"` / `"Tanveerkhan86710 subscribers"` / `"[Watch on](...)"`.
Também aparece `"Press enter or click to view image in full size"` sete vezes e
`"Remember me for faster sign in"`.

### 0055 - Keras Cheat Sheet (DataCamp), 17,8% de ruído

Abre com banner promocional: `"[Image: Promo | 50% Off](...)"` e
`"**Build job-ready data + AI skills. Save **50%** today**"`. Termina com cross-sell de outros
cheat sheets da DataCamp.

### 0023 e 0048 - freeCodeCamp

Ambos abrem com o header do site antes do conteúdo.
Evidência (0023): `"# Learn to code — free 3,000-hour curriculum"` seguido de imagem de capa
órfã e `"By Praveen Dubey"`. Em 0048 o mesmo padrão com `"By Aditya"`.

### 0067 - Feature Extraction and Embeddings, 15,4% de ruído

Barra de autor (`"[Siddharth M](.../author/siddharth1698/) Last Updated :"` / `"20 Jul, 2021"` /
`"6 min read"` / `"This article was published as a part of the Data Science Blogathon"`) e bio
final: `"**About Me:** I am a Research Student interested in the field of Deep Learning..."`.

### 0008 - Estruturas de Dados em Python, 14,6% de ruído

Treze ocorrências de `"# Loading Playground..."` dentro de blocos ```` ```python ````. É o
placeholder de um widget JavaScript que não carregou, sendo entregue ao modelo como se fosse
um comentário de código.

### 0043 - Gensim Core Concepts, 8,0% de ruído

Rodapé gerado pelo Sphinx-Gallery:
`"**Total running time of the script:** ( 0 minutes 1.675 seconds)"`,
`"**Estimated memory usage:** 37 MB"`, links de download do `.py` e do `.ipynb`,
`"[Gallery generated by Sphinx-Gallery](...)"` e `"[Fork on Github](...)"`.

### Livros e PDFs (0005, 0015, 0016, 0018, 0019, 0024, 0039, 0042, 0049, 0062, 0073, 0077)

Doze artifacts vêm de um leitor de ebook e carregam scaffolding de paginação repetido a cada
página do original:

```
## Page 130
Reader pageid: 129
### Reader text
```

Somam 8.449 caracteres. Incluem também páginas em branco preservadas
(`"Esta página foi deixada em branco intencionalmente."`) e o boilerplate editorial
`"Os links para sites da web fornecidos neste capítulo foram todos testados, e seu fun-cionamento foi comprovado"`
(3.702 caracteres no total).

Além disso esses arquivos concentram dois artefatos inline de extração de PDF:

- **Dingbat de bullet corrompido**: o caractere `„` substitui o marcador de lista dos objetivos
  de aprendizagem. 134 ocorrências em 10 artifacts.
  Evidência: `"„ Definir o conceito de similaridade textual. „ Diferenciar o papel..."`
- **Hifenização de quebra de linha preservada**: `lin-guagem`, `tex-tuais`, `pro-cessamento`,
  `classifi-cadores`, `sequên-cias`, `caracte-rísticas`, `mé-todos`, `fun-cionamento`,
  `onto-logy-based`. Isso quebra a tokenização e faz o modelo ver palavras inexistentes.
- **Cabeçalho de página corrido colado no texto**: `"102 Similaridade léxica No exemplo da Figura 6, é chamada a função similaridade_jaccard"`.
  O número da página e o título corrente entram no meio da frase.

### CTAs de vídeo (0003, 0012, 0017, 0025, 0031, 0053, 0057, 0071)

Pedidos de like, inscrição e financiamento estão embutidos dentro dos parágrafos de
`**Spoken content:**` das transcrições, misturados com conteúdo válido. Volume pequeno em
caracteres, mas impossível de remover por regra de linha.

- 0031: `"o jabá de sempre antes da gente começar, né? PicPay, Apoia.se, o Pix, as campanhas de financiamento coletivo, são o que mantém a gente de pé aqui"`
- 0057: `"Deixando o seu like agora no vídeo, ele será muito útil para que a inteligência artificial do YouTube [...] entenda que esse conteúdo é bom pra caramba."`
- 0003: `"If you want to see more short videos like this, make sure to hit the like button and subscribe."`
- 0012: `"![outro: thumbs up, share, subscribe, bell icon, \"Thank you for watching and stay tuned for more from Simplilearn\"](video-frame://04:52)"`
- 0071: `"![logo: AssemblyAI. Watch more. Subscribe.](video-frame://71@17:07)"`

## 5. Achados inesperados

Nenhum body está vazio (mínimo 3.484 caracteres). Os problemas abaixo não são "ruído" no
sentido de chrome, mas comprometem igualmente a extração.

### 5.1 Duplicata exata: 0022 e 0026

`si-mod6-0022-a-simple-explanation-of-the-bag-of-words-model` e
`si-mod6-0026-atividade-bag-of-words` são a mesma URL (`victorzhou.com/blog/bag-of-words/`)
capturada duas vezes. Os bodies são byte a byte idênticos após o front-matter (3.234 caracteres
cada). A única diferença é `id`, `title` e `fetched_at`, com 104 milissegundos entre as duas
capturas. O artifact 0026, que deveria ser o enunciado de uma atividade, é na verdade o artigo
do Victor Zhou.

### 5.2 Artifact 0046: conteúdo majoritariamente alheio ao título

`A mostly complete chart of Neural Networks` tem 95.050 caracteres, o maior do corpus, e foi
extraído por OCR (`route_notes: pdf_mode_ocr`, `chart_heavy_pdf_force_ocr`). O conteúdo:

- Linhas 1 a 542 (24.786 caracteres): OCR do pôster do Asimov Institute em ordem de leitura
  embaralhada (`"Backfed Input Cell"` / `"A mostly complete chart of"` / `"Input Cell"` /
  `"Neural Networks"`, alternando rótulos e título), mais uma folha de álgebra linear.
- Linhas 543 ao fim (70.263 caracteres, **73,9% do artifact**): uma pilha de cheat sheets
  da DataCamp e do RStudio sem qualquer relação com o título: Scikit-Learn, Azure ML,
  Bokeh, Keras, Matplotlib, pandas, dplyr/tidyr, ggplot2, Base R.

Também é o artifact com mais entidades HTML não decodificadas (`&gt;`, `&amp;`) dentro de
tabelas, e a cauda degenera em LaTeX corrompido (`"[(\ \ 9(\ g9)n]"`, `"\ {0(n)}"`).

### 5.3 Transcrições truncadas no meio da frase

Comparando `duration_seconds` do front-matter com o último timestamp presente no body:

- **0038** (`Como Fazer Análise de Sentimentos`): vídeo de 2.651s, transcrição para em 30:29
  (69% de cobertura) e termina no meio de uma frase: `"Aqui, especificamente para o count vectorizer, é o fit transform, né? O fit"`.
  O front-matter registra `warnings: []` e `gate_status: "passed"`.
- **0031** (`spaCy: Introdução a PLN`): vídeo de 7.050s, transcrição para em 1:30:39
  (77% de cobertura) e termina no meio de uma string dentro de um bloco de código:
  `"Joaquim suicid"`.

Outros três artifacts (0012, 0025, 0072) ficam entre 75% e 89% de cobertura, mas seus finais
são conclusões legítimas: a última seção simplesmente se estende até o fim do vídeo.

### 5.4 Doze artifacts sem `gate_status`

Exatamente os doze artifacts derivados do leitor de ebook (0005, 0015, 0016, 0018, 0019, 0024,
0039, 0042, 0049, 0062, 0073, 0077) não têm os campos `gate_status`, `gate_failures` nem
`warnings` no front-matter. Eles passaram por uma rota de ingestão que não aplica o gate de
qualidade. É a mesma rota que produziu todos os artefatos de hifenização e os dingbats `„`.

### 5.5 O gate existente não pega o que importa

Dos 55 artifacts que têm `gate_status`, 48 estão como `passed` e 7 como `passed_with_warnings`.
Nenhum foi reprovado. Entre os `passed` estão 0082 (100% de ruído), 0075 (58%) e 0038
(truncado). O warning `title_mismatch` aparece 4 vezes, mas não impediu nada.

### 5.6 Outros

- Entidades HTML não decodificadas em 0046 (14), 0061 (12) e 0069 (8). Em 0069 algumas são
  legítimas: fazem parte de um exemplo de escaping do Flask (`Markup('<strong>Hello &lt;blink&gt;...')`).
- Reticências órfãs (`...` sozinho em uma linha) em 0028, 0051, 0054 e 0069, sempre dentro de
  blocos de código onde representam código elidido pelo autor original. Não é truncamento.
- Alt text órfão no formato `[Image: ...]` (não `![...]`) em 62 linhas espalhadas por 12
  artifacts: são imagens que o pipeline não conseguiu descrever, restando só o nome do arquivo
  ou do avatar.
- O artifact 0028 (`Exemplos de Uso do NLTK`) contém o corpus português do NLTK com acentos
  substituídos por `?` (`"a inten??o de Fleury ? vender as a??es"`). Isso é fiel ao arquivo
  original do NLTK, não um erro do nosso pipeline, mas é texto degradado que chega ao modelo.

## 6. Classificação das categorias por estratégia de limpeza

### (a) Removível por regra determinística de código

| Categoria | Volume | Regra |
| --- | ---: | --- |
| Front-matter YAML | 65.450 | Bloco `---` inicial. Trivial, 100% de precisão. |
| Scaffolding de leitor de ebook | 8.449 | `^## Page \d+$`, `^Reader pageid: `, `^### Reader text$`, `^Esta página foi deixada em branco intencionalmente\.$`. Padrão fixo, gerado pela nossa própria rota de ingestão. |
| Boilerplate editorial de PDF | 3.702 | Frase literal `"Os links para sites da web fornecidos neste capítulo foram todos testados"` e sua variante. Duas strings cobrem todos os casos. |
| UI de player/embed | 1.670 | Lista fechada de linhas exatas: `Follow`, `Tap to unmute`, `1x`, `Watch on`, `N subscribers`, `Press enter or click to view image in full size`, `Copy link`, `Copy Markdown`, `Show Gist options`, `{{ message }}`. |
| Placeholder de widget JS | 312 | `# Loading Playground...` |
| Banner de cookie | ~600 | Linhas exatas `Accept all cookies`, `Use necessary cookies`, `Show details` e a frase `We use cookies essential for this site`. |
| Dingbat `„` de PDF | 134 ocorrências | Substituição por `-` ou remoção. Sem ambiguidade: `„` não ocorre em português. |
| Entidades HTML | 34 ocorrências | `html.unescape`, com exceção de blocos de código (ver ambíguas). |
| Duplicata 0022/0026 | 3.234 | Deduplicação por `content_sha256` do front-matter, que já existe e já é idêntico nos dois. |
| Truncamento de transcrição | detecção | Comparar `duration_seconds` com o último timestamp do body. Não limpa, mas sinaliza para recaptura. |

Subtotal removível por regra: cerca de **80.000 caracteres**, ou 6,3% do corpus e 45% do ruído.

### (b) Exigiria um modelo

| Categoria | Volume | Por quê |
| --- | ---: | --- |
| Chrome de site (mega-menu, header, landing page, sidebar) | 56.426 | Não tem marcador sintático. Em 0034 são 214 linhas de links markdown perfeitamente bem formados, indistinguíveis por regex de uma lista de leituras recomendadas. A fronteira "onde começa o artigo" muda por domínio e por template. |
| Rodapé | 16.376 | Mesmo problema. Em 0034 o rodapé é uma sequência de `## Heading` + listas de links, estruturalmente idêntica ao corpo do artigo. |
| Comentários de leitores | 20.534 | Em 0061 o cabeçalho de cada comentário (`### **[user]** commented on ...`) é regexável, mas o corpo do comentário não. Alguns comentários contêm código e correções técnicas úteis, outros só dizem "very good explanation". Decidir onde a seção começa exige entender que o tutorial acabou. |
| CTAs dentro de transcrição | ~2.000 | Estão no meio de parágrafos de fala. Remover exige cortar sub-frases, o que só um modelo faz sem destruir o contexto ao redor. |
| Bio de autor e CTA de assinatura | 2.173 | Formato varia por site: em 0067 é `**About Me:**`, em 0034 é uma linha de credenciais separada por pipes, em 0023 é `By Praveen Dubey`. |
| Hifenização de quebra de linha em PDF | ~1.900 candidatos | Juntar `lin-guagem` é seguro, mas juntar `pré-treinado`, `bem-vindo`, `multi-lingual`, `scikit-learn` destruiria o texto. Precisa de léxico ou de modelo. |
| Cabeçalho de página corrido colado no texto | disperso | `"102 Similaridade léxica No exemplo da Figura 6..."`: identificar onde termina o cabeçalho e começa a frase exige entender a frase. |
| Correção de escopo: 0046, 0082, 0020, 0075 | ~100.000 | O body não corresponde ao título. Nenhuma regra resolve. Precisa de recaptura ou de um julgamento de relevância. |

### (c) Ambíguas

| Categoria | Volume | Ambiguidade |
| --- | ---: | --- |
| "Artigos relacionados" e cross-sell | 4.760 | Em 0034 (`## Free Courses`, `#### Recommended Articles`) é claramente publicidade. Em 0048 (`## Resources` com links para 3Blue1Brown e Michael Nielsen) e em 0023 (`### Resources to read more on bag of words` com Wikipedia e papers) um professor consideraria isso material de apoio legítimo da lição. Mesma forma sintática, valores opostos. |
| Perguntas frequentes | 1.100 (0034) | O bloco `### Frequently Asked Questions` está dentro do rodapé do site, mas o conteúdo é uma revisão útil sobre Naive Bayes. Mantivemos como conteúdo. |
| Referências bibliográficas dos livros | ~15.000 | Presentes em todos os 12 artifacts de ebook. Não são a lição, mas são parte do capítulo e podem ancorar conceitos. Decisão editorial, não técnica. |
| Alt text órfão `[Image: nome-do-arquivo]` | 62 linhas | Quando o alt text descreve um diagrama (`[Image: run core concepts]`) tem valor marginal. Quando é `[Image: @lschomp]` (avatar) é lixo puro. Distinguir exige olhar a URL. |
| Entidades HTML dentro de blocos de código | 8 (0069) | Decodificar `&lt;blink&gt;` quebraria o exemplo do Flask, que ensina exatamente sobre escaping. |
| Metadados do dataset em 0075 | ~700 | O histograma de labels do `twitter_training.csv` é telemetria do Kaggle, mas descreve o balanceamento das classes, o que é relevante para a atividade. |
| Reticências `...` isoladas | 19 | Sempre dentro de código, sempre representando elisão intencional do autor. Removê-las quebraria os exemplos. |

## 7. Recomendação

**Regras de código primeiro, modelo apenas para o chrome de HTML.**

O corpus é muito mais limpo do que a hipótese de trabalho sugeria. Descontando o front-matter,
que é metadado que nós mesmos adicionamos e que sai com quatro linhas de código, sobram 8,97%
de ruído, e **82% desse resto está em três artifacts**. Isso muda completamente o cálculo:
não faz sentido pagar um modelo de limpeza por 67 documentos para tratar um problema que
existe em três.

Plano proposto, em ordem de custo-benefício:

1. **Strip determinístico (imediato, cobre 45% do ruído).** Remover front-matter, scaffolding
   de leitor, boilerplate editorial de PDF, UI de embed, placeholders de widget e banner de
   cookie. São cerca de 15 regras de linha exata, sem heurística, sem risco de falso positivo.
   Corrigir também `„` para bullet e decodificar entidades HTML fora de blocos de código.

2. **Deduplicação por `content_sha256` (imediato).** O campo já está no front-matter e já é
   igual em 0022 e 0026. Um `GROUP BY` resolve.

3. **Detector de truncamento (imediato).** Comparar `duration_seconds` com o maior timestamp
   presente no body. Pega 0038 e 0031 hoje, e vira parte do gate daqui pra frente.

4. **Recaptura manual dos quatro artifacts de escopo errado (0082, 0020, 0075, 0046).** Não é
   um problema de limpeza, é um problema de captura. Nenhum modelo de limpeza vai transformar
   a homepage do GitHub no enunciado de uma atividade sobre PLN. Esses quatro devem ser
   refeitos ou removidos do corpus.

5. **Modelo de limpeza somente para 0034 e 0061.** São os dois únicos casos onde chrome de
   site e comentários de leitores existem em volume que justifica o custo, e são exatamente
   os dois casos onde regra determinística não funciona. Alternativa mais barata que vale
   testar antes: recortar por marcadores de fronteira (a primeira ocorrência de `^# ` que
   coincide com o `title` do front-matter, até a última seção antes de `Responses From Readers`
   ou do primeiro `commented on`). Se funcionar, o modelo não é necessário em lugar nenhum.

6. **Deixar as categorias ambíguas em paz.** Listas de "Resources", referências bibliográficas
   e FAQs são baratas em tokens e ocasionalmente úteis. O risco de um limpador agressivo
   destruir material de apoio legítimo é maior que o ganho de remover 4.760 caracteres.

7. **Corrigir a rota de ingestão de ebook.** Os doze artifacts sem `gate_status` são a fonte
   de todos os artefatos de hifenização, dos dingbats e do scaffolding de paginação. Tratar na
   origem é mais barato que limpar na saída, e evita que o problema volte a cada nova captura.

A conclusão prática: **um modelo de limpeza aplicado ao corpus inteiro seria desperdício.**
O que o corpus precisa é de um strip determinístico barato, um gate de captura mais rigoroso
e intervenção pontual em seis artifacts.
