---
id: "24"
title: "Representação vetorial de textos - bag of words"
source_title: "Processamentos de Linguagem Natural"
resource_code: "9786556900575"
scope_kind: "pages"
scope_value: "pages 117-130"
final_url: "https://integrada.minhabiblioteca.com.br/reader/books/9786556900575/pageid/129"
captured_at: "2026-05-12T07:33:11.087015Z"
---

# Representação vetorial de textos - bag of words
## Page 117

Reader pageid: 116

### Reader text

Representação vetorial de textos — bag of words

Objetivos de aprendizagem Ao final deste texto, você deve apresentar os seguintes aprendizados:

„ Descrever como o computador realiza a interpretação de dados tex-tuais por conversão numérica.

„ Definir o conceito de vetorização de palavras. „ Analisar o método bag of words.

Introdução

O algoritmo bag ofwords é uma técnica de processamento de linguagem natural usado para extrair características de um texto/documento, a partir da contagem da frequência das palavras em um documento. Nesse contexto, um documento pode ser definido conforme necessário como uma frase única ou toda a Wikipédia. A saída desse algoritmo é um vetor de frequência dos tokens no vocabulário. Para implementar e aplicar esse algoritmo, é preciso compreender

alguns passos, como limpar o texto, definir e extrair os tokens e construir um vocabulário. Neste capítulo, observaremos como os algoritmos de aprendizagem de máquina esperam receber os dados de entrada, o que é a vetorização de textos e sua importância para o bom funcionamento de alguns algoritmos, bem como aprender a executar o método de vetorização bag of words.

## Page 118

Reader pageid: 117

### Reader text

118 Representação vetorial de textos — bag of words 1 Interpretação de dados textuais

Computadores trabalham com bases numéricas, mais especificamente sequên-cias binárias que indicam ou não a passagem de corrente elétrica por seus componentes de hardware. Quando usamos algum programa ou navegamos na internet, existem várias camadas que convertem a informação que nós vemos para a informação que a máquina é capaz de compreender, ou seja, números e corrente elétrica. Em aplicações de processamento de linguagem natural, ocorre algo se-melhante: o objeto do processamento da linguagem natural reside no fato de que a máquina consiga compreender e se comunicar com pessoas por meio da linguagem comum aos seres humanos; para isso, a linguagem como nós conhecemos deve ser tratada e convertida para a linguagem que a máquina possa compreender. Geralmente, no processamento de linguagem natural temos um algoritmo

de aprendizagem de máquina para extrair conhecimento dos dados passados a ele, aprendendo, de modo geral, a realizar um mapeamento de um valor de entrada para determinado valor de saída. Os algoritmos de aprendizado de máquina são descritos como o aprendizado

de uma função de destino (f) que mapeia melhor as variáveis de entrada (X) para uma variável de saída (Y) (BISHOP, 2006).

Y = f(X) Essa é uma tarefa geral de aprendizado em que gostaríamos de fazer previ-sões no futuro (Y), dados novos exemplos de variáveis de entrada (X). Como não sabemos como é a função (f) ou sua forma, usamos um algoritmo de aprendizagem de máquina para descobri-las. Nos algoritmos de aprendizagem de máquina, também existe um erro (e)

independente dos dados de entrada (X). Y = f (X) + e

Esse erro pode não ter atributos suficientes para caracterizar da melhor

forma de mapeamento de X para Y, sendo chamado de erro irredutível porque, por melhor que seja a estimativa da função de destino (f), não podemos reduzir esse erro. Tanto a função e o erro são valores numéricos.

## Page 119

Reader pageid: 118

### Reader text

Representação vetorial de textos — bag of words 119 Embora cada algoritmo de aprendizagem de máquina tenha implementações

diferentes das funções de aprendizado, geralmente se baseiam em valores nu-méricos, alguns em cálculos estatísticos e outros usando medidas de distância, mas sempre necessitando de valores numéricos para funcionar corretamente. Assim, podemos dizer que inicialmente em um projeto de processamento

de linguagem natural, o objetivo consiste em transformar textos em números, ou seja, em índices significativos, que podem, então, ser incorporados em outras análises, como classificação supervisionada ou não supervisionada.

2 Vetorização de textos

Os algoritmos de aprendizado de máquina operam em um espaço de recurso numérico, esperando entrada como uma matriz bidimensional em que linhas são instâncias e colunas, recursos ou características (BISHOP, 2006). Para realizar o aprendizado de máquina em texto, precisamos transformar nossos documentos em representações vetoriais, a fim de poder aplicar o aprendizado de máquina numérico, processo que leva o nome de extração de características ou vetorização e compreende um primeiro passo essencial para a análise sensível ao idioma (BENGFORT; BILBRO; OJEDA, 2018). Ao processar o texto em linguagem natural, para extrair informações

úteis de determinadas palavras usando técnicas de aprendizado de máquina, a palavra, ou o texto, deve ser convertida em um conjunto de números reais, ou seja, um vetor. Representar documentos numericamente nos permite exe-cutar análises significativas e cria as instâncias nas quais os algoritmos de aprendizado de máquina conseguem trabalhar e extrair conhecimento. Na análise de texto, as instâncias são documentos ou enunciados inteiros,

que podem variar em comprimento, mas cujos vetores têm sempre tama-nho uniforme (BENGFORT; BILBRO; OJEDA, 2018). Cada propriedade da representação vetorial é uma característica. Para o texto, as características representam atributos e propriedades dos documentos, incluindo seu conteúdo e meta atributos, como comprimento do documento, autor, fonte e data da publicação. Quando considerados juntos, as características de um documento descrevem um espaço multidimensional no qual os métodos de aprendizado de máquina podem ser aplicados.

## Page 120

Reader pageid: 119

### Reader text

120 Representação vetorial de textos — bag of words Para compreender melhor como os algoritmos de aprendizado de má-quina funcionam em relação ao processamento de textos, precisamos mudar a maneira como pensamos sobre a linguagem, de uma sequência de palavras para pontos que ocupam um espaço semântico. Os pontos no espaço podem estar próximos ou distantes, bem agrupados ou distribuídos uniformemente. O espaço semântico é, portanto, mapeado de tal maneira que documentos com significados semelhantes estão mais próximos e aqueles que são diferentes estão mais afastados. Ao codificarmos a similaridade como a distância, podemos começar a derivar os componentes principais dos documentos e traçar limites de decisão em nosso espaço semântico. A codificação mais simples do espaço semântico consiste no modelo de

saco de palavras, cuja ideia principal reside no fato de que o significado e a semelhança são codificados no vocabulário — por exemplo, os artigos da Wikipédia sobre futebol e Pelé são provavelmente muito semelhantes; não apenas muitas das mesmas palavras aparecerão em ambas, como também não compartilharão muitas palavras em comum com artigos sobre caçarolas ou flexibilização quantitativa. Embora simples, esse modelo é extremamente eficaz.

Muitas vezes, para programar em alguma linguagem e testar algumas de suas fun-cionalidades, temos certo trabalho para encontrar todos os pacotes necessários e configurar o ambiente de desenvolvimento. Algumas ferramentas podem ajudar nesse processo, como é o caso da Anaconda, uma distribuição gratuita e de código aberto das linguagens de programação Python/R para computação científica, que visa a simplificar o gerenciamento e a implantação de pacotes. Para testar o pacote nltk e sua implementação do algoritmo bag of words no Python, basta acessar o link e instalar a Anaconda.

## Page 121

Reader pageid: 120

### Reader text

Representação vetorial de textos — bag of words 3 Algoritmo bag of words

Método usado para extrair características e informações de um texto, geralmente é empregado em conjunto com outros algoritmos no processo de aprendizagem de máquina, já que as características fornecidas por ele são utilizadas na fase de treinamento de algoritmos de aprendizagem de máquina, como o Naive Bayes (SARKAR, 2016). Resumidamente, o algoritmo bag of words (“saco de palavras”) gera um conjunto de palavras de um texto, sendo amplamente utilizado na recuperação de informações de documentos, classificação de documentos e processamento de linguagem natural de forma geral (JURAFSKY, 2000). Pode-se dividir em quatro etapas:

1. Limpar o texto: as palavras sem relevância para o conteúdo são re-movidas, como as stopwords, artigos, verbos de ligação ou o que o programador definir como não relevantes. Nessa etapa, também é removida a pontuação do texto.

2. Extrair os tokens: o texto é separado em tokens, conforme a necessidade da aplicação. Geralmente, cada palavra é considerada um token, mas podemos considerá-los também frases inteiras ou sílabas.

3. Construir o vocabulário: após a limpeza do texto e a extração de tokens, construímos o vocabulário com os tokens extraídos.

4. Gerar os vetores: são gerados os vetores com as características do texto. Para cada token, associa-se sua frequência no texto.

Para compreender melhor esses conceitos e como são aplicados, analisa-remos o texto a seguir. Paulo e Cintia foram ao cinema sem comprar ingressos. Não havia

mais ingressos à venda, então Paulo comeu bolo e Cintia comeu pipoca. Essas frases podem ser representadas como uma coleção de palavras da

seguinte forma: [‘Paulo’, ‘e’, ‘Cintia’, ‘foram’, ‘ao’, ‘cinema’, ‘sem’, ‘com-prar’, ‘ingressos’, ‘Não’, ‘havia’, ‘mais’ ,‘ingressos’, ‘à’, ‘venda,’, ‘então’, ‘Paulo’, ‘comeu’, ‘bolo’, ‘e’, ‘Cintia’, ‘comeu’, ‘pipoca’]

121

## Page 122

Reader pageid: 121

### Reader text

122 Representação vetorial de textos — bag of words Após termos uma coleção de palavras, devemos remover aquelas repeti-das e contar a ocorrência de cada uma delas. O resultado desta operação é mostrado a seguir.

Palavra

Paulo Cintia

e foram ao cinema sem

comprar ingressos

Não

Havia mais à

venda então

comeu bolo

2 2 2 1 1 1 1 1 2 1 1 1 1 1 1 2 1

Neste pequeno texto, vemos que as palavras com mais frequência são:

Paulo, e, Cintia e comeu; todas aparecendo duas vezes no texto. No formato de vetor, a representação do resultado de ocorrências é:

{“Paulo”: 2, ‘e’: 2, ‘Cintia’: 2, ‘foram’: 1, ‘ao’: 1, ‘cinema’: 1, ‘sem’: 1, ‘comprar’: 1, ‘ingressos’: 2, ‘Não’: 1,

Quantidade de ocorrências

‘havia’: 1, ‘mais’: 1 ‘à’: 1, ‘venda,’: 1, ‘então’: 1, ‘comeu’: 2, ‘bolo’: 1,‘pipoca’: 1}

## Page 123

Reader pageid: 122

### Reader text

Representação vetorial de textos — bag of words 123 Essa estrutura na linguagem Python compreende um dicionário no qual a

palavra indica a chave e a quantidade aponta o valor associado à chave. A essa estrutura que criamos com todas as palavras e a e sua respectiva contagem, damos o nome de vocabulário, por meio do qual podemos criar vetores para cada frase do texto. Por padrão, o tamanho do vetor gerado é sempre igual ao tamanho do vocabulário; nesse caso, o vetor terá o tamanho 18. O vetor deve ser inicializado com todos os índices com valores zero:

[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] O vetor gerado para a primeira frase “Paulo e Cintia foram ao cinema sem

comprar ingressos.” é:

[2,2,2,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0] Nesse vetor, observamos que existem muitos elementos iguais a zero,

o que ocorre sempre que o tamanho do vocabulário for muito grande ou mesmo quando houver variações das palavras. Essa quantidade de elementos iguais a zero acaba gerando vetores que chamamos de esparsos, o que pode configurar um problema para armazenar e manipular esses dados. Uma das maneiras de reduzir o tamanho do vocabulário consiste em remover as palavras sem relevância para o significado geral, como os artigos o, a, os, as, e, ao. No nosso exemplo, podemos diminuir o vocabulário para o tamanho quinze removendo essas palavras. A linguagem de programação Python fornece diversos pacotes com métodos

para aplicações científicas, como os pacotes scipy e nltk; o último fornece um conjunto de bibliotecas com métodos para processamento de linguagem natural para inglês, no entanto também é possível usá-lo para a língua portuguesa. A biblioteca Scikit-Learn é uma biblioteca de aprendizado de máquina

gratuita e de código aberto escrita na linguagem Python, a qual oferece di-versos métodos para implementar algoritmos de aprendizagem de máquina e inteligência artificial, como regressão linear, classificadores, SVM, redes neurais convolucionais, etc. (BENGFORT; BILBRO; OJEDA, 2018), além de dispor de alguns conjuntos de dados com amostras que podem ser usados diretamente para treinamento e teste dos algoritmos.

## Page 124

Reader pageid: 123

### Reader text

124 Representação vetorial de textos — bag of words Essa biblioteca também fornece métodos para vetorização de textos, por

meio dos quais é possível aplicar as etapas do bag ofwords de maneira eficiente e mesmo aplicar pré-processamento e regras sobre o número e a frequência dos termos. O Scitkit-Learn oferece três principais tipos de vetorizadores de textos (SARKAR, 2016):

1. CountVectorizer: o mais simples, conta o número de vezes que um termo aparece no documento e usa esse valor como peso.

2. HashVectorizer: oferece boa eficiência em relação ao uso da memória. Em vez de armazenar as palavras como strings, o vetorizador aplica um hash para codificá-los como índices numéricos. A desvantagem desse método reside no fato de que, uma vez vetorizado, os nomes das características não podem mais ser recuperados.

3. TF-IDFVectorizer: TF-IDF significa “frequência de documento inversa à frequência do termo”, indicando que o peso atribuído a cada termo não depende apenas de sua frequência em um documento, mas também de sua recorrência em todo um conjunto de documentos.

O método CountVectorizer pode receber os seguintes parâmetros (PEDREGOSA et al., 2011):

„ Input: {‘filename’, ‘file’, ‘content’}: se filename, espera-se que a sequência passada como um argumento adequado seja uma lista de nomes de arquivos que precisam ser lidos para buscar o conteúdo bruto a ser analisado. Se file, os itens da sequência devem ter um método de leitura chamado para buscar os bytes na memória. Caso contrário, espera-se que a entrada seja uma sequência de itens do tipo string ou byte.

„ Encoding: por padrão, o tipo de encoding é o utf-8. Se forem fornecidos bytes ou arquivos para análise, usaremos essa codificação para decodificar.

„ decode_error {‘strict’, ‘ignore’, ‘replace’} : instruções sobre o que fazer se for fornecida uma sequência de bytes para analisar que contém caracteres que não fazem parte da codificação especificada. Por padrão, o valor é strict, o que significa que um UnicodeDecodeError será gerado. Outros valores são ignore e replace.

## Page 125

Reader pageid: 124

### Reader text

Representação vetorial de textos — bag of words 125

„ strip_accents {'ascii', 'unicode', None}: remove os acentos e executa a normalização de outros caracteres durante a etapa de pré-processamento. ASCII é um método rápido que funciona apenas em caracteres com um mapeamento ASCII direto. Já o Unicode é um método um pouco mais lento que funciona em qualquer caractere. O None não faz nada.

„ Lowercase boolean: por padrão, é verdadeiro. Converte todos os caracteres em minúsculas antes de tokenizar.

„ Preprocessor callable ou None (padrão): pré-processador programável ou substitui o estágio de pré-processamento (transforma-ção de cadeia), preservando as etapas de geração de token e n-gramas. Aplica-se apenas se o analisador não puder ser chamado.

„ Tokenizer callable ou None (padrão): substitui a etapa de tokenização de cadeia, preservando as etapas de pré-processamento.

„ stop_words: se for para língua inglesa, existe uma lista de stop words predefinida. Se for uma lista, presume-se que ela contenha stopwords, removidas dos tokens resultantes.

„ token_pattern: expressão regular que denota o que constitui um token. O regexp padrão seleciona tokens de dois ou mais caracteres alfanuméricos; a pontuação é completamente ignorada e sempre tratada como um separador de token.

„ ngram_rangetuple (min_n, max_n): por padrão, é (1, 1), indicando o limite inferior e superior do intervalo de valores n para diferentes palavras n-gramas ou n-gramas de caracteres a serem extra-ídos. Todos os valores de n tais que min_n <= n <= max_n serão usados. Por exemplo, um intervalo de n-grama de (1, 1) significa apenas unigramas, (1, 2) significa unigramas e bigramas e (2, 2) significa apenas bigramas. Aplica-se apenas se o analisador não puder ser chamado.

„ analyzerstring, {'word', 'char', 'char_wb'}: a opção char_wb cria caracteres n-gramas apenas a partir do texto dentro dos limites das palavras; n-gramas nas bordas das palavras são preenchidos com espaço. Se uma chamada for aprovada, ela será usada para extrair a sequência de características da entrada bruta e não processada. Está presente, desde a versão 0.21, se a entrada for nome de arquivo ou arquivo; os dados são lidos primeiro a partir do arquivo e, depois, passados para o analisador de chamada especificado.

## Page 126

Reader pageid: 125

### Reader text

126 Representação vetorial de textos — bag of words

„ max_dffloat no intervalo [0,0, 1,0] ou int, padrão = 1,0: ao criar o vocabulário, ignora os termos que têm uma frequência de documento estritamente maior que o limite fornecido. Se float, o parâmetro representa uma proporção de documentos, número absoluto de contagens.

„ min_dffloat no intervalo [0,0, 1,0] ou int, padrão = 1: ao criar o vocabulário, ignora os termos que tenham uma frequência de documento estritamente menor que o limite especificado. Esse valor também é chamado de corte na literatura. Se float, o parâmetro re-presenta uma proporção de documentos, número absoluto de contagens.

„ max_features int ou None: por padrão, é None; caso contrário, cria um vocabulário que considera apenas as principais características máximas ordenadas por frequência do termo no texto. Esse parâmetro será ignorado se o vocabulário não for None.

„ Vocabulary: um mapeamento (p. ex., um ditado) em que chaves são termos e valores, índices na matriz de características ou uma iterável sobre os termos. Se não for fornecido, um vocabulário é determinado a partir dos documentos de entrada. Os índices no mapeamento não devem ser repetidos e apresentar nenhum intervalo entre 0 e o maior índice.

„ Binary boolean: por padrão, é False; se o valor for True, todas as contagens diferentes de 0 são definidas como 1. Isso é útil para modelos probabilísticos discretos que modelam eventos binários em vez de contagens inteiras.

„ Dtype type: indica o tipo da matriz retornada por fit_transform () ou transform ().

Para compreender como o CountVectorizer funciona no Python,

implementaremos um método. Para usar o método CountVectorizer, devemos importá-lo da seguinte forma:

## Page 127

Reader pageid: 126

### Reader text

Representação vetorial de textos — bag of words 127 Com a biblioteca e o método importado, definiremos o texto que será ve-torizado. Na prática, em um processo de análise de linguagem natural, o texto geralmente estará em sites na internet, em documentos e arquivos de diferentes formatos e fontes, mas, para exemplificar como aplicar o CountVectorizer, usaremos um texto curto:

Primeiro, devemos instanciar o método: O parâmetro lowercase recebe o valor False para indicar que todas

as letras devem permanecer com o mesmo case, ou seja, as maiúsculas per-manecem maiúsculas. Se o valor de lowercase fosse True, todas as letras seriam convertidas para minúsculas. Após a instanciação do objeto para a vetorização do texto por meio do método CountVectorizer, podemos gerar a matriz termo-documento por meio do método fit_transform.

Para recuperar as características do texto, basta aplicar o método get_features_names():

## Page 128

Reader pageid: 127

### Reader text

128 Representação vetorial de textos — bag of words Com esses três passos, temos os vetores gerados com a frequência de cada

termo. A esses passos, acrescentamos um método para apresentar os vetores em uma matriz. Na Figura 1, você pode ver o código completo.

Figura 1. Código em Python com exemplo de utilização do CountVectorizer. A matriz termo-documento gerada é apresentada a seguir.

Doc0 Doc1

0 1

1 0

1 1

0 1

1 0

0 1

0 1

1 0

1 0

0 1

1 0

Neste No

chuva houve há

intensa inverno mais

muito não

verão

## Page 129

Reader pageid: 128

### Reader text

Representação vetorial de textos — bag of words 129

BENGFORT, B.; BILBRO, R.; OJEDA, T. Applied text analysis with python: enabling language--aware data products with machine learning. [S. l.]: O'Reilly Media, 2018.

BISHOP, C. M. Pattern recognition and machine learning. [S. l.]: Springer, 2006. JURAFSKY, D. Speech & language processing. [S. l.]: Pearson Education, 2000.

PEDREGOSA, F. et al. Scikit-learn: machine learning in Python. Journal ofMachine Learning Research, v. 12, p. 2825–2830, 2011.

SARKAR, D. Text analytics with Python: a practical real-world approach to gaining ac-tionable insights from your data. Bangalore: Apress, 2016.

Os links para sites da web fornecidos neste capítulo foram todos testados, e seu fun-cionamento foi comprovado no momento da publicação do material. No entanto, a rede é extremamente dinâmica; suas páginas estão constantemente mudando de local e conteúdo. Assim, os editores declaram não ter qualquer responsabilidade sobre qualidade, precisão ou integralidade das informações referidas em tais links.

## Page 130

Reader pageid: 129

### Reader text

Esta página foi deixada em branco intencionalmente.
