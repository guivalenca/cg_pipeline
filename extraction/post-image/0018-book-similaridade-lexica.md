---
id: "18"
title: "Similaridade Léxica"
source_title: "Processamentos de Linguagem Natural"
resource_code: "9786556900575"
scope_kind: "pages"
scope_value: "pages 89-102"
final_url: "https://integrada.minhabiblioteca.com.br/reader/books/9786556900575/pageid/101"
captured_at: "2026-05-12T07:20:42.874437Z"
---

# Similaridade Léxica
## Page 89

Reader pageid: 88

### Reader text

Similaridade léxica Objetivos de aprendizagem

Ao final deste texto, você deve apresentar os seguintes aprendizados:

„ Definir o conceito de similaridade textual. „ Diferenciar o papel da similaridade textual em diferentes aplicações de processamento de linguagem natural.

„ Demonstrar métodos de aplicação de similaridade textual. Introdução

Um dos primeiros passos para entender o conceito de processamento de linguagem natural (PLN) é entender o que é similaridade textual. O que significa a similaridade? Como é calculada? Como é possível saber se dois textos são similares ou não? Existem várias maneiras de responder a essas perguntas feitas, porém

é importante saber em qual momento utilizar determinado método e diferenciar bem conceitos importantes. Neste capítulo, você aprenderá sobre similaridade léxica, o papel da

similaridade em diferentes aplicações do processamento de linguagem natural e os métodos da similaridade textual a partir de exemplos.

1 Similaridade textual

Um dos componentes principais no PLN, a similaridade textual consiste em determinar a proximidade ou o quão dois fragmentos de texto são similares. Gomaa e Fahmy (2013) afirmam que ela pode ser aplicada em diversas situa-ções, como classificação de texto, clusterização, sumarização de texto, detecção de tópicos, etc., e que que encontrar a similaridade entre palavras representa uma parte fundamental da similaridade textual, constituindo o primeiro está-gio para achá-la entre frases, parágrafos e documentos. A similaridade entre palavras é classificada em léxica e semântica, no entanto neste capítulo serão abordados os principais conceitos sobre similaridade léxica.

## Page 90

Reader pageid: 89

### Reader text

90 Similaridade léxica A similaridade léxica refere-se ao quanto dois fragmentos de texto são

similares. Por exemplo, apenas olhando as palavras, quão similares são as frases “os gatos comem os ratos” e “os ratos comem os insetos”? Se você considerar a similaridade no nível da palavra, ambas são similares em três palavras, como observado na sobreposição a seguir:

Frase 1: ‘Os’ ‘gatos’ ‘comem’ ‘os’ ‘ratos’ Frase 2: ‘Os’ ‘ratos’ ‘comem’ ‘os’ ‘insetos’ 1

2 3 Pelas similaridades contabilizadas, o exemplo tem três palavras similares,

noção conhecida como similaridade léxica, a qual não leva em consideração o significado das palavras ou da frase no contexto, que faz parte do papel da similaridade semântica. A similaridade léxica pode ser computada em determinados níveis de gra-nularidade, como de caractere, de palavra ou de frase, em que você particiona fragmentos de texto em um grupo de palavras relacionadas antes de calcular a similaridade. Em geral, a similaridade em nível de caractere é usada para determinar a proximidade de duas strings dos caracteres, por exemplo, quão similares são as palavras “corre” e “correr”? Para responder a essa questão, utilizam-se métricas e métodos já definidos na literatura. Essencialmente, a similaridade entre palavras pode ser verificada avaliando o número de operações para transformar uma string em outra. A Figura 1 mostra um exemplo de aplicação muito conhecida, o buscador

do Google. Assim, quando o usuário digita texto na caixa de pesquisa e clica em “Pesquisar” a partir do texto digitado, o site retornará as páginas mais relevantes. Nesse exemplo, digitou-se o seguinte texto de busca: “como estudar ead”.

Esse texto tem três palavras, consideradas pelos resultados retornados. Como pode ser observado na Figura 1, as três páginas com maior relevância apre-sentam as palavras “estudar” e “EAD” em seu conteúdo (ambas marcadas em bold). Nesse contexto, a similaridade textual ajuda a identificar os documentos mais similares a partir do que o usuário deseja pesquisar.

## Page 91

Reader pageid: 90

### Reader text

Similaridade léxica 91 Figura 1. Buscador Google.

2 Similaridade textual em diferentes aplicações de processamento de linguagem natural (PLN)

Diferentes abordagens foram propostas para medir a similaridade entre um texto e outro; conforme Gomaa e Fahmy (2013), uma métrica de string é aquela que mede a similaridade ou a dissimilaridade (distância) entre textos. Em seu trabalho, os autores mostram 14 algoritmos baseados em strings que fazem a comparação entre textos, citando duas categorias em que se pode classificar os algoritmos: baseado em caracteres e baseado em termos. A Figura 2 mostra os algoritmos de maneira esquematizada.

## Page 92

Reader pageid: 91

### Reader text

92 Similaridade léxica LCS

Damerau--Lavenshtein

Baseado em caracteres

Jaro-winkler Jaro

Needleman--Wunsch

Smith--Waterman N-gram

Baseados em string

Block distance

Cosine similarity

Dice’s coefficient

Baseado em termos

Euclidean distance

Jaccard similarity

Matching coefficient

Overlap coefficient

Figura 2. Algoritmos baseados em strings. Fonte: Adaptada de Gomaa e Fahmy (2013).

## Page 93

Reader pageid: 92

### Reader text

Similaridade léxica 93 Similaridade baseada em string é a mais antiga, simples e utilizada, ope-rando sobre sequências de string e composição de caractere. Já a similaridade baseada em caractere, também chamada de medição de

distância de edição, considera duas strings e, então, calcula a distância de edição (inserção, deleção e substituição) entre elas. Em outras palavras, dada uma string s1 e uma string s2, a distância de edição consiste no número de operações necessárias para transformar s1 em s2. Assim, duas strings podem ser consideradas similares se o valor da distância de edição for o menor possível ou menor que um limiar. Alguns exemplos de algoritmos que utilizam esta abordagem são: o longest

common subsequence (LCS), que leva em consideração o tamanho da cadeia contínua de caracteres entre duas strings; o Damerau-Levenshtein, que conta o número de operações para transformar uma string em outra; o Jaro, baseado no número e na ordem de caracteres comuns em duas strings; o Jaro-Winkler, uma extensão do algoritmo Jaro e que classifica melhor a similaridade de strings; o Needleman-Wunsch, que utiliza programação dinâmica; o Smith-Waterman, útil para sequências diferentes que dispõem de partes similares; e o N-gram, útil para aplicações que sugerem respostas automáticas. A similaridade baseada em termos é também chamada de similaridade

baseada em tokens, pois modela cada string como um conjunto de tokens. A similaridade entre strings pode ser encontrada a partir da manipulação dos conjuntos de tokens tal como palavras. Sua ideia principal consiste em execu-tar a medição de similaridade entre duas strings com base nos tokens gerais correspondente ao seu conjunto de tokens. Se a similaridade é encontrada, as duas strings são consideradas similares ou duplicadas. Essa abordagem é útil para reconhecer um termo no rearranjo de strings em substrings. Alguns exemplos de algoritmos que utilizam essa abordagem são: o cosine

similarity, que mede a similaridade de dois vetores; block distance, que calcula a distância de um ponto a outro; dice’s coefficient, calculado a partir do dobro de palavras em comum em dois textos dividido pelo número total de palavras nos dois textos; euclidean distance, que trabalha com a distância de elemen-tos em vetores; o jaccard similarity, que mede a similaridade de conjuntos; o matching coefficient, que conta o número de termos semelhantes em um vetor; e o overlap coefficient, que mede a sobreposição entre dois conjuntos finitos.

## Page 94

Reader pageid: 93

### Reader text

94 Similaridade léxica Existem diversos métodos para calcular a similaridade léxica, o que leva

à necessidade de entender em quais situações cada método pode ser utili-zado. Os métodos minimum edit distance, distância de Levenshein, N-Grams, similaridade de Jaccard e similaridade do cosseno serão estudados com mais detalhes a seguir, a fim de compreender melhor em que contextos são mais bem utilizados.

Minimum edit distance

O PLN é uma área que se preocupa em medir a máxima similaridade de duas strings. Em algumas aplicações, o usuário pode se comunicar por meio de comando de voz, situação na qual a correção de pronúncia é um exemplo em que se utiliza a PLN. Imagine que um usuário diga erroneamente uma expressão como “couer”, porém não era isso que ele queria dizer, e sim provavelmente

alguma palavra parecida com a expressão dita. Nesse contexto, a palavra “comer” que tem apenas uma letra diferente da expressão “couer” pode ser uma palavra candidata à correção, diferentemente da palavra “conter”, que se diferencia em mais letras. Ainda conforme Jurafsky e Martin (2009, p. 23): “[...] o minimum edit

distance entre duas strings é definido como o número mínimo de operações de edição (operações como inserção, exclusão e substituição) necessárias para transformar uma string em outra [...]”. Cada operação de inserção, deleção e substituição tem custo igual a 1. Por exemplo, dadas as seguintes strings:

1 — “ABADAC”; 2 — “CADA”.

Em quantas operações é possível transformar a string1 “ABADAC” na

string2 “CADA”? Você poderia sugerir excluir todas as letras da string1 ‘A’ - ‘B’ - ‘A’ - ‘D’ - ‘A’ - ‘C’ e inserir quatro letras ‘C’ - ‘A’ - ‘D’ - ‘A’. No total, seriam feitas 10 operações — 6 operações de exclusão e 4 operações de inserção —, mas este seria o menor número de operações possível e a maneira mais inteligente de fazê-lo? Não, pois seria bem mais custoso! A seguinte maneira poderia ser mais eficiente:

Passo 1 — Exclusão da primeira letra ‘A’ gerando a string “BADAC”; Passo 2 — Substituição da letra ‘C’ com a letra ‘B’ gerando “CADAB”; Passo 3 — Exclusão da letra ‘B’ gerando “CADA”.

## Page 95

Reader pageid: 94

### Reader text

Similaridade léxica 95 Assim, foram necessárias apenas 3 operações com um custo menor. Dessa

forma, deve-se encontrar o número mínimo de operações. Quanto menor o número mínimo de operações, maior é a similaridade entre duas strings.

Distância de Levenshtein

O método Distância de Levenshtein é parecido com o minimum edit distance, visto que as operações de inserção e deleção também apresentam custo igual a 1, embora a diferença entre os dois resida no fato de que a operação de substituição tem custo igual 2, já que ele considera a operação de substituição a soma de uma operação de deleção e uma operação de inserção. Então, para o exemplo de transformar a string1 “ABADAC” na string2 “CADA”, haveria o custo total de 4 operações.

1 operação de exclusão (custo 1) + 1 operação de substituição com

custo 2 (considerada uma inserção somada a uma exclusão) + 1 operação de exclusão (custo 1) = 4.

N-grams

Um dos métodos mais utilizados no processamento de linguagem natural consiste na modelagem de N-Gram. Um n-gram é uma sequência contínua de n itens dada uma sequência de texto. Em outras palavras, seja f1 uma frase, pode ser construída uma lista de n-grams de f1 achando pares de palavras que ocorrem ao lado umas das outras. Por exemplo, com a frase “Eu sou inteligente”, você pode construir n-grams de tamanhos de diferentes, como mostra o esquema a seguir:

1 — Unigramas (n-grams de tamanho 1): (“Eu”), (“sou”), (“inteligente”); 2 — Bigramas (n-grams de tamanho 2): (“Eu, “sou”), (“sou”, “inteligente”); 3 — Trigramas (n-grams de tamanho 3): (“Eu sou inteligente”).

Assim, você pode ter n-grams de tamanho! Quais são as aplicações desse

método? Podem ser listadas duas aplicações cotidianas, algumas das quais talvez você já tenha experimentado. Basta se lembrar da última que vez que você fez uma busca na internet: ao digitar as primeiras palavras na caixa de texto, o buscador sugeriu frases? Esse exemplo pode ser visualizado na Figura 3.

## Page 96

Reader pageid: 95

### Reader text

96 Similaridade léxica

Figura 3. Autocomplemento do Google. Fonte: Blog do Naguim (2011, documento on-line).

Outro exemplo: ao responder a um e-mail, o seu servidor de e-mail (p. ex.,

o Gmail) já sugeriu respostas prontas com base no conteúdo do e-mail? Dessa maneira, o método de N-Gram ajuda a “prever” possíveis frases ou palavras por meio da probabilidade, dado um contexto específico. Ao digitar na caixa de texto do seu buscador favorito a frase “Eu quero”,

quais palavras seriam sugeridas para completá-la? Jogar? Nadar? Estudar? Você entenderá esse cálculo a partir do seguinte texto:

Eu quero nadar na piscina. Eu quero comer peixe. Eu quero nadar

no riacho, pois é uma água mais doce. Eu quero estudar bastante para ser um bom profissional. Eu quero aprender.

Como calcular a probabilidade de aparecer a palavra “estudar” após a frase

“Eu quero”? Esse cálculo pode ser feito da seguinte maneira: p(estudar|Eu quero) = c(“Eu quero estudar”) / c(“Eu quero”) onde c é

o número de ocorrências = 1⁄5 = 20%.

## Page 97

Reader pageid: 96

### Reader text

Similaridade léxica 97 Em outras palavras, a probabilidade de aparecer a palavra “estudar” após

a frase “Eu quero” é de 20%, pois se divide o número de ocorrência da frase “Eu quero estudar” pelo número de frases “Eu quero” no texto. Essa é a base

que o método utiliza para ajudar nas mais diversas aplicações de predição de textos e palavras.

Similaridade de Jaccard

Essa abordagem mede o número de palavras comuns entre todas as palavras; quanto mais palavras comuns, maior é a similaridade. Sejam dois conjuntos A e B, a similaridade de Jaccard é definida por:

Similaridade de Jaccard = (Interseção de A e B) / (União de A e B) O valor dessa medida será um valor entre 0 e 1; se for 1, significa que são

idênticos, e, quanto mais perto de 0, menor a similaridade. Por exemplo, dadas as seguintes frases:

A — “Eu gosto de estudar e aprender”; B — “Eu quero entender o conteúdo e aprender”.

Interseção(A,B) = “Eu”, “e”, “aprender” = 3 ocorrências União(A,B) = 10

Assim, a similaridade de Jaccard é de 3/10 = 0,3. E, quanto maior esse valor,

maior a similaridade entre os conjuntos. Então, esse método pode ser mais bem empregado em situações que trabalham com conjuntos, como ao verificar a similaridade de conjuntos de dados provenientes de um banco de dados.

Similaridade de cosseno

Trata-se de um dos métodos capazes de verificar a similaridade de dois textos, como nos conhecidos sistemas de recomendação, quando como um site de notícias recomenda novos artigos a partir dos artigos já lidos anteriormente. Dadas as seguintes frases:

João te ama João te ama sim

## Page 98

Reader pageid: 97

### Reader text

98 Similaridade léxica O objetivo é encontrar a similaridade entre essas duas frases, para o qual

se fará uma lista de palavras de ambos os textos: “João”, “te”, “ama”, “sim”

Depois, contam-se quantas vezes cada palavra aparece em cada frase. Palavra Frase 1

“João” “te”

“ama” “sim”

1 1 1 0

1 1 1 1

Frase 2 São formados dois vetores verticais a partir das contagens, e se verificará a

similaridade desses dois textos a partir do cálculo da similaridade do cosseno, como visto na Figura 4.

similaridade

Figura 4. Fórmula da similaridade de cosseno. Fonte: Neo4j (2019, documento on-line).

## Page 99

Reader pageid: 98

### Reader text

Similaridade léxica 99

Não se preocupe, realizar o cálculo da similaridade de cosseno não é tão difícil como parece, como você perceberá a partir do passo a passo dado a seguir. Sejam os vetores:

a: [1,1,1,0] e b: [1,1,1,1] Cálculo do produto de vetores: a . b = 1 . 1 + 1 . 1 + 1 . 1 + 0 . 1 = 3

Cálculo da magnitude: |a| = √12

|b| = √12

+ √12 + √12

+ √12 + + √12 +

√02 √12

= √3= 1,732 = √4= 2

Cálculo do ângulo entre os vetores: cos α = a · b / |a| · |b| = 3/ 1,732 · 2 = 0,866

Se o resultado do

„ cos α = 1 → os vetores são paralelos e com mesmo sentido „ cos α = 0 → os vetores são perpendiculares „ cos α = –1 → os vetores são paralelos e com sentidos opostos

Em outras palavras, o intervalo do valor da função de cos α vai de –1 a 1, e, quanto

mais próximo de 1, maior a similaridade entre os textos. Assim, pode-se concluir que as duas frases são similares.

3 Métodos de aplicação de similaridade textual

Verificar a similaridade ou calcular a distância de similaridade representam aplicações para atividades como sistemas de recomendação, detecção de ano-malias, análise de sentimento, classificação de dados, etc. Medir a similaridade significa verificar o quanto dois objetos são iguais.

## Page 100

Reader pageid: 99

### Reader text

100 Similaridade léxica Cada método tem uma forma própria de cálculo, havendo diversas maneiras

de implementá-los capazes de calcular a similaridade entre textos ou dados. No contexto de PLN, o Python compreende uma das linguagens mais

utilizadas para implementação, a partir do qual serão apresentados alguns exemplos a seguir.

Para saber mais sobre exemplos de cálculo de similaridade textual usando Python, acesse o site Vulpi.

Implementação da similaridade de cosseno

Nesse tipo de implementação, como visto na Figura 5, são definidas duas funções: uma função que retorna a raiz quadrada de um número e outra função que faz o cálculo da similaridade de cosseno. A palavra reservada “round” é uma função que retorna um valor com ponto flutuante, como 2.3 e 5.6. E a função de similaridade_cosseno, que recebe dois vetores de objetos, representa uma tradução da fórmula da Figura 4.

Figura 5. Similaridade de cosseno em Python.

## Page 101

Reader pageid: 100

### Reader text

Similaridade léxica 101 Por fim, é impresso o valor retornado da função similaridade_cosseno,

que varia de –1 a 1, em que, quanto mais próximo de 1, maior a similaridade entre os objetos. No exemplo da Figura 5, a função similaridade_cosseno passa

os seguintes vetores para comparação: [1,1,1,0] e [1,1,1,1]. Como pode ser observado, a única diferença reside no fato de que, no primeiro vetor, o último elemento é 0. Então, a tendência é de que o resultado do cálculo da similaridade compreenda um valor próximo de 1, como você pode perceber no resultado da execução, que é o valor 0,866.

Implementação da similaridade de Jaccard

A implementação da similaridade de Jaccard utilizando a linguagem Python pode ser vista na Figura 6.

Figura 6. Similaridade de Jaccard em Python. Esse método recebe dois conjuntos como parâmetro — primeiro, faz-se

a interseção desses dois conjuntos utilizando a função pronta set.in-tersection, que, por sua vez, promove a interseção de dois objetos e os armazena em intersecao. Repete-se o mesmo passo, porém é feita a união dos dois conjuntos “a” e “b” utilizando a função pronta set.union, além do armazenamento em união. Assim, retorna-se um index a partir da divisão da interseção pela união. A impressão do valor é feita chamando a função similaridade_jac-card e passando dois vetores com valores. O valor que essa função retorna está entre 0 e 1; quanto mais próximo de 1, mais idênticos são os objetos analisados e, quantos mais próximo de 0, menos similares são os objetos.

## Page 102

Reader pageid: 101

### Reader text

102 Similaridade léxica No exemplo da Figura 6, é chamada a função similaridade_jaccard

passando os seguintes conjuntos para comparação: [4,1,1,1,3,6] e [1,2,6,9,10,5]. Como se pode observar, apenas os números ‘1’ e ‘6’ são comuns entre os dois conjuntos. Então a tendência é de que o resultado do cálculo da similaridade seja um valor próximo de 0, percebendo-se que o resultado da execução é o valor 0,25.

BLOG DO NAGUIM. O autocompletar do Google é eficiente. 2011. Disponível em: http:// naguim.blogspot.com/2011/04/o-auto-completar-do-google-e-eficiente.html. Acesso em: 8 mar. 2020.

GOMAA, W. H.; FAHMY, A. A. A survey of text similarity approaches. International Journal of Computer Applications, [s. l.], v. 68, n. 1, p. 13–18, 2013.

JURAFSKY, D.; MARTIN, J. H. Speech and language processing. 3rd ed. [S. l.: s. n.], 2009. NEO4J. The cosine similarity algorithm. [2019]. Disponível em: https://neo4j.com/docs/ graph-algorithms/current/labs-algorithms/cosine/. Acesso em: 04 mar. 2020.

Leituras recomendadas

PINTO, S. C. S. Processamento de linguagem natural e extração de conhecimento. 2015. Dissertação (Mestrado em Engenharia Informática) – Departamento de Engenharia Informática, Faculdade de Ciências e Tecnologias, Universidade de Coimbra, Coimbra, 2015.

SANTANA, O. Similaridade entre comentários. 2018. Disponível em: https://eusoudev. com.br/similaridade-entre-comentarios/. Acesso em: 04 mar. 2020.

Todos os links para sites da web fornecidos neste capítulo foram testados, o que levou à comprovação de seu funcionamento no momento da publicação do material. No entanto, pelo fato de a rede ser extremamente dinâmica e suas páginas estarem constantemente mudando de local e conteúdo, os editores declaram não ter qualquer responsabilidade sobre a qualidade, a precisão ou a integralidade das informações referidas em tais links.
