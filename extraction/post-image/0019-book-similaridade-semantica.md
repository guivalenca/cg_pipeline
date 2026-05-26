---
id: "19"
title: "Similaridade Semântica"
source_title: "Processamentos de Linguagem Natural"
resource_code: "9786556900575"
scope_kind: "pages"
scope_value: "pages 103-116"
final_url: "https://integrada.minhabiblioteca.com.br/reader/books/9786556900575/pageid/115"
captured_at: "2026-05-12T07:26:58.596873Z"
---

# Similaridade Semântica
## Page 103

Reader pageid: 102

### Reader text

Similaridade semântica Objetivos de aprendizagem

Ao final deste texto, você deve apresentar os seguintes aprendizados:

„ Diferenciar as similaridades textuais do tipo léxica e do tipo semântica. „ Determinar a similaridade semântica entre palavras. „ Descrever métodos baseados em ontologias de conhecimento.

Introdução

Medidas semânticas são utilizadas para resolver problemas em um enorme conjunto de aplicações e domínios, representando ferramentas essenciais para projetos algoritmos e métodos que lidam com problemas relaciona-dos à similaridade semântica, a qual, por sua vez, pode ajudar em áreas como processamento de linguagem natural, sistemas Web e banco de dados, biomedicina e bioinformática. Como comparar a similaridade de duas strings? Há métodos e técnicas

que foram desenvolvidos para responder a essa pergunta, e saber utilizá--los pode ajudar em um conjunto de aplicações do mundo real. Neste capítulo, você aprenderá a diferença entre similaridade léxica

e similaridade semântica, como calcular a similaridade de palavras e exemplos de métodos baseados em ontologias de conhecimento.

1 Diferenciação entre similaridade léxica e similaridade semântica

Gomaa e Fahmy (2013) afirmam que a medição de similaridade entre pala-vras, frases, parágrafos e documentos constitui uma importante técnica em várias aplicações, como clusterização de documentos, tradução automática, classificação de texto, sumarização de texto, etc.

## Page 104

Reader pageid: 103

### Reader text

104 Similaridade semântica Similaridade léxica e similaridade semântica são técnicas essenciais na me-dição da similaridade de palavras, frases ou documentos. A primeira define-se como o grau em que duas strings são similares levando em conta a sequência de letras, ou seja, considera mais a estrutura (letra por letra) de palavras, frases e documentos. Os métodos que calculam a similaridade léxica de dois fragmentos de texto geralmente têm um intervalo com valores que vão de 0 até 1, o que indica que, quanto mais próximo de 1 for o resultado, mais similares são os dois fragmentos, e, que quanto mais próximo de 0, menor a similaridade. Já a similaridade semântica considera o significado de palavras, frases

ou documentos em determinado contexto. Por exemplo, imagine as palavras “carro” e “barro”: do ponto de vista léxico, ambas apresentam alto grau de

similaridade, já que dispõem de uma sequência de caracteres parecida (“arro”), mas, do ponto de vista semântico, não são similares porque não têm signifi-cados parecidos em algum contexto. Outro exemplo para ilustrar melhor essa situação seria com as palavras “carro” e “automóvel”: elas têm um grau elevado de similaridade léxica e semântica? Da perspectiva lexical, analisando letra por letra, as duas palavras não são similares, mas o são semanticamente, já é possível utilizá-las em um mesmo contexto, como “Meu carro é muito bonito” e “Meu automóvel é muito bonito”. Perceba que é possível trocar as duas palavras com a permanência de sentido, o que configura a principal diferença entre similaridade léxica e semântica — enquanto uma analisa a estrutura das palavras, a outra avalia o significado das palavras em determinado contexto. Resumidamente, quando o assunto é similaridade textual, existem diferen-tes classificações do que similaridade significa. Em sua essência, o objetivo consiste em verificar o quão “próximos” são dois fragmentos de texto a partir do (1) significado e de sua (2) estrutura, em que o primeiro se refere à similaridade semântica e a segunda, à similaridade léxica. No contexto de aplicações, as similaridades léxicas e semânticas podem

resolver problemas diferentes. Imagine que você é dono de uma clínica médica que tem um sistema de cadastro de todos os clientes: faz sentindo ter o mesmo cliente cadastrado mais de uma vez? Dados duplicados sem propósito específico podem ser considerados dados redundantes; nessa situação, a similaridade léxica pode ajudar a identificar redundâncias em banco de dados caso sua exclusão se torne necessária.

## Page 105

Reader pageid: 104

### Reader text

Similaridade semântica 105 A similaridade semântica é capaz de contribuir na resolução de problemas

em aplicações, como tradutores automáticos. Você já deve ter utilizado um serviço Web de tradução, sendo um dos mais famosos o Google Tradutor, uma importante ferramenta da Google que utiliza similaridade semântica para auxiliar nas traduções. Por exemplo, caso você queira verificar a tradução da palavra “livro” para a língua inglesa, como a similaridade semântica entra em ação nessa situação? É necessário saber o que essa palavra significa e em quais contextos pode ser aplicada, o que se realiza por meio da similaridade semântica, ou seja, ela consegue “investigar” o real significado da palavra para que, assim, consiga fazer a tradução da palavra correspondente em inglês (“book”). Apesar de terem conceitos diferentes, as similaridades léxica e semântica

são duas importantes técnicas na área de processamento de linguagem natural (PLN) e que podem ser utilizadas em conjunto em suas inúmeras situações e problemas.

2 Similaridade semântica e ontologias de conhecimento

A similaridade semântica constitui um dos conceitos mais explorados pela comunidade científica da área de PLN e busca responder à seguinte pergunta: O quão similares são duas frases levando em consideração seus significados? Por exemplo, imagine as frases:

Frase 1 — “O rato come o inseto” Frase 2 — “O inseto come a comida do rato”

Nesse exemplo, do ponto de vista léxico é possível notar que as frases são

similares, pois existem muitas palavras em comum em ambas, além de ter havido uma troca de posicionamento das palavras. No entanto, do ponto de vista da similaridade semântica, pode-se olhar simplesmente aspectos como a ordem das palavras:

Frase 1 — [“O”, “rato”, “come”, “o”, “inseto”] Frase 2 — [“O”, “inseto”, “come”, “a”, “comida”, “do”, “rato”]

## Page 106

Reader pageid: 105

### Reader text

106 Similaridade semântica Embora existam muitas palavras em comum nas duas frases, a ordem

dela é diferente e, a partir disso, é possível dizer de maneira intuitiva que as frases têm significados diferentes. E este é apenas um simples exemplo. Para determinar de maneira mais precisa a similaridade semântica de palavras, frases ou documentos, podemos utilizar um conjunto de métodos. Patwardhan, Banerjee e Pedersen (2003) afirmam que as medidas de si-milaridade semântica baseadas em conhecimento podem ser divididas em dois grupos: medidas de similaridade semântica e medidas de relacionamento semântico. Conceitos de similaridade semântica são considerados relacionados à base em sua semelhança, enquanto o relacionamento semântico constitui uma noção mais geral de relacionamento, não especificamente ligado, por exemplo, à forma ou à forma do conceito. Em outras palavras, o relacionamento semân-tico inclui qualquer relação entre dois termos, como “é um tipo de”, “é um exemplo de”, “é uma parte de”, etc., enquanto a similaridade semântica somente tem o relacionamento “é um”. Por exemplo, a palavra “casa” é similar a “lar”, porém também está relacionada a palavras como “parede” e “sala de jantar”. A similaridade semântica entre palavras é medida com base em recursos

semânticos explorando o conhecimento existente dentro desses recursos. Várias medidas de similaridade semântica são implementadas e avaliadas usando como ontologia o WordNet, um grande banco de dados léxicos e com um grande material linguístico na língua inglesa, como substantivos, verbos, adjetivos, sinônimos, entre outros aspectos. A maneira mais utilizada pelas pessoas para comparar dois objetos e adquirir conhecimento consiste em medir a similaridade entre esses dois objetos. Para humanos, é fácil dizer se uma palavra é mais similar que outra palavra, como o fato de que a palavra “carro” é mais similar à palavra “automóvel” do que “carro” em relação à “mesa”. Mas do se trata uma ontologia no contexto da similaridade textual? Gan,

Dou e Jiang (2013), com base em estudos anteriores, afirmam que uma ontologia é um sistema de descrição abstrata que entende a constituição de conhecimento de certo domínio pela organização de conceitos de maneira hierárquica, des-crevendo os relacionamentos entre os conceitos usando um número pequeno de descritores relacionais e vocabulário padronizado para representar as entidades do domínio. Os autores afirmam que, nos domínios de biologia, biomedicina, entre outros, existem algumas ontologias disponíveis, como o caso da ontologia genética, que tem sido amplamente empregada com vocabulário-padrão para trabalhar com funções genéticas entre diferentes espécies.

## Page 107

Reader pageid: 106

### Reader text

Similaridade semântica 107 Gomaa e Fahmy (2013) apontam que a similaridade semântica pode ser

calculada por meio de algoritmos de Corpus-Based, que determina a simila-ridade entre palavras de acordo com informações adquiridas de uma grande base contendo textos escritos e registros orais em determinada língua, e de Knowledge-Based, que mede e determina o grau de similaridade entre palavras usando informações derivadas de redes semânticas como a WordNet. A WordNet é o recurso de ontologia mais popular e amplamente utili-zado na medição de similaridade baseada em conhecimento. Trata-se de um grande banco de dados léxicos de um projeto de pesquisa desenvolvido pela Universidade de Princeton que organiza substantivos, verbos, advérbios e adjetivos em um conceito de relações semânticas, chamado de conjuntos de sinônimos. Esse grande dicionário dispõe de um grande material linguístico, como trechos de fala, significados de palavras, etc. Oliveira et al. (2015) realizaram um estudo para saber quais são as versões

da WordNet para a língua portuguesa, tendo conseguido identificar as seguin-tes wordnets do português: WN.PT 1.0, MWN.PT v1, WN.BR, Onto.PT 0.6, OpenWN-PT, UfesWN.BR 1.0, PULO e WN.Pr 3.0. A Figura 1 mostra um comparativo entre os tamanhos das wordnets baseadas na língua portuguesa em relação ao número de itens lexicais.

Figura 1. Comparação das versões da wordnet da língua portuguesa. Fonte: Adaptada de Oliveira et al. (2015).

## Page 108

Reader pageid: 107

### Reader text

108 Similaridade semântica É possível perceber que a Onto.PT é a wordnet com mais itens lexicais.

A MWN.PT v1 tem apenas substantivos em seu banco de dados, a WN.PT 1.0 apenas advérbios e a Onto.PT inclui recursos que abordam diversos variantes da língua portuguesa, além de dicionários, cujo uso de dicionário, manual ou automático, é comum na construção de uma WordNet. A WordNet é considerada uma combinação e uma ampliação de um di-cionário convencional e um thesaurus, um dicionário de sinônimos, mas no qual também podem ser procurados antônimos. Assim, a WordNet se assemelha superficialmente a um thesaurus, pois agrupa palavras com base em seus significados, embora, diferentemente do thesaurus, que não segue nenhum padrão que não seja a similaridade de significado, a WordNet rotule relacionamentos semânticos. Esse grande banco de dados organiza a informação de maneira hierárquica,

usada de diferentes formas pelas medidas de similaridade semântica. Verbos, substantivos e adjetivos são separados em hierarquias, como mostrado na Figura 2, que ilustra um exemplo de taxonomia.

Animal Ave Mamífero Papagaio Canário Figura 2. Exemplo de taxonomia. Cavalo Burro

Por exemplo, uma ave é um animal, e o papagaio e o canário são aves. Da mesma maneira, um mamífero é um animal, e o cavalo e o burro mamíferos.

## Page 109

Reader pageid: 108

### Reader text

Similaridade semântica 109 Existem alguns métodos que conseguem calcular a similaridade semântica

de dois elementos utilizando essa estrutura, como o Path Similarity, que pode ser entendido como o menor caminho entre dois conceitos. Nesse contexto, o quão similares semanticamente são as palavras “cavalo” e “animal”? A medida de similaridade é inversamente proporcional à distância total do

caminho. Por exemplo, qual é o valor da distância entre as palavras “cavalo” e “animal”? Visto que, entre o nó da palavra “cavalo” e o nó “mamífero”, há o custo 1, e, do nó “mamífero” até o nó “animal”, o custo é 1, somando os custos o resultado será igual a 2. Então, é dessa forma que fazemos o cálculo do custo. No entanto, para calcular o valor do método Path Similarity se utiliza a seguinte fórmula:

Path Similarity = 1/(valor da distância + 1) No exemplo, ficaria da seguinte forma: 1/ 2 + 1 = 0,33, onde 2 é o valor

da distância. Quanto mais próximo de 0, menos similares semanticamente são as palavras. Outra maneira de encontrar a similaridade entre palavras consiste no em-prego da medida lowest commom subsumer (LCS), que encontra o ancestral mais próximo de duas palavras. Por exemplo, “ave” e “animal” são ancestrais de “papagaio” e “canário”. E qual o ancestral mais próximo de “burro” e “ca-valo”? É o mamífero. E qual o ancestral mais próximo de “cavalo” e “canário”? O animal. Então, quanto mais distante for o ancestral comum de duas palavras, menos similares semanticamente essas palavras são; e o contrário também é verdadeiro, já que, quanto mais próximo for o ancestral de duas palavras, mais similares essas palavras são. Então, medidas de similaridade semântica são amplamente utilizadas

atualmente para comparar entidades, conceitos e instâncias de acordo com seu significado. Esse cálculo é feito levando em consideração grandes bases de texto e ontologias para que se consiga extrair evidências semânticas e responder se as palavras são similares ou não. Assim, medidas de similaridade semântica que usam informações de redes

semânticas para identificar o grau de similaridade entre palavras são chamadas medidas de similaridade baseadas em conhecimento, uma abordagem que usa uma representação explícita de conhecimento, como interconexão de fatos, e significados de palavras e regras para descrever conclusões sobre domínios específicos. A representação do conhecimento inclui regras de conclusão, proposição lógica e redes semânticas como ontologia.

## Page 110

Reader pageid: 109

### Reader text

110 Similaridade semântica Relações semânticas em uma ontologia

As relações semânticas representam um tipo de relação entre as palavras e significados. A seguir, são apresentados os tipos de relações semânticas em uma ontologia.

Sinonímia

Relação de igualdade de sentido entre duas palavras, ou seja, duas palavras são sinônimas se uma puder substituir a outra em uma frase sem alterar o significado desta. Por exemplo, “casa” e “residência”, “carro” e “automóvel”.

Antonímia

Relação de oposição no sentido de duas palavras, ou seja, palavras são antô-nimas se têm significados contrários. Por exemplo, “alto” e “baixo”, “forte” e “fraco”.

Meronímia

Relação de parte entre duas palavras, ou seja, uma relação “é parte de”. Por exemplo, “pneu” e “motor” são merônimos da palavra “carro”, e “teclado” é merônimo (parte) de “computador”.

Holonímia

Relação inversa da meronímia, ou seja, uma relação “é formada por”. Por exemplo, “carro” é holônimo de “pneu” e “motor”, e “computador” é holônimo de teclado.

Hiponímia

Trata-se da relação entre palavras em que o significado de uma está contido no significado de outra, ou seja, é uma relação em que o termo é subclasse de outro. Por exemplo, “gato” e “animal”, em que todo “gato” é um tipo de animal; assim, “gato” é um hipônimo de “animal”.

## Page 111

Reader pageid: 110

### Reader text

Similaridade semântica 111 Hiperonímia

Relação inversa da hiponímia, por exemplo, dada as palavras “gato” e “animal”, é possível dizer que “animal” é hiperônimo de “gato”. Homonímia

Relação na qual uma mesma palavra apresenta dois ou mais significados. Essas palavras homônimas podem ser de três tipos, listados a seguir.

1. Homônimos perfeitos: palavras iguais na escrita e na pronúncia. Por exemplo, “cedo” (verbo) e “cedo” (advérbio).

2. Homógrafas: palavras iguais na escrita e diferentes na pronúncia. Por exemplo, “gosto” (verbo) e “gosto” (substantivo).

3. Homófonas: palavras iguais na pronúncia e diferentes na escrita. Por exemplo, “cela” (substantivo) e “sela” (verbo).

Polissemia

Trata-se da relação na qual uma palavra pode ter diversos significados de acordo com o contexto. Por exemplo, a palavra “posto” pode significar “cargo” em uma empresa ou “posto de gasolina”. Não existe uma diferença clara entre homonímia e polissemia, mas os verbetes do dicionário conseguem ajudar a diferenciar os dois conceitos. No caso da homonímia, os dicionários apresentam mais de um verbete para o mesmo vocábulo e, no de polissemia, os significados em um mesmo verbete. Conhecer cada uma das definições apresentadas é importante para entender

como funciona e como são organizadas as diversas ontologias como a WordNet. Nesse contexto, a WordNet pode ser considerada uma ontologia léxica em que os conceitos são conectados entre si pelas relações apresentadas. Por exemplo, sinonímia é a relação mais básica na WordNet, pois conceitos são representados como synsets (conjuntos de sinônimos). Cada synset representa uma percepção específica de uma palavra e todos os relacionamentos semânticos e termos envolvidos com aquela percepção. Assim, cada synset define um domínio com suas particularidades, termos relevantes e relações, como mostrado nos exemplos citados. As relações de hiponímia e hiperonímia podem ajudar na hierarquia de uma ontologia como a WordNet em que uma palavra é a gene-ralização de outra, que, por sua vez, é a generalização de outra, conseguindo

## Page 112

Reader pageid: 111

### Reader text

112 Similaridade semântica

ajudar na construção de uma taxonomia (Figura 2). Ainda, as relações de polissemia e homonímia podem auxiliar no mapeamento de informações, porque termos com a mesma forma podem ser considerados iguais, mas, em diferentes domínios, apresentar significados diferentes.

3 Acesso à WordNet utilizando o NLTK

NLTK é uma plataforma para desenvolver programas em Python para trabalhar com dados de linguagem humana que provê interfaces para o uso de grandes bases de recursos léxicos como WordNet, além de um conjunto de bibliotecas de processamento para classificação, tokenização, bibliotecas de PLN e mé-todos para calcular a similaridade semântica. Seu site oficial, inclusive, tem um fórum de discussão ativo. Após instalado o NLTK, o próximo passo é escrever o seguinte código para importar a WordNet:

from nltk.corpus import wordnet

Após essa importação, é possível utilizar alguns métodos já prontos e explorar palavras na WordNet, como visualizado na Figura 3.

Figura 3. Exemplo de sinônimo. A função wordnet.synsets (“qualquer palavra”) retorna um vetor

contendo todos os synsets relacionados à palavra entre parênteses. O método retornou cinco synsets para a palavra “room”, que, em português, pode ter significado de “quarto” ou “sala”. Assim, a saída desse programa sugere que essa palavra tem um total de cinco significados ou contextos.

## Page 113

Reader pageid: 112

### Reader text

Similaridade semântica 113 A Figura 4 apresenta outro exemplo utilizando a palavra “house”, que

significa “casa” em português. Empregando o método definition(), é possível saber a definição de uma palavra que está sendo passada como parâmetro. Mas, se uma palavra tem vários sentidos, como é feito o processo de escolha da definição retornada pelo método definition? Esse método retorna uma definição comum para todas as palavras. No exemplo da Figura 4, houve o retorno da seguinte frase: “a dwelling that serves as living quarters for one or more families”, que, em uma tradução livre, significa: “uma habitação que serve de moradia para uma ou mais famílias”.

Figura 4. Exemplo de método para definição de palavra. A Figura 5 apresenta outro exemplo utilizando a palavra “happy”, na qual

se mostram os três imediatos sinônimos dessa palavra, que significa “feliz” em português. Primeiro, buscam-se os synsets da palavra “happy”, e, depois, são impressos três sinônimos dessa palavra pelo método .lemmas().name.

Figura 5. Exemplo de método para sinônimos de uma palavra.

Nesse contexto, o NLTK e a WordNet compreendem estruturas que facilitam o estudo de palavras para que se possa avaliar suas similaridades semânticas.

## Page 114

Reader pageid: 113

### Reader text

114 Similaridade semântica Exemplos em português na WordNet

O NLTK fornece uma interface para o Open Multilingual Wordnet que inclui o português e outros idiomas. A Open Multilingual Wordnet é uma página de wordnets abertas nas mais diversas linguagens, todas baseadas na WordNet da Universidade de Princeton, cujo objetivo é facilitar o uso de wordnets em diferentes idiomas. Cada wordnet foi desenvolvida por diferentes projetos independentes e tem um conjunto enorme de informações. É possível utilizar a OpenWN-PT, uma wordnet de língua portuguesa, por

meio da adição de um argumento que informa a linguagem a ser utilizada, como exemplificado na Figura 6.

Figura 6. Exemplo de método para sinônimos de uma palavra. Observamos que, ao colocarmos o atributo lang=”por”, é possível

utilizar palavras em português, como no exemplo da Figura 7, em que se usou a palavra “gato”. Então, podemos verificar vários sinônimos da palavra “gato” pelo retorno da função lemmas().

## Page 115

Reader pageid: 114

### Reader text

Similaridade semântica 115

E quais são os synsets ou seja, conjunto de sinônimos das palavras “celular” e “computador”? A Figura 7 mostra o código que responde a essa pergunta.

Figura 7. Synsets das palavras “celular” e “computador”. É possível perceber que utilizar o atributo lang=”por” facilita um

pouco o uso NLTK com o OpenWN-PT por nativos da língua portuguesa, pois é possível escrever qual palavra em português será avaliada, embora os resultados ainda sejam retornados em inglês — por exemplo, como exercício tente imprimir as definições de “celular” e “computador” por meio do método definition(); isso acontece porque essa wordnet baseia-se na WordNet da Universidade de Princeton. Esse tipo de facilidade auxilia pesquisadores, estudantes e profissionais

da área em seus respectivos idiomas nativos. Assim, é possível perceber a importância da similaridade semântica e sua

utilidade para um conjunto grande de aplicações reais. Existem métodos, ferramentas e bibliotecas que auxiliam na verificação da similaridade semân-tica entre dois documentos, cabendo ao usuário decidir qual utilizar para a resolução de eventuais problemas durante sua vida profissional.

## Page 116

Reader pageid: 115

### Reader text

116 Similaridade semântica

GAN, M.; DOU, X.; JIANG, R. From ontology to semantic similarity: calculation of onto-logy-based semantic similarity. The Scientific World Journal, [s. l.], v. 2013, p. 1–11, 2013.

GOMAA, W. H.; FAHMY, A. A. A survey of text similarity approaches. International Journal of Computer Applications, [s. l.], v. 68, n. 13, p. 13–18, 2013.

OLIVEIRA, H. G. et al. As wordnets do português. OSL, [s. l.], v. 7, n. 1, p. 397–424, 2015.

PATWARDHAN, S.; BANEJEE, S.; PEDERSEN, T. Using measures of semantic relatedness for word sense disambiguation. [S. l.: s. n.], 2003. Leitura recomendada JURAFSKY, D.; MARTIN, J. H. Speech and language processing. 3rd ed. [S. l.: s. n.], 2019.
