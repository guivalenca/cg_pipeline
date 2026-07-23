---
id: "57"
title: "Tensorflow"
source_url: "https://www.youtube.com/watch?v=2eYLt1NA4Ss"
fetch_url: "https://www.youtube.com/watch?v=2eYLt1NA4Ss"
resolved_url: "https://www.youtube.com/watch?v=2eYLt1NA4Ss"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T05:31:01.403938Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "c7aeb2a6d63bb840b96276420038cb597f939991daee2f664f9d2f839d51baa5"
cache_keys:
  - "c7aeb2a6d63bb840b96276420038cb597f939991daee2f664f9d2f839d51baa5"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 610.0
transcript_source: "local_whisper_vtt"
transcript_sha256: "98fa2dbee92b95442b5a71eb05186769142e4d4d6694a0ae066f226aaaf14b59"
word_count: 2495
char_count: 15315
content_sha256: "0bcdadce31ea2d9259fcad9a72ccaf713b488afa7fa1c6e7ea3c80b0457f08be"
image_count: 16
link_count: 0
total_token_count: 39898
estimated_input_tokens: 32805
warnings:
  - "title_mismatch"
gate_status: "passed_with_warnings"
gate_failures: []
route_notes: []
---

## [00:00] Introduction to TensorFlow

**Spoken content:**
- [00:00] Contextualizando, o TensorFlow é uma plataforma open source para machine learning,
- [00:05] criada e utilizada por ninguém menos que o Google.
- [00:07] Com o TensorFlow, desenvolvedores conseguem construir e implementar facilmente
- [00:11] aplicações como machine learning, já que ele disponibiliza um ecossistema flexível,
- [00:16] com muitas ferramentas, bibliotecas e recursos da própria comunidade.
- [00:20] Deixando assim em nossas mãos o que há de mais moderno em aprendizado de máquina.
- [00:25] Que tal então aprender sobre elas primeiro, antes que elas aprendam mais sobre você?
- [00:31] Fique então conosco em mais esse dicionário do programador.
- [00:36] Olá, CDF! Seja bem-vindo a esse vídeo recheado de conteúdo.

**On-screen content:** ![image: two presenters in lab coats with "Código Fonte TV" shirts](video-frame://57@00:00)

## [00:40] TensorFlow Core and its Origins

**Spoken content:**
- [00:43] Falar de TensorFlow é falar de machine learning, redes neurais, deep learning e muito mais.
- [00:48] Deixando o seu like agora no vídeo, ele será muito útil para que a inteligência artificial do YouTube
- [00:53] e entenda que esse conteúdo é bom pra caramba.
- [00:56] E que esse vídeo deve ser apresentado para o maior número possível de pessoas interessadas por programação.
- [01:02] Like detectado? Agora podemos seguir.
- [01:04] O TensorFlow tem como núcleo uma biblioteca de código aberto
- [01:08] para computação numérica usando grafos computacionais.
- [01:11] Essa biblioteca é o que ajuda deveras a desenvolver e treinar os modelos de machine learning.
- [01:17] Ele foi desenvolvido pela Google Brain Team, uma das equipes de pesquisa da empresa,
- [01:21] cujo lema é Make Machines Intelligent, Improve People's Life.
- [01:25] Ou torne as máquinas inteligentes e melhore a vida das pessoas.
- [01:29] A versão 1.0 do TensorFlow foi lançada em fevereiro de 2017,
- [01:32] contando com muitas contribuições de desenvolvedores externos,
- [01:35] já que a Lib se tornou open source em 2015.
- [01:38] Atualmente, ela é amplamente utilizada por desenvolvimento em deep learning
- [01:42] e aplicações com inteligência artificial.
- [01:44] Sem contar que é o TensorFlow que está por trás de serviços como busca, Gmail e o tradutor do Google.
- [01:51] Só com esses três já podemos ver toda a capacidade do TensorFlow, não é mesmo?
- [01:56] Estamos aqui com o Snap, mas ele não fica só com a gente, não.

**On-screen content:** ![image: two presenters in lab coats with "Código Fonte TV" shirts](video-frame://57@00:40)

## [01:56] HostGator Sponsorship

**Spoken content:**
- [01:59] Todos os clientes da HostGator contam com a companhia do Snap
- [02:02] através de um suporte que nunca te deixa sozinho.
- [02:05] Eles estão lá prontos para te ajudar 24 horas por dia, 7 dias por semana.
- [02:10] O suporte para toda hora é na HostGator.
- [02:12] Não esquece que acessando o link aqui na descrição, você consegue um super desconto.
- [02:17] O TensorFlow teve como antecessor o Disbelieve,

**On-screen content:** ![image: HostGator logo with a blue alligator mascot](video-frame://57@01:56)

## [02:18] TensorFlow's Evolution and Ecosystem

**Spoken content:**
- [02:21] que foi a ferramenta original do Google para deep learning,
- [02:24] mas que acabou tendo algumas limitações de usabilidade e flexibilidade.
- [02:28] Por isso, o Google Brain Team já criou o TensorFlow
- [02:31] sabendo que ele teria que ser flexível, eficiente, extensível e portável.
- [02:36] Dá para usar o TensorFlow em qualquer projeto.
- [02:38] Inclusive, ele pode ser integrado tanto em um simples smartphone,
- [02:42] quanto em um cluster gigante de computadores.
- [02:44] O TensorFlow ainda tem um ecossistema completo,
- [02:47] com workflows para desenvolver e treinar modelos,
- [02:49] usando Python, JavaScript e também Swift.
- [02:52] Esses workflows facilitam o deploy,
- [02:54] sejam na nuvem, localmente, no browser,
- [02:57] ou em um dispositivo compatível,
- [02:59] independente da linguagem que está sendo utilizada.
- [03:02] Nesse ecossistema, é possível encontrar

**On-screen content:** ![image: two presenters in lab coats with "Código Fonte TV" shirts](video-frame://57@02:18)

## [03:02] Components of the TensorFlow Ecosystem

**Spoken content:**
- [03:04] o TensorFlow, chamado de TensorFlow Core.
- [03:06] O TensorFlow.js, utilizado para consumir modelos
- [03:10] ou implementar modelos já existentes em JavaScript.
- [03:13] O TensorFlow.light, utilizado para implementar modelos de machine learning
- [03:16] em dispositivos mobile ou IoT.
- [03:18] O TensorFlow.extended, ou TFX,
- [03:21] que é uma plataforma para fazer deploy em produção
- [03:24] de uma pipeline machine learning.
- [03:26] Ou seja, ele permite criar e gerenciar tarefas específicas de machine learning
- [03:30] que serão executadas através de uma pipeline já definida.
- [03:33] Swift for TensorFlow é a próxima geração para Deep Learning
- [03:37] e Differenceable Computing,
- [03:38] que integra a linguagem de programação Swift
- [03:41] diretamente no TensorFlow.
- [03:42] De acordo com o GitHub, o projeto ainda não está finalizado.
- [03:46] Ou seja, não está preparado para ir para a produção,
- [03:48] mas já pode ser e deve ser testado.

**On-screen content:** ![image: two presenters in lab coats with "Código Fonte TV" shirts](video-frame://57@03:02)

## [03:51] TensorFlow Tools and Features

**Spoken content:**
- [03:51] O TensorBoard, que traz um conjunto de ferramentas
- [03:54] para visualização de dados e experimentações para machine learning.
- [03:57] Ele apresenta gráficos, métricas, dados, fotos, imagens e até áudios.
- [04:02] E o TensorFlow Hub, que é a biblioteca onde estão disponíveis
- [04:05] os modelos de machine learning que podem ser reutilizáveis em qualquer projeto.
- [04:10] Utilizar um módulo disponível para lá também é bem simples.
- [04:14] Dá uma olhadinha nesse código.
- [04:15] Nele, estamos usando um modelo de classificação de texto
- [04:18] que já está treinado e provavelmente através de uma base de dados
- [04:21] muito maior do que a que teríamos disponível.

**On-screen content:** ![image: TensorBoard interface showing graphs and metrics](video-frame://57@03:51)
```python
embed = hub.Module("https://tfhub.dev/google/nnlm-en-dim50/1")
embeddings = embed(["Conteúdo incrível!"])
```
**On-screen content:** ![image: HostGator logo with a blue alligator mascot](video-frame://57@04:22)

## [04:25] Understanding Machine Learning Models

**Spoken content:**
- [04:25] Já citamos várias vezes os models ou modelos machine learning.
- [04:29] Mas você sabe exatamente o que eles são e para que eles servem?
- [04:32] O modelo de machine learning é um arquivo que foi treinado
- [04:35] para reconhecer determinados tipos de padrões.
- [04:37] Esse treinamento é feito com um conjunto de dados, ou dataset,
- [04:40] criando para ele um algoritmo que pode ser usado
- [04:43] para ponderar e aprender com base nesse conjunto de dados iniciais.
- [04:47] Depois que esse modelo estiver treinado,
- [04:48] ele será usado para analisar novos dados e fazer previsões sobre eles.
- [04:52] Vamos dar um exemplo para clarear vossas mentes.
- [04:55] Imagina que precisamos criar um aplicativo para identificar a raça de cachorros.
- [04:59] Teríamos que treinar o modelo alimentando ele com imagens de vários cachorros
- [05:03] e suas respectivas raças.
- [05:05] Quando ele estiver devidamente treinado,
- [05:06] será um modelo capaz de identificar a raça de qualquer cachorro.
- [05:10] Esses modelos já treinados podem ser compartilhados e reutilizados em outros projetos.
- [05:15] Eles ficam disponíveis no TensorFlow Hub ou no Model Garden,
- [05:19] duas fontes de consultas importantíssimas para quem quer trabalhar na plataforma.
- [05:23] Além dos modelos, existem também diversas coleções de datasets
- [05:27] ou conjuntos de dados prontos para serem utilizados nos projetos.

**On-screen content:** ![image: two presenters in lab coats with "Código Fonte TV" shirts](video-frame://57@04:25)

## [05:30] TensorFlow Tools and Resources

**Spoken content:**
- [05:30] O TensorFlow traz algumas ferramentas, como Collab ou Collaboratory,
- [05:34] que é um ambiente que permite a execução do código TensorFlow
- [05:38] usando uma aplicação web super poderosa chamada Jupyter Notebook.
- [05:42] O Tensor Board, que já explicamos agora mesmo.
- [05:45] Esqueceu não, né?
- [05:46] What If Tool, uma ferramenta com interface visual e interativa
- [05:49] que ajuda a inspecionar um modelo de Machine Learning.
- [05:51] Ela ainda é compatível com o Tensor Board, o Jupyter e o Collab Notebooks.
- [05:56] É Mel Perf, que traz um grande conjunto de dados
- [05:59] para medir a performance de frameworks, aceleradores de hardware e plataforma cloud.
- [06:04] Tudo voltado para Machine Learning, é claro.
- [06:06] O ZLA é um compilador otimizado para Machine Learning.
- [06:09] Ele acelera os modelos criados sem mexer no código fonte,
- [06:12] usando apenas o poder escondido na álgebra linear.
- [06:16] TensorFlow Playground.
- [06:18] Eu adoro quando ferramentas um pouco mais complexas disponibilizam um parquinho
- [06:22] para aprendermos futucando.
- [06:24] E é exatamente isso que o TensorFlow Playground oferece.
- [06:27] Uma rede neural para você mexer à vontade direto pelo navegador.
- [06:31] TensorFlow Research Cloud, que não é uma ferramenta,
- [06:33] e sim um programa onde pesquisadores podem solicitar acesso
- [06:36] a um cluster de mais de mil cloud TPUs sem custo.
- [06:40] Tudo isso para ajudar em pesquisa.
- [06:42] TPUs, para quem não sabe, são os processadores gráficos
- [06:45] transformados em processadores de inteligência artificial do próprio Google.
- [06:50] WebLier, ou Multi-Level Intermediate Representation,
- [06:53] que explicando de uma forma simplificada,
- [06:55] ajuda a realizar uma ponte entre a representação dos modelos
- [06:58] e compiladores que geram código de baixo nível.

**On-screen content:** ![image: two presenters in lab coats with "Código Fonte TV" shirts](video-frame://57@05:30)
![image: What-If Tool interface](video-frame://57@05:46)
![image: TensorFlow Playground interface](video-frame://57@06:15)

## [07:01] TensorFlow Competitors

**Spoken content:**
- [07:01] Para você não ficar achando que só existe o TensorFlow no mundo,
- [07:04] vamos citar alguns concorrentes dessa plataforma,
- [07:07] como o PyTorch, construído em Python,
- [07:09] que tem algumas semelhanças com o TensorFlow.
- [07:11] Ele é uma boa opção para projetos um pouco menores.
- [07:14] O CNTK, ou Microsoft Cognitive Toolkit,
- [07:17] que também usa uma estrutura gráfica para descrever o fluxo de dados,
- [07:21] mas é mais focada na criação de redes neurais de Deep Learning.
- [07:24] O Apache MXNet, que é o principal framework de Deep Learning adotado pela AWS,
- [07:30] com suporte a APIs Python, C++, Scala R, JavaScript, Julia, Perl e Go.
- [07:36] E o CAF, um framework para Deep Learning Open Source.
- [07:40] Falar dos exemplos de utilização do TensorFlow acaba sendo bem fácil,

**On-screen content:** ![image: two presenters in lab coats with "Código Fonte TV" shirts](video-frame://57@07:01)

## [07:40] Real-World Applications of TensorFlow

**Spoken content:**
- [07:43] principalmente pelos serviços do Google, que já citamos,
- [07:46] buscador, Gmail e tradutor.
- [07:48] Mas podemos citar vários outros cases igualmente interessantes.
- [07:52] Como o PayPal, que utiliza o TensorFlow para o controle de fraudes.
- [07:56] Ou o Twitter, que utiliza ele para gerar o ranking dos tweets.
- [07:59] Ou a General Electric, que está treinando uma rede neural
- [08:02] para identificar anatomia específica durante uma ressonância magnética do cérebro,
- [08:06] para ajudar a agilizar e melhorar a confiabilidade dos exames.

**On-screen content:** ![image: two presenters in lab coats with "Código Fonte TV" shirts](video-frame://57@07:40)

## [08:10] The Future of TensorFlow: Quantum Computing

**Spoken content:**
- [08:10] Quanto ao futuro,
- [08:11] o futuro do TensorFlow pode ter sido anunciado em 9 de março de 2020,
- [08:16] quando o TensorFlow Quantum foi apresentado através do blog de inteligência artificial do Google.
- [08:22] O TFQ traz as ferramentas necessárias
- [08:24] para que pesquisadores de Machine Learning e computação quântica
- [08:27] possam juntos controlar e criar modelos naturais ou artificiais de sistemas quânticos.
- [08:32] Acho que vale a pena a gente reforçar que trabalhar com Machine Learning

**On-screen content:** ![image: two presenters in lab coats with "Código Fonte TV" shirts](video-frame://57@08:10)

## [08:34] Becoming a Machine Learning Specialist

**Spoken content:**
- [08:38] não é só aprender uma determinada ferramenta,
- [08:40] mesmo ela sendo tão completa e interessante quanto o TensorFlow.
- [08:43] Sua própria equipe descreve que acredita ser uma base sólida
- [08:46] para quem deseja se tornar um especialista no assunto.
- [08:49] Essa base está dividida em quatro pilares.
- [08:52] Programação, que será usada para gerenciar dados,
- [08:54] ajustar parâmetros e analisar resultados necessários
- [08:56] para testar e otimizar os modelos.
- [08:59] Matemática e estatística.
- [09:01] Dessas duas não dá para fugir.
- [09:02] Elas são a base para a criação dos modelos de Machine Learning.
- [09:05] Conhecer esses conceitos é fundamental.
- [09:08] Teoria de Machine Learning.
- [09:09] Conhecer a teoria é o primeiro passo para aplicar os conceitos de forma correta
- [09:13] e a melhor maneira de evoluir tecnicamente.
- [09:16] E agora sim, pôr a mão na massa.
- [09:18] Aí não tem mistério, né gente?
- [09:19] É usar o TensorFlow Playground
- [09:21] ou construir seus próprios projetos com a ajuda de vários conteúdos disponíveis na web.
- [09:26] Essa sim é uma excelente forma de testar os seus conhecimentos
- [09:30] e de pôr toda aquela teoria em prática.
- [09:32] Para quem se interessar, existe um programa de certificações
- [09:34] chamado TensorFlow Developer Certificate,
- [09:37] que oferece alguns benefícios, mas não é gratuito.
- [09:40] Depois desses pontos e de todas as informações que te demos sobre o TensorFlow,
- [09:44] só nos resta desejar bons estudos
- [09:46] para quem vai se aprofundar no mundo do Machine Learning.
- [09:49] Nós vamos ficando por aqui e até um próximo vídeo.
- [09:51] Tchau!

**On-screen content:** ![image: two presenters in lab coats with "Código Fonte TV" shirts](video-frame://57@08:34)

## [09:53] Conclusion

**Spoken content:**
- [09:53] Tchau!
- [09:53] Que bom que você ainda está aqui com a gente.
- [09:55] Muito obrigada por ficar até o finalzinho.
- [09:58] Aproveita quem gostou desse vídeo e assiste esse aqui do lado sobre Deep Learning.
- [10:02] Uma excelente sugestão, Gabriel.
- [10:04] Esse daí é um dos vídeos que também está repleto de informações
- [10:06] e que completa perfeitamente esse daqui.
- [10:08] Corre lá!
- [10:09] Vai lá!

**On-screen content:** ![image: two presenters in lab coats with "Código Fonte TV" shirts, with a suggested video thumbnail for "Deep Learning" on the right](video-frame://57@09:53)
