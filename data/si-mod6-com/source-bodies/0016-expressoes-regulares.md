---
id: "16"
title: "Expressões Regulares"
source_title: "Processamentos de Linguagem Natural"
resource_code: "9786556900575"
scope_kind: "pages"
scope_value: "pages 69-87"
final_url: "https://integrada.minhabiblioteca.com.br/reader/books/9786556900575/pageid/86"
captured_at: "2026-05-12T07:14:28.748901Z"
---

# Expressões Regulares
## Page 69

Reader pageid: 68

### Reader text

Expressões regulares Objetivos de aprendizagem

Ao final deste texto, você deve apresentar os seguintes aprendizados:

„ Definir o papel das expressões regulares como recurso para o pro-cessamento de linguagem natural (PLN).

„ Reconhecer as diferentes funções disponíveis para utilizar expressões regulares.

„ Programar algoritmos de PLN empregando expressões regulares. Introdução

Ao buscarem uma melhor compreensão e interpretação automatizada de textos, as técnicas de processamento de linguagem natural (PLN) se deparam com o desafio de compreender variações em palavras com sentidos próximos, como no caso da língua portuguesa e de suas di-versas formas de flexão verbal e nominal. Nesse contexto, as expressões regulares se apresentam como uma solução robusta e elegante para detectar padrões variados em textos. Neste capítulo, você identificará a importância das expressões regu-lares como recurso para o PLN, conhecerá os tipos de metacaracteres e implementará suas primeiros expressões regulares usando a linguagem de programação Python.

1 Expressões regulares no processamento de linguagem natural (PLN)

Expressões regulares (também conhecidas como ER, RE ou regex) fornecem métodos poderosos e flexíveis para detectar padrões de caracteres (BIRD; KLEIN; LOPER, 2009), podendo, na prática, ser compreendidas como nota-ções algébricas que representam determinado padrão de textos passíveis de empregar em uma pesquisa (JURAFSKY; MARTIN, 2014).

## Page 70

Reader pageid: 69

### Reader text

70 Expressões regulares Para entender a importância das expressões regulares, supomos que você

deseje realizar uma busca de trechos em um texto que apresentem o verbo “escrever”. Na língua portuguesa, conforme o tempo verbal ou a pessoa ado-tada na escrita, o verbo “escrever” poderia adotar diversas conjugações, como descrito no exemplo.

Conjugação do verbo escrever no presente do indicativo

eu escrevo tu escreves ele escreve nós escrevemos vós escreveis eles escrevem

Logo, conclui-se que uma simples busca pela palavra “escrever” pode não

retornar os resultados desejados, embora notemos que a existência de certos padrões nas diferentes formas que esse verbo consegue assumir. Nas variações apresentadas, os verbos iniciam-se pelos caracteres escrev. Após esse con-junto de caracteres, as variações desse verbo apresentaram entre um e quatro caracteres, como no caso da palavra “escreve” (e) e a palavra “escrevemos” (emos). Nesse contexto, as expressões regulares podem ser eficientes para uma busca genérica de palavras. Observe o exemplo a seguir:

escrev[a-z]{1,4} Na expressão regular apresentada, procuram-se todas as palavras iniciadas

pelo conjunto de caracteres escrev, seguidas por um conjunto de uma a quatro letras [a-z]{1,4}. Expressões regulares fazem uso de caracteres especiais para representar

generalizações. Por exemplo, a combinação dos caracteres [a-z] indica que se trata de uma letra (qualquer uma de A a Z); já o padrão {1,4} indica que o padrão anterior [a-z] deve se repetir de uma a quatro vezes.

## Page 71

Reader pageid: 70

### Reader text

Expressões regulares 71

Expressões regulares devem ser generalizadas e específicas

Expressões regulares devem permitir buscas generalizadas. No exemplo apresentado, a expressão regular foi eficiente para detectar todas as variações apresentadas, contudo o verbo “escrever” pode apresentar outras conjugações, como as descritas no exemplo a seguir.

Conjugação do verbo escrever no futuro do pretérito (indicativo)

eu escreveria tu escreverias ele escreveria nós escreveríamos vós escreveríeis eles escreveriam

Aqui, a expressão regular apresentada não conseguiria detectar quatro das

seis variações, uma vez que podem apresentar de duas a cinco letras depois do padrão escrev. Além disso, o padrão descrito anteriormente poderia retornar falsos-positivos, como a palavra “descrever”, pelo fato de não ter sido especificado nenhum padrão condicional no início da palavra. Essa questão pode ser resolvida simplesmente adicionando um espaço antes da expressão regular, embora você ainda tivesse problemas caso compreenda a primeira palavra da frase. Você também poderia adicionar um padrão excluindo qualquer palavra com uma letra antes de “escrev”. Ainda, deve-se levar em consideração que expressões regulares são case sensitive, isto é, a busca diferencia letras maiúsculas e minúsculas. Logo, se a palavra “escrever” aparecer no texto, não será detectada. Por fim, deve-se considerar acentos, que não seriam englobados no padrão [a-z]. Assim, uma expressão regular que atende melhor aos requisitos poderia ser:

[^a-z][Ee]screv[\w]*

## Page 72

Reader pageid: 71

### Reader text

72 Expressões regulares Agora complicou um pouco, não é mesmo? Expressões regulares podem

ser mais específicas ou mais generalizadas de acordo com a necessidade — o ideal é que sejam genéricas o suficiente para identificar todas as variações desejadas, mas específicas para que não haja falsos-positivos. A expressão regular citada apresentou uma série de caracteres especiais

para representar esses padrões, denominados metacaracteres (MARIANO; MINARDI, 2016). Para construir expressões regulares mais robustas, deve-se primeiro conhecer os tipos de metacaracteres.

Tipos de metacaracteres

Metacaracteres podem ser compreendidos como um conjunto de símbolos com características próprias que possibilitam buscas generalizadas e específicas em expressões regulares, como:

. [ ] ? * + { } ^ $ \ | ( ) Metacaracteres podem ser classificados em quatro tipos (JARGAS, 2016):

„ representantes; „ quantificadores; „ âncoras; „ outros (incluindo metacaracteres relacionais, agrupamento e escape).

Metacaracteres representantes

Podem atuar como outros caracteres e representar exclusivamente um único outro caractere, o que exige combiná-los a metacaracteres do tipo quantificador (JARGAS, 2016). São exemplos de metacaracteres do tipo representante: o ponto, que age

como coringa podendo representar qualquer outro caractere; a lista, que per-mite a busca de um conjunto de caracteres presentes entre colchetes; e a lista negada, que possibilita buscas por caracteres que não estão listados (Quadro 1).

## Page 73

Reader pageid: 72

### Reader text

Expressões regulares 73 Quadro 1. Metacaracteres representantes Metacaractere .

[ ] [^]

Nome Ponto Lista Lista negada Fonte: Adaptado de Mariano e Minardi (2016). Significado

Busca qualquer caractere simples (exceto /n)

Busca uma lista de caracteres indicados

Busca uma lista de caracteres NÃO indicados na lista.

Considere o exemplo a seguir. Bola cola sola mola

Expressão regular .ola

[a-z]ola [^csm]ola

Correspondências Bola cola sola mola cola sola mola Bola

Nesse exemplo, o ponto na expressão regular .ola pode ser substituído

por qualquer outro caractere, podendo casar, portanto, casar com qualquer uma das quatro palavras. O padrão [a-z]ola permite apenas que o primeiro caractere seja uma

letra de A a Z (desde que minúscula), logo “Bola” não seria incluído (caracteres maiúsculos não seriam aceitos). Para que ele fosse aceito, seria necessário acrescentar letras maiúsculas [a-zA-Z]ola. Se, no lugar de [a-z]ola, fosse apresentado [a-m]ola, apenas as palavras “cola” e “mola” casariam com o resultado, pois o padrão permitiria apenas caracteres de A a M.

## Page 74

Reader pageid: 73

### Reader text

74 Expressões regulares

O traço em [a-z] indica que a lista inclui um intervalo de valores com base na tabela ASCII, ou seja, é o equivalente a [abcdefghijklmnopqrstuvwxyz]. O mesmo pode ser feito com valores numéricos, por exemplo, [0-9] é o mesmo que [0123456789].

Por fim, a lista negada na expressão regular [^csm]ola rejeita todas as

palavras iniciadas em c, s ou m; assim, apenas a palavra “Bola” casaria com essa expressão.

Metacaracteres quantificadores

Possibilitam definir a quantidade de repetições do elemento anteriormente apresentado (JARGAS, 2016), podendo ser usados em combinação com outros metacaracteres, como o ponto e a lista. No Quadro 2, são apresentados os quatro metacaracteres que se incluem nessa categoria: asterisco, opcional, mais e chaves.

Quadro 2. Metacaracteres quantificadores Metacaractere * ? + Nome Asterisco Opcional Mais {x, y} Chaves Significado

Permite buscas de caracteres que aparecem nenhuma ou várias vezes

Permite buscas de caracteres que não apareçam ou que apareçam uma única vez

Possibilita buscas de caracteres que aparecem várias vezes ou pelo menos uma vez

Permite buscas de um caractere que apareça no mínimo x vezes e no máximo y vezes

Fonte: Adaptado de Mariano e Minardi (2016).

## Page 75

Reader pageid: 74

### Reader text

Expressões regulares 75

Observe o exemplo a seguir. Bola cola sola mola ola sol

Expressão regular .*

sol[a-z]? sol[a-z]+

[a-zA-Z]ola{1,10} Correspondências

Bola cola sola mola ola sol sola sol sola

Bola cola sola mola O ponto no padrão .* pode indicar qualquer caractere e, seguido, pelo

asterisco aponta qualquer conjunto de caracteres; logo, essa expressão retorna todos os elementos. O metacaractere opcional em sol[a-z]? indica que o último caractere pode existir ou não, quando a busca retorna “sola” e “sol”. Em contradição, a expressão regular sol[a-z]+ exige que o último caractere seja uma letra, logo esse padrão corresponderia apenas com “sola”. Por fim, em [a-zA-Z]ola{1,10}, os valores entre chaves indicam

quantas vezes o caractere anterior deve se repetir (nesse caso, entre uma e dez vezes). A lista “Bola”, “cola”, “sola” e “mola” apresenta uma letra A, padrão que permitiria correspondências com palavras de até dez letras A, por exemplo, “molaaaaaaaaa”. Ainda, seria possível passar um único valor entre chaves para definir o valor máximo de ocorrências, por exemplo, para detecção de apenas uma ocorrência, seria {1}.

## Page 76

Reader pageid: 75

### Reader text

76 Expressões regulares Metacaracteres âncoras

Delimitam o posicionamento de busca em determinada linha (JARGAS, 2016) e são de dois tipos, conforme o Quadro 3.

Quadro 3. Metacaracteres âncoras Metacaractere ^ $ Nome

Circunflexo Cifrão

Fonte: Adaptado de Mariano e Minardi (2016). Significado

Busca no início de uma linha/string Busca no fim de uma linha/string

Veja o exemplo a seguir. rato roeu a roupa do rei de Roma

Expressão regular ^[Rr][a-z]*

[Rr][a-z]*$

Correspondências rato

Roma O circunflexo permite buscas no início da linha. No exemplo, esse metaca-ractere retornaria a primeira palavra iniciada com R (maiúsculo ou minúsculo), desde que esteja no começo de uma linha. Já o cifrão possibilita buscas no fim da linha. O padrão [Rr][a-z]*$ retornaria a última palavra da linha, mas, mais uma vez, desde que seja iniciada com a letra R.

O circunflexo combinado com o metacaractere de lista [^ ] representa negação. Quando inserido fora de colchetes, ele se torna um metacaractere âncora.

## Page 77

Reader pageid: 76

### Reader text

Expressões regulares 77 Outros metacaracteres

A última categoria (Quadro 4) engloba metacaracteres com diversas funções específicas, como o alternativo (ou), o agrupamento e o escape (JARGAS, 2016).

Quadro 4. Outros metacaracteres Metacaractere |

( ) \

Ou Nome Significado

Busca pelo caractere à direita ou à esquerda

Agrupamento Permite a busca por grupos de caracteres Escape

Fonte: Adaptado de Mariano e Minardi (2016).

Converte metacaractere em um caractere normal

Observe o exemplo a seguir. rato roeu a roupa do rei de Roma.

Expressão regular rato|Roma

(rato|Roma) [a-z]*\.

Correspondências rato Roma rato Roma Roma.

O metacaractere alternativo | permite buscar correspondências para um ou

outro elemento, podendo ser combinado com o metacaractere de agrupamento para procurar quantidades maiores de caracteres.

## Page 78

Reader pageid: 77

### Reader text

78 Expressões regulares

Observe que o agrupamento se diferencia da lista. Enquanto (rato|Roma) correspon-deria a “rato” e “Roma”, [rato|Roma] faria referência a todas as letras presentes em qualquer um dos grupos, ou seja, “r a t o r o a r o a o r R o m a”.

O último metacaractere é o escape (ou barra invertida), que converte me-tacaracteres em caracteres comuns, possibilitando seu emprego em buscas. Por exemplo, o metacaractere ponto pode ser usado para traçar uma correspon-dência com qualquer outro caractere. Entretanto, imagine que a necessidade de uma busca no texto exclusivamente pelo caractere ponto, ou como no exemplo apresentado, uma busca pela última anterior a um ponto [a-z]*\.. Nesse caso, o uso de uma barra invertida antes do ponto remove as características do metacaractere. Ainda, a barra invertida pode ser combinada com alguns caracteres obtendo atalhos para expressões regulares (Quadro 5).

Quadro 5. Pseudônimos para conjuntos comuns de caracteres ER

\d \D \w

\W \s \S Equivalente [0-9] [^0-9] Correspondência Qualquer dígito Qualquer não dígito

[a-zA-Z0-9_] Qualquer caractere alfanumérico ou sublinhado

[^\w]

[espaço\ r\t\n\f]

[^\s]

Qualquer caractere não alfanumérico

Qualquer tipo de espaçamento (espaço, tabulação, quebra de linha)

Qualquer coisa que não seja um espaçamento

Fonte: Adaptado de Jurafsky e Martin (2014). Primeira correspondência

Número 5 Número 5

Qualquer coisa Olá mundo! — Qualquer coisa

## Page 79

Reader pageid: 78

### Reader text

Expressões regulares 2 Implementação em Python

Na linguagem Python, expressões regulares podem ser utilizadas com o módulo re, carregando-o a partir do comando import. import re

Para lidar com buscas usando expressões regulares, o módulo re fornece uma série de métodos, descritos no Quadro 6.

Quadro 6. Métodos para manipulação de expressões regulares em Python Método match( ) Definição

Realiza buscas por combinação no início da string Retorna um objeto de correspondência (match object)

search( ) group( )

Faz buscas simples em strings. Retorna o primeiro resultado

Retorna um ou mais subgrupos da correspondência

findall( ) Retorna todas as correspondências de determinado padrão (desde que não sobrepostas), como uma lista

split( ) sub( )

Divide determinada string no ponto delimitado pelo padrão e retorna uma lista

Substitui parte da string com base no padrão informado

Fonte: Adaptado de Python Software Foundation (2020). Uso

re.match(“padrão”, “string”)

79

re.search(“padrão”, “string”)

re.group(0)

re.findall(“padrão”, “string”)

re.split(“padrão”, “string”)

re.sub(“padrão”, “novo valor”, “string”)

## Page 80

Reader pageid: 79

### Reader text

80 Expressões regulares

Na Figura 1, foi utilizado o método search para fazer uma busca de pa-lavras iniciadas com a letra R na frase: “O rato roeu a roupa do rei de Roma.”.

Figura 1. Método search( ) — gerado usando Google Colab. Ao imprimir o resultado na tela em print(busca), o Python retorna um

objeto de correspondência (match object). Pode-se imprimir o resultado da busca ao informar a posição 0 da busca usando colchetes: print(busca[0]).

O Python fornece duas operações primitivas diferentes com base em expressões regulares: „ re.match( ) verifica uma correspondência apenas no início da string; „ re.search( ) verifica uma correspondência em qualquer lugar da string. Por exemplo:

Comando

re.match("d", "abcde") re.search("d", "abcde") re.match("d", "dbcae") re.search("c", "dbcae")

x

✓ ✓ ✓

Fonte: Adaptado de Python Software Foundation (2020, documento on-line). Resultado

## Page 81

Reader pageid: 80

### Reader text

Expressões regulares 81

Observe que o método search( ) é “guloso”, ou seja, retorna a primeira ocorrência do padrão (no caso, a palavra “rato”). Entretanto, na string apresen-tada, outras palavras poderiam corresponder ao padrão, como “roeu”, “roupa”, “rei” e “Roma”. Para realizar buscas que retornam todas as ocorrências de um padrão, podemos utilizar o método findall( ), como visto na Figura 2.

Figura 2. Método findall( ) — gerado usando Google Colab. O método findall( ) retorna uma lista com todas as ocorrências de determinado padrão.

3 Aplicações reais de expressões regulares Identificação de endereços de e-mails

Expressões regulares podem ser utilizadas para detectar e extrair endereços de e-mail de conjuntos de texto, como visto na Figura 3.

Figura 3. Realização de buscas por endereços de e-mail — gerado usando Google Colab.

## Page 82

Reader pageid: 81

### Reader text

82 Expressões regulares No exemplo da Figura 3, foi utilizado o padrão [a-z0-9]+@[a-z\.]

para detectar os endereços de e-mail na sentença. Analisemos cada parte dessa expressão regular:

„ [a-z0-9]+ — trecho que busca caracteres alfanuméricos que se repetem pelo menos uma vez;

„ @ — os caracteres anteriores devem ser obrigatoriamente procedidos do símbolo @. Nesse caso, essa expressão regular determina que não pode haver espaços ou outros tipos de caracteres especiais (p. ex., !?&%$#);

„ [a-z\.] — o símbolo @ deve ser procedido por um conjunto de letras ou pontos (observe que a expressão regular não permite números no fim do endereço de e-mail).

Identificação de números de telefone

Expressões regulares também podem ser utilizadas para detectar e extrair números de telefone, como podemos observar na Figura 4.

Figura 4. Realização de buscas por números de telefone — gerado usando Google Colab.

## Page 83

Reader pageid: 82

### Reader text

Expressões regulares 83 No exemplo da Figura 4, foi utilizado o padrão [0-9]+-[0-9]+ para

detectar os endereços de e-mail na sentença. Analisamos cada parte dessa expressão regular a seguir.

„ [0-9]+. Trecho que busca caracteres numéricos que se repetem pelo menos uma vez;

„ -. Os caracteres anteriores devem ser obrigatoriamente procedidos do símbolo -. Essa expressão regular também determina que não pode haver espaços ou outros tipos de caracteres especiais (p. ex., !?&%$#); „ [0-9]+. O símbolo - deve ser procedido por um conjunto de números.

Análise de textos Para as análises a seguir, usaremos o texto a seguir.

β-glicosidases (EC 3.2.1.21) são enzimas-chave no processo de produção de biocom-bustíveis de segunda geração. Elas agem em conjunto com endoglucanases e exo-glucanases na conversão de biomassa em açúcares fermentáveis. Entretanto, a maior parte das β-glicosidases conhecidas são altamente inibidas por grandes concentrações de glicose. Assim, a busca por mutações que melhorem a atividade de β-glicosidases não tolerantes a inibição por glicose é de grande importância para a indústria. Nesta tese, é apresentada uma revisão sistemática da literatura para coletar informações sobre β-glicosidases glicose-tolerantes e construir uma base de dados, denominada BETAGDB. Além disso, são caracterizados resíduos importantes no bolsão catalítico para atividade e glicose-tolerância. Por fim, apresenta-se um método baseado na diferença de variação de assinaturas estruturais para propor mutações em enzimas, denominado SSV (Structural Signature Variation). SSV usa modelagem em grafos para criar uma assinatura estrutural identificadora de β-glicosidases glicose-tolerantes. Os resultados obtidos nesta tese podem ajudar na produção de enzimas β-glicosidases mutantes capazes de aperfeiçoar a produção de biocombustíveis de segunda geração. O método SSV pode ser estendido a outras enzimas e pode ainda ser utilizado em conjunto com outras estratégias e ferramentas para propor mutações mais eficientes. Fonte: Adaptado de Mariano (2019).

## Page 84

Reader pageid: 83

### Reader text

84 Expressões regulares Esse texto apresenta 10 frases. Para separar todas elas em uma lista, seria

possível utilizar o método split( ). Como argumentos, split receberia uma string com o padrão de busca e uma string, na qual seria realizada a busca (no caso, o texto previamente apresentado). Nesse exemplo, o padrão de busca pode ser um caractere que indica o final de uma frase: o ponto final. Entretanto, algumas particularidades devem ser avaliadas (Figura 5).

Figura 5. Identificação de frases — gerado usando Google Colab. Para uma correta coleta de frases, a expressão regular não considerou ape-nas pontos, mas também a presença de um espaçamento após o ponto: \.\s, o que evitou que o trecho “(EC 3.2.1.21)” fosse erroneamente reconhecido como quatro frases distintas, quando, na verdade, faz parte de uma única frase.

Detectar acrônimos e correspondências

Expressões regulares podem ainda ser utilizadas para coleta de dados mais es-pecíficos, como na identificação de acrônimos e/ou na correlação entre termos. Essa coleta poderia ser utilizada, por exemplo, para a construção automática de uma lista de abreviaturas. No exemplo apresentado anteriormente, dois excertos são possíveis candidatos:

1. β-glicosidases (EC 3.2.1.21); 2. SSV (Structural Signature Variation).

## Page 85

Reader pageid: 84

### Reader text

Expressões regulares 85 No primeiro trecho, há uma correlação entre o termo “β-glicosidases”

e o código “EC 3.2.1.21, e, no segundo, o trecho “Structural Signature Variation” corresponde ao significado da sigla “SSV”. Com isso, é possível estabelecer um padrão para detectar correlações entre termos:

Termo (significado) Observe que o significado é exibido entre parênteses, que permitem letras,

números e pontos, ressaltando-se que, entre eles, não há qualquer espaço. O termo que o precede é separado por um espaço, permitindo não apenas letras, mas também caracteres especiais, como o caractere grego β (beta), e traços. Assim, a expressão regular poderia ser modelada da seguinte maneira:

\S* \(.[^\)]*\) Agora, vamos compreendê-la por partes:

„ \S* — busca qualquer conjunto de caracteres desde que não haja espaçamentos (permite letras, números e outros caracteres especiais como o “β” ou traços). Essa expressão deve ser procedida por um espaço;

„ \( — a seguir, o conjunto \( detecta a presença do caractere (, ou seja, a abertura do parênteses;

„ .[^\)]* — aqui, temos o ponto-chave, que pode parecer contro-verso. Após a abertura do parêntese, é aceito qualquer caractere (por isso o ponto no início), repetido quantas vezes for necessário (por isso o asterisco no fim), desde que o caractere não seja o fechamento de parênteses (por isso lista negada para \)). Isso é exigido para que a expressão regular não colete vários parênteses como se fosse um único, por exemplo: ■ Esse texto tem duas siglas: SIGLA_1 (significado da sigla 1) e SIGLA_2 (significado da sigla 2).

■ Caso o trecho [^\)] não fosse utilizado, a expressão corresponderia ao trecho da abertura do primeiro parêntese até final do segundo parênteses, ou seja: – (significado da sigla 1) e SIGLA_2 (significado da sigla 2)

„ \) — o último trecho busca o caractere literal de fechamento de pa-rênteses \).

## Page 86

Reader pageid: 85

### Reader text

86 Expressões regulares A busca de abreviaturas e outras correlações pode ser implementada em

Python usando a estrutura de dicionários. Nesse caso, a chave corresponderia ao tempo e o valor, ao significado, como observado na Figura 6.

Figura 6. Detecção de abreviaturas usando expressões regulares — gerado usando Google Colab.

Após a detecção de possíveis abreviaturas no texto, realiza-se a modela-gem dos dados como um dicionário. Primeiro, a chave é detectada usando o método match( ), que promove buscas apenas no início de linhas, portanto o mais indicado para detectar a sigla/palavra-chave (modelada como chave do dicionário). A busca do significado é realizada usando o método search( ), em seguida os parênteses são removidos usando o método sub( )e, por fim, os dados são gravados em um dicionário denominado “abreviaturas”. Expressões regulares constituem poderosas ferramentas para a busca de

padrões complexos em textos, mas sempre devemos nos atentar às regras de uso de metacaracteres.

## Page 87

Reader pageid: 86

### Reader text

Expressões regulares 87

BIRD, S.; KLEIN, E.; LOPER, E. Natural language processing with python: analyzing text with the natural language toolkit. [S. l.]: O’Reilly Media, 2009.

JARGAS, A. M. Expressões regulares: uma abordagem divertida. São Paulo: Novatec, 2016. JURAFSKY, D.; MARTIN, J. H. Speech and language processing. 2nd ed. [S. l.]: Pearson, 2014. MARIANO, D. C. B. Uso de assinaturas estruturais para proposta de mutações em enzimas

β-glicosidase usadas na produção de biocombustíveis. 2019. Tese (Doutorado em Bioin-formática) — Universidade Federal de Belo Horizonte, Belo Horizonte, 2019.

MARIANO, D. C. B.; MINARDI, R. C. M. Introdução à programação para bioinformática com perl. North Charleston: CreateSpace Independent Publishing Platform, 2016. v. 2.

PYTHON SOFTWARE FOUNDATION. re — Regular expression operations. 2020. Disponível em: https://docs.python.org/3/library/re.html. Acesso em: 04 maio 2020.

Os links para sites da web fornecidos neste capítulo foram todos testados, e seu fun-cionamento foi comprovado no momento da publicação do material. No entanto, a rede é extremamente dinâmica; suas páginas estão constantemente mudando de local e conteúdo. Assim, os editores declaram não ter qualquer responsabilidade sobre qualidade, precisão ou integralidade das informações referidas em tais links.
