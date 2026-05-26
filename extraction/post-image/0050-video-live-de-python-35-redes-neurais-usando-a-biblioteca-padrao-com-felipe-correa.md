---
id: "50"
title: "Live de Python #35 - Redes neurais usando a biblioteca padrão (com Felipe Corrêa)"
source_url: "https://www.youtube.com/watch?v=GqVQRrE1axw&feature=share&t=3630"
fetch_url: "https://www.youtube.com/watch?v=GqVQRrE1axw&feature=share&t=3630"
resolved_url: "https://www.youtube.com/watch?v=GqVQRrE1axw"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T05:43:22.513775Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: null
cache_keys:
  - "ac752df24ee769d48a428801fd30f313df7dcfdfc5cbb6d22e479b096c681378"
  - "0dba6706a295ab657ceeb149c6bcb17542ac5dca6f167d5c9e060beb14f85951"
  - "c13a389bb2b07b294a264bca50dd15477daa1ffc9f6f0ecbc58e38a476e57159"
  - "71d975804746f271e25e0b3306016974ec4af295e3c6b9205986c5548e2091c4"
  - "ecb0f6449d4884688e8aba422ff71ebd9b5722c30f12ca8204241a96243e0e58"
  - "d19b2dda766a3c42339f85b2a039d9efe6798dd4d3bec39ca25da7cef86c5545"
  - "04af9b0ac5305f46ac3a8ec80c42fb2457a69f241358de77131899d4437f5c0d"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.05
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 4185.0
transcript_source: "local_whisper_vtt"
transcript_sha256: "ce7236cbb5aa63f221eca9e45120f4204cb84a884dd006f2ac549c5cdee29a51"
word_count: 14705
char_count: 78340
content_sha256: "4c7a2a2eecd192d867889ea609b06bfae9022af4971bad3cc1246416445a270a"
image_count: 23
link_count: 0
total_token_count: 195726
estimated_input_tokens: 147730
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## 00:00 Introdução e apresentação do tema

**Spoken content:**
- [00:01] Estamos no ar.
- [00:02] Fala jovenzinhos, como vão vocês?
- [00:05] Então, hoje a gente vai ter a presença ilustre do menino aí que tá devendo uma live desde o outubro do ano passado.
- [00:13] Mas vamos tocar isso aí hoje.
- [00:17] Ele vai falar pra gente um pouco sobre redes neurais.
- [00:20] E, pô, redes neurais from scratch é muito hardcore, né?
- [00:26] A gente podia ter usado um scikit-learn aí pra facilitar as coisas.
- [00:30] Mas ele gosta do desafio.
- [00:32] É, mas é complicado um pouquinho.
- [00:34] Então, cara, se apresenta aí, fala o que tu faz da vida.
- [00:38] O que você quiser falar aí, você gosta de comer laranja, cara, sei lá, qualquer coisa.
- [00:41] E pode tocar, que a live é toda sua.
- [00:43] E qualquer coisa, se alguém perguntar alguma coisa específica aqui, eu te aviso.
- [00:48] E aí eu te interrompo um pouquinho, mas a gente toca.
- [00:52] Beleza.
- [00:53] Aqui, boa noite, povo.
- [00:56] Meu nome é Felipe, eu sou estudante em área de computação.
- [01:00] Tô aí querendo formar já, veja a hora.
- [01:03] E hoje a gente vai falar um pouco sobre redes neurais.
- [01:06] Assim, um pouquinho da teoria, porque vai ser bem básico mesmo,
- [01:11] porque é uma matéria muito grande,
- [01:14] pra estudar, assim, é muita fórmula, é muita matemática, envolve muita coisa.
- [01:17] Então a gente vai falar, vai raspar um pouco sobre o que é,
- [01:20] como ela foi construída, foi concebida.
- [01:23] Depois a gente vai pra parte mais legal, que é o código mesmo.
- [01:26] Então vou passar aqui uma apresentação,
- [01:28] que eu fiz aqui bem básica, bem simples, bem resumida.
- [01:32] Espero que vocês gostem.
- [01:34] Um instante.

**On-screen content:** The video shows two men in a video call. The first speaker (left, with curly hair and beard, wearing a striped shirt) introduces the second speaker (right, with short hair and beard, wearing a dark t-shirt). The background of the first speaker shows a plain white wall, while the second speaker has a yellow wall with a whiteboard and shelves with books.

## 01:34 Dificuldades técnicas com a apresentação

**Spoken content:**
- [01:44] Vocês estão vendo em tela cheia a apresentação?
- [01:46] Tá vendo, Du?
- [01:48] Em tela cheia?
- [01:49] Tá só a janela aqui, cara, não tá a tela cheia, não.
- [01:53] Ó, grande.
- [01:55] Ah, tá.
- [01:56] Beleza, então.
- [01:58] Tô aqui, redes neurais.
- [02:00] A gente vai implementar um Perceptor.
- [02:02] Acho que ainda não foi, cara.
- [02:03] A gente ainda tá só na...
- [02:04] Ah, deixa eu ver aqui.
- [02:10] Tá só na normal.
- [02:12] Tá, tá, tá no browser.
- [02:14] Tipo...
- [02:15] Tá no browser normal.
- [02:15] Agora.
- [02:16] Mudou?
- [02:17] Ainda tá no browser normal ainda.
- [02:19] Tá no browser.
- [02:20] Deixa eu fazer o seguinte aqui.
- [02:22] E agora?
- [02:24] Agora eu tô te vendo.
- [02:26] Ó.
- [02:27] Viagem.
- [02:28] Só um instante, então.
- [02:30] Tá mal aí, galera?
- [02:32] Não, vai com calma aí.
- [02:34] Tranquilo.
- [03:00] Não, vai com calma aí.
- [03:02] Não, vai com calma aí.
- [03:03] Não, vai com calma aí.
- [03:04] Não, vai com calma aí.
- [03:05] Não, vai com calma aí.
- [03:05] Não, vai com calma aí.
- [03:06] Não, vai com calma aí.
- [03:07] Não, vai com calma aí.
- [03:07] Não, vai com calma aí.
- [03:07] Não, vai com calma aí.
- [03:09] Não, vai com calma aí.
- [03:09] Não, vai com calma aí.
- [03:10] Não, vai com calma aí.
- [03:11] Não, vai com calma aí.
- [03:11] Não, vai com calma aí.
- [03:12] Não, vai com calma aí.
- [03:13] Não, vai com calma aí.
- [03:14] Não, vai com calma aí.
- [03:15] Não, vai com calma aí.
- [03:16] Não, vai com calma aí.
- [03:17] Não, vai com calma aí.
- [03:18] Não, vai com calma aí.
- [03:30] E agora, pessoal?

**On-screen content:** The second speaker attempts to share his screen. Initially, only a small window of the presentation is visible, or the browser window itself, not the full-screen presentation. The first speaker guides him through the process.

## 03:52 Apresentação "Redes Neurais"

**Spoken content:**
- [03:53] Oh, agora está show de bola, velho.
- [03:57] Beleza, então a gente vai implementar aqui um Percepto com o Simples, com o Python e as
- [04:02] bibliotecas padrões que ele já vem, né?

**On-screen content:** ![Slide: Redes Neurais - Implementação de Perceptron Simples com Python e bibliotecas padrão](video-frame://50@04:00)

## 04:04 O que são Redes Neurais?

**Spoken content:**
- [04:04] Então, o que são as redes neurais?
- [04:07] Elas são basicamente uma construção que eles fizeram baseada no neurônio biológico.
- [04:13] É um trabalho lá que veio de 1943 com esses dois caras aqui, só que por causa do processamento
- [04:20] que era muito baixo, máquinas antigas, ficou meio que no limbo toda essa parte, esse estudo.
- [04:27] E aí veio florescer de uns anos para cá, né?
- [04:29] Com o crescimento, a quantidade de dados aumentando, o processamento das máquinas e tudo mais.
- [04:36] Então, aqui a gente tem um exemplo aqui do neurônio biológico, como ele é.
- [04:39] E aqui é uma rede neural mesmo em si, que são as entradas, aqui são seguidas pelos
- [04:45] pesos, cada um desses traços aqui representa um peso.
- [04:48] Essas aqui são a camada oculta, ou neurônios intermediários, e as camadas de saída.
- [04:56] Tem essas duas definições aqui, que eu já demorei muito, eu não vou nem falar muito, não.
- [05:00] E aqui a gente tem o percepton simples.

**On-screen content:** ![Slide: O que são Redes Neurais? - Trabalho proposto por McCulloch e Pitts em 1943; Baseada em um neurônio biológico. Diagrama de neurônio biológico e diagrama de rede neural com entradas, pesos, neurônios intermediários e saídas.](video-frame://50@04:00)

## 05:00 Perceptron Simples

**Spoken content:**
- [05:03] O que o percepton simples é?
- [05:05] Ele foi um modelo proposto por esse cara aqui em 1958, e ele é a forma mais simples de
- [05:11] representar uma rede neural, com uma única camada.
- [05:14] Ele só resolve problemas linearmente separáveis, ou seja, problemas de classificação de padrão,
- [05:21] onde você consegue traçar uma linha entre as duas classes.
- [05:25] Se não for assim, ele pode até funcionar, mas ele fica muito instável.
- [05:31] Então, aqui a gente tem a representação do que são cada um desses pontos aqui.
- [05:36] Acho que acredito até no próximo slide aqui.
- [05:38] Melhor esse aqui.
- [05:40] Então, aqui a gente tem as entradas.
- [05:41] Cada uma dessa entrada aqui, ela é seguida por um peso.
- [05:45] Você multiplica esse peso pela entrada, soma tudo aqui.
- [05:51] Aí tem uma função de ativação que vai falar, dependendo do resultado, se ele é de uma classe ou de outra.
- [05:58] E aí, fornece para a gente a saída.
- [06:01] Esse bias aqui, ele é um potencial, ele é um limiar de ativação que ele serve para quê?
- [06:08] Vamos supor, no caso de você ter uma rede que os valores vão de 200 a 2 mil, vamos supor.
- [06:16] Ele deixa, ele faz com que esse valor não comece em zero.
- [06:22] Ele comece sempre em 200 e vai até onde ele tem que ir.
- [06:27] Mas ele não deixa ficar, abaixar muito para não demorar muito a convergência da rede.
- [06:32] Então, a gente tem aqui o modelo matemático.
- [06:35] Ele é, nada mais é do que esse modelo aqui, um perceptor.
- [06:39] Com as entradas de rede, que você vai somar pelo peso,
- [06:43] diminuir pelo limiar de ativação, que é esse bias,
- [06:47] ou alguns falam de viés,
- [06:49] que fica, que mantém o algoritmo no hiperplano.
- [06:53] O potencial de ativação, que é esse U, vai receber esses valores,
- [06:57] aqui do somatório, vai jogar dentro dessa função,
- [07:00] e vai sair para mim o valor da rede aqui.
- [07:04] A função que nós vamos usar é essa função degrau.
- [07:07] Essa função degrau, ela vai falar o quê?
- [07:10] Se esse valor de U aqui, que eu jogar aqui, for maior do que zero,
- [07:16] ou igual a zero, ele pertence à classe 1.
- [07:19] Se não, pertence à classe zero.
- [07:20] Então, esse é o modelo dele, ele vai traçando retas
- [07:26] até que todos os pontos estejam separados.
- [07:31] Então, ele vai...
- [07:34] Isso vai depender do projeto, mas pode ser que demore
- [07:36] 500 vezes, 100 vezes, 10 vezes, vai depender muito da montagem
- [07:41] e dos dados também.
- [07:43] Então, aqui, completando aqui, o bias serve para aumentar
- [07:46] os graus de liberdade,
- [07:47] permitindo uma melhor adaptação por parte do conhecimento.
- [07:51] E tem a taxa de aprendizagem também,
- [07:53] que é bem importante, porque é ela que vai definir
- [07:57] o quanto, o quanto tempo a sua rede pode demorar para convergir.
- [08:02] Se for uma taxa de aprendizagem muito pequena,
- [08:04] uma rede demora muito mais.
- [08:06] Caso contrário, demora menos.
- [08:07] Aqui, a gente tem um algoritmo.
- [08:09] Algoritmo de treinamento.
- [08:12] Nós vamos fazer, basicamente, nós vamos fazer isso aqui,
- [08:15] que é o algoritmo de treinamento do Perceptor,
- [08:18] e depois vamos jogar ele para uma taxa de validação,
- [08:20] que aí a gente vai falar quais as classes,
- [08:23] se eles pertencem, eles vão retornar para a gente os valores.
- [08:26] Lembrando que o processo que a gente vai utilizar aqui
- [08:31] é o processo supervisionado.
- [08:33] Que é isso aqui.
- [08:35] Quando os itens, os atributos alvo, vamos dizer assim,
- [08:39] os atributos, as variáveis atributo,
- [08:43] elas são seguidas de variáveis alvo.
- [08:47] Ou seja, a gente já sabe o quanto que aquele resultado,
- [08:51] aqueles valores que a gente tem, tem que dar.
- [08:53] A gente já sabe isso.
- [08:55] O não supervisionado, ele já é mais para a questão de cluster,
- [08:59] é para você pegar itens, identificar pontos iguais entre os itens
- [09:03] e poder agrupar.
- [09:05] Mas no caso, a gente vai usar o supervisionado.
- [09:08] Aqui são umas referências que eu peguei, alguns dados.
- [09:12] Tem esses livros aqui, esse primeiro, o Data Science do Zero.
- [09:16] Ele é bom para você ver a implementação.
- [09:19] No caso de você ver...
- [09:21] A teoria, ele é muito básico, muito, muito básico.
- [09:24] Mas ele é muito legal para ver a implementação.
- [09:26] Tem esse aqui, que já é um pouco mais pesado.
- [09:29] Eu não li, mas colegas meus que leram, falaram que ele é bem mais pesado.
- [09:33] E tem esse aqui, Inteligente Fiscal, noções gerais,
- [09:36] que ele é bem mais básico.
- [09:37] E assim, é bem tranquilo de entender.
- [09:40] Ele é muito light mesmo.
- [09:41] E aqui é onde a gente buscou o Data Set,
- [09:44] que é o mais importante que a gente precisa.
- [09:46] É o Data Set.
- [09:47] Então, vamos agora...
- [09:49] Esse aí mesmo.
- [09:51] Eu tenho até esse livro, mas ele é bem básico mesmo.
- [09:54] Se você quiser pegar para...

**On-screen content:** ![Slide: Perceptron Simples - Proposto por Frank Rosenblatt (1958); Forma mais simples de uma rede neural, possui uma única camada; Resolvem apenas problemas linearmente separáveis; Utilizada, em geral, para classificação de padrões. Diagrama de um perceptron simples com entradas (x1, x2, ..., xn), pesos (w1, w2, ..., wn), bias (w0), somador, função de ativação

## [09:55] Data Science elements and coding setup

**Spoken content:**
- [09:56] Oh, eu quero saber se Data Science é de elementos, é bem mais difícil.
- [10:04] Então, galera, a gente vai começar aqui a parte do código.
- [10:07] Tudo...
- [10:08] Você está legal aí?
- [10:09] Está dando para ver?
- [10:10] De boa a tela aqui?
- [10:13] Cara, a resolução está excelente.
- [10:14] Pode seguir, velho.
- [10:15] Está excelente?
- [10:16] Beleza, então.
- [10:16] Mas eu estou te vendo no...
- [10:18] Eu estou vendo o browser de novo agora.
- [10:21] E agora?
- [10:30] Você está vendo o VS Code?
- [10:31] Isso.
- [10:32] Beleza.
- [10:33] Então, pessoal, a gente...

**On-screen content:**
![Slide: Referências e dicas de leitura](video-frame://50@09:55)
![VS Code with file explorer](video-frame://50@10:30)

## [10:35] Dataset overview and preparation

**Spoken content:**
- [10:35] A primeira coisa que a gente tem que fazer é baixar um Data Set.
- [10:38] O Data Set que eu peguei foi esse aqui.
- [10:41] Binary, não sei o quê, Data Set.
- [10:44] Ele tem para mim...
- [10:46] Ele disponibiliza para mim dois Data Set diferentes.
- [10:48] O cara fez aqui só para criar um thumbnail aqui, para mostrar como é que usava o Matplot.
- [10:54] Mas ele é bem tranquilo.
- [10:56] Ele tem 100 posições.
- [10:57] E ele é bem linearmente separável.
- [10:59] Vocês estão vendo?
- [11:00] Então, assim, vai ser bem tranquilo implementar com ele.
- [11:02] E o outro aqui, que a gente vai ver, ele já não é.
- [11:06] Então, dá até para...
- [11:08] Caso vocês queiram usar aí depois para poder brincar, ver os resultados que vão dar com esse que já não é linearmente separado.
- [11:16] Então, aqui eu já joguei aqui para a pasta raiz aqui o nosso Data.
- [11:20] Então, vamos começar a codar agora.
- [11:22] Deixa eu colocar o nome aqui.

**On-screen content:**
![VS Code file explorer showing binary-classification-dataset-master, thumbnail.png, data1.csv, data.csv](video-frame://50@10:42)
![VS Code file explorer showing data.csv moved to root](video-frame://50@11:19)

## [11:22] Initial code setup and CSV reading

**Spoken content:**
- [11:27] É agora que os filhos choram e a mãe não vê.
- [11:30] É.
- [11:30] A gente vai colocar aqui, melhorar o padrão.
- [11:33] Vamos para o pai.
- [11:34] Beleza.
- [11:37] Eu não vi a live de...
- [11:39] de arquivos.
- [11:42] Então, me perdoa se eu estiver fazendo coisa a mais aqui.
- [11:45] Fica tranquilo.
- [11:47] Fica tranquilo.
- [11:48] Beleza.
- [11:48] Aqui a gente vai importar um CSV, que é o nosso tipo de arquivo.
- [11:52] E vamos importar já de cara a biblioteca randômica.
- [11:55] Porque a gente vai precisar gerar número aleatório a torta direito.
- [11:58] Vocês vão ver.
- [11:59] Então, primeiro a gente vai criar aqui uma...
- [12:01] Datacete aqui.
- [12:04] Uma lista aqui.
- [12:07] E vamos fazer a inclusão do arquivo aqui.
- [12:11] OpenAta.csv.
- [12:18] Só para você aumentar um pouquinho a fonte.
- [12:31] A fonte?
- [12:32] Beleza.
- [12:33] Agora.
- [12:34] Vamos ver se melhorou.
- [12:36] Como é, galera?
- [12:39] Hoje esse computador está me trolando, só pode.
- [12:44] Fica tranquilo, velho.
- [12:45] Toda vez.
- [12:46] Cara, está ótimo agora.
- [12:47] Beleza.
- [12:48] Então, vamos lá.
- [12:51] A gente vai passar o file aqui que a gente criou, né?
- [12:54] E vamos fazer a delimitação.
- [12:56] A delimitação dele aqui.
- [12:57] São lá as vírgulas, né?
- [13:02] Que já...
- [13:03] CSV, pelo menos, ele está bonitinho.
- [13:04] Então, aqui.
- [13:06] For.
- [13:06] LiningData.
- [13:09] A gente vai fazer o seguinte agora.
- [13:10] A gente vai...
- [13:12] Como ele é uma string,
- [13:14] se a gente passar somente os valores de cara,
- [13:17] na hora de a gente fazer as contas, vai dar pau.
- [13:19] Ele vai falar que não pode,
- [13:21] porque é um string, não sei o quê.
- [13:24] Então, a gente vai precisar de fazer o...
- [13:26] De transformar todas as linhas num float.
- [13:30] Então, eu vou pegar aqui a própria linha, vai receber o float dela mesma.
- [13:36] O float da própria linha.
- [13:38] Float, elemento, desculpa.
- [13:46] Elemento.
- [13:52] O que eu estou fazendo?
- [13:58] Eu estou pegando essa linha,
- [13:59] transformando ela toda em float.
- [14:01] Eu vou pegar o meu dataset aqui.
- [14:03] Vou dar um append-leito.
- [14:05] Estou jogando aqui minha linha
- [14:08] para o dataset.
- [14:11] Beleza.
- [14:12] Aqui, eu já fiz a leitura do arquivo.
- [14:14] Vamos codar aqui para ver se está de boa.
- [14:17] Beleza.
- [14:20] Codou.
- [14:21] Bacaninha.
- [14:22] Então, aqui a gente já pegou
- [14:24] e já tem o dataset já gravado
- [14:27] meio que na memória.
- [14:27] Então, vou mandar agora
- [14:29] fazer o seguinte.
- [14:31] Quando a gente vai treinar uma rede,
- [14:33] a gente, em geral,
- [14:35] tem meio que um padrão
- [14:37] que existe,
- [14:38] que é você utilizar
- [14:40] 80% dos seus dados
- [14:42] para treinar
- [14:43] e os outros 20%
- [14:45] é para fazer teste.
- [14:46] Porque, senão, não teria sentido
- [14:49] você pegar
- [14:49] o mesmo...
- [14:50] a mesma quantidade de elementos
- [14:52] treinar
- [14:52] e como é que você testaria.
- [14:54] Então, você tem que fazer isso de forma
- [14:56] até melhor, seria aleatória.
- [14:58] Então, o que a gente vai fazer?
- [15:00] A gente vai criar uns métodos aqui
- [15:02] que vai fazer isso.
- [15:04] A gente vai chamar ele de
- [15:06] treino.
- [15:08] Se vocês forem usar
- [15:10] site de LAN,
- [15:11] vocês vão ver que tem esses nomes mesmo.
- [15:12] Treino, teste,
- [15:14] split.
- [15:15] Por quê?
- [15:16] Agora eu vou separar
- [15:17] cada um dos meus elementos
- [15:21] em elementos de teste
- [15:22] e elementos de treino.
- [15:24] Por quê?
- [15:25] Porque quando eu chegar lá no final,
- [15:26] eu já sei quais os valores
- [15:28] que meu elemento de teste tem.
- [15:31] Então, eu vou comparar
- [15:32] com aquilo que ele predizeu
- [15:33] que é aquilo que a minha rede
- [15:35] treinou e respondeu.
- [15:37] Para ver se ela está legal,
- [15:38] se ela está muito longe
- [15:40] da realidade e tudo mais.
- [15:41] E aqui,
- [15:42] geralmente,
- [15:43] eles têm aqui
- [15:44] porcentagem.
- [15:45] Eles colocam lá...
- [15:49] Se eu não me engano,
- [15:50] no site kit
- [15:50] é a porcentagem de teste.
- [15:52] Você vai colocar sempre
- [15:53] a porcentagem
- [15:53] que você quer
- [15:54] para...
- [16:01] para receber
- [16:03] a porcentagem.
- [16:06] Vou colocar aqui
- [16:09] o tamanho da minha...
- [16:11] meu dataset.
- [16:12] Datasete.
- [16:15] E por cento.
- [16:17] Beleza.
- [16:18] Peguei.
- [16:19] Já está aqui
- [16:20] o quanto eu vou ter
- [16:24] de porcentagem aqui
- [16:25] para poder
- [16:26] gerar
- [16:27] o meu caso treino, né?
- [16:31] Meu data treino aqui,
- [16:32] eu vou fazer o seguinte com ele.
- [16:34] Ele vai receber para mim
- [16:36] um handle
- [16:37] .sample
- [16:39] porque ele vai gerar
- [16:41] aleatoriamente para mim
- [16:43] elementos
- [16:45] do meu dataset
- [16:46] com a quantidade que eu quero.
- [16:49] Então, eu vou colocar aqui
- [16:50] o percent.
- [16:51] Então, ele vai gerar para mim
- [16:52] 80 elementos aleatórios
- [16:54] dentro do meu dataset.
- [16:56] E agora, eu tenho que pegar aqui
- [16:59] o meu datatest
- [16:59] que vai fazer o quê?
- [17:01] ele vai receber
- [17:02] o contrário.
- [17:04] Então, eu vou colocar aqui,
- [17:05] data for data.
- [17:06] Vou fazer uma...
- [17:08] Vou iterar sobre ele
- [17:09] em dataset.
- [17:10] Então, estou iterando
- [17:12] dentro do dataset.
- [17:13] Se data
- [17:14] tiver
- [17:19] um
- [17:19] data treino.
- [17:21] Ou seja,
- [17:22] ele vai receber
- [17:23] os 80 elementos
- [17:24] que
- [17:24] eu...
- [17:25] para gerar minha rede,
- [17:26] meu teste...
- [17:27] meu dataset de treino.
- [17:29] e aqui ele vai gerar
- [17:31] o que sobra,
- [17:31] que no caso são 20,
- [17:32] porque a gente tem...
- [17:33] Esse dataset,
- [17:34] ele tem 100 linhas, né?
- [17:36] 100 linhas.
- [17:37] Então, aqui, beleza.
- [17:39] Aqui eu já separei
- [17:40] naquilo que eu quero.
- [17:40] O que é teste
- [17:41] e o que é treino.
- [17:42] Só que eu preciso agora
- [17:43] de montar.
- [17:44] Então, eu vou criar aqui
- [17:45] um método dentro desse outro
- [17:47] que é o meu método montar.
- [17:49] Eu vou mandar aqui
- [17:51] o meu dataset de novo.
- [17:52] O dataset aí
- [17:53] vai ser o de treino
- [17:54] ou de teste.
- [17:56] Vou colocar aqui duas...
- [17:57] Vou criar duas listas aqui.
- [17:58] E vou iterar
- [18:05] sobre o meu dataset.
- [18:06] For data
- [18:07] em...
- [18:08] Isso.
- [18:11] Vai receber
- [18:12] data.
- [18:16] Só que da posição
- [18:17] 1 até 3,
- [18:18] porque o meu...
- [18:20] Deixa eu mostrar para vocês
- [18:22] o dataset aqui,
- [18:23] que aí vai ficar mais claro
- [18:24] para eu entender.
- [18:26] posição 1, 0.
- [18:28] O dataset...
- [18:30] Deixa eu ver.
- [18:30] Ele está aqui, ó.
- [18:32] Aqui estão os atributos alvo,
- [18:34] que são 1 e menos 1,
- [18:36] no caso.
- [18:37] E aqui estão as minhas variáveis,
- [18:38] minhas variáveis de atributo aqui, ó.
- [18:41] Então, eu estou pegando
- [18:42] a posição 1 até a 2
- [18:44] para ser o meu treino,
- [18:46] meu dataset de treino.
- [18:47] E 1 até 0
- [18:49] para ser o meu dataset
- [18:51] de resultados,
- [18:52] vamos dizer assim.
- [18:53] e aqui
- [18:54] o meu dataset
- [18:56] que eu vou colocar
- [18:56] para treinar.
- [18:57] Então, estou recebendo aqui
- [18:58] ou retornar.
- [19:00] Retornar
- [19:01] o x
- [19:03] e o y.
- [19:03] Beleza.
- [19:06] Agora...
- [19:07] Pode dar exemplo
- [19:08] para a gente
- [19:08] do que é, sei lá,
- [19:09] do que seria uma variável
- [19:11] considerada
- [19:11] nesse menos 1
- [19:12] e 1,
- [19:13] por exemplo?
- [19:14] Ah, sim.
- [19:15] Igual, no caso,
- [19:16] nesse caso,
- [19:17] essas duas variáveis aqui
- [19:18] são as variáveis
- [19:20] atributo.
- [19:20] Ou seja,
- [19:21] elas têm
- [19:24] alguma fórmula
- [19:26] entre essas duas variáveis
- [19:29] que está me gerando
- [19:30] esse resultado aqui.
- [19:31] Elas pertencem
- [19:32] a essa classe.
- [19:32] Entendeu?
- [19:33] Então, assim,
- [19:35] alguma fórmula aqui
- [19:37] com essas duas variáveis aqui
- [19:41] que são as minhas variáveis
- [19:42] atributo
- [19:42] está me gerando
- [19:43] esse resultado.
- [19:44] Isso aqui poderia ser,
- [19:46] sei lá,
- [19:46] qualidade do...
- [19:48] igual tem um dataset de vinho.
## [19:50] Dataset variability and attributes

**Spoken content:**
- [19:50] A qualidade de vinho
- [19:51] pode ser, assim,
- [19:52] teor alcoólico
- [19:55] mais acidez.
- [19:56] Aí ele é da classe 1.
- [19:58] Entendeu?
- [19:59] Aí tem outro aqui,
- [20:00] ó, não.
- [20:01] O teor alcoólico aqui
- [20:03] e acidez
- [20:04] é de outra classe.
- [20:05] Então,
- [20:06] isso vai variar
- [20:07] do que é seu dataset.
- [20:08] Né?
- [20:11] Depois eu...
- [20:13] O site da UCI,
- [20:15] da...
- [20:16] Kaggle,
- [20:16] que eles têm
- [20:17] alguns datasets
- [20:18] que eles são bem explicados.
- [20:19] Nesse aqui,
- [20:20] o cara só gerou os valores
- [20:23] e criou um dataset.
- [20:24] Mas,
- [20:25] pode ser qualquer coisa
- [20:27] essas variáveis aqui.
- [20:28] Pode ser qualquer coisa.
- [20:29] Isso aí vai depender realmente
- [20:32] do que que é seu dataset.
- [20:33] Deu pra ficar claro?
- [20:36] Sim.
- [20:36] Cara, deu.
- [20:37] Ficou ótimo, cara.
- [20:38] Elas têm correlação
- [20:40] com a classe.
- [20:41] As duas variáveis formadas.
- [20:43] As duas variáveis...
- [20:44] Por isso que são chamadas
- [20:45] de atributos.
- [20:46] Porque elas têm...
- [20:47] Elas são as caixas de atributos
- [20:48] para a variável alvo.
- [20:49] Pronto.
- [20:50] Aí é uma coisa
- [20:51] que elas estão fazendo.

**On-screen content:**
The screen shows a code editor with a file named `neural_padrao.csv` open. The file displays numerical data in two columns, resembling a dataset.
![Code editor showing neural_padrao.csv data](video-frame://50@19:50)

## [20:52] Dataset splitting function

**Spoken content:**
- [20:52] Então, aqui,
- [20:53] eu vou criar aqui
- [20:55] meu Xtrain e Ytrain
- [20:57] que vai receber
- [20:59] para mim
- [20:59] montar aqui
- [21:00] de datatrain
- [21:03] e Xtrain
- [21:08] e Xtrain
- [21:08] Eu estou fazendo
- [21:11] dessa fórmula
- [21:11] eu poderia até
- [21:12] já passar direto
- [21:13] mas é porque
- [21:14] se vocês forem
- [21:15] usar a site
- [21:16] de learning
- [21:17] ela já retorna
- [21:18] os quatro elementos
- [21:19] para mim, entendeu?
- [21:20] Quando você sai
- [21:22] do método lá
- [21:23] ele já retorna
- [21:24] para mim
- [21:24] os quatro elementos
- [21:26] já
- [21:26] que você
- [21:27] que você quis.

**On-screen content:**
The code editor displays a Python script. A function `montar` is defined, which takes a `dataset` as input and returns `x` and `y`.
```python
def montar(dataset):
    x = []
    y = []
    for data in dataset:
        x.append(data[:3])
        y.append(data[3])
    return x, y
```
Below this, the speaker is writing the lines to assign the split data:
```python
x_train, y_train = montar(data_treino)
x_test, y_test = montar(data_teste)
```
![Code editor showing montar function and dataset splitting](video-frame://50@20:52)

## [21:29] Returning split data and variable assignment

**Spoken content:**
- [21:29] Então, aqui
- [21:30] eu estou retornando
- [21:31] estou pegando aqui
- [21:33] e já vou retornar
- [21:34] para
- [21:34] no final
- [21:36] do meu método aqui
- [21:37] todos os quatro
- [21:41] Xtrain
- [21:42] Contrain
- [21:45] Beleza.
- [21:54] Vou pegar aqui
- [21:56] criar as variáveis
- [21:58] aqui fora
- [21:58] já para receber
- [21:59] Xtrain
- [22:00] Y
- [22:01] A gente está colocando
- [22:21] ela aqui
- [22:21] com 80%
- [22:22] na variável
- [22:25] de Xtrain
- [22:26] Beleza.

**On-screen content:**
The code editor shows the `montar` function and the subsequent assignment of the split data.
```python
def montar(dataset):
    x = []
    y = []
    for data in dataset:
        x.append(data[:3])
        y.append(data[3])
    return x, y

x_train, y_train = montar(data_treino)
x_test, y_test = montar(data_teste)

return x_train, y_train, x_test, y_test
```
The speaker then adds the line to call the `treino_teste_split` function:
```python
x_treino, y_treino, x_teste, y_teste = treino_teste_split(dataset, 80)
```
![Code editor showing return statement and variable assignment](video-frame://50@21:29)

## [22:26] Running the code and fixing indentation

**Spoken content:**
- [22:27] Vamos ver
- [22:27] se está rodando
- [22:28] De novo
- [22:39] Beleza
- [22:53] Rodou bacaninha
- [22:54] Então já criei aqui
- [22:57] já estou com
- [22:58] meu dataset pronto
- [22:59] e já estou com ele
- [23:00] dividido
- [23:01] naquilo que é treino
- [23:02] e naquilo que é teste
- [23:03] Agora a gente
- [23:04] a gente vai fazer
- [23:05] de novo aqui
- [23:07] a nossa apresentação
- [23:13] que aí vocês vão ver
- [23:14] a parte mesmo
- [23:15] de treinamento
- [23:16] Vou abrir
- [23:17] Agora nós vamos pegar
- [23:28] essa parte aqui
- [23:29] de treinamento
- [23:31] e começar a jogar
- [23:34] Em geral
- [23:36] nas bibliotecas
- [23:37] que a gente usa
- [23:37] para
- [23:38] aprendizagem de máquina
- [23:40] existe o método
- [23:41] Fit
- [23:42] que é o método
- [23:42] de treinamento
- [23:43] em si
- [23:44] e depois tem o método
- [23:45] predict
- [23:46] que é o que pega
- [23:47] e pega os valores
- [23:48] que você gerou
- [23:49] e vê
- [23:51] e treina
- [23:52] e dá o resultado
- [23:53] do treinamento
- [23:54] Aí que você vai avaliar
- [23:56] se a sua rede
- [23:56] está boa
- [23:58] ou não
- [23:58] Então a gente vai pegar
- [24:00] esse algoritmo
- [24:01] de aprendizado
- [24:02] agora
- [24:03] e vai
- [24:04] jogar
- [24:05] aqui dentro
- [24:06] da nossa
- [24:07] do nosso
- [24:08] nosso algoritmo
- [24:09] aqui
- [24:10] Então um pouquinho
- [24:11] Beleza
- [24:12] Então vamos lá
- [24:13] F
- [24:14] Eu vou chamar ele
- [24:16] de Perceptron
- [24:18] Fit
- [24:20] A Kitland
- [24:22] se eu não me engano
- [24:22] ela tem esse mesmo nome
- [24:23] Perceptron Fit
- [24:24] Ele vai receber para mim
- [24:25] o X
- [24:26] que seria
- [24:27] as minhas entradas
- [24:29] e o D
- [24:31] que são as saídas
- [24:32] Se a gente ver
- [24:34] a notação aqui
- [24:35] desse modelo
- [24:37] algoritmo
- [24:39] deixa eu só
- [24:40] mudar aqui
- [24:40] desse algoritmo
- [24:46] vocês estão vendo aqui
- [24:47] que ela
- [24:47] o T
- [24:48] W
- [24:49] X
- [24:49] que são as entradas
- [24:50] o W
- [24:51] que são os pesos
- [24:52] o Eta
- [24:53] aqui
- [24:54] que é a nossa
- [24:54] variável de aprendizagem
- [24:56] e o D
- [24:57] que é a saída
- [24:57] Então a gente vai
- [24:58] usar essa mesma
- [25:00] anotação
- [25:00] para ficar mais
- [25:01] mais legal
- [25:02] assim de entender
- [25:03] Porque até
- [25:05] acho que disponibiliza
- [25:07] a apresentação
- [25:08] aí fica legal
- [25:09] para
- [25:09] para poder
- [25:10] se assinar
- [25:11] assim
- [25:12] assim
- [25:12] Beleza
- [25:13] Põe lá
- [25:15] e vamos
- [25:15] colocar aqui
- [25:16] época
- [25:17] recebe zero
- [25:18] O que é a época?
- [25:20] A época
- [25:20] é como se fosse
- [25:22] o limite
- [25:23] de convergência
- [25:25] não de convergência
- [25:26] mas
- [25:26] vamos supor que
- [25:27] sua rede
- [25:27] está demorando
- [25:29] muito a convergir
- [25:30] aí
- [25:31] você
- [25:31] deixa rodando
- [25:33] aí ela demora
- [25:34] mil
- [25:35] mais de mil
- [25:36] interações
- [25:37] e não converge
- [25:38] então
- [25:39] essa época
- [25:40] ela usa assim
- [25:40] para limitar mesmo
- [25:41] fala assim
- [25:42] não
- [25:42] quando chegar a mil
- [25:43] para
- [25:43] porque provavelmente
- [25:45] a rede
- [25:45] tem algum problema
- [25:46] igual essa rede
- [25:47] mesmo
- [25:48] que está
- [25:48] bem separada
- [25:49] linearmente
- [25:51] separada
- [25:51] se ela demorar
- [25:53] mil
- [25:54] é porque
- [25:54] tem realmente
- [25:55] alguma coisa
- [25:56] errada
- [25:56] eu tenho que
- [25:57] mudar
- [25:58] e tal
- [25:58] alguma coisa
- [26:00] no meu algoritmo
- [26:02] aqui o W
- [26:03] a gente vai
- [26:03] receber o W
- [26:05] lá com
- [26:06] nove
- [26:07] com três
- [26:09] entradas
- [26:10] então são
- [26:11] três pesos
- [26:13] a nossa taxa
- [26:18] de limiar
- [26:18] lá
- [26:18] e as duas
- [26:20] entradas
- [26:21] tanto
- [26:21] x1
- [26:21] quanto x2
- [26:22] que são as
- [26:23] entradas
- [26:24] normais
- [26:24] do
- [26:25] do
- [26:26] dataset
- [26:26] então a gente
- [26:27] vai receber
- [26:28] handle
- [26:29] para gerar
- [26:31] um número
- [26:31] aleatório
- [26:32] entre 0 e 1
- [26:33] três números
- [26:38] a gente vai
- [26:39] printar o W
- [26:40] aqui
- [26:40] só para no final
- [26:41] lá
- [26:42] ficar legal
- [26:43] vocês verem
- [26:43] o W
- [26:44] que era
- [26:45] e
- [26:45] depois do treinamento
- [26:47] quanto que ele ficou
- [26:47] mas beleza
- [26:49] aqui a gente tem
- [26:51] está iterando aqui
- [26:52] está criando
- [26:53] três W
- [26:53] aqui
- [26:54] e agora
- [26:55] a gente vai
- [27:01] vamos embora
- [27:02] erro
- [27:03] recebe
- [27:04] falso
- [27:05] eu já começo
- [27:06] o erro
- [27:06] como se a minha rede
- [27:08] não tivesse erro
- [27:09] nenhum
- [27:09] deixa eu
- [27:10] dividir a tela
- [27:12] que eu acho
- [27:12] que vai ficar melhor
- [27:13] um instante
- [27:17] está dando
- [27:30] para ver as duas telas
- [27:31] Eduard
- [27:35] eu só estou vendo
- [27:36] um pedaço
- [27:37] do editor
- [27:37] eu não estou vendo
- [27:38] o outro pedaço
- [27:39] não está vendo
- [27:40] deixa eu ver
- [27:41] acho que vai ficar
- [27:48] melhor
- [27:48] agora
- [27:49] e agora
- [27:54] agora está
- [27:55] dando para ver
- [27:56] agora está tranquilo
- [27:57] beleza
- [27:57] então deixa eu só
- [27:58] aumentar aqui
- [27:59] o slide
- [28:02] toma calma gente
- [28:09] deixa eu ver
- [28:39] vamos
- [28:43] então
- [28:59] aqui
- [29:00] o erro
- [29:02] sempre inicializa
- [29:03] em falso
- [29:04] e a gente vai
- [29:05] começar a fazer
- [29:06] as iterações
- [29:06] que a gente precisa
- [29:07] e eu recebo
- [29:14] falso
- [29:14] e
- [29:16] é para
- [29:17] criar
- [29:18] a minha
- [29:20] fazer a minha
- [29:23] interação
- [29:23] eu estou pegando
- [29:30] o tamanho
- [29:30] estou pegando
- [29:31] o x completo
- [29:32] e vou iterar
- [29:33] sobre ele
- [29:33] vai fazer o seguinte
- [29:35] o u aqui
- [29:36] vai receber
- [29:37] o somatório
- [29:38] do meu w0
- [29:41] que seria
- [29:41] o meu bias
- [29:42] vezes menos 1

**On-screen content:**
The terminal shows an `IndentationError: unexpected indent` message.
```bash
$ python neural_padrao.py
  File "neural_padrao.py", line 29
    return x_train, y_train, x_test, y_test
IndentationError: unexpected indent
```
The speaker then corrects the indentation in the `treino_teste_split` function.
```python
def treino_teste_split(dataset, porcentagem):
    # ... (previous code)
    return x_treino, y_treino, x_teste, y_teste
```
After correction, the terminal shows no errors.
![Terminal showing IndentationError and subsequent successful execution](video-frame://50@22

## [29:45] Defining the `perceptron_fit` function

**Spoken content:**
- [29:48] aí o w2
- [29:52] o w1
- [29:53] no caso
- [29:54] vai receber
- [29:56] x
- [29:58] 0
- [30:01] 0
- [30:02] 0
- [30:03] posição
- [30:04] 0
- [30:05] opa desculpa
- [30:05] x i
- [30:06] posição 0
- [30:08] que é o primeiro
- [30:08] x
- [30:10] e aqui o meu w2
- [30:12] posição 2
- [30:15] vai receber
- [30:16] o meu próximo x
- [30:17] que é o x
- [30:18] e
- [30:19] a posição 1
- [30:23] beleza
- [30:25] isso aqui
- [30:26] já é a minha
- [30:26] função
- [30:27] já é o meu u
- [30:28] que eu vou criar
- [30:29] que é no caso
- [30:30] esse u aqui
- [30:32] tranquilo

**On-screen content:**
```python
def perceptron_fit(x, d):
    epoca = 0
    w = [random.random() for i in range(3)]
    print(w)
    while True:
        erro = False
        for i in range(len(x)):
            u = sum(w[0] * -1, w[1] * x[i][0], w[2] * x[i][1])
```

## [30:35] Creating the `sinal` function

**Spoken content:**
- [30:35] agora a gente vai criar
- [30:37] uma função
- [30:38] sinal
- [30:39] porque ela
- [30:40] vai receber
- [30:42] para mim
- [30:44] criar aqui fora
- [30:45] sinal
- [30:48] u
- [30:50] passar aqui
- [30:51] sinal de 1
- [30:52] o que ela vai retornar
- [30:53] para mim
- [30:53] retorne
- [30:54] 1
- [30:55] si
- [30:56] u
- [30:58] maior ou igual a 0
- [31:02] else
- [31:04] menos 1
- [31:06] pode ser 1 e 0
- [31:09] mas é porque
- [31:10] aqui foi
- [31:12] o dataset
- [31:12] é como
- [31:13] 1 e menos 1
- [31:14] então não vai fazer
- [31:15] diferença não
- [31:17] e aí eu vou colocar aqui

**On-screen content:**
```python
def sinal(u):
    return 1 if u >= 0 else -1
```

## [31:17] Implementing the `sinal` function in `perceptron_fit`

**Spoken content:**
- [31:18] o y
- [31:19] daquela
- [31:20] daquela linha
- [31:21] vamos dizer assim
- [31:22] para receber
- [31:23] sinal
- [31:24] u
- [31:27] e agora

**On-screen content:**
```python
def perceptron_fit(x, d):
    epoca = 0
    w = [random.random() for i in range(3)]
    print(w)
    while True:
        erro = False
        for i in range(len(x)):
            u = sum(w[0] * -1, w[1] * x[i][0], w[2] * x[i][1])
            y = sinal(u)
```

## [31:29] Adjusting weights based on error

**Spoken content:**
- [31:30] se
- [31:31] se o meu y
- [31:33] for diferente
- [31:35] diferente do meu d
- [31:39] o meu d na posição i
- [31:41] ou seja
- [31:42] se for diferente
- [31:43] daquele
- [31:44] do resultado
- [31:45] se aqui
- [31:46] vamos supor
- [31:46] se meu i
- [31:48] se o somatório
- [31:49] desse aqui
- [31:49] for diferente
- [31:50] de 1
- [31:52] ou de menos 1
- [31:53] ele vai ter que
- [31:55] punir
- [31:56] essa
- [31:56] esse treinamento
- [31:59] essa linha
- [32:01] vamos dizer assim
- [32:02] então a gente vai ter que criar
- [32:04] uma
- [32:05] negócio de ajuste
- [32:06] que a gente vai punir
- [32:07] o nosso w
- [32:07] o nosso p
- [32:08] então vamos criar

**On-screen content:**
```python
def perceptron_fit(x, d):
    epoca = 0
    w = [random.random() for i in range(3)]
    print(w)
    while True:
        erro = False
        for i in range(len(x)):
            u = sum(w[0] * -1, w[1] * x[i][0], w[2] * x[i][1])
            y = sinal(u)
            if y != d[i]:
                # Adjustment logic will go here
```

## [32:11] Defining the `ajuste` function

**Spoken content:**
- [32:12] também uma outra
- [32:13] aqui fora
- [32:14] que a gente vai chamar
- [32:15] de ajuste
- [32:16] essa de ajuste
- [32:19] ela vai receber
- [32:19] para a gente
- [32:20] o nosso w
- [32:20] que é
- [32:22] o peso
- [32:23] a nossa saída
- [32:24] o nosso x

**On-screen content:**
```python
def ajuste(w, x, d, y, taxa_aprendiz):
    return w + taxa_aprendiz * (d - y) * x
```

## [32:25] Applying the `ajuste` function in `perceptron_fit`

**Spoken content:**
- [32:26] a nossa linha
- [32:27] vamos dizer
- [32:27] a nossa saída
- [32:29] original
- [32:30] e a nossa saída
- [32:31] treinada
- [32:34] e aí vou retornar aqui
- [32:36] para
- [32:36] vou retornar
- [32:37] como resultado
- [32:39] o w
- [32:43] mais
- [32:44] a
- [32:45] aprendizagem
- [32:46] vou colocar aqui
- [32:48] taxa
- [32:50] aprendiz
- [32:53] vezes o nosso
- [33:06] b
- [33:07] menos o y
- [33:08] vezes o x
- [33:12] então
- [33:14] essa aqui
- [33:15] é a nossa
- [33:16] é a nossa taxa
- [33:19] aqui de
- [33:19] de ajuste
- [33:21] a punição
- [33:23] que esse w
- [33:24] esse peso
- [33:24] tem que sofrer
- [33:25] então a gente vai colocar aqui
- [33:26] ajuste
- [33:27] e vamos
- [33:29] jogar
- [33:30] para
- [33:30] para
- [33:31] para ele
- [33:33] o primeiro
- [33:35] do bias
- [33:35] o valor
- [33:39] de x
- [33:40] a saída
- [33:41] que vai ser
- [33:42] a saída
- [33:43] correspondente
- [33:44] a linha lá
- [33:45] e
- [33:46] o nosso y
- [33:48] que é o valor
- [33:50] que foi
- [33:51] que foi treinado
- [33:52] o resultado
- [33:53] do treino
- [33:53] então vamos fazer isso aqui
- [33:55] três vezes
- [33:56] uma para cada
- [33:57] uma para cada linha
- [33:59] independente de
- [34:00] assim
- [34:00] é impossível a gente saber
- [34:02] qual foi
- [34:03] o valor
- [34:04] que foi errado
- [34:04] então no caso
- [34:05] o w
- [34:06] aqui ele vai ter que
- [34:07] vai ser refletido
- [34:09] em todos
- [34:10] posição 0
- [34:15] b e o y
- [34:17] e o y
- [34:18] a gente vai mudar aqui
- [34:20] x
- [34:22] e
- [34:23] posição
- [34:28] posição 1
- [34:34] beleza
- [34:35] w2
- [34:37] beleza
- [34:38] w2
- [34:39] w1
- [34:39] w2
- [34:40] e nisso

**On-screen content:**
```python
def perceptron_fit(x, d):
    epoca = 0
    w = [random.random() for i in range(3)]
    print(w)
    while True:
        erro = False
        for i in range(len(x)):
            u = sum(w[0] * -1, w[1] * x[i][0], w[2] * x[i][1])
            y = sinal(u)
            if y != d[i]:
                w[0] = ajuste(w[0], -1, d[i], y, taxa_aprendiz)
                w[1] = ajuste(w[1], x[i][0], d[i], y, taxa_aprendiz)
                w[2] = ajuste(w[2], x[i][1], d[i], y, taxa_aprendiz)
                erro = True
```

## [34:40] Epoch tracking and loop termination

**Spoken content:**
- [34:40] o erro recebe
- [34:41] verdade
- [34:42] ou seja
- [34:44] o erro recebe
- [34:45] true
- [34:45] ou seja
- [34:45] significa que a rede
- [34:47] está
- [34:47] está a falha
- [34:48] se ele
- [34:49] passasse aqui
- [34:50] direto
- [34:51] com o erro
- [34:52] falso aqui
- [34:53] e não
- [34:54] precisasse de punir
- [34:55] ou seja
- [34:55] a rede
- [34:56] teria
- [34:56] 100% boa
- [34:57] mas nesse caso
- [34:59] aqui
- [34:59] não está
- [35:00] então ele vai
- [35:01] vir para cá
- [35:02] o erro vai receber
- [35:04] o true
- [35:04] e o época
- [35:05] aqui vai receber
- [35:06] o época
- [35:06] mais 1
- [35:06] ou seja
- [35:07] você vai começar
- [35:07] a contar as épocas
- [35:10] e época
- [35:13] mais igual
- [35:18] 1
- [35:19] for
- [35:25] agora a gente vai
- [35:27] colocar aqui
- [35:27] ó
- [35:28] if
- [35:28] erro
- [35:31] false
- [35:35] or
- [35:37] error
- [35:38] igual
- [35:41] new
- [35:43] break
- [35:44] ou seja
- [35:45] se ele
- [35:45] iterar
- [35:46] e não encontrar
- [35:47] nenhum erro
- [35:48] significa que
- [35:49] a rede
- [35:49] já foi treinada
- [35:50] já está testada
- [35:51] e acabou
- [35:52] a gente não precisa
- [35:53] fazer mais nada
- [35:54] print
- [35:55] print
- [35:55] aqui no final
- [35:56] print
- [35:59] aqui
- [36:00] nossa época
- [36:02] beleza

**On-screen content:**
```python
def perceptron_fit(x, d):
    epoca = 0
    w = [random.random() for i in range(3)]
    print(w)
    while True:
        erro = False
        for i in range(len(x)):
            u = sum(w[0] * -1, w[1] * x[i][0], w[2] * x[i][1])
            y = sinal(u)
            if y != d[i]:
                w[0] = ajuste(w[0], -1, d[i], y, taxa_aprendiz)
                w[1] = ajuste(w[1], x[i][0], d[i], y, taxa_aprendiz)
                w[2] = ajuste(w[2], x[i][1], d[i], y, taxa_aprendiz)
                erro = True
        if erro == False or epoca == 1000:
            break
        epoca += 1
    print(epoca)
    return w
```

## [36:06] Training the perceptron

**Spoken content:**
- [36:06] então essa aqui é a nossa função fit
- [36:08] é a função mesmo que vai
- [36:09] treinar o algoritmo
- [36:11] depois da gente treinar
- [36:12] a gente tem que passar
- [36:13] para a parte
- [36:14] de
- [36:14] de operação
- [36:17] que a gente vai validar
- [36:18] o nosso treino
- [36:18] vai validar a nossa rede
- [36:20] para saber se ela
- [36:21] está bacana ou não
- [36:22] então vamos embora
- [36:24] criar já o nosso
- [36:26] nosso
- [36:27] algoritmo
- [36:31] o fit
- [36:34] aqui
- [36:35] esqueci de colocar um detalhe
- [36:38] aqui
- [36:39] a gente vai sempre
- [36:40] retornar
- [36:41] o w
- [36:44] porque o w
- [36:46] ele vai
- [36:47] estar com os valores
- [36:48] alterados
- [36:48] depois a gente vai
- [36:49] depois a gente vai
- [36:51] colocar
- [36:51] aqui vocês vão
- [36:52] vocês vão ver
- [36:53] beleza
- [36:54] nosso w fit
- [36:57] vai receber
- [36:57] o perceptro
- [36:59] fit
- [37:01] o nosso
- [37:02] x de treino
- [37:04] e o y de treino
- [37:06] beleza
- [37:09] w
- [37:12] tranquilo
- [37:14] aqui
- [37:14] acabou a parte
- [37:16] de fit
- [37:16] agora a gente tem que fazer

**On-screen content:**
```python
w_fit = perceptron_fit(x_treino, y_treino)
print(w_fit)
```

## [37:16] Defining the `perceptron_predict` function

**Spoken content:**
- [37:17] a parte
- [37:18] de predict
- [37:19] é a parte
- [37:25] de validação
- [37:25] do nosso
- [37:26] elemento
- [37:28] teste
- [37:30] x
- [37:32] vamos receber a mesma coisa
- [37:33] x e y
- [37:34] só que agora
- [37:35] são os de teste
- [37:36] né
- [37:36] marçante
- [37:41] se tiver alguma
- [37:42] pergunta
- [37:42] pode falar
- [37:43] cara
- [37:45] tá tudo
- [37:46] tranquilo
- [37:46] aqui
- [37:46] o pessoal
- [37:47] deve estar
- [37:47] prestando
- [37:47] muita atenção
- [37:48] deve estar
- [37:49] funcionando
- [37:49] neurônios
- [37:50] aí
- [37:50] a rede
- [37:51] de oral
- [37:51] tá funcionando
- [37:52] espero que
- [37:54] funcione
- [37:54] vai tranquilo
- [37:56] aí
- [37:56] beleza
- [37:58] vou iterar
- [38:04] sobre
- [38:04] o dataset
- [38:06] e vou fazer
- [38:08] a mesma
- [38:08] coisa
- [38:09] predict
- [38:12] aqui
- [38:12] o somatório
- [38:16] no caso
- [38:21] aqui
- [38:21] eu não vou
- [38:21] passar o w
- [38:22] gente
- [38:22] eu vou
- [38:22] passar
- [38:22] o w
- [38:23] ajustado
- [38:25] vou colocar
- [38:26] aqui o w fit
- [38:27] seria isso
- [38:27] o nosso
- [38:28] vou colocar aqui
- [38:29] mais fácil
- [38:30] para ler
- [38:31] o nosso w
- [38:34] ajustado
- [38:35] que é o w
- [38:35] que a gente recebe
- [38:36] lá do fit
- [38:36] que são os pesos
- [38:37] o mais importante
- [38:38] aqui são os pesos
- [38:39] são eles que variam
- [38:41] o somatório
- [38:46] aqui
- [38:46] de
- [38:48] w
- [38:50] ajustado
- [38:50] o que a gente recebeu?
- [39:02] o que a gente recebeu?
- [39:04] o que a gente recebeu?
- [39:05] o que a gente recebeu?
- [39:06] o que a gente recebeu?
- [39:06] o que a gente recebeu?
- [39:07] o que a gente recebeu?
- [39:07] o que a gente recebeu?
- [39:10] o que a gente recebeu?
- [39:10] o que a gente recebeu?
- [39:11] o que a gente recebeu?
- [39:11] o que a gente recebeu?
- [39:12] o que a gente recebeu?
- [39:12] o que a gente recebeu?
- [39:13] o que a gente recebeu?
- [39:13] o que a gente recebeu?
- [39:13] o que a gente recebeu?
- [39:14] o que a gente recebeu?
- [39:14] e na posição 1
- [39:28] então esse aqui já é o nosso w
- [39:30] ajustado
- [39:32] ele vai efetuar o somatório
- [39:34] só colocar isso aqui
- [39:35] eu esqueci
- [39:35] ele vai reclamar
- [39:38] mas aqui ele vai

**On-screen content:**
```python
def perceptron_predict(x, y, w_ajustado):
    predict = []
    for i in range(len(x)):
        u = sum(w_ajustado[0] * -1, w_ajustado[1] * x[i][0], w_ajustado[2] * x[i][1])

## [39:40] Predicting and defining class

**Spoken content:**
- [39:40] receber esse valor de predict
- [39:43] a gente vai jogar
- [39:45] a gente vai fazer da mesma forma
- [39:46] a gente vai jogar na função do sinal
- [39:48] que ele vai falar
- [39:49] aí ele vai definir
- [39:51] se esse elemento
- [39:52] ele é
- [39:54] da classe A
- [39:55] ou se é da classe B
- [39:57] Felipe, o pessoal está falando aqui

**On-screen content:**
```python
        y_predict = sum([w_ajustado[0], w_ajustado[1] * x_teste[i][0], w_ajustado[2] * x_teste[i][1]])
        y_predict.append(sinal(predict))
```

## [40:05] Addressing a bug in `w_fit` and `taxa_aprendiz`

**Spoken content:**
- [40:06] que vai dar pau
- [40:07] quando você der aquele print do W
- [40:09] na linha 58
- [40:10] dá pau?
- [40:13] deixa eu ver por que
- [40:14] não era o WFIT?
- [40:15] ah, é o WFIT
- [40:16] foi mal
- [40:16] e na função de ajuste
- [40:19] também ficou uma variável solta
- [40:21] deixa eu ver
- [40:24] a taxa aprendiz
- [40:25] a gente vai colocar o valor
- [40:28] geralmente
- [40:29] os valores que a gente usa
- [40:31] são em geral
- [40:32] entre 0 e 1
- [40:33] então vocês vão ver
- [40:35] que variando esse valor aqui
- [40:36] de aprendizagem
- [40:37] o treinamento pode ser mais longo
- [40:41] ou não
- [40:42] aí vai
- [40:42] vai depender
- [40:44] desse valor
- [40:45] esse valor é muito importante
- [40:46] pra isso
- [40:47] então aqui o sinal

**On-screen content:**
```python
def perceptron_predict(x_teste, w_ajustado):
    y_predict = []
    for i in range(len(x_teste)):
        predict = sum([w_ajustado[0], w_ajustado[1] * x_teste[i][0], w_ajustado[2] * x_teste[i][1]])
        y_predict.append(sinal(predict))
    return y_predict

# ... (earlier code for perceptron_fit)
def ajuste(w, x, d, y):
    taxa_aprendiz = 0.01
    w = w + taxa_aprendiz * (d - y) * x
    return w
```

## [40:47] Completing `perceptron_predict`

**Spoken content:**
- [40:48] de predict
- [40:50] ele vai me retornar aqui
- [40:55] o valor de sinal
- [40:57] beleza
- [41:14] aí vou retornar
- [41:16] predict
- [41:22] né
- [41:23] predict
- [41:26] tranquilo

**On-screen content:**
```python
def perceptron_predict(x_teste, w_ajustado):
    y_predict = []
    for i in range(len(x_teste)):
        predict = sum([w_ajustado[0], w_ajustado[1] * x_teste[i][0], w_ajustado[2] * x_teste[i][1]])
        y_predict.append(sinal(predict))
    return y_predict
```

## [41:29] Validating predictions

**Spoken content:**
- [41:30] aqui
- [41:30] até agora
- [41:31] até aqui acabou
- [41:32] esse aqui
- [41:33] é o
- [41:33] principal
- [41:34] do nosso treinamento
- [41:36] então a gente vai agora
- [41:37] receber
- [41:38] criar uma variável
- [41:39] aqui
- [41:40] y validado
- [41:41] que vai receber pra gente
- [41:43] nosso perceptron
- [41:44] predict
- [41:45] ele variando
- [41:46] entre x-test
- [41:47] vírgula
- [41:50] o w-fit
- [41:51] gente
- [41:54] o validado
- [42:01] vamos dizer assim
- [42:02] que aí a gente vai ver
- [42:04] quais os valores
- [42:05] que ele
- [42:05] que ele validou
- [42:06] que ele acertou

**On-screen content:**
```python
y_validado = perceptron_predict(x_teste, w_fit)
print(y_validado)
```

## [42:07] Implementing an accuracy function

**Spoken content:**
- [42:07] e pra finalizar
- [42:08] é uma funçãozinha
- [42:10] que eu vou escrever
- [42:11] aqui
- [42:11] que ela é de acurácia
- [42:12] que ela vai ser bem básica
- [42:14] mesmo
- [42:14] é só pra gente ver
- [42:15] quanto
- [42:16] que a nossa
- [42:17] rede
- [42:18] foi
- [42:19] foi boa
- [42:20] assim
- [42:20] em preguizer
- [42:21] ela vai ser bem simples
- [42:23] a gente vai pegar aqui
- [42:24] só o y de treino
- [42:26] o y de teste
- [42:29] que a gente já sabe
- [42:30] os valores
- [42:31] e o nosso y
- [42:32] validado
- [42:33] que foi
- [42:35] o valor predict
- [42:36] e a gente vai colocar aqui
- [42:38] o total
- [42:39] recebe zero
- [42:40] vamos colocar
- [42:46] se o y de teste
- [42:48] lá
- [42:49] na posição i
- [42:50] vou fazer aqui
- [42:52] eu vou colocar
- [43:08] se o y de teste
- [43:09] na minha posição i
- [43:11] foi igual
- [43:12] ao meu y
- [43:13] validado
- [43:15] na posição i
- [43:16] e também
- [43:16] o total
- [43:17] só uma 1
- [43:24] não
- [43:28] não faz nada
- [43:30] beleza
- [43:34] aí

**On-screen content:**
```python
def acuracia(y_teste, y_validado):
    total = 0
    for i in range(len(y_teste)):
        if y_teste[i] == y_validado[i]:
            total += 1
        else:
            pass
    return total / len(y_treino) # Note: y_treino is used here, but y_teste is mentioned in speech
```

## [43:37] Calculating and printing accuracy

**Spoken content:**
- [43:37] a gente vai retornar
- [43:38] aqui
- [43:39] o número de total
- [43:43] que são todos
- [43:43] os meus acertos
- [43:44] dividido
- [43:45] pelo meu número
- [43:48] de
- [43:48] pelo
- [43:50] pelo total
- [43:52] de amostras
- [43:52] que eu tenho
- [43:53] e no caso
- [43:54] seria o meu y
- [43:55] de treino
- [43:56] de linhas
- [43:58] vamos dizer assim
- [43:59] isso aqui
- [44:01] ele vai me falar
- [44:02] vai me dar um número
- [44:02] entre 0 e 1
- [44:03] que vai refletir
- [44:04] qual que foi a minha
- [44:05] a minha
- [44:07] a acurácia
- [44:08] da minha rede
- [44:09] quantos por cento
- [44:10] ela acertou
- [44:10] daquilo que ela
- [44:11] propus
- [44:13] só para colocar
- [44:19] uns
- [44:19] nomes diferentes
- [44:20] aqui
- [44:20] para não ficar
- [44:21] o y
- [44:23] teste
- [44:25] o y
- [44:28] validado
- [44:29] beleza pessoal

**On-screen content:**
```python
def acuracia(y_teste, y_validado):
    total = 0
    for i in range(len(y_teste)):
        if y_teste[i] == y_validado[i]:
            total += 1
        else:
            pass
    return total / len(y_teste) # Corrected from y_treino to y_teste in code
print(acuracia(y_teste, y_validado))
```

## [44:35] Debugging initial run and accuracy calculation

**Spoken content:**
- [44:36] é isso aqui
- [44:37] a gente vai colocar
- [44:38] para rodar agora
- [44:38] Espero que tudo funcione
- [44:41] Quase
- [44:43] Só ver o que está falando aqui
- [44:45] 73X
- [44:47] Uma coisa aqui que está errada
- [44:49] X, X
- [44:50] X, X, X
- [44:55] Aqui pessoal, então aqui
- [45:04] Esse aqui foi o meu W inicial
- [45:06] Que a gente printou lá
- [45:07] Que é esse W que está dentro de fit
- [45:10] Esse primeiro W
- [45:13] Foram gerados esses valores aqui
- [45:15] Aí depois de 34 épocas
- [45:19] Que foram, que precisou
- [45:21] Para treinar essa rede
- [45:22] Eles ficaram com esses valores aqui
- [45:25] Aí a minha rede
- [45:29] Ela gerou
- [45:31] Essa saída
- [45:34] E ficou com zero aqui
- [45:37] Deixa eu ver o problema que gerou
- [45:39] Entendi
- [45:40] Deixa eu só ver um detalhe aqui
- [45:42] Mais um
- [45:45] Total
- [45:46] Galera
- [45:50] É alguma coisa que eu estou fazendo errado aqui na hora de rodar o código
- [46:13] Deixa eu ver
- [46:14] A hora de caçar os bugs
- [46:30] É
- [46:31] Ó galera
- [46:36] Assim
- [46:37] Está passando
- [46:38] Já tem 17 minutos
- [46:39] Eu
- [46:41] Eu acho que vai ficar
- [46:43] Você quer que continue procurando?
- [46:45] Não cara
- [46:47] Fica tranquilo
- [46:47] Ainda falta 15 minutos
- [46:48] Ainda falta 15 minutos
- [46:50] Então tá
- [46:51] Acho que ele tinha acabado o tempo já
- [46:53] Não
- [46:54] Está tranquilo
- [46:55] Quero saber qual foi o problema aqui
- [46:58] Cara
- [46:59] Isso sempre acontece comigo
- [47:00] Alguém vai comentar aqui
- [47:01] Pan
- [47:02] E vai falar onde está o problema
- [47:04] Fica vendo
- [47:04] Deixa eu ver aqui
- [47:09] X
- [47:09] X1
- [47:10] Tá
- [47:12] Ajuste
- [47:14] O D
- [47:16] Isso
- [47:18] Até aqui parece que está tudo bem
- [47:19] Aprendizagem
- [47:22] A parte de aprendizagem
- [47:25] Pessoal
- [47:30] Pode ficar tranquilo
- [47:30] Que isso funciona
- [47:31] Alguma coisa que está
- [47:33] Ainda falta de aprendizagem
- [48:03] Tá bom
- [48:11] O negócio aqui
- [48:14] Deixa eu perguntar antes para ver se algum erro na conta
- [48:24] Deixa eu cortar
- [48:26] Cara
- [48:29] Tinha pintado
- [48:31] Vocês estão vendo que está dando aqui
- [48:40] Ah tá
- [48:42] Aqui ó
- [48:43] Peste
- [48:44] Hum
- [48:46] Achou
- [48:46] Por isso
- [48:48] Tipo assim
- [48:49] Pô
- [48:49] Ele está dando total
- [48:50] Está dando certo
- [48:51] Ó
- [48:52] Está dando zero
- [48:53] Tipo assim
- [48:54] Tá bem
- [48:54] Não
- [48:55] Ah não
- [48:59] Mal lidado
- [49:00] Mesmo assim
- [49:01] De qualquer forma
- [49:02] Não tinha que estar
- [49:04] Calma aí
- [49:06] Que agora
- [49:06] O código não está salvando
- [49:07] Onde está vindo esse 20
- [49:10] E está dando
- [49:17] E eu estou printando o total aqui no final
- [49:19] E está dando o valor
- [49:20] Certo
- [49:20] É 17
- [49:29] Tinha que retornar o float aqui
- [49:34] Não tinha que estar retornando inteiro
## [49:35] Debugging `len(y_validado)` and `total` calculation

**Spoken content:**
- [49:36] Cara
- [49:43] Prenta o land validado aí
- [49:44] Para a gente ver
- [49:45] Faltou um parênteses
- [50:02] Acho
- [50:02] Não
- [50:12] O 20 por um
- [50:13] Deu
- [50:14] Não
- [50:15] Está errado
- [50:16] Isso aqui
- [50:16] Tinha que estar dando um
- [50:17] Tinha que
- [50:18] Parece que o código não está salvando
- [50:22] Regarde
- [50:25] Aí
- [50:30] Está vendo
- [50:30] Está dando menos resultado
- [50:31] Uhum
- [50:32] Se tivesse
- [50:33] 20 aqui
- [50:36] Eu estou printando só um número
- [50:37] E está me procurando dois
- [50:39] Ah não
- [50:39] Desculpa
- [50:40] 20
- [50:42] É que no final ele printa o total da curaça
- [50:46] É
- [50:48] E o retorno está dando sempre zero
- [50:50] 20
- [50:54] Total
- [50:55] 20
- [51:00] Teste
- [51:00] Teste
- [51:00] Não vou dar
- [51:01] Aí

**On-screen content:**
![Code showing `print(len(y_validado))` and `total = total / len(y_validado)`](video-frame://50@49:55)

The user is debugging the `acuracia` function.
The code snippet shows:
```python
def acuracia(y_teste, y_validado):
    total = 0
    for i in range(len(y_teste)):
        if y_teste[i] == y_validado[i]:
            total += 1
        else:
            pass
    print(len(y_validado))
    return total / len(y_validado)

accuracy = acuracia(y_teste, y_predict)
print(accuracy)
```
The terminal output shows `20` and then `0.0`. The speaker notes that the code seems to be giving the same incorrect result repeatedly, suggesting it might not be saving or running correctly.

## [51:01] Correcting the `acuracia` function and Python version issue

**Spoken content:**
- [51:06] 20
- [51:06] 20
- [51:06] Agora sim
- [51:07] Mas mesmo assim
- [51:08] Ele está dando muito
- [51:09] Tinha que dar
- [51:10] Ah não
- [51:11] 1.0
- [51:11] Está certo
- [51:12] 1.0
- [51:13] Deu certinho
- [51:16] Está vendo
- [51:17] Mas aqui
- [51:17] Ele está printando como se fosse inteiro
- [51:19] E não é inteiro
- [51:20] É um float
- [51:21] Um float
- [51:22] Não sei por que ele está fazendo isso
- [51:24] Porque aquilo
- [51:25] Seria para printar um float
- [51:27] Será que ele não está rodando isso no Python 2?
- [51:30] No on-time?
- [51:30] Não
- [51:32] Não
- [51:33] Não acredito que seria não
- [51:36] Não no Python 3 aqui
- [51:38] Deixa eu ver
- [51:41] Ah esse mesmo
- [51:43] Coloquei só Python aqui
- [51:45] É porque ele é redondo
- [51:46] Ele é redondo o valor no Python 2
- [51:49] Vacilo
- [51:50] Mas então pessoal

**On-screen content:**
![Terminal output showing `20` and `1.0`](video-frame://50@51:05)

The terminal now correctly shows `20` (length of `y_validado`) and `1.0` (the accuracy). The speaker then realizes that the previous output showing `0` instead of `0.0` was due to running the script with `python` (which defaults to Python 2 on some systems) instead of `python3`, where integer division behaves differently. Python 2 performs integer division if both operands are integers, truncating the result. Python 3 performs float division.

## [51:50] Perceptron summary and impact of learning rate

**Spoken content:**
- [51:51] Era só isso então
- [51:53] Então a gente tem aqui
- [51:54] A nossa
- [51:55] Os nossos dados de entrada
- [51:56] Aí nesse caso
- [51:59] Precisou de 28
- [52:00] É
- [52:01] Épocas para poder
- [52:03] Treinar o nosso algoritmo
- [52:05] Ele retornou esses dados aqui
- [52:07] E aí você usa para fazer
- [52:09] A validação
- [52:11] E aí ele retornou
- [52:13] Ele está com 100%
- [52:14] Não é normal
- [52:14] Dar 100%
- [52:16] É porque aqui são os dados
- [52:17] Estão totalmente
- [52:18] Estão bem separados
- [52:20] O cara fez para aquilo
- [52:21] Então assim
- [52:22] Está bem linearmente separado
- [52:25] Eu estou mudando só que o valor da aprendizagem
- [52:27] Para vocês terem ideia de quanto vai ficar
- [52:29] Aí está vendo
- [52:32] Aí de 28 com 0.01
- [52:36] 0.01
- [52:39] Ele passou para 112 com 0.01
- [52:43] Ou seja
- [52:44] Um milho
- [52:45] Um milhado
- [52:46] Então
- [52:47] Significa o que?
- [52:48] Que
- [52:49] Você vai ajustando valores tão pequenos
- [52:52] Que aí vai demorando mais a convergir
- [52:54] A rede
- [52:55] E tal
- [52:56] Então assim

**On-screen content:**
![Code and terminal output showing perceptron training with 28 epochs and 100% accuracy](video-frame://50@52:00)

The speaker summarizes the perceptron implementation. For the given dataset, it took 28 epochs to train and achieved 100% accuracy. This high accuracy is attributed to the data being perfectly linearly separable. The speaker then changes the `taxa_aprendiz` (learning rate) from `0.01` to `0.001`.

![Code and terminal output showing perceptron training with 112 epochs after changing learning rate](video-frame://50@52:31)

With `taxa_aprendiz = 0.001`, the number of epochs increased to 112, demonstrating that a smaller learning rate requires more epochs to converge.

## [52:57] Conclusion and experimentation with non-linearly separable data

**Spoken content:**
- [52:57] É isso que eu queria passar para vocês
- [53:00] Espero que tenha sido legal
- [53:03] Tenha ficado claro algumas coisas
- [53:05] A matéria de rede neural é muito complexa
- [53:10] É muito grande
- [53:11] Mas assim
- [53:12] É legal
- [53:13] Vale a pena vocês estudarem
- [53:14] Pegar esse mesmo
- [53:16] Essa mesma rede aqui
- [53:20] Esse mesmo dataset aqui
- [53:23] No data 1 aqui
- [53:25] Ele coloca
- [53:26] Não linearmente separável
- [53:28] Vamos fazer o teste com eles
- [53:30] Aqui
- [53:30] Vocês vão ver
- [53:31] Porque a mesma quantidade
- [53:32] A única mudança que a gente vai ter
- [53:34] É essa aqui
- [53:34] Ele faz aquela curva
- [53:36] Isso
- [53:37] Que faz a curva
- [53:38] Ele já não é um grafo linear
- [53:40] Então
- [53:43] Ficou um espaço
- [53:56] Então olha lá
- [53:56] De 95%
- [53:57] E ele precisou de mil
- [53:58] Tá vendo?
- [53:59] Então provavelmente
- [54:00] Vai precisar de mais
- [54:01] E ainda não vai nem chegar
- [54:02] Porque ele usou todas as épocas que eu tinha
- [54:05] E ficou com 95%
- [54:07] Porque ele não é linearmente separável
- [54:09] Então
- [54:10] Nesse caso
- [54:11] O Percepto
- [54:12] Então
- [54:12] Simples
- [54:12] Ele não serve para isso
- [54:14] Ele só serve para coisa linear mesmo
- [54:16] Aí
- [54:17] Se quiserem
- [54:19] Se quiserem
- [54:19] Depois eu acho
- [54:20] Eu disponibilizo o código
- [54:21] Vocês brincam
- [54:22] Muda
- [54:23] Tastra de treinamento
- [54:24] Coloca mais
- [54:25] Mais entradas
- [54:26] Tem o dataset
- [54:27] No Kaggle
- [54:28] Tem o dataset
- [54:29] No UCI
- [54:30] Brinca de poder
- [54:31] Transformar
- [54:32] Variável
- [54:33] Em
- [54:34] Número
- [54:35] Também
- [54:36] Porque
- [54:36] Letra
- [54:37] Nome
- [54:38] Não tem como
- [54:39] Então tem
- [54:40] Que ter um valor
- [54:41] Então tenta pegar um dataset
- [54:43] Colocar valor
- [54:44] Jogar no código
- [54:45] Para ver quanto vai ficar
- [54:46] Aumenta o número de variáveis
- [54:47] E tal
- [54:50] Cara
- [54:51] Agora eu vou começar com as perguntas
- [54:53] Aqui que eu tenho várias
- [54:54] Beleza
- [54:55] Cara
- [54:56] No Percepto
- [54:57] Por exemplo
- [54:58] Essa
- [54:59] Essa taxa de ciclos
- [55:01] Que ele vai ter
- [55:02] Que são as épocas
- [55:03] São cada reta
- [55:04] Que ele vai tentar cruzar
- [55:05] No meio
- [55:06] Da dispersão do gráfico
- [55:08] Certo?
- [55:08] Isso mesmo
- [55:09] Ele vai cruzando retas
- [55:11] Até
- [55:11] Conseguir
- [55:12] Separar todos os elementos
- [55:14] Então ele vai
- [55:16] Aumentando
- [55:17] Ele vai contando
- [55:18] Uma época
- [55:19] Ele conseguiu separar
- [55:20] Um
- [55:21] Dois
- [55:22] Aí ele vai fazendo até
- [55:23] Seria o treinamento em si
- [55:26] Até ele
- [55:26] Até o que a gente chama de convergir
- [55:29] Convergir
- [55:30] O dado
- [55:32] Convergir a rede neural
- [55:33] Em todos os elementos
- [55:34] Cara, você pode mostrar de novo a imagem
- [55:36] Para o pessoal entender agora
- [55:37] Quem chegou depois
- [55:38] Quem
- [55:38] Ah, sim
- [55:39] Aquela que a gente tinha mostrado
- [55:40] Agora
- [55:41] Tá vendo?
- [55:43] Tá dando pra ver o slide?
- [55:45] Uhum
- [55:46] Aqui, ó
- [55:48] Isso
- [55:48] Então o que ele tá fazendo é isso
- [55:50] Ele vai traçando retas entre as classes
- [55:53] Até chegar na reta
- [55:55] Que vai ter
- [55:56] Separado todas as classes
- [55:58] Aí
- [55:59] É o que a gente chama de convergência
- [56:01] Que a reta convergiu
- [56:04] A rede convergiu, né?
- [56:08] Pô, muito show
- [56:11] Cara, e algumas coisas que a galera perguntou aqui
- [56:14] Tipo assim
- [56:14] O que a gente consegue fazer com uma rede neural?
- [56:16] Assim
- [56:16] Que é uma coisa suficiente
- [56:18] Ou sei lá
- [56:19] Um problema básico que eu possa ter
- [56:20] Que eu possa usar redes neurais
- [56:22] Você consegue fazer
- [56:24] Classificação de
- [56:27] De reconhecimento de imagem
- [56:29] Com Perceptor Simples
- [56:31] Você já consegue fazer
- [56:32] O reconhecimento de imagem já
- [56:33] Tendo ali
- [56:35] O seu dataset
- [56:37] O dataset pronto
- [56:39] Bem estruturado
- [56:41] Feito lá
- [56:42] O seu pré-processamento
- [56:44] De forma legal
- [56:44] Você já consegue colocar ele pra reconhecer
- [56:47] Padrão
- [56:49] Então se for padrão
- [56:50] Se você precisar de reconhecer padrão
- [56:53] O Perceptor já é capaz
- [56:55] O Perceptor Simples
- [56:56] Aí se você vai precisar de fazer alguma outra coisa mais complexa
- [57:00] Que exige
- [57:00] Coisa que não seja linear
- [57:03] E tudo mais
- [57:03] Aí tem o Perceptor multicamadas
- [57:05] Que já é bem mais complicado
- [57:08] Que já cairia nisso aqui
- [57:09] Vamos supor
- [57:11] Esse aqui é um multicamadas
- [57:15] Ou seja, você tem entrada
- [57:16] Aí você tem os somatórios para cada uma das entradas
- [57:21] Para cada uma desses neurônios ocultos
- [57:23] Aí o somatório desses neurônios aqui
- [57:26] Vão inferir aqui
- [57:29] Para essas saídas
- [57:30] E aí você pode ter até mais redes aqui
- [57:33] Mais camadas
- [57:34] Aí a cada camada que você tem
- [57:36] É uma complexidade maior
- [57:38] Que você está gerando
- [57:40] Para a sua rede
- [57:42] Pô, muito show
- [57:44] Perguntaram aqui
- [57:47] Como que cria um dataset
- [57:49] E aí
- [57:50] Essa é uma pergunta interessantíssima
- [57:52] O que que serviria de base
- [57:54] Para a gente começar um dataset
- [57:56] Para a gente conseguir estudar um pouco disso
- [57:58] Eu sei que tem vários prontos no Kego
- [58:00] A galera pode entrar lá e baixar
- [58:01] No GitHub tem vários também
- [58:03] Eu nunca criei um dataset
- [58:05] Eu nunca criei
- [58:06] Eu não sei falar
- [58:07] Criar
- [58:08] Mas assim
- [58:08] Porque
- [58:09] É mais complicado
- [58:11] Pelo seguinte
- [58:11] Você pode gerar
- [58:13] Duas
- [58:13] Duas
- [58:14] Linhas
- [58:15] De números aleatórios
- [58:18] E gerar uma classe
- [58:19] Vamos supor
- [58:21] Se eu quiser
- [58:22] Gerar aqui
- [58:23] Pegar esse dataset
- [58:25] E criar um random
- [58:26] Que vai me
- [58:27] Gerar esses números aqui
- [58:29] Tanto essas linhas
- [58:31] E aqui também
- [58:32] Vai me gerar um número aleatório
- [58:34] Só que a aleatoriedade
- [58:36] Em rede neural
- [58:37] Não vai convergir
- [58:39] Porque assim
- [58:39] Tem que ter uma
- [58:41] Tem que ter uma lógica
- [58:42] Entendeu?
- [58:42] É que eu não sei
- [58:44] Para você analisar os dados
- [58:45] Isso
- [58:46] Tanto que
- [58:47] Igual existem de vinho
- [58:49] E não sei o que
- [58:49] Que aí você tem
- [58:50] Igual eu falei
- [58:52] Um outro exemplo lá
- [58:53] Você tem
- [58:54] Teor alcoólico
- [58:55] Você tem aqui
- [58:56] Acidez
- [58:59] Você tem cor
- [59:00] Você tem
- [59:01] Então
- [59:01] Os valores fazem sentido
- [59:03] Para gerar um resultado
- [59:06] Você criar assim
- [59:09] Do nada
- [59:10] Eu acho difícil
- [59:11] Pode até
- [59:12] Se alguém tentar
- [59:13] E tal
- [59:14] Eu acho até legal
- [59:14] Depois vou até pensar
- [59:16] Vou fazer
- [59:16] Vou fazer isso
- [59:17] Mas eu acho difícil
- [59:18] A rede convergir
- [59:19] Sim
- [59:20] Cara eu acho
- [59:21] Uma coisa legal
- [59:22] Também que dá
- [59:22] Para o pessoal fazer
- [59:23] Pô
- [59:23] Quem curte sensores
- [59:25] Essas coisas
- [59:25] Cara
- [59:26] Se tiver um sensor
- [59:27] De luminosidade
- [59:28] Um sensor de temperatura
- [59:29] No arduino
- [59:29] Você já começa a conseguir
## [59:30] Perceptron for classification

**Spoken content:**
- [59:31] Estabelecer altas relações
- [59:32] De temperatura
- [59:34] E luminosidade
- [59:36] Por exemplo
- [59:36] Cara
- [59:36] Dá para fazer
- [59:37] Bastante coisa
- [59:38] Dá para fazer
- [59:39] Com perceptum
- [59:40] Assim
- [59:40] Simples
- [59:41] É mais para classificação
- [59:43] Mas assim
- [59:44] Para você estudar
- [59:45] Ele assim
- [59:47] Na mão
- [59:47] Ela é de boa demais
- [59:48] Ela é muito de boa
- [59:50] Tanto que
- [59:51] Deixa eu ver
- [59:52] Porque eu não tenho tempo
- [59:53] Porque eu ia fazer
- [59:54] Com a gente aqui
- [59:56] Deixa eu ver
- [59:57] Se dá para
- [59:58] Perguntaram se isso é a mesma coisa

**On-screen content:** The video shows a Python script in VS Code. The script defines a `Perceptron` class and functions for `predict`, `y_validado`, and `accuracia`.
![Python code for Perceptron class and related functions](video-frame://50@59:30)

## [1:00:06] TensorFlow vs. scikit-learn

**Spoken content:**
- [1:00:07] Que o TensorFlow faz
- [1:00:08] É
- [1:00:10] É e não é
- [1:00:11] Porque assim
- [1:00:12] O TensorFlow
- [1:00:14] Ele tem mais aplicativos
- [1:00:16] Ele é bem mais completo
- [1:00:18] Então assim
- [1:00:20] Ele faz também
- [1:00:22] Ele faz
- [1:00:23] Site learning
- [1:00:24] Ele faz
- [1:00:25] Ele faz
- [1:00:26] De uma forma
- [1:00:27] Bem mais simples
- [1:00:28] Quer ver
- [1:00:28] Eu vou até mostrar
- [1:00:30] Para vocês aqui
- [1:00:31] O tamanho do código
- [1:00:34] Que vai ficar
- [1:00:34] Se você fizer
- [1:00:35] Com
- [1:00:36] Site learning
- [1:00:37] Isso é a mesma coisa
- [1:00:38] É a mesma coisa
- [1:00:39] Aqui eu estou pegando

**On-screen content:** The user navigates through file explorer, then returns to VS Code, opening a new file `neural_science.py`.
![VS Code with an empty Python file `neural_science.py`](video-frame://50@1:00:10)

## [1:00:42] Importing libraries and loading data with scikit-learn

**Spoken content:**
- [1:00:44] Estou pegando
- [1:00:49] As bibliotecas já
- [1:00:50] Que a gente vai usar
- [1:00:51] Porque ela
- [1:00:52] Ela tem
- [1:00:53] Elas são
- [1:00:53] Separadas
- [1:00:54] Você tem aqui
- [1:00:56] As bibliotecas
- [1:00:58] Para trabalhar
- [1:00:59] Com elementos lineares
- [1:01:00] Que é essa linear model
- [1:01:01] Essa model selection
- [1:01:03] É a que você faz
- [1:01:04] O
- [1:01:04] Train
- [1:01:05] Trash
- [1:01:05] Split
- [1:01:06] E a metrics
- [1:01:06] Que você pega
- [1:01:07] A acurácia
- [1:01:08] Você pega aqui
- [1:01:10] Vamos usar o pandas
- [1:01:11] Também
- [1:01:12] Para importar os dados
- [1:01:13] Vocês vão ver
- [1:01:20] Como é que é

**On-screen content:** The user starts typing code in `neural_science.py`.

```python
from sklearn import linear_model, model_selection, metrics
import pandas
```
![Python code importing scikit-learn modules and pandas](video-frame://50@1:00:50)

## [1:01:20] Loading and preparing data

**Spoken content:**
- [1:01:21] Mamão com açúcar
- [1:01:22] Estreja
- [1:01:23] Não precisa de converter
- [1:01:34] Converter nada
- [1:01:35] Ele já
- [1:01:36] Ele já faz tudo
- [1:01:37] Para você
- [1:01:38] Você pega os valores
- [1:01:38] Ele já sabe
- [1:01:39] Que é
- [1:01:40] Que são valores
- [1:01:42] Ele já
- [1:01:44] Converte tudo
- [1:01:45] Para inteiro
- [1:01:46] Para float
- [1:01:47] Inteiro
- [1:01:47] Para você precisar
- [1:01:48] Estou pegando aqui
- [1:01:49] Todas as linhas
- [1:01:50] E estou pegando
- [1:01:51] A coluna
- [1:01:52] 1
- [1:01:52] E o y
- [1:01:57] Eu vou pegar
- [1:01:58] As variáveis
- [1:01:59] De atributos
- [1:02:00] Eu estou pegando aqui
- [1:02:04] Só as que estão
- [1:02:05] Na
- [1:02:06] Linha 0
- [1:02:08] O meu percept

**On-screen content:** The user adds code to load a CSV file and split data into X and Y.

```python
dataset = pd.read_csv('data.csv')
X = dataset.iloc[:, 1:].values
y = dataset.iloc[:, 0].values
```
![Python code for loading data and splitting X and Y](video-frame://50@1:01:30)

## [1:02:09] Creating Perceptron and splitting data

**Spoken content:**
- [1:02:10] Eu vou criar o meu percept
- [1:02:11] Estão aqui
- [1:02:12] O elemento
- [1:02:13] Percept
- [1:02:14] O objeto
- [1:02:15] Percept
- [1:02:15] E aqui o meu objeto
- [1:02:26] Estou passando aqui
- [1:02:49] O meu x
- [1:02:49] O meu y
- [1:02:50] Vou passar aqui
- [1:02:51] O meu test size
- [1:02:53] O meu test size
- [1:02:56] Ele vai ter o tamanho
- [1:02:58] De 0.2
- [1:02:58] Ou seja
- [1:02:59] 20%
- [1:03:00] E o random state
- [1:03:02] Aqui é só
- [1:03:03] Para ele não variar
- [1:03:04] Se vocês
- [1:03:06] Fizer
- [1:03:06] Igual
- [1:03:08] É só colocar
- [1:03:10] O mesmo número
- [1:03:11] Aqui
- [1:03:11] Estou colocando aqui
- [1:03:12] Como
- [1:03:12] Percept
- [1:03:16] Já peguei os valores
- [1:03:17] Que é meu objeto
- [1:03:18] Percept
- [1:03:18] Já estou
- [1:03:20] Gerando aqui
- [1:03:20] Meu train
- [1:03:21] Trash split
- [1:03:22] Eu vou colocar aqui

**On-screen content:** The user adds code to instantiate `Perceptron` and perform `train_test_split`.

```python
perceptron = linear_model.Perceptron()

X_train, X_test, y_train, y_test = model_selection.train_test_split(X, y, test_size=0.2, random_state=0)
```
![Python code for Perceptron instantiation and train_test_split](video-frame://50@1:03:11)

## [1:03:22] Training and predicting

**Spoken content:**
- [1:03:23] Classificador
- [1:03:24] Pro
- [1:03:29] Pro
- [1:03:29] Fit
- [1:03:33] Pego no x
- [1:03:36] No x de treino
- [1:03:39] E o y de treino
- [1:03:41] Recebe
- [1:03:50] Desculpa
- [1:03:54] Pegar o classificador
- [1:03:56] Ponto
- [1:03:57] Vamos jogar aqui
- [1:04:10] O meu x de teste
- [1:04:11] Beleza
- [1:04:22] Beleza
- [1:04:22] E agora

**On-screen content:** The user adds code for training the perceptron and making predictions.

```python
classificador = perceptron.fit(X_train, y_train)
y_predict = classificador.predict(X_test)
```
![Python code for training and predicting with the Perceptron](video-frame://50@1:04:11)

## [1:04:23] Calculating and printing accuracy

**Spoken content:**
- [1:04:24] Eu vou printar aqui
- [1:04:25] A minha métrica
- [1:04:26] Que é a curácia dele
- [1:04:28] Já acabou?
- [1:04:30] Sério?
- [1:04:31] Acabou
- [1:04:32] Aí eu já
- [1:04:36] Jogo aqui
- [1:04:36] Meu y de teste
- [1:04:37] E jogo
- [1:04:38] Meu y
- [1:04:38] Y de
- [1:04:39] Meu y
- [1:04:39] Predict
- [1:04:40] E ele já
- [1:04:42] Printa para mim
- [1:04:43] O valor
- [1:04:44] Foi com ponto

**On-screen content:** The user adds code to print the accuracy score.

```python
print(metrics.accuracy_score(y_test, y_predict))
```
![Python code to print accuracy score](video-frame://50@1:04:30)

## [1:04:49] Debugging an error

**Spoken content:**
- [1:04:50] Foi isso
- [1:04:53] Ah, você cortou o panda
- [1:05:01] Desculpa
- [1:05:02] Normal
- [1:05:03] E aí eu vou colocar aqui no x de treino
- [1:05:12] Ajuda a seleção, a 30, a split, a 6, a size, a state.
- [1:05:42] Eu não sei qual é o erro agora, 0.2, não está certo, x e y, não está certo, x3, x test, y3, y test.
- [1:06:10] Não está certo, ele retorna sempre nesse jeito aqui, nessa ordem, x treino, x test, y treino, y test.
- [1:06:19] O classificador está recebendo, vai ser confite, com o classificador x test.
- [1:06:33] Cara, o Lugão falou aqui que você tirou o primeiro valor no x, e aí ele está dando um ponto a mais.

**On-screen content:** The user runs the script and encounters an error. The terminal output shows a `ValueError: Found input variables with inconsistent numbers of samples: [99, 3]`.
![Terminal output showing a ValueError](video-frame://50@1:04:50)

## [1:06:37] Fixing the data slicing error

**Spoken content:**
- [1:06:45] É porque eu esqueci de incluir as linhas, é porque eu tenho que passar todas as linhas e a coluna que eu quero.
- [1:06:54] Então eu esqueci de passar todas as linhas aqui.
- [1:06:57] Por isso que ele estava reclamando, porque ele está dando valores diferentes, não é tipo, tem só um valor nenhum, ou vários nenhum outro.
- [1:07:08] Aí ele deu aqui, ele dá esse warning aqui, mas, ignorar, mas aqui ele deu.

**On-screen content:** The user corrects the data slicing for `X` and `y`.

```python
X = dataset.iloc[:, 1:].values
y = dataset.iloc[:, 0].values
```
The corrected code should be:
```python
X = dataset.iloc[:, 1:].values
y = dataset.iloc[:, 0].values
```
The original code was `X = dataset.iloc[:, 1].values` and `y = dataset.iloc[:, 0].values` which was incorrect. The fix is to use `1:` for X to select all columns from the second one onwards. The video shows the fix at 1:06:49, where the `X` line is changed to `X = dataset.iloc[:, 1:].values`.
![Python code with corrected data slicing for X](video-frame://50@1:06:50)

## [1:07:09]

**Spoken content:**
- [1:07:14] 1.0 de acurácia.
- [1:07:16] 1.0, ou seja, 100% de acurácia.
- [1:07:19] Se a gente jogar aqui o data 1, provavelmente ele vai dar um valor menor.
- [1:07:23] Acho que até mais baixo mesmo.
- [1:07:25] Olha lá, 75%.
- [1:07:28] Show com esse data 1.
- [1:07:30] É isso.
- [1:07:31] E aqui, sem lembrar também, lembrando também, que aqui você consegue mudar o valor de alfa, que no caso, aqui é o valor de treinamento.
- [1:07:41] Você tem o valor de eta, que é o valor de, desculpa, de alfa, é o valor do bias.
- [1:07:46] O valor de eta, que é o valor do bias, que o padrão é menos 1.
- [1:07:52] Então, você consegue mudar tudo isso aqui, pelo próprio Perceptor Feature aqui, você consegue criar e ir variando os valores.
- [1:08:02] Show, cara.
- [1:08:04] É isso.
- [1:08:05] Ficou muito mais simples.
- [1:08:06] 15 linhas.
- [1:08:07] Bem melhor.
- [1:08:09] Bem melhor, não tem nem comparação, né?
- [1:08:11] Cara, eu acho que você tinha que voltar qualquer outro dia para dar uma live só de Psychic Learning, cara.
- [1:08:16] Ué, na hora.
- [1:08:17] Só se querer.
- [1:08:19] É só combinar, vamos levar mais uns seis meses aí de novo, mas tá tudo bem.
- [1:08:23] Não, mas aí tem problema não.
- [1:08:25] Tranquilo, pessoal?
- [1:08:27] Não, cara, fica tranquilo.
- [1:08:28] Cara, o pessoal falou que foi muito bacana, que você mandou muito bem.
- [1:08:31] Valeu.
- [1:08:32] Cara, muito obrigado por ter participado.
- [1:08:35] Eu te agradeço.
- [1:08:36] Esse é um assunto que eu não daria uma live, mas, cara, muito bacana.
- [1:08:42] Cara, fica com vontade para voltar quando você quiser.
- [1:08:45] Só me convidado.
- [1:08:47] Tô aí.
- [1:08:48] Sempre convidado.
- [1:08:49] E para o pessoal que está assistindo, pô, os links vão ficar, eles estão aqui embaixo.
- [1:08:55] O link do GitHub, o link da live no grupo do Telegram.
- [1:09:00] E, pô, o pessoal falou que foi show demais, muito fixe, embora eu não saiba o que isso significa.
- [1:09:07] Obrigado, parabéns, cara.
- [1:09:09] Obrigado, Aline.
- [1:09:11] Obrigado por todos os elogios do mundo.
- [1:09:12] Obrigado, Aline.
- [1:09:14] Cara, se você quiser depois mandar um...
- [1:09:17] Se quiser fazer um fork lá do repositório da live e mandar um pull request, cara, fica à vontade.
- [1:09:24] Sim, vou fazer agora mesmo.
- [1:09:26] A gente tem tudo organizadinho, as pastinhas da live com código, as pastinhas do...
- [1:09:30] Pô, cara, fica à vontade para fazer o que você quiser.
- [1:09:32] Legal, tô mandando aí agora.
- [1:09:34] Beleza, então, cara.
- [1:09:36] Beleza, pessoal.
- [1:09:36] Então, obrigado, gente.
- [1:09:37] Boa noite aí de vocês.
- [1:09:39] Muito obrigado, boa noite e um abraço a todos.
