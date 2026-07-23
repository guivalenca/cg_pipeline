---
id: "30"
title: "Curso de spaCy"
source_url: "https://course.spacy.io/pt/chapter1"
fetch_url: "https://course.spacy.io/pt/chapter1"
resolved_url: "https://course.spacy.io/pt/chapter1"
firecrawl_title: "Capítulo 1: Selecionando palavras, frases, nomes e alguns conceitos"
description: "Neste capítulo vamos apresentar os conceitos básicos de processamento de texto utilizando a  biblioteca spaCy. Você vai aprender sobre as estruturas de dados, como trabalhar fluxos de processamento (pipelines) treinados e como usá-los para prever anotações linguísticas do seu texto."
fetched_at: "2026-05-12T03:59:51.552498Z"
provider: "firecrawl"
strategy: "spacy_course_gatsby"
cache_key: "6b8839b9a5ecb38afe187477397421f97a223f7ddfb43df97e38081acde377cf"
firecrawl_status_code: 200
firecrawl_content_type: "application/json"
word_count: 1117
char_count: 7545
content_sha256: "1dcb4d6853cd276ab7867c1c9e106cec40704d3e9709b35be5c824be4b469aad"
image_count: 0
link_count: 0
warnings: []
gate_status: "passed"
gate_failures: []
route_notes:
  - "separate_screenshot"
  - "spacy_gatsby_page_data_extractor"
---

# Capítulo 1: Selecionando palavras, frases, nomes e alguns conceitos

Neste capítulo vamos apresentar os conceitos básicos de processamento de texto utilizando a  biblioteca spaCy. Você vai aprender sobre as estruturas de dados, como trabalhar fluxos de processamento (pipelines) treinados e como usá-los para prever anotações linguísticas do seu texto.

## 1. Introdução a biblioteca spaCy (slides)

> spaCy slide deck: `chapter1_01_introduction-to-spacy`


## 2. Primeiros passos

Vamos começar colocando a mão na massa! Neste exercício você fará
experimentos com alguns dos mais de 60 [idiomas disponíveis](https://spacy.io/usage/models#languages).

### Parte 1: Inglês

- Utilize `spacy.blank` para criar um objeto `nlp` vazio do idioma inglês (“en”).
- Crie uma variável `doc` e imprima o seu conteúdo.

### Parte 2: Alemão

- Utilize `spacy.blank` para criar um objeto `nlp` vazio do idioma alemão (“de”).
- Crie uma variável `doc` e imprima o seu conteúdo.

### Parte 3: Espanhol

- Utilize `spacy.blank` para criar um objeto `nlp` vazio do idioma espanhol (“es”).
- Crie uma variável `doc` e imprima o seu conteúdo.


## 3. Documentos, partições e tokens

Quando você chama o objeto `nlp` passando uma string como parâmetro, a spaCy
faz a toquenização do texto e cria um objeto do tipo documento. Neste exercício, você
vai aprender mais sobre o documento `Doc`, assim como os objetos `Token` e
partição `Span`.

### Passo 1

- Utilize `spacy.blank` para criar um objeto `nlp` vazio do idioma português (“pt”).
- Processe o texto e instancie um objeto `Doc` na variável `doc`.
- Selecione o primeiro token do objeto `Doc` e imprima seu texto `text`.

> spaCy interactive code block: `01_03_01`

### Passo 2

- Crie um objeto `nlp` vazio do idioma `Português`.
- Processe o texto e instancie um objeto `Doc` na variável `doc`.
- Crie uma partição do `Doc` para os tokens “três cachorros” e
“três cachorros e dois gatos”.

> spaCy interactive code block: `01_03_02`


## 4. Atributos léxicos

Neste exemplo, você poderá usar os objetos `Doc` e `Token` combinados com
atributos léxicos para encontrar referências de porcentagem em seu texto. Você irá procurar
por dois elementos (tokens) sequenciais: um número e um sinal de porcentagem.

- Use o atributo `like_num` para identificar se algum token no documento
`doc` se assemelha a um número.
- Selecione o token _seguinte_ ao token atual no documento. O índice para o
próximo token no `doc` é `token.i + 1`.
- Verifique se o atributo `text` do próximo token é o sinal de porcentagem ”%“.

> spaCy interactive code block: `01_04`


## 5. Fluxos de processamento treinados (slides)

> spaCy slide deck: `chapter1_02_statistical-models`


## 6. Biblioteca dos modelos (choice)

O que **NÃO** está incluído nos fluxos de processamento (pipelines) que você pode carregar na spaCy?

> spaCy multiple-choice exercise

Todos os fluxos de processamento (pipelines) incluem um arquivo `config.cfg` que define o idioma de
inicialização, os componentes do fluxo (pipeline) de processamento que devem ser carregados, bem como as informações
sobre o treinamento do fluxo (pipeline) de processamento e as configurações que foram utilizadas neste treinamento.

Para fazer a previsão de anotações linguísticas como o tagueamento de classes
gramaticais, termos sintáticos e reconhecimento de entidades, os pacotes de fluxos de processamento (pipelines) incluem
os pesos binários.

Os fluxos de processamento treinados permitem a generalização a partir de um conjunto de
exemplos de treinamento. Uma vez treinados, os modelos usam os pesos binários
para fazer as previsões. É por este motivo que não é necessário que os dados de
treinamento sejam incluídos nos modelos.

As bibliotecas de fluxos de processamento (pipelines) incluem um arquivo `strings.json` que armazena o mapeamento
do vocabulário para códigos indexadores (hash). Isso permite que a spaCy utilize apenas os
códigos hash e faça a consulta da palavra correspondente, se necessário.


## 7. Carregando os fluxos (pipelines) de processamento

Os fluxos (pipelines) de processamento que estamos usando neste treinamento já vem pré-instalados. Para
saber mais informações sobre os fluxos (pipelines) de processamento treinados e como instalá-los em seu
computador, consulte [essa documentação](https://spacy.io/usage/models).

- Utilize `spacy.load` para carregar o fluxo (pipeline) de processamento pequeno do idioma português `"pt_core_news_sm"`.
- Processe o texto e imprima o texto do documento.

> spaCy interactive code block: `01_07`


## 8. Prevendo anotações linguísticas

Agora vamos experimentar um dos fluxos (pipelines) de processamento treinados da biblioteca spaCy e
ver o resultado de sua previsão. Fique à vontade e experimente com seu
próprio texto! Use `spacy.explain` para saber o significado de um determinado
marcador. Por exemplo: `spacy.explain("PROPN")` ou `spacy.explain("GPE")`.

### Parte 1

- Processe o texto utilizando o objeto `nlp` e crie um `doc`.
- Para cada token, imprima seu texto, sua classe gramatical  `.pos_` e seu
termo sintático `.dep_`

> spaCy interactive code block: `01_08_01`

### Parte 2

- Processe o texto utilizando o objeto `nlp` e crie um `doc`.
- Construa uma iteração em `doc.ents` e imprima os atributos texto e o
marcador `label_`.

> spaCy interactive code block: `01_08_02`


## 9. Prevendo Entidades em um contexto

Os modelos são estatísticos e por isso não acertam 100% dos casos.  A acurácia
do modelo depende dos dados nos quais o modelo foi treinado e também dos
dados que você está processando. Vamos ver um exemplo:

- Processe o texto utilizando o objeto `nlp`.
- Construa uma iteração nas entidades e imprima o texto e o marcador (label) da entidade.
- Note que o modelo não previu “iPhone X”. Crie manualmente uma partição
para esses tokens.

> spaCy interactive code block: `01_09`


## 10. Correspondência de texto baseada em regras (slides)

> spaCy slide deck: `chapter1_03_rule-based-matching`


## 11. Usando o comparador Matcher

Vamos agora testar o comparador de expressões  `Matcher` baseado em
regras. Você vai usar o exemplo do exercício anterior e escrever uma expressão
que faça a correspondência para a frase “iPhone X” no texto.

- Importe o `Matcher` de `spacy.matcher`.
- Inicialize o comparador com o objeto compartilhado `vocab`do `nlp`.
- Crie uma expressão que faça a correspondência dos valores em `"TEXT"` para dois tokens:
`"iPhone"` e `"X"`.
- Use o método `matcher.add` e adicione essa expressão ao comparador.
- Chame o comparador passando como parâmetro o `doc` e armazene o resultado
na variável `matches`.
- Itere nos resultados e selecione a partição de texto com o índice `start` até
`end`.

> spaCy interactive code block: `01_11`


## 12. Escrevendo expressões de correspondência

Neste exercício, você vai escrever algumas expressões mais complexas de
correspondência, usando os atributos dos tokens e operadores.

### Parte 1

- Escreva **uma** expressão que corresponda às menções da versão IOS  _completa_:
“iOS 7”, “iOS 11” e “iOS 10”.

> spaCy interactive code block: `01_12_01`

### Parte 2

- Escreva **uma** expressão que corresponda às variações de “baixar” (tokens
que tenham “baixar” como lema), seguido de um token da classe gramatical
substativo próprio `"PROPN"`.

> spaCy interactive code block: `01_12_02`

### Part 3

- Escreva **uma** expressão que corresponda a adjetivos (`"ADJ"`) seguidos por um
ou dois substantivos. (um substantivo obrigatório e um seguinte opcional).

> spaCy interactive code block: `01_12_03`
