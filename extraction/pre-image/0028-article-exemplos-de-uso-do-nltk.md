---
id: "28"
title: "Exemplos de Uso do NLTK"
source_url: "https://www.nltk.org/howto/portuguese_en.html"
fetch_url: "https://www.nltk.org/howto/portuguese_en.html"
resolved_url: "https://www.nltk.org/howto/portuguese_en.html"
firecrawl_title: "NLTK :: Sample usage for portuguese_en"
description: null
fetched_at: "2026-05-12T03:59:51.534563Z"
provider: "firecrawl"
strategy: "standard"
cache_key: "a4ca713f6ed74dddb2dc887d3a8f9ea369a072ceaa1e9cafe7564c3f172d5ce1"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=utf-8"
word_count: 2129
char_count: 14734
content_sha256: "7510de10e04f57ecdb7c59d028b6a8b3413639514d10b624778ed2d99d19c060"
image_count: 0
link_count: 28
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

# Sample usage for portuguese_en

## Examples for Portuguese Processing

This HOWTO contains a variety of examples relating to the Portuguese language. It is intended to be read in conjunction with the NLTK book (`https://www.nltk.org/book/`). For instructions on running the Python interpreter, please see the section _Getting Started with Python_, in Chapter 1.

### Python Programming, with Portuguese Examples

Chapter 1 of the NLTK book contains many elementary programming examples, all with English texts. In this section, we’ll see some corresponding examples using Portuguese. Please refer to the chapter for full discussion. _Vamos!_

```python
>>> from nltk.test.portuguese_en_fixt import setup_module
>>> setup_module()
```

```python
>>> from nltk.examples.pt import *
*** Introductory Examples for the NLTK Book ***
Loading ptext1, ... and psent1, ...
Type the name of the text or sentence to view it.
Type: 'texts()' or 'sents()' to list the materials.
ptext1: Memórias Póstumas de Brás Cubas (1881)
ptext2: Dom Casmurro (1899)
ptext3: Gênesis
ptext4: Folha de Sao Paulo (1994)
```

Any time we want to find out about these texts, we just have to enter their names at the Python prompt:

```python
>>> ptext2
<Text: Dom Casmurro (1899)>
```

#### Searching Text

A concordance permits us to see words in context.

```python
>>> ptext1.concordance('olhos')
Building index...
Displaying 25 of 138 matches:
De pé , à cabeceira da cama , com os olhos estúpidos , a boca entreaberta , a t
orelhas . Pela minha parte fechei os olhos e deixei - me ir à ventura . Já agor
xões de cérebro enfermo . Como ia de olhos fechados , não via o caminho ; lembr
gelos eternos . Com efeito , abri os olhos e vi que o meu animal galopava numa
me apareceu então , fitando - me uns olhos rutilantes como o sol . Tudo nessa f
 mim mesmo . Então , encarei - a com olhos súplices , e pedi mais alguns anos .
...
```

For a given word, we can find words with a similar text distribution:

```python
>>> ptext1.similar('chegar')
Building word-context index...
acabada acudir aludir avistar bramanismo casamento cheguei com contar
contrário corpo dali deixei desferirem dizer fazer filhos já leitor lhe
>>> ptext3.similar('chegar')
Building word-context index...
achar alumiar arrombar destruir governar guardar ir lavrar passar que
toda tomar ver vir
```

We can search for the statistically significant collocations in a text:

```python
>>> ptext1.collocations()
Building collocations list
Quincas Borba; Lobo Neves; alguma coisa; Brás Cubas; meu pai; dia
seguinte; não sei; Meu pai; alguns instantes; outra vez; outra coisa;
por exemplo; mim mesmo; coisa nenhuma; mesma coisa; não era; dias
depois; Passeio Público; olhar para; das coisas
```

We can search for words in context, with the help of _regular expressions_, e.g.: 

```python
>>> ptext1.findall("<olhos> (<.*>)")
estúpidos; e; fechados; rutilantes; súplices; a; do; babavam;
na; moles; se; da; umas; espraiavam; chamejantes; espetados;
...
```

We can automatically generate random text based on a given text, e.g.: 

```python
>>> ptext3.generate()
No princípio , criou Deus os abençoou , dizendo : Onde { estão } e até
a ave dos céus , { que } será . Disse mais Abrão : Dá - me a mulher
que tomaste ; porque daquele poço Eseque , { tinha .} E disse : Não
poderemos descer ; mas , do campo ainda não estava na casa do teu
pescoço . E viveu Serugue , depois Simeão e Levi { são } estes ? E o
varão , porque habitava na terra de Node , da mão de Esaú : Jeús ,
Jalão e Corá
```

#### Texts as List of Words

A few sentences have been defined for you.

```python
>>> psent1
['o', 'amor', 'da', 'glór...]}\n```

Notice that the sentence has been _tokenized_. Each token is represented as a string, represented using quotes, e.g. `'coisa'`. Some strings contain special characters, e.g. `\xf3`, the internal representation for ó. The tokens are combined in the form of a _list_. How long is this list?

```python
>>> len(psent1)
25
```

What is the vocabulary of this sentence?

```python
>>> sorted(set(psent1))
[',', '.', 'a', 'amor', 'coisa', 'conseqüentemente', 'da', 'e', 'era',\
 'feição', 'genuína', 'glória', 'homem', 'humana', 'há', 'mais', 'no',\
 'o', 'que', 'sua', 'verdadeiramente']
```

Let’s iterate over each item in `psent2`, and print information for each:

```python
>>> for w in psent2:
...     print(w, len(w), w[-1])
...
Não 3 o
consultes 9 s
dicionários 11 s
. 1 .
```

Observe how we make a human-readable version of a string, using `decode()`. Also notice that we accessed the last character of a string `w` using `w[-1]`.

We just saw a `for` loop above. Another useful control structure is a _list comprehension_.

```python
>>> [w.upper() for w in psent2]
['NÃO', 'CONSULTES', 'DICIONÁRIOS', '.']
>>> [w for w in psent1 if w.endswith('a')]
['da', 'glória', 'era', 'a', 'coisa', 'humana', 'a', 'sua', 'genuína']
>>> [w for w in ptext4 if len(w) > 15]
['norte-irlandeses', 'pan-nacionalismo', 'predominatemente', 'primeiro-ministro',\
'primeiro-ministro', 'irlandesa-americana', 'responsabilidades', 'significativamente']
```

We can examine the relative frequency of words in a text, using `FreqDist`:

```python
>>> fd1 = FreqDist(ptext1)
>>> fd1
<FreqDist with 10848 samples and 77098 outcomes>
>>> fd1['olhos']
137
>>> fd1.max()
','
>>> fd1.samples()[:100]
[',', '.', 'a', 'que', 'de', 'e', '-', 'o', ';', 'me', 'um', 'não',\
'—', 'se', 'do', 'da', 'uma', 'com', 'os', 'é', 'era', 'as', 'eu',\
'lhe', 'ao', 'em', 'para', 'mas', '...', '!', 'à', 'na', 'mais', '?',\
'no', 'como', 'por', 'Não', 'dos', 'o', 'ele', ':', 'Virgília',\
'me', 'disse', 'minha', 'das', 'O', '/', 'A', 'CAPÍTULO', 'muito',\
'depois', 'coisa', 'foi', 'sem', 'olhos', 'ela', 'nos', 'tinha', 'nem',\
'E', 'outro', 'vida', 'nada', 'tempo', 'menos', 'outra', 'casa', 'homem',\
'porque', 'quando', 'mim', 'mesmo', 'ser', 'pouco', 'estava', 'dia',\
'tão', 'tudo', 'Mas', 'até', 'D', 'ainda', 'só', 'alguma',\
'la', 'vez', 'anos', 'há', 'Era', 'pai', 'esse', 'lo', 'dizer', 'assim',\
'então', 'dizia', 'aos', 'Borba']
```

### Reading Corpora

#### Accessing the Machado Text Corpus

NLTK includes the complete works of Machado de Assis.

```python
>>> from nltk.corpus import machado
>>> machado.fileids()
['contos/macn001.txt', 'contos/macn002.txt', 'contos/macn003.txt', ...]
```

Each file corresponds to one of the works of Machado de Assis. To see a complete list of works, you can look at the corpus README file: `print machado.readme()`. Let’s access the text of the _Posthumous Memories of Brás Cubas_.

We can access the text as a list of characters, and access 200 characters starting from position 10,000.

```python
>>> raw_text = machado.raw('romance/marm05.txt')
>>> raw_text[10000:10200]
u', 'primou no\nEstado, e foi um dos amigos particulares do vice-rei Conde
da Cunha.\n\nComo este apelido de Cubas lhe\ncheirasse excessivamente a
tanoaria, alegava meu pai, bisneto de Damião, que o\ndito ape'
```

However, this is not a very useful way to work with a text. We generally think of a text as a sequence of words and punctuation, not characters:

```python
>>> text1 = machado.words('romance/marm05.txt')
>>> text1
['Romance', ',', 'Memórias', 'Póstumas', 'de', ...]
>>> len(text1)
77098
>>> len(set(text1))
10848
```

Here’s a program that finds the most common ngrams that contain a particular target word.

```python
>>> from nltk import ngrams, FreqDist
>>> target_word = 'olhos'
>>> fd = FreqDist(ng
...               for ng in ngrams(text1, 5)
...               if target_word in ng)
>>> for hit in fd.samples():
...     print(' '.join(hit))
...
, com os olhos no
com os olhos no ar
com os olhos no chão
e todos com os olhos
me estar com os olhos
os olhos estúpidos , a
os olhos na costura ,
os olhos no ar ,
, com os olhos espetados
, com os olhos estúpidos
, com os olhos fitos
, com os olhos naquele
, com os olhos para
```

#### Accessing the MacMorpho Tagged Corpus

NLTK includes the MAC-MORPHO Brazilian Portuguese POS-tagged news text, with over a million words of journalistic texts extracted from ten sections of the daily newspaper _Folha de Sao Paulo_, 1994.

We can access this corpus as a sequence of words or tagged words as follows:

```python
>>> import nltk.corpus
>>> nltk.corpus.mac_morpho.words()
['Jersei', 'atinge', 'média', 'de', 'Cr$', '1,4', ...]
>>> nltk.corpus.mac_morpho.sents()
[['Jersei', 'atinge', 'média', 'de', 'Cr$', '1,4', 'milhão',\
'em', 'a', 'venda', 'de', 'a', 'Pinhal', 'em', 'São', 'Paulo'],\
['Programe', 'sua', 'viagem', 'a', 'a', 'Exposição', 'Nacional',\
'do', 'Zeb', ',', 'que', 'começa', 'dia', '25'], ...]
>>> nltk.corpus.mac_morpho.tagged_words()
[('Jersei', 'N'), ('atinge', 'V'), ('média', 'N'), ...]
```

We can also access it in sentence chunks.

```python
>>> nltk.corpus.mac_morpho.tagged_sents()
[[('Jersei', 'N'), ('atinge', 'V'), ('média', 'N'), ('de', 'PREP'),\
  ('Cr$', 'CUR'), ('1,4', 'NUM'), ('milhão', 'N'), ('em', 'PREP|+'),\
  ('a', 'ART'), ('venda', 'N'), ('de', 'PREP|+'), ('a', 'ART'),\
  ('Pinhal', 'NPROP'), ('em', 'PREP'), ('São', 'NPROP'),\
  ('Paulo', 'NPROP')],\
 [('Programe', 'V'), ('sua', 'PROADJ'), ('viagem', 'N'), ('a', 'PREP|+'),\
  ('a', 'ART'), ('Exposição', 'NPROP'), ('Nacional', 'NPROP'),\
  ('do', 'NPROP'), ('Zeb', 'NPROP'), (',', ','), ('que', 'PRO-KS-REL'),\
  ('começa', 'V'), ('dia', 'N'), ('25', 'N|AP')], ...]
```

This data can be used to train taggers (examples below for the Floresta treebank). 

#### Accessing the Floresta Portuguese Treebank

The NLTK data distribution includes the “Floresta Sinta(c)tica Corpus” version 7.4, available from `https://www.linguateca.pt/Floresta/`.

We can access this corpus as a sequence of words or tagged words as follows:

```python
>>> from nltk.corpus import floresta
>>> floresta.words()
['Um', 'revivalismo', 'refrescante', 'O', '7_e_Meio', ...]
>>> floresta.tagged_words()
[('Um', '>N+art'), ('revivalismo', 'H+n'), ...]
```

The tags consist of some syntactic information, followed by a plus sign, followed by a conventional part-of-speech tag. Let’s strip off the material before the plus sign:

```python
>>> def simplify_tag(t):
...     if "+" in t:
...         return t[t.index("+")+1:]
...     else:
...         return t
>>> twords = floresta.tagged_words()
>>> twords = [(w.lower(), simplify_tag(t)) for (w,t) in twords]
>>> twords[:10]
[('um', 'art'), ('revivalismo', 'n'), ('refrescante', 'adj'), ('o', 'art'), ('7_e_meio', 'prop'),\
('é', 'v-fin'), ('um', 'art'), ('ex-libris', 'n'), ('de', 'prp'), ('a', 'art')]
```

Pretty printing the tagged words:

```python
>>> print(' '.join(word + '/' + tag for (word, tag) in twords[:10]))
um/art revivalismo/n refrescante/adj o/art 7_e_meio/prop é/v-fin um/art ex-libris/n de/prp a/art
```

Count the word tokens and types, and determine the most common word:

```python
>>> words = floresta.words()
>>> len(words)
211852
>>> fd = nltk.FreqDist(words)
>>> len(fd)
29421
>>> fd.max()
'de'
```

List the 20 most frequent tags, in order of decreasing frequency:

```python
>>> tags = [simplify_tag(tag) for (word,tag) in floresta.tagged_words()]
>>> fd = nltk.FreqDist(tags)
>>> fd.keys()[:20]
['n', 'prp', 'art', 'v-fin', ',', 'prop', 'adj', 'adv', '.',\
 'conj-c', 'v-inf', 'pron-det', 'v-pcp', 'num', 'pron-indp',\
 'pron-pers', '«', '»', 'conj-s', '}']
```

We can also access the corpus grouped by sentence:

```python
>>> floresta.sents()
[['Um', 'revivalismo', 'refrescante'],\
 ['O', '7_e_Meio', 'é', 'um', 'ex-libris', 'da', 'noite',\
  'algarvia', '.'], ...]
>>> floresta.tagged_sents()
[[('Um', '>N+art'), ('revivalismo', 'H+n'), ('refrescante', 'N<+adj')],\
 [('O', '>N+art'), ('7_e_Meio', 'H+prop'), ('é', 'P+v-fin'),\
  ('um', '>N+art'), ('ex-libris', 'H+n'), ('de', 'H+prp'),\
  ('a', '>N+art'), ('noite', 'H+n'), ('algarvia', 'N<+adj'), ('.', '.')],\
 ...]
>>> floresta.parsed_sents()
[Tree('UTT+np', [Tree('>N+art', ['Um']), Tree('H+n', ['revivalismo']),\
                 Tree('N<+adj', ['refrescante'])]),\
 Tree('STA+fcl',\
     [Tree('SUBJ+np', [Tree('>N+art', ['O']),\
                       Tree('H+prop', ['7_e_Meio'])]),\
      Tree('P+v-fin', ['é']),\
      Tree('SC+np',\
         [Tree('>N+art', ['um']),\
          Tree('H+n', ['ex-libris']),\
          Tree('N<+pp', [Tree('H+prp', ['de']),\
                         Tree('P<+np', [Tree('>N+art', ['a']),\
                                        Tree('H+n', ['noite']),\
                                        Tree('N<+adj', ['algarvia'])])])]),\
      Tree('.', ['.'])]), ...]
```

To view a parse tree, use the `draw()` method, e.g.: 

```python
>>> psents = floresta.parsed_sents()
>>> psents[5].draw()
```

#### Character Encodings

Python understands the common character encoding used for Portuguese, ISO 8859-1 (ISO Latin 1).

```python
>>> import os, nltk.test
>>> testdir = os.path.split(nltk.test.__file__)[0]
>>> text = open(os.path.join(testdir, 'floresta.txt'), 'rb').read().decode('ISO 8859-1')
>>> text[:60]
'O 7 e Meio é um ex-libris da noite algarvia.
É uma das mais '
>>> print(text[:60])
O 7 e Meio é um ex-libris da noite algarvia.
É uma das mais
```

For more information about character encodings and Python, please see section 3.3 of the book.

### Processing Tasks

#### Simple Concordancing

Here’s a function that takes a word and a specified amount of context (measured in characters), and generates a concordance for that word.

```python
>>> def concordance(word, context=30):
...     for sent in floresta.sents():
...         if word in sent:
...             pos = sent.index(word)
...             left = ' '.join(sent[:pos])
...             right = ' '.join(sent[pos+1:])
...             print('%*s %s %-*s' %
...                 (context, left[-context:], word, context, right[:context]))
```

```python
>>> concordance("dar")
anduru , foi o suficiente para dar a volta a o resultado .
             1. O P?BLICO veio dar a a imprensa di?ria portuguesa
  A fartura de pensamento pode dar maus resultados e n?s n?o quer
                      Come?a a dar resultados a pol?tica de a Uni
ial come?ar a incorporar- lo e dar forma a um ' site ' que tem se
r com Constantino para ele lhe dar tamb?m os pap?is assinados .
va a brincar , pois n?o lhe ia dar procura??o nenhuma enquanto n?
?rica como o ant?doto capaz de dar sentido a o seu enorme poder .
. . .
>>> concordance("vender")
er recebido uma encomenda para vender 4000 blindados a o Iraque .
m?rico_Amorim caso conseguisse vender o lote de ac??es de o empres?r
mpre ter jovens simp?ticos a ? vender ? chega ! }
       Disse que o governo vai vender ? desde autom?vel at? particip
ndiciou ontem duas pessoas por vender carro com ?gio .
        A inten??o de Fleury ? vender as a??es para equilibrar as fi
```
