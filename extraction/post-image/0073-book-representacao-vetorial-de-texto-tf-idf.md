---
id: "73"
title: "Representação vetorial de texto TF-IDF"
source_title: "Processamentos de Linguagem Natural"
resource_code: "9786556900575"
scope_kind: "pages"
scope_value: "pages 131-144"
final_url: "https://integrada.minhabiblioteca.com.br/reader/books/9786556900575/pageid/143"
captured_at: "2026-05-12T08:10:05.080604Z"
---

# Representação vetorial de texto TF-IDF
## Page 131

Reader pageid: 130

### Reader text

Representação vetorial de texto TF-IDF

Objetivos de aprendizagem Ao final deste texto, você deve apresentar os seguintes aprendizados:

„ Analisar o método TF-IDF. „ Diferenciar os métodos bag of words e TF-IDF. „ Aplicar o método TF-IDF em programação.

Introdução

A recuperação de informação em textos constitui uma das principais áreas do processamento de linguagem natural (PLN), na qual analisar documentos e identificar características importantes capazes de revelar in-formações sobre os documentos são atividades cada vez mais requeridas. Neste capítulo, você conhecerá um pouco mais sobre o método

TF-IDF (term frequency-inverse document frequency) e como ele processa textos para extrair características, além das principais diferenças do TF-IDF e do bag ofwords, e como aplicar esse algoritmo utilizando a linguagem de programação Python.

1 Definição do método TF-IDF

Com o desenvolvimento da tecnologia, os documentos virtuais têm se tornado o principal método de armazenamento de informações comerciais e mesmo pessoais, cuja maioria provêm de textos, embora os paradigmas de desenvol-vimento tradicionais de software não consigam compreender a relação confusa e ambígua existente nos documentos de textos virtuais (MACHADO et al., 2010). A partir disso, surgiu a necessidade de técnicas para extrair informa-ções fundamentando-se em bases textuais, denominada mineração de textos, um campo multidisciplinar composto por conhecimentos das áreas de infor-mática, linguística estatística e ciência cognitiva.

## Page 132

Reader pageid: 131

### Reader text

132 Representação vetorial de texto TF-IDF A mineração de textos consiste em extrair padrões, regularidades ou ten-dências de grandes volumes de texto em linguagem natural com finalidades específicas. Entre suas diversas abordagens disponíveis, há o term frequency--inverse document frequency (TF-IDF), no qual duas métricas podem ser representadas por (SARKAR, 2016):

tfidf = tf ∙ idf Em que tf é o mesmo calculado na abordagem bag of words, ou seja,

calcula-se a frequência em que determinado termo aparece no documento. Como todo documento tem um tamanho diferente, alguns termos podem aparecer em maior quantidade em documentos longos em relação aos mais curtos. Considerando esse aspecto, a métrica de frequência sempre se divide pelo tamanho do documento, mensurado por meio da quantidade de termos em um documento; assim, quanto maior a frequência do termo, maior será a sua importância. Com isso, tem-se que:

E idf mede a “importância” de um termo em um conjunto de documentos.

Nesse cálculo, os termos que aparecem com muita frequência em todos os do-cumentos têm os pesos diminuídos, e aqueles menos comuns são aumentados; assim, quanto maior a frequência nos documentos, menor será a importância do termo (JURAFSKY; MARTIN, [2020]). Em que:

Ao obter os valores de tf e idf, é possível efetuar o produto e encontrar o tfidf.

## Page 133

Reader pageid: 132

### Reader text

Representação vetorial de texto TF-IDF 2 Bag of words vs. TF-IDF

Atualmente, estão disponíveis diversos modelos para o processamento de textos. Nesta seção, discutiremos sobre as particularidades dos algoritmos bag of words e TF-IDF. A principal diferença entre os dois modelos reside em seu comportamento,

já que o bag of words se refere a qual tipo de informação se pode extrair de um documento (palavras), e o TF-IDF faz menção à estrutura de dados de cada documento, ou seja, provê um vetor de características dos pares termo a termo (JURAFSKY; MARTIN, [2020]). Um dos maiores problemas do algoritmo bag of words é o fato de não considerar o contexto no qual os termos estão inseridos, levando em conta na sua análise na etapa de extração de características somente a quantidade de vezes em que um termo aparece. Assim, palavras que se repetem muitas vezes em um texto acabam ganhando destaque em processos de extração de conhecimento. Considere um texto em que se aplicará a técnica bag ofwords sem realizar

nenhum tipo de limpeza prévia no texto. Esse texto provavelmente estaria cheio de artigos, proposições e palavras irrelevantes para o significado do texto. A técnica TF-IDF consegue contornar esse problema do bag of words, visto compreender uma medida estatística numérica capaz de identificar a impor-tância de uma palavra para um documento em uma coleção de documentos (SARKAR, 2016; JURAFSKY; MARTIN, [2020]). O bag of words lista a contagem de palavras por documento. Na matriz

em que as palavras e os documentos que efetivamente se tornam vetores são armazenados, cada linha é uma palavra, cada coluna um documento e cada célula o número de vezes das palavras no texto (JURAFSKY; MARTIN, [2020]). Cada um dos documentos no conjunto é representado por colunas de igual comprimento, os vetores de contagem de palavras que não consideram o contexto. O valor de TF-IDF aumenta proporcionalmente ao número de vezes em

que uma palavra aparece no documento e é compensado pelo número de documentos no conjunto que contêm a palavra, o que ajuda a ajustar o fato de que algumas palavras são mais frequentes. O TF-IDF é um dos esque-mas de ponderação de termos mais populares, usado por 83% dos sistemas de recomendação baseados em texto nas bibliotecas digitais (BENGFORT; BILBRO; OJEDA, 2018).

133

## Page 134

Reader pageid: 133

### Reader text

134 Representação vetorial de texto TF-IDF 3 TF-IDF em Python

Na linguagem Python, após compreender o conceito da abordagem TF-IDF é possível implementar manualmente desde o código de bag ofwords até utilizar bibliotecas que já efetuam o cálculo diretamente com poucas linhas de código. Neste capítulo, observaremos o funcionamento da classe TfidfVectorizer da biblioteca sklearn.feature_extraction.text, que converte uma coleção de documentos brutos em uma matriz de recursos TF-IDF (Quadro 1).

Quadro 1. Parâmetros da classe TfidfVectorizer Parâmetro Input Encoding Decode_error Strip_accents Lowercase

Preprocessor Tokenizer

Analyzer Stop_words Token_pattern Ngram_range Max_df Descrição

Entrada a ser processada, que pode ser uma sequência de caracteres ou um arquivo

Codificação do texto. Por padrão, utiliza-se utf-8

Instrução sobre o que fazer quando do recebimento de uma sequência de bytes que contém caracteres não especificados em encoding

Remove os acentos durante uma etapa de pré-processamento

Converte todos os caracteres para minúsculo Substitui a etapa de pré-processamento Substitui a etapa de tokenização Deverá conter palavras ou caracteres

Palavras que deverão ser retiradas de acordo com a linguagem (p. ex., ‘portugues’)

Expressão regular que determina o padrão de um token

Limites inferior e superior da faixa de valores n para diferentes n gramas a serem extraídos

Ignorar termos com frequência maior que a estabelecida

(Continua)

## Page 135

Reader pageid: 134

### Reader text

Representação vetorial de texto TF-IDF (Continuação) Quadro 1. Parâmetros da classe TfidfVectorizer Parâmetro Min_df Max_features Vocabular Descrição

Ignorar termos com frequência menor que a estabelecida

Se o valor for None, constrói um vocabulário com o máximo de tokens do texto; caso contrário, é ignorado

Mapeamento em que chaves são termos e valores, índices na matriz de features ou uma iterável sobre os termos

Binary

Dtype Norm

Use_idf Smooth_idf

Todas as contagens diferentes de zero passam a ser 1, indicando somente as que repetem e não repetem

Tipo da matriz retornada em fit_transform() Utilizada para normalizar os vetores do termo

Ativa a ponderação inversa da frequência de documentos

Suaviza os pesos de IDF adicionando 1 às frequências do documento. O algoritmo entende que cada termo existe pelo menor uma vez no texto. Impede divisões por zero

Sublinear_tf

Aplica a escala sublinear para TF, ou seja, substitui TF por 1 + log(tf)

Fonte: Adaptado de The scikit-learn Developers (2018). 135 No exemplo de utilização da classe para extrair informações de textos,

empregaremos textos originados de pesquisas do site Wikipédia. Para isso, o Python fornece a biblioteca wikipedia, mas também poderia ser um vetor com frases. Para instalar a biblioteca, basta aplicar o comando pip install wikipedia no terminal (Figura 1).

## Page 136

Reader pageid: 135

### Reader text

136 Representação vetorial de texto TF-IDF Figura 1. Utilização da biblioteca wikipedia. Na linha 1, fazemos a importação da biblioteca; na linha 3, alteramos a

linguagem da página com base na qual será feita (de acordo com as lingua-gens suportadas pela Wikipédia); e, na linha 4, utilizamos a função page(), em que passamos por parâmetro qual será o termo de busca a pesquisar na Wikipédia. No nosso caso, utilizamos o termo “Teste de sistema”. Observe que os espaços foram substituídos por sublinhado ( _). Além disso, chamamos content, que nos retornará o conteúdo da página após a busca e será armazenado na variável textoPagina. Ao executarmos o código, após a execução da linha 6, é apresentado o texto do conteúdo da página, como exposto no console da Figura 1. Utilizaremos também o módulo stopwords da biblioteca nltk.corpus.

nltk (natural language toolkit) é um conjunto de ferramentas para PLN. Para instalar a biblioteca, basta aplicar o comando pip install nltk no terminal. Ao utilizar algumas funções da biblioteca, será necessária a instalação de novos módulos. No nosso caso, usaremos o stopwords, devendo antes fazer o download diretamente pela biblioteca (Figura 2).

## Page 137

Reader pageid: 136

### Reader text

Representação vetorial de texto TF-IDF 137 Figura 2. Download de módulos utilizando a biblioteca nltk. Acesse o site oficial para saber mais sobre o conjunto de bibliotecas nltk. Para convertermos nossa coleção de documentos em uma matriz TF-IDF,

utilizaremos a classe TfidfVectorizer da biblioteca scikit-learn, como mencionado no início da seção. Para instalá-la, basta executar o comando pip install scikit-learn no terminal. Veja o resultado final de nosso exemplo na Figura 3.

Conheça o potencial da biblioteca scikit-learn acessando o site oficial Scikit-learn.

## Page 138

Reader pageid: 137

### Reader text

138 Representação vetorial de texto TF-IDF Figura 3. Exemplo da utilização de tf-idf em código. Das linhas 1 a 6, temos as importações das bibliotecas que utilizaremos

para construir nosso código. Na primeira linha, importamos a biblioteca wikipedia e, na linha 2, a biblioteca nltk. Como vimos no exemplo da Figura 2, a segunda biblioteca é necessária para efetuar o download do módulo que usaremos. Caso já tenha feito o download, esta linha pode ser removida com a sua chamada na linha 11. Vale lembrar que, caso queira executar o seu código em outro computador, e este precise de algum módulo externo e não tenha a chamada para seu download, o código pode não executar por falta de dependências. Em seguida, na linha 3 temos a importação do módulo que utilizaremos

(caso não tenha sido feito o download, o código apresentará erro), além da biblioteca numpy, para efetuar arredondamento de números, pandas, para criar dataFrames e facilitar a visualização do resultado, e a classe respon-sável por vetorizar nosso conteúdo, TfidfVectorizer. Nas linhas 8 e 9, alteramos a linguagem da wikipedia para português,

ou seja, estamos indicando que queremos efetuar uma busca na base de dados brasileira da wikipedia. Em seguida, buscamos pelo termo “Teste de sistema”. O método responsável por buscar a página é o page, e aquele por retornar o conteúdo é o content.

## Page 139

Reader pageid: 138

### Reader text

Representação vetorial de texto TF-IDF 139 Na linha 11, efetuamos o download do módulo stopwords. Em seguida,

nas linhas 13 e 14, indicamos ao nltk os STOPWORDS de qual linguagem usaremos para o processamento de textos. Podemos inserir mais de uma linguagem, mas, no exemplo, empregaremos português e inglês, para o caso de haver termos em inglês no conteúdo retornado da wikipedia. Das linhas 16 a 18, criamos uma função para apresentar o resultado forma-tado em formato de matriz, para que consigamos visualizar melhor os pesos atribuídos a cada palavra. Então, na linha 17, criamos um dataFrame , em que os dados serão os valores e os nomes das colunas, as palavras retornadas da busca. Por fim, na linha 18, imprimimos na tela o resultado. Das linhas 20 a 23, temos nossa função principal, e, na linha 21, criamos

uma variável que recebe a configuração da vetorização que desejamos para nosso cálculo de extração de características em texto. Como observado no Quadro 1, a classe TfidfVectorizer tem vários parâmetros, embora em nosso exemplo utilizemos apenas 1: o stop_words, para remover termos e palavras corriqueiras, como os artigos a e o, além de preposições e pronomes, que, para o algoritmo, são tratados como “lixos”, e passamos como valores os STOPWORDS definidos na linha 13. Nos restantes dos parâmetros, serão utilizados os valores-padrões. Para verificar a configuração para o Tfi-dfVectorizer, basta imprimir na tela a variável tfidf, quando teremos o resultado apresentado na Figura 4.

Figura 4. Resultado da configuração do tfidf.

## Page 140

Reader pageid: 139

### Reader text

140 Representação vetorial de texto TF-IDF

Na linha 1.286 do site Github, é possível observar um exemplo de implementação da classe TfidfVectorizer.

Podemos, assim, observar as configurações-padrões e os STOPWORDS

que delineamos. Na linha 22, chamamos a função fit_transform, que efetua a conversão dos textos em valores numéricos, promove a normalização dos dados e retorna os pesos de cada palavra. Caso façamos a impressão do retorno da variável X, teremos a situação apresentada na Figura 5.

Figura 5. Prévia do retorno de fit_transform.

Ao apresentarmos as características (linha 23) na chamada do método mostrar_caracteristicas, teremos o resultado apresentado na Figura 6, que são os mesmos valores da Figura 5, porém formatados em matriz. As linhas da primeira coluna de 0 a 7 indicam que o retorno do termo

de busca da wikipedia nos retornou 7 parágrafos, pois, na linha 22, com a chamada do método splitlines(), fazemos com que o conteúdo da página seja quebrado a cada parágrafo; para esse algoritmo, cada parágrafo é um documento. Para validar isso, observemos a Figura 7.

## Page 141

Reader pageid: 140

### Reader text

Representação vetorial de texto TF-IDF 141 Figura 6. Retorno de fit_transform formatado.

Figura 7. Retorno de textopagina.splitlines(). Fonte: Adaptada de Teste... (2008).

## Page 142

Reader pageid: 141

### Reader text

142 Representação vetorial de texto TF-IDF Podemos observar que, ao imprimir somente textopagina.spli-tlines(), é gerado um vetor, em que cada posição apresenta um parágrafo. As posições vazias foram promovidas provavelmente por haver quebras de linha após o último parágrafo, e, com isso, temos o cálculo de tfidf. Como podemos observar, as palavras que se repetem menos — como ambiente, anteriores e aspectos — apresentam pesos menores, apresentados na matriz na Figura 5, e, por consequência, maior importância.

BENGFORT, B.; BILBRO, R.; OJEDA, T. Applied text analysis with Python: enabling language--aware data products with machine learning. Sebastopol: O’Reilly, 2018. 312 p.

JURAFSKY, D. S.; MARTIN, J. H. Constituency parsing. In: JURAFSKY, D. S.; MARTIN, J. H. Speech and language processing. 3. ed. Upper Saddle River: Prentice Hall, [2020]. chap. 13. Disponível em: https://web.stanford.edu/~jurafsky/slp3/13.pdf. Acesso em: 9 mar. 2020.

MACHADO, A. P. et al. Mineração de Texto em Redes Sociais Aplicada à Educação a Distância. Colabor@ — Revista Digital da CVA — RICESU, Curitiba, v. 6, n. 23, p. 1–21, 2010.

SARKAR, D. Text analytics with Python: a practical real-world approach to gaining ac-tionable insights from your data. New York: Apress, 2016. 385 p.

TESTE de sistema: In: WIKIPÉDIA: a enciclopédia livre. [San Francisco: Wikimedia Foun-dation, 2008]. Disponível em: https://pt.wikipedia.org/wiki/Teste_de_sistema. Acesso em: 9 mar. 2020.

THE SCIKIT-LEARN DEVELOPERS. sklearn.feature_extraction.text.TfidfVectorizer. W3cub-Docs, [S. l.], 2018. Disponível em: https://docs.w3cub.com/scikit_learn/modules/gene-rated/sklearn.feature_extraction.text.tfidfvectorizer/. Acesso em: 9 mar. 2020.

Leitura recomendada

WHAT DOES tf-idf mean? Tf-idf :: A Single-Page Tutorial - Information Retrieval and Text Mining, [S. l.], [2019]. Disponível em: http://www.tfidf.com/. Acesso em: 9 mar. 2020.

## Page 143

Reader pageid: 142

### Reader text

Representação vetorial de texto TF-IDF 143

Todos os links para sites da web fornecidos neste capítulo foram testados, o que levou à comprovação de seu funcionamento no momento da publicação do material. No entanto, pelo fato de a rede ser extremamente dinâmica e suas páginas estarem constantemente mudando de local e conteúdo, os editores declaram não ter qualquer responsabilidade sobre a qualidade, a precisão ou a integralidade das informações referidas em tais links.

## Page 144

Reader pageid: 143

### Reader text

Esta página foi deixada em branco intencionalmente.
