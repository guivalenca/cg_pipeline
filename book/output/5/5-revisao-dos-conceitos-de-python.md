---
id: "5"
title: "Revisão dos conceitos de Python"
source_title: "Aprenda Python 3 do Jeito Certo"
resource_code: "9788550809205"
scope_kind: "mixed"
scope_value: "exercise 6 page 25; exercise 13 page 43; exercise 15 page 51; exercise 16 page 54; exercise 17 page 63; exercise 21 page 81; exercise 30 page 111; exercise 31 page 115; exercise 36 page 137; exercise 37 page 143"
final_url: "https://integrada.minhabiblioteca.com.br/reader/books/9788550809205/pageid/165"
captured_at: "2026-05-12T06:58:31.881725Z"
---

# Revisão dos conceitos de Python
## Page 25

Reader pageid: 47

### Reader text

25 EXERCÍCIO 6

Strings e Texto E

mbora você tenha escrito strings, ainda não sabe o que elas fazem. Neste exercício, criamos muitas variáveis com strings complexas para que possa ver sua finalidade. Primeiramente, uma explicação sobre strings.

Uma string geralmente é um pequeno texto que você deseja exibir para alguém ou “exportar” do programa que está escrevendo. O Python sabe que você deseja que algo seja uma string quando coloca " (aspas duplas) ou ' (aspas simples) em volta do texto. Você viu isso muitas vezes usando print quando colocou o texto que queria dentro da string entre " ou ' após o print para imprimir a string.

As strings podem conter diversas variáveis que estão em seu script do Python. Lembre que uma variável é como qualquer linha de código, na qual você define um nome = (igual) com um valor. No código deste exercício, types_of_people = 10 cria uma variável denomina-da types_of_people e define-a = (igual a) 10. É possível colocar isso em qualquer string com {types_of_people}. Também é possível ver que tenho que usar um tipo especial de string para “formatar”. Isso é chamado de “f-string” e fica assim:

f"some stuff here {avariable}" f"some other stuff {anothervar}"

O Python também tem outro tipo de formatação que usa a sintaxe .format(), vista na linha 17. Irei usá-la algumas vezes quando quiser aplicar um formato em uma string já criada, como em um loop. Falaremos sobre isso mais tarde.

Agora, digitaremos muitas strings, variáveis e formatos, e iremos imprimi-los. Também usare-mos nomes de variáveis curtos e abreviados. Os programadores adoram economizar tempo usando nomes de variáveis curtos muito enigmáticos, portanto, comece a lê-los e escrevê-los desde cedo.

ex6.py

1 2

3 4 5 6

7 8 9

10 11 12

types_of_people = 10 x = f"There are {types_of_people} types of people."

binary = "binary" do_not = "don't"

y = f"Those who know {binary} and those who {do_not}."

print(x) print(y)

print(f"I said: {x}") print(f"I also said: '{y}'")

## Page 43

Reader pageid: 65

### Reader text

43 EXERCÍCIO 13

Parâmetros, Descompactação, Variáveis

N

1 2 3

4 5 6 7 8

este exercício, falaremos sobre mais um método de entrada que você pode usar para passar variáveis para um script (com script sendo outro nome para seus ar-quivos .py). Você sabe como digitar python3.6 ex13.py para executar o arquivo? Bem, a parte ex13.py do comando é chamada de argumento. O que faremos agora é escrever um script que também aceita argumentos.

Digite este programa e explicarei em detalhes: ex13.py from sys import argv

# leia a seção O que Você Deve Ver para saber como executar isso script, first, second, third = argv

print("The script is called:", script) print("Your first variable is:", first) print("Your second variable is:", second) print("Your third variable is:", third)

Na linha 1, temos o que é chamado de import. É como você adiciona recursos ao script a partir do conjunto de recursos do Python. Ao invés de lhe dar todos os recursos de uma só vez, o Python pede que você informe o que pretende usar. Isso mantém seus programas pequenos, mas também age como uma documentação para outros programadores que lerão seu código depois.

A parte argv é a variável do argumento, um nome muito padrão na programação, que você verá usado em muitas outras linguagens. Essa variável retém os argumentos passados para o script do Python quando você o executa. Nos exercícios, você usará isso mais vezes e verá o que acontece.

A linha 3 descompacta argv, ao invés de conter todos os argumentos. Ele é atribuído às quatro variáveis com as quais você pode trabalhar: script, first, second e third. Pode parecer estranho, mas “descompactar” provavelmente é a melhor palavra para descrever o que ele faz. Significa: “Pegue qualquer coisa em argv, descompacte e atribua a todas essas variáveis à esquerda, em ordem.”

Depois, apenas imprimimos como sempre.

## Page 51

Reader pageid: 73

### Reader text

51 EXERCÍCIO 15

Lendo Arquivos V

ocê sabe como obter a entrada de um usuário com input ou argv. Agora, apren-derá a ler de um arquivo. Você pode precisar brincar mais com este exercício para entender o que está acontecendo, portanto, faça-o com cuidado e lembre-se das veri-ficações. Trabalhar com arquivos é um modo fácil de apagar seu trabalho se não tiver cuidado.

O exercício envolve escrever dois arquivos. Um é o arquivo ex15.py normal que você executará, mas o outro é denominado ex15_sample.txt. Este segundo arquivo não é um script, mas um arquivo de texto sem formatação que iremos ler em nosso script. Veja o conteúdo do arquivo:

This is stuff I typed into a file. It is really cool stuff. Lots and lots of fun to have in here.

O que desejamos fazer é abrir o arquivo em nosso script e imprimi-lo. Contudo, não quere-mos apenas colocar o nome ex15_sample.txt em hard code no nosso script. “Hard code” significa colocar diretamente no código-fonte alguma informação que deve vir do usuário como uma string. Isso é ruim porque queremos que ele carregue outros arquivos mais tarde. A solução é usar argv ou input para peguntar ao usuário qual arquivo abrir, ao invés de incorporar no código o nome do arquivo.

ex15.py 1

2 3

4 5

6 7 8 9

10 11

12 13

14 15

from sys import argv script, filename = argv txt = open(filename)

print(f"Here's your file {filename}:") print(txt.read())

print("Type the filename again:") file_again = input("> ")

txt_again = open(file_again) print(txt_again.read())

## Page 54

Reader pageid: 76

### Reader text

54 APRENDA PYTHON 3 DO JEITO CERTO

Nomeei o arquivo como script, ex15_sample.txt = argv, mas não funcionou. Não é assim que se faz. O código deve ficar exatamente como o meu, depois execute-o na linha de comando do mesmo modo. Você não coloca os nomes dos arquivos, o Python faz isso.

## Page 63

Reader pageid: 85

### Reader text

63 EXERCÍCIO 18

Nomes, Variáveis, Código, Funções

G

rande título, não é? Vou apresentá-lo à função! Dum dum dá! Todo programador sempre fala sobre funções e sempre com ideias diferentes de como elas funcionam

e o que fazem. Mas darei a explicação mais simples que você poderá usar agora. As funções fazem três coisas:

1. Nomeiam partes do código, assim como as variáveis nomeiam strings e números. 2. Recebem argumentos da mesma maneira que seus scripts recebem argv.

3. Usando 1 e 2, permitem que você crie seus próprios “miniscripts” ou “pequenos co-mandos”.

É possível criar uma função usando a palavra def no Python. Você criará quatro funções diferentes que funcionam como scripts, portanto, mostrarei a relação de cada uma.

ex18.py

1 2 3 4

5 6 7 8 9

10 11 12

13 14 15 16

17 18 19 20 21 22

# essa aqui é como seus scripts com argv def print_two(*args): arg1, arg2 = args

print(f"arg1: {arg1}, arg2: {arg2}")

# ok, aquele *args é desnecessário, podemos simplesmente fazer isso def print_two_again(arg1, arg2):

print(f"arg1: {arg1}, arg2: {arg2}")

# essa recebe apenas um argumento def print_one(arg1):

print(f"arg1: {arg1}")

# essa não recebe argumento nenhum def print_none():

print("I got nothin'.") print_two("Zed","Shaw")

print_two_again("Zed","Shaw") print_one("First!") print_none()

## Page 81

Reader pageid: 103

### Reader text

81 EXERCÍCIO 23

Strings, Bytes e Codificações de Caracteres

ara fazer este exercício, você precisará baixar um arquivo de texto que eu escrevi, denominado languages.txt (https://learnpythonthehardway.org/python3/languages.txt). Esse arquivo foi criado com uma lista de idiomas para demonstrar alguns conceitos interessantes:

1. Como os computadores modernos armazenam os idiomas para exibir e processar, e como o Python 3 chama isso de strings.

2. Como você deve “codificar” e “decodificar” as strings do Python em um tipo chamado bytes.

3. Como lidar com os erros no tratamento das string e bytes. 4. Como ler o código e descobrir o que significa, mesmo que nunca tenha visto antes.

Além disso, você também verá rapidamente a instrução if e as lists do Python 3 para processar uma lista de coisas. Não é necessário dominar o código nem entender os concei-tos agora. Você irá praticar nos exercícios posteriores. No momento, seu trabalho é ter uma ideia do futuro e aprender os quatro tópicos na lista anterior.

AVISO! Este exercício é difícil! Há muitas informações que você precisa en-tender e que vão fundo nos computadores. O exercício é complexo porque as strings do Python são complexas e difíceis de usar. Recomendo fazer o exercício bem lentamente. Anote cada palavra que não entende e pesquise. Pegue um parágrafo por vez, se precisar. Você pode continuar com os outros exercícios enquanto estuda este, portanto, não fique preso aqui. Explore por quanto tempo for necessário.

P Pesquisa Inicial

Ensinarei como pesquisar uma parte do código para mostrar seus segredos. Você precisa-rá do arquivo languages.txt para o código funcionar, portanto, baixe-o primeiro. O arquivo languages.txt simplesmente contém uma lista de nomes de idiomas que estão codifica-dos em UTF-8.

ex23.py

1 2

import sys script, encoding, error = sys.argv

## Page 111

Reader pageid: 133

### Reader text

111 EXERCÍCIO 31

Tomando Decisões N

a primeira metade do livro, você imprimiu strings e chamou funções na maioria das vezes, mas tudo estava basicamente em uma linha reta. Seus scripts começavam no topo e seguiam até o final, onde terminavam. Se você criou uma função, poderá executá-la mais tarde, mas ainda não tem o tipo de desvio necessário para realmente tomar decisões. Agora que você tem if, else e elif, poderá começar a criar scripts que decidem coisas.

No último script, você escreveu um conjunto simples de testes fazendo algumas perguntas. No script, você pergunta ao usuário e toma decisões com base nas respostas dele. Escreva o script e experimente muito para entendê-lo.

ex31.py

1 2

3 4

5 6 7 8 9

10

11 12

13 14 15 16 17 18 19 20

21 22 23 24 25 26

27 28

29 30 31

print("""You enter a dark room with two doors. Do you go through door #1 or door #2?""")

door = input("> ") if door == "1":

print("There's a giant bear here eating a cheese cake.") print("What do you do?") print("1. Take the cake.")

print("2. Scream at the bear.") bear = input("> ") if bear == "1": print("The bear eats your face off. Good job!") elif bear == "2": print("The bear eats your legs off. Good job!") else:

print(f"Well, doing {bear} is probably better.") print("Bear runs away.")

elif door == "2":

print("You stare into the endless abyss at Cthulhu's retina.") print("1. Blueberries.")

print("2. Yellow jacket clothespins.") print("3. Understanding revolvers yelling melodies.") insanity = input("> ") if insanity == "1" or insanity == "2": print("Your body survives powered by a mind of jello.")

## Page 115

Reader pageid: 137

### Reader text

115 EXERCÍCIO 32

Loops e Listas A

gora, você deve conseguir fazer alguns programas muito mais interessantes. Se você vem acompanhando direito, deve ter percebido que agora consegue combinar tudo o que aprendeu com as instruções if e as expressões booleanas para que seu programa faça comandos inteligentes.

Contudo, os programas também precisam fazer coisas repetidas com muita rapidez. Usare-mos um loop for neste exercício para criar e imprimir várias listas. Quando fizer o exercício, começará a entender o que são. Não contarei. Terá que descobrir.

Antes de usar um loop for, você precisa de uma maneira de armazenar os resultados dos loops em algum lugar. O melhor modo de fazer isto é com listas. Uma lista é exatamente isso: um contêiner de coisas organizadas, da primeira até a ultima. Não é complicado; você só precisa aprender uma nova sintaxe. Primeiramente, veja como criar as listas:

hairs = ['brown', 'blond', 'red'] eyes = ['brown', 'blue', 'green'] weights = [1, 2, 3, 4]

A lista é iniciada com [ (colchete esquerdo), que a “abre”. Então, você dispõe nela cada item que deseja, separado por vírgulas, semelhante aos argumentos da função. Por último, termi-na a lista com um ] (colchete direito) para indicar que acabou. O Python pega a lista e todo o seu conteúdo, e o atribui a uma variável.

AVISO! Aqui é que as coisas ficam complicadas para as pessoas que não con-seguem codificar. Seu cérebro foi ensinado que o mundo é plano. Lembra do último exercício, quando colocou instruções if dentro de instruções if? Pro-vavelmente isso confundiu sua cabeça, porque a maioria das pessoas não considera “aninhar” coisas dentro de coisas. Na programação, as estruturas aninhadas estão em todos os lugares. Você encontrará funções que chamam outras funções com instruções if que têm listas com listas dentro de listas. Se você vir tal estrutura e não conseguir entender, pegue lápis e papel, divida-a manualmente parte por parte até compreender.

Agora, criaremos algumas listas usando loops for e imprimiremos: ex32.py

1 2 3

the_count = [1, 2, 3, 4, 5]

fruits = ['apples', 'oranges', 'pears', 'apricots'] change = [1, 'pennies', 2, 'dimes', 3, 'quarters']

## Page 137

Reader pageid: 159

### Reader text

137 EXERCICIO 38

Fazendo Coisas com Listas V

ocê aprendeu sobre listas. Quando aprendeu sobre os loops while, “anexou” nú-meros ao final de uma lista e imprimiu. Houve também Exercícios Simulados nos

quais precisou encontrar todas as coisas que poderia fazer com as listas na documen-tação do Python. Isso foi pouco tempo atrás, portanto, reveja os tópicos se não souber sobre o que estou falando.

Encontrou? Lembrou? Bom. Quando fez isso, tinha uma lista e “chamou” a função append. Contudo, é possível que não entenda mesmo o que está acontecendo, portanto, vejamos o que podemos fazer com as listas.

Quando você escreve mystuff.append('hello'), está realmente iniciando uma cadeia de eventos dentro do Python e fazendo com que algo aconteça com a lista mystuff. Veja como funciona:

1. O Python vê a lista mystuff mencionada e pesquisa a variável. Ele pode ter que retornar para ver se você a criou com =, se for um argumento da função, ou se é uma variável global. De qualquer modo, tem que encontrar mystuff.

2. Assim que encontra mystuff, lê o operador . (ponto) e começa a ver as variáveis que fazem parte de mystuff. Como mystuff é uma lista, ele sabe que tem muitas funções.

3. Depois, acessa append e compara o nome com todos os nomes que mystuff diz que possui. Se append existir (existe), o Python pegará isso para usar.

4. Em seguida, o Python vê o parêntese ( (de abertura) e entende: “Ah sim, deve ser uma função.” Nesse ponto, ele chama (executa) a função normalmente, mas com um argumento extra.

5. Tal argumento é ... mystuff! Eu sei, é estranho, certo? Mas é como o Python fun-ciona, portanto, é melhor lembrar e aceitar o resultado. O que acontece, no final de tudo, é uma chamada da função que parece com append(mystuff, 'hello'), ao invés do que você lê, que é mystuff.append('hello').

Em grande parte, não é necessário saber que isso está acontecendo, mas ajuda quando há mensagens de erro do Python como esta:

$ python3.6 >>> class Thing(object): ... ... ...

>>> a = Thing() >>> a.test("hello")

def test(message): print(message)

## Page 143

Reader pageid: 165

### Reader text

143 EXERCÍCIO 39

Dicionários, Ah, os Adoráveis Dicionários

gora, você aprenderá sobre a estrutura de dados Dicionário no Python. Um dicioná-rio (ou dic) é um modo de armazenar dados assim como uma lista, mas, ao invés de usar apenas números para obter dados, é possível usar quase tudo. Isso permite tratar um dic como um banco de dados para armazenar e organizar dados.

A

Vamos comparar o que os dics e as listas podem fazer. Veja, uma lista permite fazer isto: Sessão Python do Exercício 39

>>> things = ['a', 'b', 'c', 'd'] >>> print(things[1]) b

>>> things[1] = 'z' >>> print(things[1]) z

>>> things ['a', 'z', 'c', 'd']

Você pode usar números para indexar uma lista, significando que pode usar números para descobrir o que existe nas listas. A essa altura, você já deveria saber isso sobre as listas, mas certifique-se de que você entenda que só pode usar números para obter os itens em uma lista.

Um dic permite usar qualquer coisa, não apenas números. Sim, um dic associa uma coisa à outra, não importa o que é. Veja:

Sessão Python do Exercício 39

>>> stuff = {'name': 'Zed', 'age': 39, 'height': 6 * 12 + 2} >>> print(stuff['name']) Zed >>> print(stuff['age']) 39

>>> print(stuff['height']) 74

>>> stuff['city'] = "SF" >>> print(stuff['city']) SF

Você verá que, ao invés de apenas números, estamos usando strings para informar o que queremos do dicionário stuff. Também podemos colocar coisas novas no dicionário com strings. Contudo, não precisam ser strings. Também podemos fazer isso:
