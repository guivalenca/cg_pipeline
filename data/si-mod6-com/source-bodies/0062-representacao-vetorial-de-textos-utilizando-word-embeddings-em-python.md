---
id: "62"
title: "Representação vetorial de textos - utilizando word embeddings em Python"
source_title: "Processamentos de Linguagem Natural"
resource_code: "9786556900575"
scope_kind: "pages"
scope_value: "pages 189-204"
final_url: "https://integrada.minhabiblioteca.com.br/reader/books/9786556900575/pageid/203"
captured_at: "2026-05-12T08:02:36.720798Z"
---

# Representação vetorial de textos - utilizando word embeddings em Python
## Page 189

Reader pageid: 188

### Reader text

Representação vetorial de textos — utilizando word embeddings em Python

Objetivos de aprendizagem Ao final deste texto, você deve apresentar os seguintes aprendizados:

„ Identificar os recursos disponibilizados pela biblioteca Gensim. „ Usar modelos pré-treinados de word2vec. „ Desenvolver modelos pré-treinados de word2vec.

Introdução

O word2vec é um modelo relevante, mas complexo de implementar, exigindo a utilização de bibliotecas para diminuir o esforço necessário para seu treinamento, o que facilita o seu emprego. Neste capítulo, utilizaremos como exemplo a biblioteca Gensim,

já que dispõe de ferramentas de pré-processamento e leitura/escrita de arquivos de modelos pré-treinados. A partir de agora, você conhecerá a biblioteca Gensim e a importância

de suas funções de sintaxe simples, especialmente no mundo acadêmico. Ainda, verá que, mesmo com poucas linhas de código, é possível treinar um modelo ou realizar operações a partir de um modelo já treinado.

1 Biblioteca Gensim

Para analisar de maneira não supervisionada a imensidão de dados criados diariamente, foram desenvolvidos algoritmos de modelagem tópica, que utili-zam métodos estatísticos para analisar a composição de palavras presentes nos documentos e tentar descobrir o tema abordado para melhorar, por exemplo, a maneira como estes são relacionados em uma busca. Assim, o sistema con-vencional de links e palavras-chave pode ser aprimorado para melhor atender

## Page 190

Reader pageid: 189

### Reader text

190 Representação vetorial de textos —utilizando word embeddings em Python

às reais expectativas do navegador (BLEI, 2012). Obviamente, tais técnicas não se restringem a mecanismos de busca, embora esse contexto confira exa-tamente a dimensão dos problemas e das soluções buscadas a eles associados. Aproveitando o desenvolvimento desses métodos de modelagem tópica,

deu-se origem à biblioteca Gensim, uma biblioteca de processamento de linguagem natural (PLN), de código aberto, originalmente desenvolvida para modelagem de tópicos por Radim Řehůřek. A biblioteca foi criada na linguagem Python, o que requer o uso de um

interpretador. Os exemplos deste capítulo fazem uso do sistema Jupyter in-tegrado à plataforma Anaconda — para utilizá-los, você poderá instalar a plataforma Anaconda, que já inclui o Jupyter e outros sistemas e bibliotecas.

Faça uma busca pela biblioteca “Gensim” e procure pelo link oficial disponibilizado na página pessoal de Radim Řehůřek, na qual você poderá realizar o download da ferramenta e consultar a documentação integral da biblioteca. Contudo, ressaltamos que esta é apenas uma das formas de realizar o download da biblioteca. Já a plataforma Anaconda + Jupyter pode ser encontrada na página oficial do aplicativo, bastando procurar pelo termo “Anaconda” na internet.

Uma vez instalado o Anaconda, as bibliotecas adicionais podem ser inte-gradas ao sistema por meio do comando no console do Anaconda: conda install [nome do pacote] onde o nome do pacote deve ser substituído pela biblioteca que se deseja

instalar, por exemplo: conda install gensim Você pode ainda instalar todos os pacotes/bibliotecas de uma única vez,

separando cada pacote por um simples espaço. A instalação da plataforma Anaconda e das bibliotecas necessárias e a

criação de um novo arquivo de projeto podem ser realizadas por meio dos passos mostrados na Figura 1.

## Page 191

Reader pageid: 190

### Reader text

Representação vetorial de textos —utilizando word embeddings em Python 191

Figura 1. Sequência de passos para download, configuração e inicialização de um arquivo no ambiente Anaconda/Jupyter. (a) Página de download. (b) Console do Anaconda demons-trando comandos para instalação das bibliotecas necessárias. (c) Console do Anaconda demonstrando a inicialização do ambiente Jupyter. (d) Página inicial do Jupyter com destaque para os passos necessários para criar um arquivo Python. (e) Página de edição e simulação do arquivo criado: o retângulo no qual está presente o cursor é onde o código deve ser redigido, podendo ser testado pelo atalho Ctrl+Enter, ou Shit+Enter caso se queira criar um bloco de código adicional.

Para a biblioteca Gensim, podemos definir documento como um texto

qualquer, corpus como uma coleção de documentos, vetor como uma re-presentação matemática de um documento e modelo como o algoritmo que transforma representações de vetores (ŘEHŮŘEK, 2019a). Normalmente, o processamento inclui os documentos à medida que se fazem necessários, já que, muitas vezes, a quantidade de dados, se carregada para toda a memória ao mesmo tempo, poderia exceder a capacidade da maioria dos computadores convencionais (ŘEHŮŘEK, 2019a).

## Page 192

Reader pageid: 191

### Reader text

192 Representação vetorial de textos —utilizando word embeddings em Python

Antes de iniciar o processo de aprendizagem e modelagem, em geral os documentos são pré-processados, executando funções de:

„ remoção de palavras de frequência excessiva, como artigos e preposi-ções, normalmente denominadas stop words;

„ tokenização, para indexar palavras distintas encontradas no texto e elaborar o seu vocabulário, etc.

Na biblioteca Gensim, existe uma função de pré-processamento acessível

pelo módulo utils por gensim.utils.simple_preprocess(), que recebe o documento como parâmetro obrigatório e outros três parâmetros opcionais (ŘEHŮŘEK, 2019b):

„ deacc, quando True remove as acentuações das palavras; „ min_len, que estabelece o comprimento mínimo de uma palavra; „ max_len, que estabelece o comprimento máximo que deve ter uma palavra. Um exemplo de uso dessa função pode ser visto a seguir.

Todos os exemplos podem ser executados no ambiente Jupyter seguindo

as orientações de criação de um novo arquivo da Figura 1. Uma vez redigidos conforme os exemplos, os códigos podem ser executados a partir dos comandos Ctrl+Enter ou Shift+Enter, que criarão um bloco de código após a execução. A biblioteca pandas, utilizada no Exemplo 1, instalada pelo console do

Anaconda conforme a Figura 1b, será útil para a criação e a manipulação de matrizes e vetores no formato de tabelas, que facilitam a visualização. A função simple_preprocess() retorna uma lista de palavras de

acordo com as regras especificadas nos parâmetros. No Exemplo 1, no entanto, a função é executada duas vezes, já que um laço for é utilizado para varrer o corpus e pré-processar os dois documentos nele existentes e incluí-los em uma nova lista, ou seja, o resultado esperado consiste na exibição de uma lista de documentos pré-processados, em que cada documento é representado também por uma lista, e seus membros correspondem às palavras com tamanho maior que (min_len = 3), transformadas para letras minúsculas e sem acento (deacc = False), conforme a imagem, na qual a parte superior exibe a lista como originalmente retornada pela função usada para criar uma tabela e facilitar a visualização e o entendimento dessas informações. Os tokens obtidos podem ser visualizados na Figura 2, inicialmente da

maneira como são retornados normalmente pelo método, seguidos da tabela criada pela biblioteca pandas para facilitar a sua visualização.

## Page 193

Reader pageid: 192

### Reader text

Representação vetorial de textos —utilizando word embeddings em Python 193

# Exemplo 1 – Definição de um corpus e pré-processamento utilizando Gensim de cada um deles # Importação das bibliotecas utilizadas import pandas as pa import gensim

from gensim.utils import simple_preprocess # Definição de um corpus

corpus = [ 'Primeiro texto do capítulo', 'Segundo texto do capítulo' ]

# Pré-processamento de cada documento do corpus corpus_preprocessed = [] for doc in corpus:

corpus_preprocessed.append(simple_preprocess(doc,

deacc=True, min_len=3))

display(corpus_preprocessed) df = pa.DataFrame(corpus_preprocessed, index=['Documento 1', 'Documento 2'],

columns=['Token 1', 'Token 2', 'Token 3']) display(df)

Figura 2. Lista e quadro que exibem os tokens criados para cada um dos documentos após a execução do pré-processamento com a função simple_preprocess() da biblioteca Gensim.

## Page 194

Reader pageid: 193

### Reader text

194 Representação vetorial de textos —utilizando word embeddings em Python Caso deseje apenas tokenizar as palavras, o usuário pode utilizar a função

gensim.utils.tokenize(),chamada internamente pela simple_ preprocess(). Outras funções do módulo utils incluem salvar e abrir arquivos, alterar a codificação do texto e a reordenação de vetores, criação de dicionários, além de muitas outras funções que auxiliam na manipulação de corpus e documentos. Na sequência, pode ser necessário criar um vocabulário, pela possibilidade

de haver palavras repetidas entre os documentos, como as palavras “texto” e “capítulo” do Exemplo 1. No Exemplo 2 (como continuação do script do Exemplo 1), é utilizada a função gensim.corpora.Dictionary() para criar esse vocabulário. Para que seja possível executar o Exemplo 2, o Exemplo 1 deve antecedê-lo, já que faz uso de variáveis e bibliotecas utili-zadas no Exemplo 1. Durante os seus testes, você pode, por exemplo, copiar o código do Exemplo 1 seguido do código do Exemplo 2, ou simplesmente executá-los na ordem em que estão dispostos.

# Exemplo 2 – Vocabulário criado a partir dos documentos tokenizados e tratados from gensim.corpora import Dictionary as corpDict # nova função importada

vocab = corpDict(corpus_preprocessed) print(vocab)

df2 = pa.DataFrame(vocab.values(), columns=['Palavra']) display(df2)

O vocabulário é um tipo de arquivo próprio da biblioteca Gensim, similar

e baseado nos dicionários da linguagem Python. Seu resultado pode ser vi-sualizado na Figura 3, novamente em sua representação original e na forma de uma tabela usando o pandas.DataFrame.

## Page 195

Reader pageid: 194

### Reader text

Representação vetorial de textos —utilizando word embeddings em Python 195

Figura 3. Vocabulário de palavras distintas entre todos os documentos pré-processados criado a partir da função gensim.corpora.Dictionary().

Antes da criação de um modelo, os documentos precisam estar na forma

vetorial, e não textual. Assim, cada documento será representado por um vetor em que as dimensões compreendem uma característica do documento, portanto um vetor denso, com valores diretamente relacionados a ele (ŘEHŮŘEK, 2019a).

Lembre-se de que, sempre que algumas dimensões dos vetores são desconhecidas, diz-se que o vetor é esparso e todas as características faltantes são tratadas como zero (ŘEHŮŘEK, 2019a).

Como observado, a biblioteca Gensim disponibiliza, inclusive, métodos

para facilitar a etapa de pré-processamento dos dados. Além dos métodos vistos, muitos outros estão disponíveis no módulo gensim.utils e podem ser conhecidos pela documentação na página da biblioteca. Na sequência, você poderá criar seus próprios modelos também utilizando a biblioteca Gensim.

## Page 196

Reader pageid: 195

### Reader text

196 Representação vetorial de textos —utilizando word embeddings em Python Desenvolvimento de modelos

Apesar de a biblioteca Gensim ter vários modelos e algoritmos diferentes, como TF-IDF, word2vec, LDA, fastText, etc., a forma de utilização e os padrões de parâmetros e variáveis são muito similares para cada um deles. Aqui, daremos enfoque ao modelo word2vec. A biblioteca implementa tanto os algoritmos de Skip-Gram quanto de

CBOW (continuous bag-of-words) com função de softmax hierárquico ou amostragem negativa (ŘEHŮŘEK, 2019c). Para iniciar e treinar um modelo word2vec, basta instanciar o modelo

fornecendo os documentos como parâmetro, como no Exemplo 3, cujo código é uma sequência dos Exemplos 1 e 2, que devem ser executados antes dele para que consiga funcionar.

# Exemplo 3 – Treinamento de um modelo de word2vec from gensim.models import Word2Vec

# Treina um modelo de Word2Vec model = Word2Vec(corpus_preprocessed, min_count=1, size=10)

# Exibe uma tabela com os vetores dic = {v: model[v] for v in vocab.values()} df3 = pa.DataFrame(dic) display(df3)

O parâmetro min_count do Word2Vec() permite ignorar palavras

encontradas nos documentos com frequência menor que o parâmetro, enquanto o Size especifica a dimensão dos vetores. O algoritmo do Exemplo 3 ainda utiliza o vocabulário anteriormente criado

para servir de referência na exibição dos valores do modelo treinado na forma de uma DataFrame (Figura 4).

## Page 197

Reader pageid: 196

### Reader text

Representação vetorial de textos —utilizando word embeddings em Python 197

Figura 4. Representação vetorial de 10 dimensões das pala-vras encontradas no corpus para um modelo de word2vec.

Assim como especificado pelo parâmetro size do Exemplo 3, cada palavra

é formada por um vetor de 10 dimensões. Muitos outros parâmetros podem ser modificados, como os listados a seguir.

„ O parâmetro corpus_file substitui o uso de uma variável direta de sentenças, como o corpus_preprocessed do Exemplo 3, por um arquivo em que cada linha será interpretada como uma sentença. Assim, é possível economizar memória, já que o arquivo será lido conforme for necessário e outros parâmetros de restrição de memória configurados.

„ O valor sg quando igual a 0 especifica o algoritmo de Skip-Gram; já quando igual a 1, será utilizado o algoritmo de CBOW.

„ A janela máxima do contexto de uma palavra é especificada pelo pa-râmetro window.

„ Também é possível optar pelo uso da função softmax hierárquica ou amostragem negativa, em que o parâmetro hs receberá 1 ou 0, respectivamente.

„ O parâmetro negative, quando maior que 0, determina a quantidade de palavras de amostragem negativa que devem ser utilizadas no pro-cesso de treinamento.

„ O valor de alpha determina a taxa de aprendizado. „ O parâmetro seed permite que se forneça um valor de base para os geradores de números aleatórios necessários durante o processo.

## Page 198

Reader pageid: 197

### Reader text

198 Representação vetorial de textos —utilizando word embeddings em Python

Nenhum dos parâmetros de gensim.models.Word2Vec() é obrigatório, tornando-se possível instanciar um modelo sem qualquer treinamento. Ao fornecer uma variável contendo as sentenças, o nome do parâmetro pode ser ocultado desde que seja o primeiro valor fornecido. Do contrário, se utilizado um arquivo externo, será necessário explicitar o parâmetro corpus_file=’caminho do arquivo’.

O modelo treinado pode ser salvo em um arquivo para utilização posterior

ou, ainda, prosseguir com o treinamento — esta é, inclusive, uma das grandes vantagens dos modelos de word embeddings. Apesar do volume de dados e do tempo de treinamento requerido para modelos de linguagem natural, os algoritmos de word embeddings possibilitam o compartilhamento de modelos pré-treinados, usados diretamente para realizar alguma tarefa ou para ampliar o treinamento do modelo de maneira progressiva, como veremos a seguir.

2 Modelos pré-treinados

Após treinar um modelo, você pode salvá-lo em um arquivo para utilizá-lo em suas aplicações ou, ainda, para prosseguir com o aperfeiçoamento do modelo em novos treinamentos no futuro, conforme o Exemplo 4.

# Exemplo 4 – Armazenando um modelo de word2vec import gensim import nltk

from gensim.models import Word2Vec from nltk.corpus import brown

nltk.download('brown') corpus = brown.sents()

model_brown = gensim.models.Word2Vec(corpus, min_count=1) model_brown.save('C:\\Sagah\\modelo_brown.bin')

## Page 199

Reader pageid: 198

### Reader text

Representação vetorial de textos —utilizando word embeddings em Python 199 No Exemplo 4, ainda é utilizado um corpus presente na biblioteca NLTK;

caso você não tenha essa biblioteca, poderá instalá-la no console do Anaconda utilizando o comando:

conda install nltk O Brown Corpus é um compilado de 500 textos publicados em inglês no

ano de 1961 pela Universidade de Brown, no qual há pouco mais de 1 milhão de palavras diferentes, com textos de estilos diversos, mas todos escritos por nativos americanos (FRANCIS; KUCERA, 1979). Esse corpus tem sido frequentemente utilizado em modelos de linguagem natural pelo tamanho e pela qualidade dos textos. Ao final do Exemplo 4, o modelo gerado é salvo, pois se torna muito mais eficiente carregar o modelo em si no lugar de treinar um novo modelo de word2vec sempre que for utilizá-lo. O nome e a pasta em que serão salvos os modelos são passados pelo pri-meiro parâmetro da função save, e não havendo qualquer restrição quanto ao nome ou à extensão do arquivo. Sempre que necessário, o modelo pode ser carregado novamente utilizando o método load de alguma instância de gensim.models.Word2Vec() ou acessando diretamente a função a partir da classe Word2Vec, como no Exemplo 5.

# Exemplo 5 – Carregando um modelo from gensim.models import Word2Vec

model_carreg = Word2Vec.load('C:\\Sagah\\modelo_brown. bin')

Contudo, a load não é utilizada apenas para aproveitar seus próprios

modelos: você pode aproveitar modelos previamente treinados de outros de-senvolvedores, alguns dos quais contendo quantidades imensas de dados que dificilmente um usuário comum conseguiria coletar ou filtrar e pré-processar para treinar um modelo adequado.

## Page 200

Reader pageid: 199

### Reader text

200 Representação vetorial de textos —utilizando word embeddings em Python Modelos pré-treinados podem ser encontrados no repositório no Github dos

desenvolvedores da biblioteca Gensim, caso em que os arquivos podem ser automaticamente carregados utilizando o método gensim.downloaded. download() informando como parâmetro o nome do corpus.

A lista de modelos pré-treinados localizados na biblioteca Gensim pode ser visualizada por meio do repositório no Github da RaRe Technologies (2018) ao buscar na internet o termo “gensim-data”.

O Exemplo 6 faz uso de um modelo word2vec pré-treinado chamado word2vec-google-news-300, um compilado de notícias contendo vetores de 300 dimensões e cerca de 3 milhões de palavras e frases, que, inteiro, tem pouco mais de 1,5 GB.

# Exemplo 6 – Carregando um modelo pré-treinado import gensim.downloader as corpus_data

model = corpus_data.load('word2vec-google-news-300') Com modelos pré-treinados, com grandes quantidades de palavras e do-cumentos, espera-se encontrar relações mais complexas entre as palavras. Por exemplo, quando utilizado o modelo anterior para avaliar a similaridade entre as palavras car (“carro” em inglês) e house (“casa” em inglês), percebe--se que as 5 primeiras palavras retornadas para cada um seguem realmente um padrão. Para tanto, utilizou-se o algoritmo do Exemplo 7, em que um DataFrame é criado para listar na ordem da primeira até a quinta palavra mais similar às palavras car e house. Lembrando que o modelo (model) foi carregado no Exemplo 6, código do qual depende o Exemplo 7; portanto, deve ser executado por primeiro.

## Page 201

Reader pageid: 200

### Reader text

Representação vetorial de textos —utilizando word embeddings em Python 201

# Exemplo 7 – Palavras similares a car e house import pandas as pa

dfC = pa.DataFrame(model.similar_by_word('car', topn=10), columns=['Palavra', 'Similaridade']) dfC = dfC.set_index('Palavra')

dfH = pa.DataFrame(model.similar_by_word('house', topn=10), columns=['Palavra', 'Similaridade']) dfH = dfH.set_index('Palavra') display(dfC) display(dfH)

No Exemplo 7, os vetores são colocados lado a lado, conforme podemos observar na Figura 5. Figura 5. Dez palavras mais similares a car (à esquerda) e a house (à direita).

## Page 202

Reader pageid: 201

### Reader text

202 Representação vetorial de textos —utilizando word embeddings em Python Para ambos os vetores (car e house), foram encontradas palavras com

um contexto ou significado muito parecido com os da palavra original. Para o vetor casa (house), foram encontrados casas, bangalô, apartamento, quarto, etc. Já as palavras próximas a carro também apresentaram características muito similares. Assim, uma vez criado, o modelo de representação vetorial pode ser uti-lizado diretamente em uma aplicação nas tarefas mais diversas, como clas-sificação de textos, robôs de bate-papo, sumarização, tradução de idioma, etc. Bibliotecas como a Gensim e a NLTK auxiliam tanto nos processos de criação e treinamento de um modelo quanto nas fases de pré-processamento dos dados para remover palavras e outros elementos textuais indesejados. Além disso, por meio delas, você consegue compartilhar os modelos criados e usar outros modelos pré-treinados por terceiros para seus projetos, reduzindo, assim, o custo computacional e o tempo e o custo de desenvolvimento para obter soluções de alto desempenho.

BLEI, D. M. Surveying a suíte of algorithms that offer a solution to managing large do-cument archuves. Communication ofthe ACM, [s. l.], v. 55, n. 2, p. 77–84, 2012. Disponível em: http://www.cs.columbia.edu/~blei/papers/Blei2012.pdf. Acesso em: 28 abr. 2020.

FRANCIS, W. N.; KUCERA, H. Brown corpus manual. 1979. Disponível em: http://korpus. uib.no/icame/manuals/BROWN/INDEX.HTM. Acesso em: 28 abr. 2020.

RARE TECHNOLOGIES. Gensim-data. [2018]. Disponível em: https://github.com/RaRe--Technologies/gensim-data. Acesso em: 28 abr. 2020.

ŘEHŮŘEK, R. Core concepts. [2019a]. Disponível em: https://radimrehurek.com/gensim/ auto_examples/core/run_core_concepts.html#sphx-glr-auto-examples-core-run-core--concepts-py. Acesso em: 28 abr. 2020.

ŘEHŮŘEK, R. Models.word2vec: Word2vec embeddings. [2019c]. Disponível em: https:// radimrehurek.com/gensim/models/word2vec.html. Acesso em: 28 abr. 2020.

ŘEHŮŘEK, R. Utils: various utility functions. [2019b]. Disponível em: https://radimrehurek. com/gensim/utils.html. Acesso em: 28 abr. 2020.

Leitura recomendada

SEAGATE. Data age 2025: the digitalization of the world. [2018]. Disponível em: https:// www.seagate.com/br/pt/our-story/data-age-2025/. Acesso em: 28 abr. 2020.

## Page 203

Reader pageid: 202

### Reader text

Representação vetorial de textos —utilizando word embeddings em Python 203

Os links para sites da web fornecidos neste capítulo foram todos testados, e seu fun-cionamento foi comprovado no momento da publicação do material. No entanto, a rede é extremamente dinâmica; suas páginas estão constantemente mudando de local e conteúdo. Assim, os editores declaram não ter qualquer responsabilidade sobre qualidade, precisão ou integralidade das informações referidas em tais links.

## Page 204

Reader pageid: 203

### Reader text

Esta página foi deixada em branco intencionalmente.
