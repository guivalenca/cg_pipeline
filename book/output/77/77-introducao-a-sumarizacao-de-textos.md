---
id: "77"
title: "Introdução à sumarização de textos"
source_title: "Processamentos de Linguagem Natural"
resource_code: "9786556900575"
scope_kind: "pages"
scope_value: "pages 161-172"
final_url: "https://integrada.minhabiblioteca.com.br/reader/books/9786556900575/pageid/171"
captured_at: "2026-05-12T08:15:05.526462Z"
---

# Introdução à sumarização de textos
## Page 161

Reader pageid: 160

### Reader text

Introdução à sumarização de textos

Objetivos de aprendizagem Ao final deste texto, você deve apresentar os seguintes aprendizados:

„ Definir os objetivos da sumarização de textos. „ Descrever os processos de um algoritmo de sumarização de textos. „ Analisar algoritmos de sumarização de textos.

Introdução

O grande volume de conhecimento humano disponível exige cada vez mais a utilização de ferramentas automatizadas a fim de armazenar, organizar e recuperar informações. Nesse sentido, empregamos a sumarização de textos para organizar

de maneira lógica informações sobre diferentes coleções de dados, nas quais podem ser realizadas pesquisas de maneira facilitada por conta de seus resumos. Para aumentar a eficiência e otimizar o tempo na realização desses sumários ou resumos, a área de pesquisa do processamento de linguagem natural vem desenvolvendo e aprimorando métodos de automatização desses processos, por meio de algoritmos empregados na sumarização automática de textos (SAT). Neste capítulo, você estudará sobre os conceitos e os objetivos da su-marização de textos, além de conhecer a SAT e exemplos de sua aplicação.

1 Objetivos da sumarização de textos

Sumarizar ou resumir textos constitui uma prática comum na vida de estudan-tes de diferentes níveis, como do médio ao superior, casos em que os textos representam parte importante na elaboração de trabalhos ou de pesquisas acadêmicas. Mas os textos servem, de modo geral, para comunicar a respeito de determinado assunto, tanto na vida profissional quanto pessoal das pessoas.

## Page 162

Reader pageid: 161

### Reader text

162 Introdução à sumarização de textos

Os sumários ou resumos dos textos também são textos, motivo pelo qual constituem, do mesmo modo, uma forma de se comunicar. Diferentemente dos textos do meio acadêmico, textos postados em pá-ginas da internet em geral não apresentam um resumo ou a definição de palavras-chave para que o leitor tenha uma visão inicial do seu conteúdo. Nessa perspectiva, uma forma de contribuir na melhoria da representação, na mediação, na recuperação e no uso das informações consiste em possibilitar que as páginas tenham um resumo, tornando o primeiro contato do leitor mais produtivo, além de auxiliar na decisão de ler ou não o documento completo (SOUZA et al., 2017). Tendo em vista a abundância de informações sobre diferentes assuntos dis-poníveis na internet, condensá-las na forma de um resumo traz benefícios para vários usuários. Nesse sentido, existe um interesse crescente da comunidade de pesquisa em linguagem natural em desenvolver abordagens para resumir automaticamente o texto. Os sistemas de sumarização automática de texto dão origem a um texto de tamanho curto que inclui informações importantes do documento (GAMBHIR; GUPTA, 2016). Os objetivos da sumarização se classificam principalmente em dois pontos

de vista: o do leitor, portanto o usuário do sumário; e do produtor, o escritor. Assim, o foco da sumarização textual consiste em escrever um texto conden-sado que transmita ou comunique somente o que é importante de determinada fonte de informação, preservando a ideia central do texto (RINO; PARDO, 2003). Compreende-se que os resumos são ferramentas de acessibilidade in-formacional, considerando a grande quantidade de informação disponível. E, para que sejam gerados em tempo hábil para sua efetiva utilização, precisam sê-lo de forma automática, motivo pelo qual esse processo, quando realizado por sistemas de informação, é chamado de sumarização automática de textos (SAT) (SOUZA et al., 2017). Sistemas utilizados para realizar a sumarização automática de textos pre-cisam produzir um resumo conciso e fluente, que transmita as informações principais, identificando as frases mais importantes na entrada dos dados (um único documento ou uma coleção de documentos relacionados) e agru-pando-as para formar um resumo (NENKOVA; MCKEOWN, 2012). Portanto, a sumarização pode ser empregada em diferentes casos, como em notícias, artigos científicos ou prontuários de pacientes de um hospital.

## Page 163

Reader pageid: 162

### Reader text

Introdução à sumarização de textos 163 De acordo com Rino e Pardo (2003), a SAT refere-se ao uso de um sistema

com o objetivo de produzir uma representação condensada de determinado conteúdo de entrada, para que a informação mais importante seja consumida pelos usuários. Para isso, o sistema que realiza a SAT deve identificar, em um texto ou em um conjunto de informações, o que é relevante, estruturando o resumo em unidades informativas correspondentes para que este seja coe-rente e consistente. A seguir, apresentamos um exemplo com dois textos: o primeiro é o texto-fonte e o segundo, um sumário criado com utilização de um sistema de SAT.

Texto-fonte: Os apaixonados receberam hoje uma boa notícia dos cardiologistas: o amor faz bem ao coração. Enquanto os apaixonados enviavam cartas e rosas vermelhas em comemoração ao

Dia dos Namorados (dia de São Valentim, comemorado em muitos países), a Federação Mundial do Coração (WHF, na sigla em inglês) divulgou um comunicado pedindo aos casais de todo o mundo que demonstrem suas emoções com liberdade. “Os namorados têm outra razão para comemorar porque estudos mostram que estar apaixonado e ser correspondido nos ajuda a manter a saúde e é particularmente bom para nossos corações”, afirma o comunicado do WHF, que tem sua sede em Genebra, na Suíça. A federação, cujo objetivo é combater doenças cardíacas e reúne 166 socieda-des de cardiologia de 97 países, também acrescentou que o amor reduz o estresse,

a depressão e a ansiedade — três fatores de risco associados às doenças do coração. “Uma em cada três mortes no mundo ocorrem devido a problemas no coração e

derrame, seis vezes superior do que as mortes associadas à Aids”, afirmou o professor Philip Poole-Wilson, cardiologista do Imperial College, em Londres, e presidente da

federação. “É por essa razão que estamos ressaltando a importância de adotar um estilo de

vida saudável e o impacto positivo que o amor pode ter para a saúde.” De acordo com a WHF, muitos estudos publicados demonstraram que fatores psi-cológicos, assim como os físicos, estão envolvidos com a doença cardíaca. Em uma pesquisa de cinco anos, 10 mil homens com risco elevado de desenvolver angina (dor no peito) foram questionados se a mulher com quem estavam demonstrava seu amor por eles. Aqueles que responderam “sim” tinham a metade do risco de apresentar a condição.

## Page 164

Reader pageid: 163

### Reader text

164 Introdução à sumarização de textos

Sumário: Enquanto os apaixonados enviavam cartas e rosas vermelhas em comemoração ao Dia dos Namorados (dia de São Valentim, comemorado em muitos países), a Federação Mundial do Coração (WHF, na sigla em inglês) divulgou um comunicado pedindo aos casais de todo o mundo que demonstrem suas emoções com liberdade. A federação, cujo objetivo é combater doenças cardíacas e reúne 166 sociedades de

cardiologia de 97 países, também acrescentou que o amor reduz o estresse, a depressão e a ansiedade — três fatores de risco associados às doenças do coração. Fonte: Pardo (2008).

Como existem diferentes utilidades para algoritmos de SAT, estes podem

ser classificados conforme a sua aplicação. Pardo (2008) aponta que o processo de sumarização pode ser classificado conforme o número de textos proces-sados em monodocumento, que produz um sumário de uma única fonte de texto, e em multidocumento, que tem como fonte do sumário uma coleção de textos. Nesse sentido, os algoritmos multidocumentos demonstram-se muito importantes, pelo grande número de informações que conseguem processar. Sobre a formação dos sumários, eles podem ser classificados em extratos

(ou extrativos), compostos somente por trechos do texto-fonte que não foram alterados, e em abstratos (ou abstrativos), que apresentam trechos ou todas as suas partes reescritas, e, portanto, podem modificar a estrutura ou o significado dos trechos extraídos (PARDO, 2008). Os métodos abstratos de sumários são altamente complexos, pois precisam

de extenso processamento de linguagem natural. Portanto, a comunidade de pesquisa tem se concentrado mais em resumos extrativos, tentando obter resumos mais coerentes e significativos. Várias abordagens extrativas foram desenvolvidas nos últimos anos para a geração automática de resumos que programam diferentes técnicas de aprendizado de máquina e otimização (GAMBHIR; GUPTA, 2016). Outra classificação possível é a de sumários indicativos e informativos,

em que os primeiros não podem substituir os textos que serviram como fonte, visto que não preservam necessariamente todo o seu conteúdo, conclusões e estrutura, transmitindo apenas uma ideia vaga do texto-fonte, e os segundos mantêm os conteúdos principais do texto-fonte, o que dispensa sua leitura para saber o assunto a que se refere (RINO; PARDO, 2003).

## Page 165

Reader pageid: 164

### Reader text

Introdução à sumarização de textos 165 Por esses motivos, os sumários indicativos podem ser empregados para

classificar documentos bibliográficos, por exemplo, indicando o conteúdo de maneira sucinta para agilizar o acesso às informações, enquanto os informa-tivos, como o próprio nome diz, são mais informativos para o usuário, pois resultam em uma quantidade maior de informações. Contudo, o seu resultado dependerá da avaliação do usuário, a fim de verificar se as suas necessidades foram atendidas, motivo pelo qual os sumários indicativos podem ser consi-derados mais fáceis de produzir automaticamente, embora com uma utilidade mais limitada que dos informativos (RINO; PARDO, 2003). Quanto aos destinatários dos sumários, eles se classificam como genéricos,

que apresentam as informações mais importantes dos textos-fontes, sem uma preocupação explícita com seus usuários, e como sumários orientados ao interesse dos usuários, que trazem as informações de maneira customizada, de acordo com o conhecimento dos usuários. Por exemplo, se o usuário for leigo no assunto a ser sumarizado, é mais útil um sumário com informações contextuais, mas, para um usuário especialista no assunto, é mais interessante que tenha somente informações novas ou essenciais do texto (PARDO, 2008). Existe ainda a classificação que divide a sumarização em supervisionada,

considerada uma tarefa de classificação e identificação das sentenças que serão incluídas no resumo, por meio do treinamento do algoritmo, e não supervisionada, que não precisa de amostras para ser empregada, utilizando algoritmos especializados para marcar as sentenças nos documentos, por meio da combinação de um conjunto de características especificado previamente (PARDO, 2008).

2 Processos da sumarização de textos

Para facilitar a compreensão sobre a utilização dos algoritmos de SAT, con-vém apresentar os processos que o compõem: a representação intermediária, a pontuação de sentenças, a seleção de sentenças e a reformulação de sentenças. Basicamente, cria-se uma representação intermediária da entrada que captura somente os aspectos principais do texto; depois, pontuam-se as sentenças baseadas na representação inicial e se seleciona um sumário composto por várias sentenças, e, por fim, há a reformulação ou paráfrase do conteúdo (NENKOVA; MCKEOWN, 2012).

## Page 166

Reader pageid: 165

### Reader text

166 Introdução à sumarização de textos Mesmo os sistemas mais simples derivam alguma representação inter-mediária do texto que precisam resumir. As abordagens de representação de tópicos convertem o texto em uma representação intermediária interpretada como o(s) tópico(s) discutido(s) no texto. Alguns dos métodos de resumo mais populares contam com representações de tópicos, e essa classe de abordagens exibe uma variação de representação, incluindo abordagens de frequência e representação de tópicos. Essa representação de tópicos consiste na definição de uma tabela simples de palavras com seus pesos correspondentes (NENKOVA; MCKEOWN, 2012). Depois da criação de uma representação intermediária, cada frase recebe

uma pontuação que indica sua importância. Para abordagens de representação de tópicos, a pontuação de sentenças está geralmente relacionada à quão bem uma frase expressa alguns dos tópicos mais importantes do documento ou até que ponto combina informações sobre diferentes tópicos. Para a maioria dos métodos de representação de indicadores, o peso de cada sentença é de-terminado a partir da combinação das evidências dos diferentes indicadores, geralmente usando técnicas de aprendizado de máquina para descobrir os pesos dos indicadores (NENKOVA; MCKEOWN, 2012). Na terceira etapa, o sistema de sumarização deve selecionar as sentenças

que formem a melhor combinação de frases importantes para um resumo, com o tamanho almejado. Nas melhores abordagens, as sentenças mais importantes, respeitando o comprimento de resumo desejado, são selecionadas para formar o resumo. Em cada etapa do procedimento, a pontuação da importância de cada sentença é recalculada como uma combinação linear entre o peso da importância original da sentença e sua similaridade com as frases já escolhidas. Frases semelhantes às frases já escolhidas são desprezadas. Nas abordagens de seleção global, a coleção ideal de sentenças é selecionada sujeita a restrições que tentam maximizar a importância geral, minimizar a redundância e, para algumas abordagens, maximizar a coerência (NENKOVA; MCKEOWN, 2012). A etapa posterior, a reformulação das sentenças, somente será aplicada nos casos em que se realiza a sumarização abstrativa. Na Figura 1, é apresentado um esquema dos processos que envolvem a SAT.

## Page 167

Reader pageid: 166

### Reader text

Introdução à sumarização de textos 167

Texto fonte

Síntese/ seleção de sentenças

Reformulação de sentenças

Análise/

representação intermediária

Figura 1. Etapas da SAT. Fonte: Adaptada de Pardo (2008).

Transformação/ pontuação de sentenças

Sumário Pardo (2008) apresenta as etapas da sumarização com outras nomenclaturas,

mas com o mesmo resultado: para ele, a primeira etapa é a análise, na qual um ou mais textos-fonte são processados e se produz uma representação interna de todo o conteúdo; a segunda a transformação, que realiza a sumarização sobre o resultado da representação interna do conteúdo, o que produz uma representação interna do sumário; e a terceira a síntese, a representação em linguagem natural da sumarização interna ao usuário. O resultado da sumarização é guiado pela taxa de compressão, ou seja,

o tamanho definido pelo usuário para o sumário. Por exemplo, um sumário com taxa de compressão de 60% dará origem a um resumo com o equivalente a 40% do tamanho (em número de palavras) do texto-fonte. Existem poucas dependências relacionadas às etapas de processamento

descritas, como o fato de um resumo poder incorporar qualquer combinação de opções específicas sobre como executar as etapas e as alterações na maneira como uma etapa específica é executada conseguirem alterar o desempenho do algoritmo de SAT. Ao classificar a importância das frases para resumos, outros fatores também precisarão ser avaliados. Informações sobre o contexto em que o resumo é gerado podem ajudar a determinar a importância e a pontuação das palavras e sentenças (NENKOVA; MCKEOWN, 2012).

## Page 168

Reader pageid: 167

### Reader text

168 Introdução à sumarização de textos O contexto, uma fonte de informação sobre as necessidades do usuário,

geralmente apresentadas por meio de uma consulta, pode incluir o ambiente em que um documento de entrada está situado, como os links que apontam para uma página da web. Outro fator que afeta a classificação das frases é o gênero de um documento — se o documento de entrada é um artigo de notícias, um tópico de e-mail, uma página da internet ou um artigo de jornal, pode-se empregar diferentes influências nas estratégias usadas para selecionar frases (NENKOVA; MCKEOWN, 2012). As etapas da SAT não dependem das classificações apresentadas anterior-mente, mas podem ser adaptadas conforme a metodologia seguida. Há casos em que as etapas de análise e síntese podem ser simplificadas ou inexistentes, como o fato de somente contar a frequência de palavras em um texto, ou mais complexas. Essa definição também pode ser feita na etapa de transformação, assim como o caso de incluir a etapa de reformulação de sentenças somente na sumarização abstrativa (PARDO, 2008).

3 Algoritmos de sumarização de textos

A SAT tem duas características essenciais: os sumários remetem diretamente aos seus textos-fonte e precisam ser construídos de maneira que não haja perda do significado original da fonte de informações, mesmo que o sumário apresente um número limitado de palavras, com diferentes estruturas. Assim, os sumários são textos elaborados com base em outros textos e suas corres-pondentes representações, servindo como indexadores ou substitutos destes (RINO; PARDO, 2003). A seguir, apresentaremos um exemplo de sumarização na linguagem Phyton

de uma notícia de um portal da internet. As expressões levam em conta o uso das bibliotecas NLTK e BeautifulSoap. O exemplo está dividido em dez partes, apresentadas em sequência e intercaladas com as suas devidas interpretações. O exemplo inicia com a importação das funções Request e urlopen da

biblioteca urllib.request, que, no Python 2, é a urllib2. Na segunda parte, as funções são utilizadas para ler uma notícia do portal Último Se-gundo, sendo as informações armazenadas em uma variável chamada pagina. A terceira etapa consiste em utilizar o BeautifulSoap para verificar as palavras mais importantes da notícia, com a leitura feita por meio da id=noticia disponível no código do portal (LIMA, 2017).

## Page 169

Reader pageid: 168

### Reader text

Introdução à sumarização de textos 169

1. Importação das funções Request e urlopen da biblioteca urllib.request: from urllib.request import Request, urlopen 2. Utilização das funções para ler uma notícia de um portal de notícias:

Link = Request(‘https://delas.ig.com.br/2020-01-23/nao-e--mito-o-estresse-pode-ser-a-causa-dos-seus-cabelos-bran-cos.html’,headers={User-Agent’: ’Mozilla/5.0’})

Pagina = urlopen (link).read().decode(‘utf-8’, ‘ignore’)

3. Utilização do BeautifulSoap para verificar na página da notícia apenas os tópicos essenciais:

from bs4 import BeautifulSoup soup = BeautifulSoup(pagina, “lxml”) texto = soup.find(id=”noticia”).text Fonte: Lima (2017).

4. Tokenização com a biblioteca NLTK e divisão de sentenças e palavras:

from nltk.tokenize import Word_tokenize from nltz.tokenize import sent_tokenize sentenças = sent_tokenize(text) palavras = Word_tokenize(texto.lower())

5. Eliminação das stopwords da lista de palavras: from nltk.corpus import stopwords from string import punctuation

stopwords = set (stopwords.words(‘portugueses’) + list(punctuation)) palavras_sem_stopwords = [palavras for palavras in palavras if palavras not in stopwords] Fonte: Lima (2017).

## Page 170

Reader pageid: 169

### Reader text

170 Introdução à sumarização de textos A quarta etapa refere-se à aplicação do processamento sobre linguagens

naturais para tratamento do texto da notícia — a chamada tokenização, com-plementada pela divisão do texto em sentenças e em palavras. Já a etapa seguinte do exemplo trata de identificar as palavras de ligação do texto, que não complementam o seu sentido: as stopwords, em um processo que auxilia na posterior análise das sentenças. Já as palavras sem as stopwords são arma-zenadas na variável palavras_sem_stopwords (LIMA, 2017).

6. Criação da distribuição de frequência com a função FreqDist: from nltk.probability import FreqDist frequencia = FreqDist (palavras_sem_stopwords)

7. Criação de escala para as sentenças, de acordo com as palavras importantes que se repetem nelas:

from collections import defaultdict sentenças_importantes = defaultdict(int) 8. Criação de looping para coletar as estatísticas de cada sentença: for i, sentença in enumerate(sentenças):

for palavra in word_tokenize(sentenca.lower()): if palavra in frequencia: sentencas_importantes[i] += frequencia[palavra]

Fonte: Lima (2017). Na parte seis, verifica-se a frequência das palavras, a fim de definir quais

são as mais importantes para a compreensão de seu conteúdo. A etapa seguinte separa as sentenças mais importantes com base na quantidade de vezes em que as palavras mais importantes são repetidas nelas. O dicionário utilizado não lança uma exceção quando a chave for inexistente, mas adiciona a chave ao próprio dicionário. Na oitava parte do exemplo, o dicionário é povoado por meio do looping criado para passar por todas as sentenças a fim de coletar todas as estatísticas das instruções anteriores (LIMA, 2017).

## Page 171

Reader pageid: 170

### Reader text

Introdução à sumarização de textos 171

9. Seleção das sentenças mais importantes do dicionário: from heapq import nlargest idx_sentencas_importantes = nlargest(4, sentenças_impor-tantes, Sentenças_importantes.get) 10. Criação do resumo/sumário:

for i in sorted(idx_sentencas_importantes): print(sentenças[i])

Fonte: Lima (2017). Por fim, na parte nove, é possível selecionar as quatro sentenças mais im-portantes do dicionário, número que deve ser definido conforme a necessidade do usuário. E a etapa 10 solicita que o resumo elaborado seja apresentado em tela (LIMA, 2017), a partir do qual se tem um resumo da notícia referenciada no link da etapa dois do exemplo. Esta é apenas uma das possibilidades de realizar a sumarização, feita em um único texto-fonte, que serve como base para a compreensão dos conceitos abordados.

Você viu ao longo deste capítulo diferentes conceitos sobre a sumarização automática de textos e sua aplicação na linguagem Python. Acessando o site IBM developer, você pode conhecer mais conceitos e exemplos sobre a biblioteca NLTK, a Python e o Aprendizado por Máquina.

## Page 172

Reader pageid: 171

### Reader text

172 Introdução à sumarização de textos

GAMBHIR, M.; GUPTA, V. Recent automatic text summarization techniques: a survey. Ar-tificial Intelligence Review, [s. l.], v. 47, n. 1, 2016. Disponível em: https://www.researchgate. net/publication/299499824_Recent_automatic_text_summarization_techniques_a_ survey. Acesso em: 05 mar. 2020.

LIMA, V. R. Utilizando o processamento de linguagem natural para criar uma sumarização automática de textos. 2017. Disponível em: https://medium.com/@viniljf/utilizando--processamento-de-linguagem-natural-para-criar-um-sumariza%C3%A7%C3%A3o--autom%C3%A1tica-de-textos-775cb428c84e. Acesso em: 05 mar. 2020.

NENKOVA, A.; MCKEOWN, K. A survey oftext summarization techniques. 2012. Disponível em: https://www.cs.bgu.ac.il/~elhadad/nlp16/nenkova-mckeown.pdf. Acesso em: 05 mar. 2020.

PARDO, T. A. S. Sumarização automática: principais conceitos e sistemas para o por-tuguês brasileiro. São Paulo: Núcleo Interinstitucional de Linguística Computacional USP, 2008. Disponível em: https://sites.icmc.usp.br/taspardo/NILCTR0804-Pardo.pdf. Acesso em: 05 mar. 2020.

RINO, L. H. M.; PARDO, T. A. S. A Sumarização automática de textos: principais caracte-rísticas e metodologias. In: CONGRESSO DA SOCIEDADE BRASILEIRA DE COMPUTAÇÃO, 23., 2003; JORNADA DE MINICURSOS DE INTELIGÊNCIA ARTIFICIAL, 3., 2003, Campinas. Anais [...]. Campinas: USP, 2003. p. 203–245. Disponível em: https://sites.icmc.usp.br/ taspardo/JAIA2003-RinoPardo.pdf. Acesso em: 05 mar. 2020.

SOUZA, O. et al. Um método de sumarização automática de textos através de dados estatísticos e processamento de linguagem natural. Informação & Sociedade, João Pessoa, v. 27, n. 3, p. 307–320, 2017.

Todos os links para sites da web fornecidos neste capítulo foram testados, o que levou à comprovação de seu funcionamento no momento da publicação do material. No entanto, pelo fato de a rede ser extremamente dinâmica e suas páginas estarem constantemente mudando de local e conteúdo, os editores declaram não ter qualquer responsabilidade sobre a qualidade, a precisão ou a integralidade das informações referidas em tais links.
