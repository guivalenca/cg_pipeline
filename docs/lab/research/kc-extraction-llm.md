# Extração automática de Knowledge Components e learning objectives com LLMs (2023 a 2026)

Relatório de revisão de literatura. Escopo: estado da arte em geração/extração automática de Knowledge Components (KCs, no sentido do framework KLI de Koedinger, Corbett e Perfetti, 2012) e de learning objectives a partir de texto instrucional, usando LLMs.

Data da revisão: julho de 2026. Método: busca web e leitura direta dos papers (o L@S '24 de Moore et al. foi lido integralmente em PDF; os demais via abstract, HTML do arXiv ou página de proceedings). Onde só tive acesso a abstract ou resumo, sinalizo no texto.

---

## 1. O trabalho de Steven Moore, John Stamper e colaboradores (CMU)

### 1.1 Paper central: geração e tagging de KCs a partir de MCQs

**Referência.** Steven Moore, Robin Schmucker, Tom Mitchell, John Stamper (2024). *Automated Generation and Tagging of Knowledge Components from Multiple-Choice Questions*. Proceedings of ACM Learning @ Scale (L@S '24), Atlanta, GA. DOI 10.1145/3657604.3662030. Preprint: https://arxiv.org/abs/2405.20526

Este é o trabalho de referência mais detalhado do grupo sobre o tema, e vale a pena descrevê-lo com precisão porque o desenho experimental tem implicações diretas para o nosso pipeline.

**Ponto de partida importante para nós:** o input deles NÃO é texto de ensino corrido. É um item de avaliação já pronto (uma MCQ com enunciado, alternativas e gabarito). Eles geram o KC *a partir da questão*, não a partir da fonte que ensina. O único contexto adicional fornecido ao modelo é o nível educacional (undergraduate ou master's) e a área (Chemistry ou E-Learning). Essa escolha foi deliberada: eles queriam um método generalizável que não dependesse de ter o material-fonte disponível.

**Datasets.** Dois cursos de MOOC de ensino superior:
- Chemistry (curso introdutório de graduação, plataforma OLI/Torus, DataShop dataset 4640): 80 MCQs, 40 KCs, exatamente 2 MCQs por KC.
- E-Learning (curso de mestrado, DataShop dataset 5843): 80 MCQs, 40 KCs, mesma estrutura.

O gold standard são os KCs atribuídos pelos próprios autores/especialistas que criaram os cursos. Critério de seleção das questões: cada uma tinha que mapear para exatamente um KC.

Modelo: `gpt-4-0125-preview`, escolhido explicitamente por estabilidade/reprodutibilidade (evitar drift da API padrão do GPT-4).

**Método de prompting: NÃO é extração direta em um passo.** São duas estratégias, cada uma com uma cadeia de **três prompts** encadeados:

*Estratégia A, "simulated expert"* (tree-of-thought):
1. Prompt 1: simular três especialistas colaborando, verbosamente, para determinar quais componentes de conhecimento e habilidades a questão avalia; os personas são descritos como "brilliant, logical, detail-oriented, nit-picky", refinam as falas uns dos outros e param quando há uma lista definitiva de cinco itens.
2. Prompt 2: reescrever essa lista de cinco pontos começando com verbos de ação da Taxonomia de Bloom revisada. Detalhe metodológico relevante: eles fazem esse alinhamento a Bloom **depois** da geração, de propósito. Em piloto, colocar Bloom no prompt inicial degradou a qualidade, porque o modelo passava a gerar habilidades em torno de "understand", "apply", "analyze" para satisfazer os níveis da taxonomia em vez de descrever o conteúdo.
3. Prompt 3: selecionar, dos cinco pontos, o mais relevante para a questão.

*Estratégia B, "simulated textbook"*:
1. Prompt 1: "esta questão apareceu num livro-texto de {subject} para {context}; que cinco tópicos domain-specific e de baixo nível a página cobriria?"
2. Prompt 2: reescrever com verbos de Bloom, mantendo domain-specific, low-level e detalhado.
3. Prompt 3: selecionar o mais relevante.

Em ambas, o desenho de saída é o mesmo: gera-se um **top-5 de candidatos** e depois se escolhe um. Ou seja, mesmo o "single KC" final é produto de uma geração ampla seguida de seleção, não de uma extração direta.

**Custo reportado (Tabela 1 do paper).** 160 MCQs por estratégia: expert = 462.880 tokens totais (307.680 prompt, 155.200 completion), USD 8,00; textbook = 436.480 tokens, USD 8,00. Indução de ontologia: Chemistry 104.548 tokens, USD 3,34; E-Learning 87.742 tokens, USD 2,83. São valores de 2024 para GPT-4 preview.

**Avaliação, parte 1: match direto com o KCM humano.**

| Métrica | Chemistry Expert | Chemistry Textbook | E-Learning Expert | E-Learning Textbook |
|---|---|---|---|---|
| Match direto | 42/80 (52%) | 45/80 (56%) | 28/80 (35%) | 28/80 (35%) |
| KC humano no top-5 do LLM | 64/80 (80%) | 63/80 (79%) | 45/80 (56%) | 50/80 (63%) |
| Match exclusivo daquela estratégia | 9/80 (11%) | 12/80 (15%) | 9/80 (11%) | 9/80 (11%) |
| Match por ambas as estratégias | 33/80 (41%) | | 19/80 (24%) | |

Teste z de duas proporções comparando textbook em Chemistry (52%, note a discrepância com a tabela, o texto do paper cita 42/80 aqui) contra E-Learning (35%): Z = 2,698, p = 0,007. A diferença entre domínios é significativa.

Consistência por KC (cada KC tem 2 MCQs): em Chemistry, ambas as MCQs foram casadas corretamente em 15/80 (19%), apenas uma em 15/80 (19%), nenhuma em 10/80 (13%). Em E-Learning: ambas em 7/80 (9%), uma em 14/80 (18%), nenhuma em 19/80 (24%). Chi-quadrado de independência entre domínio e categoria de match: X²(2, N=160) = 5,737, p = 0,057 (não significativo).

Falha total (o KC humano não aparece nem no top-5): 21% em Chemistry, 38% em E-Learning.

**Avaliação, parte 2: preferência humana nos casos de discordância.**

Só para os mismatches da estratégia textbook (35 MCQs em Chemistry, 52 em E-Learning). Três especialistas por domínio. Em Chemistry, recrutados via Prolific com bacharelado em Química; em E-Learning, instructional staff do próprio curso que não participaram da criação do KCM original. Survey em Google Forms, ordem de questões e ordem de apresentação dos dois rótulos randomizadas. Critérios de julgamento alinhados ao framework KLI: clareza, relevância direta ao conteúdo, acurácia factual, e capacidade de transferir/integrar o conhecimento para outros contextos. Tarefa de ~28 min (Chemistry, USD 10) e ~32 min (E-Learning, USD 15).

Controle metodológico importante: os KCs gerados por LLM eram sistematicamente mais verbosos que os humanos, o que é um confound de apresentação. Eles usaram um prompt adicional para reescrever cada KC do LLM limitando o comprimento a no máximo 1,5x a contagem de palavras do KC humano correspondente.

Resultados:
- Chemistry: LLM preferido em 23/35 (66%), humano em 12/35 (34%). Acordo de maioria (2 de 3) em 25/35 (71%); unanimidade em 10/35 (29%).
- E-Learning: LLM preferido em 32/52 (62%), humano em 20/52 (38%). Maioria em 34/52 (65%); unanimidade em 18/52 (35%).
- Agregado: teste binomial bicaudal, LLM preferido em 57/87 MCQs, p = 0,017.
- Todos os seis avaliadores individualmente preferiram os rótulos do LLM.

**Avaliação, parte 3: indução de ontologia de KCs (Algorithm 1).**

Este é o pedaço mais próximo do que queremos fazer. O problema que motiva: duas questões que avaliam o mesmo KC recebem rótulos semanticamente corretos mas com wording diferente ("Apply Boyle's law" vs "Examine Boyle's Law" vs "Utilize Boyle's Law"), o que produz redundância no KCM.

O algoritmo é um particionamento hierárquico recursivo, top-down, feito inteiramente por prompts (sem embeddings, sem clustering numérico):
- Começa com todas as questões num único grupo.
- A cada passo, para cada grupo: prompt "DETERMINE KCs" pede ao modelo que atue como educador, olhe a lista de questões e as agrupe por learning objectives, com cada questão em exatamente um grupo, retornando nome do grupo (o learning objective) e a lista de questões.
- Depois, um prompt separado "CLASSIFY QUESTION" atribui cada questão individualmente ao learning objective mais relevante da lista. Eles observaram que usar diretamente o particionamento do primeiro prompt falha com listas grandes (>50 questões): o GPT-4 omite questões ou coloca a mesma questão em vários grupos. O passo de classificação explícita resolve isso. **Este é um achado prático diretamente reutilizável.**
- Recorre até que os learning objectives fiquem de granularidade fina demais ou até que um grupo tenha só uma questão.

Métricas propostas (não requerem dados de aluno, apenas o gold KCM):
- *grouping accuracy*: proporção de pares de questões do mesmo KC que estão co-localizadas em algum grupo.
- *grouping refinement*: número médio de KCs distintos por grupo, normalizado. Refinement 1 é o ótimo.

Resultados: Chemistry converge em 6 iterações para 63 KCs (gold: 40), com accuracy 0,65 e refinement 0,804. E-Learning converge em 5 iterações para 63 KCs (gold: 40), accuracy 0,175 e refinement 0,848. As curvas (Figura 8) mostram o trade-off clássico: accuracy cai monotonicamente e refinement sobe monotonicamente conforme se desce na árvore. Os autores explicitam que o expert pode simplesmente parar o algoritmo mais cedo para escolher a granularidade desejada, ou seja, **granularidade vira um parâmetro de corte na árvore, não uma propriedade do prompt.**

**Limitações e modos de falha declarados pelos autores.**
- Sensibilidade extrema ao wording do prompt.
- "A definição de um KC 'bom' ainda não é clara", o que torna a avaliação dependente de julgamento individual; subjetividade humana alta mesmo com rubrica.
- Viés para generalização: o LLM tende a escolher opções gerais em vez de precisas e domain-specific quando há jargão de domínio presente.
- Cobertura de domínio: E-Learning (nicho, sub-representado no treino) teve desempenho bem pior que Chemistry (bem representado). Nossa expectativa de performance deve ser condicionada à popularidade do domínio.
- Escopo restrito a dois domínios e a MCQs; eles próprios apontam short-answer e outros formatos como trabalho futuro.
- Eles observam honestamente que o gold KCM humano pode estar errado: para E-Learning, sugerem que o KCM do expert "contém imprecisões e é de qualidade inferior", o que penaliza artificialmente as métricas.
- Recomendação final dos autores: os rótulos do LLM são um **primeiro passe preliminar** para um sistema human-in-the-loop, não um substituto do expert.

### 1.2 O resto do programa de pesquisa do grupo

O paper de 2024 não é isolado. Ele é a versão LLM de uma linha que o grupo vinha tocando com crowdsourcing e topic modeling, e está cercado por uma linha paralela sobre *avaliação automática da qualidade de questões*, que é justamente o que precisamos se formos gerar tarefas de avaliação como estágio intermediário.

**Linha A, KCs por crowdsourcing e topic modeling (pré-LLM):**
- Steven Moore, Huy A. Nguyen, John Stamper (2020). *Towards Crowdsourcing the Identification of Knowledge Components*. L@S '20. https://stevenjamesmoore.com/assets/papers/las20_wip_moore.pdf
- Moore, Nguyen, Stamper (2020). *Evaluating Crowdsourcing and Topic Modeling in Generating Knowledge Components from Explanations*. AIED 2020.
- Moore, Nguyen, Stamper (2020). *Utilizing Crowdsourcing and Topic Modeling to Generate Knowledge Components for Math and Writing Problems*. ICCE 2020.
- Moore, Nguyen, Stamper (2022). *Leveraging Students to Generate Skill Tags that Inform Learning Analytics*. ISLS 2022. https://stevenjamesmoore.com/assets/papers/isls22_full_moore.pdf

O achado que o paper de 2024 herda dessa linha: crowdworkers "têm dificuldade em atingir a especificidade necessária para definir KCs com precisão". Isto é, o problema difícil nunca foi *produzir texto que descreve uma habilidade*; foi produzir texto na **granularidade certa e consistente**. Vale internalizar: granularidade é o eixo de falha primário, não fluência.

**Linha B, avaliação automática da qualidade de itens (diretamente aplicável ao nosso estágio de geração de tarefas):**
- Moore, Nguyen, Bier, Domadia, Stamper (2022). *Assessing the Quality of Student-Generated Short Answer Questions Using GPT-3*. EC-TEL 2022.
- Moore, Nguyen, Chen, Stamper (2023). *Assessing the Quality of Multiple-Choice Questions Using GPT-4 and Rule-Based Methods*. EC-TEL 2023.
- Moore, Costello, Nguyen, Stamper (2024). *An Automatic Question Usability Evaluation Toolkit* (SAQUET). AIED 2024. Ferramenta open-source que combina GPT-4, word embeddings e transformers de complexidade textual para aplicar automaticamente uma rubrica de **19 critérios de Item-Writing Flaws (IWF)** a MCQs. Relevante porque nos dá um instrumento pronto para filtrar tarefas geradas antes de agrupá-las.
- Moore, Bier, Stamper (2024). *Assessing Educational Quality: Comparative Analysis of Crowdsourced, Expert, and AI-Driven Rubric Applications*. AAAI HCOMP 2024.

**Linha C, geração automática de questões a partir de material textual:**
- Nguyen, Moore, Stamper et al. (2022). *Towards Generalized Methods for Automatic Question Generation in Educational Domains*. EC-TEL 2022. https://stevenjamesmoore.com/assets/papers/ectel22_full_nguyen.pdf Pipeline de geração e avaliação de questões a partir de materiais textuais de um curso introdutório de data science.

**Linha D, learnersourcing e conteúdo gerado por IA:**
- Khosravi, Denny, Moore, Stamper (2023). *Learnersourcing in the Age of AI: Student, Educator and Machine Partnerships for Content Creation*. Computers and Education: Artificial Intelligence.
- Moore et al. (2023). *Empowering Education with LLMs: The Next-Gen Interface and Content Generation*. AIED 2023 workshop. https://stevenjamesmoore.com/assets/papers/aied23_workshop_moore.pdf

### 1.3 Continuação direta pelo grupo de Koedinger: o problema de redundância em escala

**Referência.** Canwen Wang, Jionghao Lin, Kenneth R. Koedinger (2025). *Leveraging Large Language Models for Identifying Knowledge Components*. Workshop "LLMs for Qualitative Analysis in Education" (LAK). https://arxiv.org/abs/2511.09935

Este é o teste de estresse do método de Moore et al. em escala maior, e o resultado é sóbrio.

- Método: exatamente a estratégia *simulated textbook* de três turnos, mas com `gpt-4o-mini`, aplicada a **646 MCQs** do dataset E-Learning (DataShop 5426).
- Resultado bruto: 646 questões geraram **569 KCs distintos**. O modelo especialista tem **101**. Ou seja, extração direta questão a questão produz um KCM com quase um KC por item, o que é inútil como modelo cognitivo.
- Mitigação: embeddings da API da OpenAI sobre os rótulos de KC, e merge por similaridade de cosseno acima de um limiar.

| Configuração | Nº de KCs | RMSE (AFM, 3-fold CV, item-blocked, média de 10 seeds) |
|---|---|---|
| Expert "LOs-new-MCQ" | 101 | 0,4206 |
| LLM sem merge | 569 | 0,4285 |
| Merge cosseno >= 0,9 | 511 | 0,4264 |
| Merge cosseno >= 0,8 | 428 | 0,4259 |
| Merge cosseno >= 0,7 | 273 | 0,4270 |

O limiar 0,8 é o ótimo, com melhora estatisticamente significativa sobre o LLM cru (t(18) = 5,13, p < 0,001). **Mas o modelo do especialista continua melhor que qualquer variante do LLM**, e por uma margem que nenhum limiar fecha. Note também que o RMSE é uma função em U rasa do limiar: mergear demais (0,7) volta a piorar.

Exemplo de redundância que eles dão: duas questões sobre random assignment recebem KCs separados só porque um deles ganhou a frase "in experimental design".

Conclusão relevante para nós: **merge por similaridade de embeddings sobre os rótulos textuais é um paliativo, não uma solução.** Ele opera sobre a superfície linguística do nome do KC, não sobre o que o KC realmente exige cognitivamente. Duas formulações do mesmo KC podem ter cosseno baixo, e dois KCs genuinamente distintos podem ter cosseno alto por compartilharem jargão de domínio.

### 1.4 Outra continuação do mesmo laboratório: KCluster

**Referência.** Yumou Wei, Paulo F. Carvalho, John Stamper (2025). *KCluster: An LLM-based Clustering Approach to Knowledge Component Discovery*. EDM 2025. https://arxiv.org/abs/2505.06469

Mesmo laboratório (Stamper), abordagem oposta: em vez de pedir ao LLM que *nomeie* o KC, usa-se o LLM apenas como **medidor de similaridade**, e o clustering faz o resto.

- Métrica proposta: *question congruity*, derivada de pointwise mutual information entre questões. Congruity(qs, qt) = ½[Δ(qs, qt) + Δ(qt, qs)], onde Δ é a diferença de log-probabilidade de uma questão com e sem a outra no contexto. A hipótese subjacente é que questões do mesmo KC tendem a co-ocorrer em materiais educacionais, então uma aumenta a verossimilhança da outra.
- LLM: **Phi-2 (2,7B)**, escolhido por ser open-source e expor log-probs. Não é preciso um modelo de fronteira.
- Clustering: **Affinity Propagation**, escolhido por não exigir número de clusters a priori e por aceitar medidas de similaridade não métricas.
- Datasets: ScienceQA (10.701 questões), E-learning 2022 (630 questões, 42.176 tentativas, 39 alunos), E-learning 2023 (497 questões, 44.065 tentativas, 41 alunos).

Resultados com AFM:

E-learning 2022:

| Modelo | Nº KCs | AIC | BIC | item-RMSE |
|---|---|---|---|---|
| LOs-new (expert) | 101 | 43.353,28 | 45.437,83 | 0,4236 |
| Question-emb (baseline de embeddings) | 91 | 43.880,70 | 45.792,27 | 0,4232 |
| KCluster | 114 | 43.424,56 | 45.734,00 | **0,4227** |

t(98) = -2,9963, p = 0,0035 contra o expert.

E-learning 2023:

| Modelo | Nº KCs | AIC | BIC | item-RMSE |
|---|---|---|---|---|
| v1-CTA (expert) | 75 | 43.434,50 | 45.077,55 | 0,4088 |
| Question-emb | 78 | 43.946,26 | 45.641,48 | 0,4108 |
| KCluster | 92 | 42.999,91 | 44.938,54 | **0,4071** |

t(98) = -5,0956, p < 0,001, e melhor BIC de todos os modelos.

Este é, até onde a literatura vai, **o primeiro resultado em que um KCM descoberto automaticamente bate o modelo do especialista em predição de desempenho de aluno**. Contraste direto com Wang/Lin/Koedinger (seção 1.3), onde extração direta com nomeação por LLM ficou abaixo do expert. A diferença metodológica é exatamente a que nos interessa: **agrupar primeiro, nomear depois** vence **nomear primeiro, deduplicar depois**.

Limitações declaradas: só MCQs; custo computacional quadrático no número de questões (congruity exige forward passes por par); dependência do template de prompt; datasets pequenos (<650 questões nos cursos com dados de aluno).

### 1.5 Learning objectives "atômicos" (granularidade como escolha de design)

**Referência.** Naiming Liu, Shashank Sonkar, Debshila Basu Mallick, Richard Baraniuk, Zhongzhou Chen (2024/2025). *Atomic Learning Objectives Labeling: A High-Resolution Approach for Physics Education*. arXiv:2412.09914; versão de conferência: *Atomic Learning Objectives and LLMs Labeling: A High-Resolution Approach for Physics Education*, LAK '25, DOI 10.1145/3706468.3706550.

Contribuição de design: um sistema de LOs "atômicos" com estrutura sintática forçada **subject-verb-object**, cobrindo nove capítulos de física introdutória universitária. Aplicado a 131 questões de bancos curados por especialistas e do OpenStax University Physics, cada questão rotulada com **1 a 8 LOs atômicos** (note: multi-label, ao contrário do single-KC de Moore et al.). Comparam várias estratégias de prompting e vários LLMs contra rotulação humana, e propõem um conjunto de métricas para a qualidade da rotulação.

O que importa para nós: eles atacam granularidade **restringindo a forma do output** (uma gramática fixa sujeito-verbo-objeto) em vez de pedir "seja específico". Isso é uma alavanca de engenharia de prompt mais confiável que adjetivos.

---

## 2. Outros grupos: KCs, skills, prerequisites e learning objectives de texto instrucional

A literatura se divide em quatro famílias com pouca conversa entre si. Vale mapear as quatro porque cada uma resolve um pedaço do nosso problema.

### 2.1 Família A: geração de learning objectives a partir de descrição de curso

**Pragnya Sridhar, Aidan Doyle, Arav Agarwal, Christopher Bogart, Jaromir Savelka, Majd Sakr (2023).** *Harnessing LLMs in Curricular Design: Using GPT-4 to Support Authoring of Learning Objectives*. arXiv:2306.17459 (também apresentado no contexto AIED 2023).

- Método: **prompt único, muito elaborado**, contendo guidelines detalhadas de como se escreve um bom LO (verbos de ação, níveis de Bloom, especificidade, mensurabilidade) mais exemplos few-shot.
- Escala: 127 LOs gerados automaticamente para um curso universitário de "AI Practitioner".
- Avaliação: análise de aderência a boas práticas de redação, e se o nível de Bloom era apropriado ao tipo de módulo (conceitual vs projeto).
- Resultado: os LOs eram "sensatos, bem expressos" e majoritariamente no nível certo de Bloom.
- Limitação honesta a registrar: **a avaliação é sobre a forma do LO, não sobre se o LO descreve corretamente o que a fonte ensina, nem sobre se o conjunto de LOs é completo ou não redundante.** É um estudo de qualidade de redação, não de validade cognitiva. É o modo de avaliação mais comum e mais fraco nesta família.

**Christian Lohr et al. (2025).** *Leveraging Large Language Models to Generate Course-Specific Semantically Annotated Learning Objects*. Journal of Computer Assisted Learning, 41. DOI 10.1111/jcal.13101. Geração de learning objects com anotação semântica a partir do material do curso.

**Paulina Gacek, Weronika T. Adrian (2025).** *Automated Curriculum Analysis Using Large Language Models and Knowledge Graphs*. Publicado em journal da SAGE, DOI 10.1177/17248035251360196. LLMs extraem conceitos centrais e relações de pré-requisito de texto não estruturado de ementas, ligando as entidades extraídas ao Wikidata para construir um grafo de conhecimento curricular. Interessante pelo *grounding* em uma ontologia externa como controle de alucinação e de granularidade.

### 2.2 Família B: prerequisite relations e educational knowledge graphs

Esta família é anterior aos LLMs e foi absorvida por eles. O objeto é o *grafo de conceitos com arestas de pré-requisito*, não o KC no sentido KLI (que é uma unidade de habilidade aferível, não um nó conceitual).

- **Mehmet Cem Aytekin, Yücel Saygın (2024).** *ACE: AI-Assisted Construction of Educational Knowledge Graphs with Prerequisite Relations*. Journal of Educational Data Mining. https://jedm.educationaldatamining.org/index.php/JEDM/article/view/737 Usa word embeddings para pontuar pares de conceitos, envia os pares de score alto para avaliação humana, e o grafo evolui com o feedback; pré-requisitos adicionais são inferidos por transitividade a partir dos já confirmados, reduzindo a carga do especialista. Resultado reportado: alunos que estudaram pares de conceitos na ordem de pré-requisito tiveram melhor taxa de sucesso. **O padrão de design "gerar candidatos por método barato, ranquear, mandar só o topo para humano, propagar por transitividade" é reutilizável.**
- **A Graph Neural Network Model for Concept Prerequisite Relation Extraction**. CIKM 2023, DOI 10.1145/3583780.3614761. Baseline não-LLM ainda competitivo.
- **Rui Yang et al. (2024).** *Leveraging Large Language Models for Concept Graph Recovery and Question Answering in NLP Education*. arXiv:2402.14293. Avalia LLMs em recuperar grafos de conceitos em domínio educacional (NLP), com achado geral de que LLMs são bons em identificar conceitos e fracos em decidir direção de pré-requisito sem sinal adicional.
- **Education-Oriented Graph Retrieval-Augmented Generation for Learning Path Recommendation** (2025), arXiv:2506.22303. EDU-Graph RAG, gera grafos capturando relações de pré-requisito e similaridade entre conceitos a partir de texto não estruturado.
- **Inferring Prerequisite Knowledge Concepts in Educational Knowledge Graphs: A Multi-criteria Approach** (2025), Springer, DOI 10.1007/978-981-95-5009-8_19.

### 2.3 Família C: embeddings e clustering (com ou sem nomeação por LLM)

- **KCluster** (Wei, Carvalho, Stamper, EDM 2025) já detalhado na seção 1.4. É o representante mais forte: LLM pequeno como métrica de similaridade + Affinity Propagation, superando o expert em AFM.
- **Question-emb**, o baseline de embeddings usado no próprio paper do KCluster: embeddar o texto da questão e clusterizar. Fica próximo do expert mas atrás do KCluster, o que sugere que **similaridade de superfície do enunciado não é a mesma coisa que compartilhar KC**. Duas questões sobre Boyle podem ter enunciados lexicalmente distantes.
- **Merge por cosseno sobre rótulos de KC** (Wang, Lin, Koedinger 2025, seção 1.3). Paliativo com ganho pequeno e não-monotônico no limiar.
- **K. M. Shahana, Chandrashekar Lakshmanarayanan (2023).** *Unsupervised Concept Tagging of Mathematical Questions from Student Explanations*. AIED 2023, Springer LNAI 13916, pp. 627-638. Tagging não supervisionado de conceitos usando as **explicações escritas pelos alunos** como sinal, não o enunciado. Relevante: o sinal de qual KC uma questão exercita pode estar melhor no processo de resolução do que no enunciado.
- **Yang Shi, Robin Schmucker, Min Chi, Tiffany Barnes, Thomas Price (2023).** *KC-Finder: Automated Knowledge Component Discovery for Programming Problems*. EDM 2023. https://eric.ed.gov/?id=ED630850 Descoberta de KCs para problemas de programação a partir de código de aluno, com KCs aprendidos de forma end-to-end junto com o modelo de knowledge tracing.
- **Automated Recommendation of Programming Learning Content Using Pattern-based Knowledge Components** (2026), arXiv:2607.05409. Extensão da linha de KCs baseados em padrões de código.

### 2.4 Família D: descoberta de KCs a partir de dados de resposta de alunos (sem texto)

Linha clássica de EDM, que é o **benchmark contra o qual nossa abordagem textual será julgada**, e a fonte das métricas usadas em toda a literatura acima:

- **Tiffany Barnes (2005).** *The Q-matrix Method: Mining Student Response Data for Knowledge*. AAAI 2005 EDM Workshop.
- **Hao Cen, Kenneth Koedinger, Brian Junker (2006).** *Learning Factors Analysis: A General Method for Cognitive Model Evaluation and Improvement*. ITS 2006, pp. 164-175. Origem do AFM e da busca por refinamento de KCM.
- **Michel Desmarais, Rhouma Naceur (2013).** Fatoração de matrizes para mapear itens a habilidades / q-matrizes.
- **Benjamin PaaBen, Malwina Dywel, Melanie Fleckenstein, Niels Pinkwart (2022).** *Sparse Factor Autoencoders for Item Response Theory*. EDM 2022. Abordagem VAE.
- **Zachary Pardos, Anant Dadu (2017).** *Imputing KCs with Representations of Problem Content and Context*. UMAP 2017.
- **Napol Rachatasumrit, Kenneth Koedinger et al.**, e a linha de *Yanjin Long, Kenneth Holstein, Vincent Aleven (2018), What exactly do students learn when they practice equation solving?*, LAK 2018, que refina KCs com AFM.
- **A Framework for Human-AI Q-Matrix Refinement: A NeuralCDM Evaluation** (2026), arXiv:2604.16398. Versão contemporânea, human-in-the-loop, do refinamento de q-matriz.

A crítica padrão a esta família, que Moore et al. repetem e que justifica a abordagem textual: os KCs descobertos por fatoração são **numericamente ótimos e semanticamente opacos**. O rótulo resultante não é interpretável por um educador, o que os torna inúteis para sequenciamento de instrução ou para explicar a um aluno o que ele não sabe. Nosso pipeline textual troca poder preditivo por interpretabilidade; KCluster é notável exatamente por conseguir os dois ao mesmo tempo.

---

## 3. Modos de falha reportados para extração direta em um único prompt

Ressalva importante antes de listar: **quase ninguém publica um estudo cujo objetivo declarado seja catalogar os modos de falha da extração direta.** O que existe são modos de falha reportados como limitações, como justificativas para a arquitetura escolhida, ou como observações de piloto. Compilei abaixo o que está documentado, com a fonte de cada um. Onde a evidência é anedótica ou de piloto, sinalizo.

### 3.1 Redundância e explosão do número de KCs (o mais bem documentado)

Evidência mais forte da literatura. Wang, Lin, Koedinger (2025): 646 questões produziram **569 KCs** contra 101 do especialista. Praticamente um KC por item. Depois de merge por cosseno no melhor limiar, ainda 428. Moore et al. (2024) observaram o mesmo em menor escala e foi exatamente isso que motivou o algoritmo de indução de ontologia: "Apply Boyle's law" / "Examine Boyle's Law" / "Utilize Boyle's Law" para o mesmo KC.

Causa estrutural: quando você processa cada item de forma independente, o modelo não tem como saber que já nomeou aquele KC. Não é um problema de qualidade do modelo, é um problema de arquitetura do pipeline. Nenhum prompt melhor resolve isso.

### 3.2 Granularidade inconsistente

Documentado em duas direções opostas, o que é o ponto:
- **Abstrato demais.** Duan, Fernandez, Lekshmi Narayanan, Hassany, Sampaio de Alencar, Brusilovsky, Akram, Lan (arXiv:2502.18632, KCGen-KT) reportam explicitamente que **prompting zero-shot produz KCs excessivamente gerais**; o pipeline deles exige ao menos um exemplo humano em contexto para gerar KCs de baixo nível. A ablação confirma: sem in-context examples, AUC cai de 0,816 para 0,782. Também reportam que "KCs excessivamente abstratos falham em identificar as habilidades necessárias num problema".
- **Específico demais.** Wang, Lin, Koedinger (2025) chamam de "over-specification of learning objectives"; o KCM resultante tem granularidade fina demais para funcionar como modelo cognitivo. Moore et al. (2024) reportam o mesmo no ramo E-Learning: 63 KCs induzidos contra 40 do expert, com grouping accuracy de apenas 0,175.
- **Inconsistência entre itens.** A literatura de KCs em código (arXiv:2607.03419, *Analyzing the Difficulty of Programming Assignments with Interpretable Knowledge Component Metrics*) enfatiza que "a consistência da granularidade ao longo de todas as tarefas" é o que determina a qualidade do KC, e que a granularidade dos KCs gerados por LLM afeta tanto a força quanto a significância da correlação KC-desempenho.

Não achei nenhum estudo que **quantifique** dispersão de granularidade dentro de um mesmo conjunto extraído (por exemplo, uma medida de variância de nível de abstração). Isso é uma lacuna real da literatura, e uma métrica que poderíamos ter que inventar.

### 3.3 Viés de generalização na presença de jargão de domínio

Moore et al. (2024) documentam isso explicitamente: "o LLM frequentemente favorece opções gerais em vez de opções precisas e domain-specific, potencialmente devido à presença de jargão de domínio". Consequência medida: em 21% (Chemistry) e 38% (E-Learning) dos casos, o KC humano correto **nem sequer aparece no top-5** de candidatos gerados. Isso significa que o erro não é de seleção, é de geração: o candidato certo nunca foi produzido.

### 3.4 KCs irrelevantes ou não alinhados ao item

Reportado como risco em KCGen-KT: "KCs gerados imprecisos, excessivamente abstratos ou desalinhados podem impactar negativamente o aprendizado do aluno". Na avaliação humana deles com dois instrutores de Java sobre 50 problemas do CodeWorkout, a precisão foi 93,2% para KCs gerados contra 92,5% para humanos: ou seja, **~7% dos KCs gerados foram julgados não relevantes ao problema**, taxa comparável à humana. É a evidência quantitativa mais próxima que encontrei para "KC alucinado", e vale notar que os humanos erram na mesma proporção.

### 3.5 Cobertura incompleta (KCs que faltam)

KCGen-KT: "a geração de KCs às vezes deixa passar habilidades compartilhadas entre problemas, por causa da independência item a item", e "cobertura de KCs incompleta para problemas complexos". Na avaliação humana, os conjuntos de KCs gerados igualaram ou superaram a cobertura humana em 96% dos casos, mas ficaram abaixo em 4%.

Este é o espelho da redundância: o processamento item a item causa duplicação de KCs comuns e omissão de KCs transversais ao mesmo tempo.

### 3.6 Falha de instruction-following em listas longas

Moore et al. (2024), no algoritmo de indução: com listas de mais de ~50 questões, o **GPT-4 falha em executar a instrução de particionamento**, ou omite questões, ou atribui a mesma questão a múltiplos grupos. A mitigação deles foi separar em dois prompts: um que propõe os grupos (com nomes) e outro que classifica cada questão individualmente contra a lista de grupos. Este é um modo de falha concreto e uma mitigação concreta.

Sinal correlato em Duan, Kankaria, Kartik, Lan (arXiv:2602.17542): Qwen3 se mostrou "mais afetado por ambiguidade de instruction-following" que o GPT-4o na mesma tarefa de mapeamento código-KC, o que sugere que a robustez a esse modo de falha varia bastante por modelo.

### 3.7 Alucinação de conteúdo que a fonte não ensina

**Esta é a lacuna mais séria da literatura para o nosso caso.** Não encontrei nenhum estudo que meça diretamente a taxa em que um KC extraído descreve conhecimento que o texto-fonte não ensina. A razão é estrutural: **praticamente toda a literatura de extração de KCs parte de itens de avaliação, não de texto de ensino.** Quando o input é uma MCQ, "alucinar conteúdo que a fonte não ensina" quase não faz sentido como categoria, porque não há fonte de ensino no loop.

O que existe é adjacente:
- A literatura geral de fact-checking e hallucination detection (por exemplo o survey em Artificial Intelligence Review 2025, DOI 10.1007/s10462-025-11454-w; benchmarks FActScore, QAGS, FRANK, HalluLens) oferece o maquinário de *factual consistency contra uma fonte*, que é exatamente o que precisaríamos, mas nunca foi aplicado a KCs.
- Gacek e Adrian (2025) usam grounding em Wikidata para restringir os conceitos extraídos de ementas a entidades que existem, o que é uma forma de controle de alucinação, mas restringe existência de conceito, não pertinência à fonte.
- Sridhar et al. (2023) avaliaram 127 LOs quanto à forma e ao nível de Bloom, e não quanto a se o curso de fato ensina aquilo.

Conclusão honesta: **se o nosso pipeline extrai KCs de texto de ensino, estaremos operando num regime que a literatura de KCs praticamente não cobre, e o modo de falha mais perigoso desse regime é o único que ninguém mediu.** Teremos que importar métricas de faithfulness/groundedness da literatura de sumarização e RAG.

### 3.8 Dependência do domínio

Moore et al. (2024): 52-56% de match em Chemistry contra 35% em E-Learning, Z = 2,698, p = 0,007. A explicação dos autores é representação no corpus de treino: domínios nicho vão performar pior. Implicação prática: **qualquer número de qualidade que medirmos num domínio popular é um teto otimista, não uma média.**

### 3.9 Subjetividade da própria avaliação (meta-falha)

Moore et al.: mesmo com rubrica derivada do KLI e três especialistas, unanimidade ocorreu em apenas 29% (Chemistry) e 35% (E-Learning) dos casos. Eles afirmam diretamente que "a definição de um KC 'bom' ainda não é clara". A implicação é desconfortável: uma parte do que medimos como erro do LLM é ruído do gold standard. Os próprios autores suspeitam que o KCM humano do curso de E-Learning é de qualidade inferior, o que explicaria parte do gap.

---

## 4. Pipelines em múltiplos estágios e geração automática de questões

Resposta curta: **sim, existem pipelines multi-estágio, e eles são o estado da arte.** Mas nenhum deles tem a forma exata que planejamos (gerar questões primeiro, agrupar, depois nomear o KC). O que existe é o padrão adjacente: **partir de itens que já existem** (ou de soluções de aluno que já existem), agrupar, e nomear o cluster.

### 4.1 O padrão dominante: gerar candidatos, agrupar, nomear o cluster

Cinco trabalhos convergiram independentemente para a mesma arquitetura de três estágios, o que é o sinal mais forte da literatura.

**(a) Moore, Schmucker, Mitchell, Stamper (L@S 2024), indução de ontologia.**
Estágios: gerar 5 candidatos por item -> selecionar 1 -> particionar recursivamente o pool de questões por prompt, com um segundo prompt de classificação forçada. Puramente por prompt, sem embeddings. Já detalhado em 1.1.

**(b) Duan, Fernandez, Lekshmi Narayanan, Hassany, Sampaio de Alencar, Brusilovsky, Akram, Lan. KCGen-KT: *Automated Knowledge Component Generation and Interpretable Knowledge Tracing in Coding Problems*. arXiv:2502.18632.**
Esta é a instância mais limpa do padrão e a mais próxima do nosso desenho:
1. **Geração:** GPT-4o recebe um conjunto diverso de *submissões corretas de alunos* por problema (não o enunciado), com few-shot e chain-of-thought, e identifica as habilidades necessárias.
2. **Clustering:** Hierarchical Agglomerative Clustering sobre embeddings Sentence-BERT das descrições de KC, com cosseno. **O nível de abstração é controlado pelo corte da hierarquia**, exatamente como a árvore de Moore et al.
3. **Nomeação:** GPT-4o gera um rótulo conciso para cada cluster, produzindo a Q-matrix final.

Resultados: CodeWorkout (Java, 50 problemas, 246 alunos, 10.834 submissões, 18 KCs humanos) e FalconCode (Python, 157 problemas, 3.267 alunos, 28.617 submissões, 20 KCs humanos). Os KCs gerados **batem os KCs humanos** em predição: +0,019 AUC em ambos, e +0,021 / +0,046 F1. Curvas de aprendizado sob PFA: R² = 0,21 para gerados contra 0,18 para humanos, melhor aderência à power law of practice. Avaliação humana com dois instrutores de Java sobre 50 problemas: interpretabilidade 98,6% (gerados) vs 94,6% (humanos), Cohen's Kappa 0,594; precisão 93,2% vs 92,5%; recall igual ou superior ao humano em 96% dos casos.

Achado de granularidade que importa muito para nós: **abstração média foi o ótimo**. Para CodeWorkout, 50 clusters foi melhor; abstração alta (10-20 clusters) degradou significativamente os resultados. Ou seja, a granularidade ótima ficou *acima* do número de problemas em ordem de grandeza próxima, não em 18 como o modelo humano.

Ablações reveladoras (AUC no CodeWorkout, full = 0,816): sem soluções corretas 0,789; sem KC loss 0,791; sem in-context examples 0,782; **usando soluções incorretas 0,773**. Duas lições: os exemplos em contexto carregam muito peso, e alimentar o modelo com o material errado é pior que não alimentar.

**(c) Moon, Davis, Neshaei, Dillenbourg (EDM 2025). *Using Large Multimodal Models to Extract Knowledge Components for Knowledge Tracing from Multimedia Question Information*.** https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.long-papers.170/index.html
Este é o trabalho que mais se aproxima de extrair KCs de **material de ensino** e não só de itens:
1. **Processamento de conteúdo:** parsear o material educacional em texto, imagens e áudio transcrito; imagens são embutidas nas chamadas ao GPT-4o preservando a posição original.
2. **Inferência:** GPT-4o com **prompt zero-shot** pedindo KCs em JSON com campos `name` (2 a 4 palavras) e `description` (1 frase). Note a restrição de forma como controle de granularidade.
3. **Clustering:** embeddings `text-embedding-3-large`, K-means, com o número de clusters escolhido por **maximização do silhouette score** (resultou em 49 a 63 clusters nos cinco datasets).

Cinco domínios OLI do CMU DataShop: Statics (189.047 transações), Computing (16.951), French (53.255), Biology (3.285.695), Psychology (1.935.496). Resultados AFM (RMSE, LLM vs humano): Statics 0,395 vs 0,394; French 0,363 vs 0,345; Computing 0,397 vs 0,416. Knowledge tracing (AUC com PFA): French 0,787 vs 0,752; Computing 0,723 vs 0,699; Statics 0,751 vs 0,693. Conclusão dos autores: os KCs extraídos automaticamente **podem substituir os rótulos humanos** em benchmarks de knowledge tracing.

**(d) KCluster (Wei, Carvalho, Stamper, EDM 2025).** Variante: pula a geração e usa o LLM só para a métrica de similaridade; Affinity Propagation agrupa; depois gera o rótulo descritivo do cluster. Detalhado em 1.4.

**(e) L@S 2025, data science.** *Systematically Identifying, Defining and Organizing Knowledge Components for Data Science Problem Solving through Human-LLM Collaboration*. DOI 10.1145/3698205.3733952. Trata o LLM como "knowledge engineering assistant". Estágios: prompt a **múltiplos LLMs** para gerar decision points; sintetizar e refinar definições de KC entre modelos; usar sentence embeddings para inferir a estrutura da taxonomia; especialistas humanos revisam e refinam iterativamente. Diferencial: KCs aqui são explicitamente *conditional knowledge*, saber que ação tomar dada uma condição, o que é a leitura mais fiel do KLI e a mais difícil de extrair.

**(f) Variante de dois passos citada no próprio KCluster:** "instrua o LLM a propor um conjunto mínimo de definições de cluster para todo o corpus de questões, obtendo rótulos e descrições; depois mostre cada questão individualmente ao LLM e force a atribuição ao cluster mais próximo entre os pré-definidos." É a mesma mitigação que Moore et al. descobriram. **Dois grupos independentes chegaram na mesma correção para o mesmo bug de instruction-following.**

### 4.2 A lacuna: ninguém gera questões *sintéticas* como estágio intermediário para descobrir KCs

Procurei explicitamente por isso e **não encontrei nenhum trabalho publicado** que: parta de texto de ensino, gere itens de avaliação sintéticos, agrupe esses itens e nomeie o KC de cada grupo.

O que existe é sempre uma das duas variantes:
- Os itens **já existem** (bancos de questões curados) e o pipeline os agrupa. Moore et al., KCluster, Wang/Lin/Koedinger, Moon et al.
- Os artefatos de agrupamento são **soluções de aluno**, que já existem. KCGen-KT, KC-Finder, Shahana e Lakshmanarayanan.

O paralelo mais próximo fora de educação é a metodologia de descoberta de failure modes em modelos de visão-linguagem (arXiv:2604.04733), que gera questões e depois mapeia para skills e meta-skills num pipeline de quatro estágios: identificação de primitivas -> topic modeling (dedup por cosseno de embeddings, depois BERTopic) -> extração de skills (refinamento dos rótulos de tópico) -> identificação de meta-skills. É um pipeline de "gerar itens e induzir a taxonomia de habilidades a partir deles" em espírito idêntico ao nosso, mas fora do contexto educacional.

**Isto é ao mesmo tempo o nosso risco e a nossa contribuição potencial.** Risco porque não há precedente validado. Contribuição porque a lógica é defensável: se um KC é, por definição do KLI, aquilo que é inferido do desempenho do aluno em avaliações relacionadas, então gerar avaliações e agrupá-las é mais fiel à definição do que descrever um trecho de texto. A questão empírica em aberto é se questões *sintéticas* carregam sinal suficiente para o agrupamento, ou se herdam vieses do gerador de tal forma que os clusters refletem o modelo e não o domínio.

### 4.3 Literatura de automatic question generation a partir de texto didático

Contexto relevante porque o estágio de geração é onde nosso erro entra no pipeline.

- **Sami Sarsa, Paul Denny, Arto Hellas, Juho Leinonen (2022).** *Automatic Generation of Programming Exercises and Code Explanations Using Large Language Models*. ICER 2022, pp. 27-43. arXiv:2206.11861. Codex gerando exercícios com solução e casos de teste. Achado central reutilizável: **é notavelmente fácil influenciar tanto os conceitos de programação quanto o tema contextual fornecendo keywords como input.** Ou seja, o gerador é altamente condicionável, o que é bom para cobertura dirigida e ruim para diversidade espontânea. A maioria do conteúdo gerado foi novo e sensato, mas com necessidade de supervisão.
- **Nguyen, Moore, Stamper et al. (2022).** *Towards Generalized Methods for Automatic Question Generation in Educational Domains*. EC-TEL 2022. Pipeline de geração + avaliação a partir de material textual de curso.
- **Jacob Doughty, Zipiao Wan et al. (2024).** *A Comparative Study of AI-Generated (GPT-4) and Human-crafted MCQs in Programming Education*. ACE 2024 (26th Australasian Computing Education Conference), DOI 10.1145/3636243.3636256. arXiv:2312.03173. Este é o desenho inverso do nosso: dado um LO e um nível de Bloom, gerar a MCQ. O prompt tem componentes fixos (MCQ Principles, Bloom's Taxonomy, Course Description, Question Type Examples, Output Format) e slots (Question Type, Course Name, Module Name, Learning Objective, Bloom's Level). **Vale muito como referência de estrutura de prompt para o nosso estágio de geração de tarefas.**
- **Nikahat Mulla et al. / Scaria, Chenna, Subramani (2024).** *Automated Educational Question Generation at Different Bloom's Skill Levels Using Large Language Models: Strategies and Evaluation*. AIED 2024, Springer LNAI, DOI 10.1007/978-3-031-64299-9_12. arXiv:2408.04394.
- **Arav Agarwal et al. (2024).** *Understanding the Role of Temperature in Diverse Question Generation by GPT-4*. SIGCSE 2024. Relevante se formos gerar múltiplas tarefas por KC e quisermos diversidade real.
- **Optimizing Automated Question Generation for Educational Assessments: A Semantic Analysis of LLMs with Structured and Unstructured Ontologies** (2025), ETASR. Compara geração baseada em ontologia estruturada (template e LLM) contra lista plana de conceitos, com BERTScore e similaridade semântica. Relevante porque testa exatamente a pergunta "ancorar em estrutura ajuda?".
- **Automatic Multiple-Choice Question Generation and Evaluation Systems Based on LLM** (COLING 2025), https://aclanthology.org/2025.coling-main.154.pdf Achado de calibração: **LLMs genéricos não produzem consistentemente distratores que satisfaçam especialistas humanos**, e LLMs fine-tuned ficam restritos a certos tipos de questão e disciplinas.
- **SAQUET** (Moore, Costello, Nguyen, Stamper, AIED 2024). Rubrica de 19 Item-Writing Flaws aplicada automaticamente. É o filtro de qualidade pronto para o nosso estágio intermediário.

---

## 5. Como avaliar um conjunto de KCs sem dados de aluno

Esta é a pergunta mais importante para nós e a mais mal servida pela literatura. Praticamente todos os resultados numéricos fortes da seção anterior (AFM, RMSE, AUC, AIC, BIC, curvas de aprendizado) **exigem dados de resposta de alunos.** Sem eles, sobram proxies mais fracos. Vou listar em ordem decrescente de força evidencial.

### 5.1 Concordância com um KCM de especialista (o proxy padrão)

- **Match direto item a item.** Proporção de itens cujo KC gerado coincide com o KC do gold. Usado por Moore et al. (52-56% Chemistry, 35% E-Learning). Fraco porque exige julgar equivalência semântica entre duas strings livres, e porque penaliza um KC que seja *melhor* que o gold.
- **Top-k recall.** O KC do gold aparece entre os k candidatos gerados. Moore et al. reportam 79-80% em Chemistry e 56-63% em E-Learning para k=5. **Muito mais informativo que o match direto para diagnóstico**, porque separa falha de geração de falha de seleção.
- **Métricas de concordância de partição.** Quando o output é um agrupamento e não um rótulo, comparam-se as partições: **Adjusted Rand Index**, **Adjusted Mutual Information**, **Fowlkes-Mallows Index**. Usadas no KCluster para medir alinhamento com o modelo do especialista sem tocar em dados de aluno. **Este é o instrumento mais limpo disponível quando se tem um gold de referência.**
- **grouping accuracy e grouping refinement** (Moore et al., seção 1.1). Definidas sobre pares de questões que compartilham KC no gold. Vantagem: são interpretáveis como precisão e granularidade separadamente, e permitem plotar o trade-off ao longo dos passos do algoritmo. Requerem gold.

Limite fundamental de toda esta família: **assume que o especialista está certo.** Moore et al. e o próprio KCluster reconhecem isso explicitamente; Moore et al. chegam a argumentar que o gold de E-Learning é ruim e que isso explica seus números baixos. Se o nosso caso de uso é justamente domínios onde não há KCM de especialista, esses proxies são inacessíveis por construção.

### 5.2 Julgamento humano com rubrica

- **Preferência pareada.** Moore et al.: mostrar o KC humano e o KC do LLM para o mesmo item, ordem randomizada, e pedir a escolha. Três especialistas, maioria decide. Resultado: 66% / 62% a favor do LLM, p = 0,017. **Cuidado metodológico obrigatório: eles tiveram que normalizar o comprimento dos rótulos (máximo 1,5x o comprimento do humano), porque verbosidade é um confound de preferência.** Se não fizermos isso, mediremos prolixidade.
- **Rubrica de critérios do KLI.** Moore et al. instruíram os avaliadores com quatro critérios: clareza, relevância direta ao conteúdo, acurácia factual, e capacidade de aplicar ou integrar o conhecimento em outros contextos. Este último é a operacionalização da testabilidade/transferência.
- **Interpretabilidade, precisão e recall julgados por instrutor.** KCGen-KT: dois instrutores avaliaram se cada KC é claramente compreensível (98,6%), se é relevante ao problema (93,2%), e se o conjunto de KCs cobre o que o problema exige (igual ou melhor que humano em 96%). **Este trio, interpretabilidade / precisão / cobertura, é o conjunto mais prático e diretamente adotável que encontrei.** Reportem Cohen's Kappa junto (eles: 0,594 para interpretabilidade, o que é apenas moderado).
- Calibração de expectativa: acordo unânime entre três especialistas ocorreu em apenas 29-35% dos casos em Moore et al. **Não devemos esperar Kappa alto. Se obtivermos Kappa alto, provavelmente estamos medindo algo trivial.**

### 5.3 Propriedades estruturais internas do conjunto (sem gold, sem humano)

Aqui a literatura é mais escassa, mas há peças utilizáveis:

- **Contagem de KCs vs contagem de itens.** O sinal mais barato e mais informativo. Wang/Lin/Koedinger: 569 KCs para 646 questões é um alarme imediato. Uma razão KC/item próxima de 1 significa que não houve abstração nenhuma.
- **Redundância semântica interna.** Distribuição das similaridades de cosseno par a par entre os embeddings dos rótulos de KC. Wang/Lin/Koedinger mostram que 428 de 569 sobrevivem a um corte em 0,8, o que quantifica quanta duplicação havia. Use como diagnóstico, não como correção.
- **Silhouette score** para escolher o número de clusters. Moon et al. (EDM 2025) usaram exatamente isso, obtendo 49-63 clusters. É um critério de qualidade de agrupamento que não precisa de gold nem de aluno.
- **Conformidade de forma.** Se você impõe uma gramática (subject-verb-object nos LOs atômicos de Liu et al.; `name` de 2-4 palavras + `description` de 1 frase em Moon et al.), pode medir a taxa de conformidade. É um proxy grosseiro de consistência de granularidade, e é o único que a literatura efetivamente usa para isso.
- **Aderência a verbos de Bloom e distribuição pelos níveis.** Sridhar et al. (2023) avaliaram 127 LOs exatamente assim, e checaram se o nível de Bloom batia com o tipo de módulo (conceitual = níveis baixos, projeto = níveis altos). Fraco, mas automatizável e barato.
- **Estabilidade entre execuções (test-retest).** Esiason, Khare, Min, Lee, Ozogul, Zheng, Jeong (BEA 2026), *Assessing the Quality and Consistency of Automated Knowledge Component Generation using Instructor-generated Questions and LLMs*, https://aclanthology.org/2026.bea-1.18/, tratam **consistência como uma dimensão de avaliação separada da qualidade**, e reportam um achado importante: fornecer material do curso via RAG **melhora a qualidade dos KCs gerados mas não melhora a consistência.** Isto é fundamental para nós: grounding no texto-fonte ajuda a acertar, mas não estabiliza a granularidade. São dois problemas distintos que exigem duas soluções distintas.
- **Concordância entre modelos.** O trabalho de data science do L@S 2025 usa múltiplos LLMs para gerar candidatos e depois sintetiza. Divergência entre modelos independentes é um sinal de KC mal definido, e é obtenível sem nenhum humano.

### 5.4 Proxies que a literatura não oferece e que teríamos que construir

Sendo honesto sobre as lacunas:

- **Groundedness / faithfulness do KC contra o texto-fonte.** Como já dito em 3.7, isso simplesmente não existe na literatura de KCs, porque a literatura parte de itens. Teríamos que importar de sumarização e RAG: entailment do KC contra os spans do texto, ou uma variante de FActScore/QAGS adaptada, ou um juiz LLM que responda "esta fonte ensina isto? cite o trecho". A exigência de citar o trecho é a mitigação mais barata e mais eficaz.
- **Cobertura da fonte.** Proporção do texto-fonte que é coberta por ao menos um KC. É trivial de definir e não achei ninguém que reporte. Detecta o modo de falha "o modelo extraiu o que estava no começo do texto e ignorou o resto".
- **Testabilidade.** A definição do KLI diz que um KC é inferido do desempenho em avaliações. O proxy operacional óbvio é: **um KC é testável se conseguimos gerar itens de avaliação distintos para ele.** Isso é exatamente o que o nosso pipeline já produz como subproduto. Não vi ninguém formalizar isso como métrica, e é uma contribuição barata que poderíamos reivindicar.
- **Discriminabilidade entre KCs.** Dois KCs são realmente distintos se um item gerado para um não é aceito como item do outro. Operacionalizável como uma matriz de confusão de re-classificação: gere n itens por KC, embaralhe, e peça a um classificador (LLM ou embedding) que reatribua. Diagonal fraca = KCs redundantes ou mal definidos. **É um teste de consistência interna que não precisa de gold nem de aluno, e é a versão sem alunos da grouping accuracy.**
- **Variância de granularidade dentro do conjunto.** Ninguém quantifica. Candidatos baratos: distribuição do número de tokens do rótulo, distribuição da especificidade medida por frequência das entidades no corpus, ou profundidade média se houver hierarquia.

### 5.5 Nota sobre os proxies que exigem alunos (para saber o que estamos abrindo mão)

Para referência, o que perdemos ao não ter dados de resposta: AFM com item-blocked RMSE e cross-validation (Moore-adjacentes, KCluster, Moon et al., Wang/Lin/Koedinger), AIC e BIC como penalização de complexidade do KCM (KCluster), AUC/F1 de knowledge tracing (KCGen-KT, Moon et al.), e **fit da curva de aprendizado à power law of practice** (KCGen-KT reporta R² = 0,21 vs 0,18; Duan, Kankaria, Kartik, Lan reportam Power Law RMSE 0,069 e r² 0,383). A curva de aprendizado é historicamente **o** teste de validade de um KCM, e não tem substituto real sem alunos. Um KCM que não produz curvas suaves está errado, e nenhuma quantidade de julgamento humano detecta isso.

Implicação de projeto: qualquer conjunto de KCs que produzirmos deve ser instrumentável para validação posterior com dados reais. Vale desenhar o formato de saída já como uma Q-matrix.

---

## 6. Implicações para o nosso pipeline

**1. Não faça extração direta em um passo. A literatura já falhou nisso e sabemos o porquê.**
O modo de falha não é de qualidade do modelo, é de arquitetura: processar cada fonte independentemente impede que o modelo saiba o que já nomeou. Wang, Lin e Koedinger produziram 569 KCs para 646 questões e ficaram abaixo do especialista mesmo após deduplicação. Todo trabalho que bateu o especialista (KCluster, KCGen-KT, Moon et al.) usa agrupar-depois-nomear.

**2. A ordem certa é: gerar amplo, agrupar, nomear o grupo. Nunca nomear e depois deduplicar.**
Comparação direta na literatura: Wang/Lin/Koedinger (nomear -> merge por cosseno) ficou abaixo do expert; KCluster e KCGen-KT (agrupar -> nomear) ficaram acima. Merge por embedding sobre rótulos textuais opera na superfície linguística e não no conteúdo cognitivo, e o ganho é pequeno e não-monotônico no limiar.

**3. Granularidade deve ser um parâmetro de corte, não uma instrução de prompt.**
Três trabalhos independentes chegaram nisso: corte da árvore de particionamento (Moore et al.), corte do dendrograma HAC (KCGen-KT), escolha de k por silhouette (Moon et al.). Adjetivos no prompt ("seja específico", "low-level", "detalhado") são o que a literatura tentou primeiro e é o que falha. Se quisermos granularidade ajustável pelo usuário, ela tem que ser um número, não uma frase.

**4. Gere um top-k de candidatos e selecione depois, em vez de pedir a resposta certa direto.**
Moore et al. medem a diferença: 52% de acerto direto contra 80% de o gold estar no top-5. O modelo *sabe* mais do que ele *escolhe*. Se o próximo estágio é agrupamento, alimente o agrupamento com os candidatos, não com o vencedor.

**5. Nunca peça particionamento de listas longas em um prompt só. Separe proposta de rótulos e atribuição de itens.**
Moore et al. e o pipeline citado no KCluster convergiram independentemente para isto. Com mais de ~50 itens, o modelo omite itens ou os coloca em vários grupos. O padrão correto: prompt A propõe o conjunto mínimo de grupos com nome e descrição; prompt B mostra um item por vez e força a atribuição a exatamente um grupo existente.

**6. Alinhamento a Bloom vem depois da geração, nunca antes.**
Achado de piloto explícito de Moore et al.: colocar Bloom no prompt inicial degradou a qualidade, porque o modelo passou a gerar habilidades em torno das palavras "understand", "apply", "analyze" para satisfazer a taxonomia. Mesma lógica vale para qualquer taxonomia ou vocabulário controlado que queiramos impor: **primeiro o conteúdo, depois a forma.**

**7. Restrinja a forma do output para controlar granularidade.**
Gramática subject-verb-object (Liu et al., LAK '25), ou `name` de 2-4 palavras + `description` de 1 frase (Moon et al., EDM 2025). São controles estruturais que funcionam onde adjetivos não funcionam. Bônus: conformidade de forma é mensurável automaticamente.

**8. Nosso estágio de geração de tarefas não tem precedente publicado, e esse é o risco principal.**
Ninguém publicou "texto de ensino -> gerar itens -> agrupar itens -> nomear KC". Todos os pipelines que agrupam partem de itens ou soluções que já existem. A pergunta empírica em aberto: itens *sintéticos* carregam sinal suficiente para o agrupamento, ou os clusters vão refletir o gerador em vez do domínio? **Teste barato para responder isso antes de investir: rode o mesmo agrupamento sobre itens sintéticos e sobre itens reais de um banco curado do mesmo domínio, e compare as partições resultantes com ARI.** Se divergirem muito, o sinal está no gerador.

**9. Alucinação contra a fonte é o nosso modo de falha específico, e ninguém o mediu.**
Porque a literatura de KCs parte de itens, não de texto de ensino, "o KC descreve algo que a fonte não ensina" nem existe como categoria lá. Temos que importar da literatura de faithfulness (FActScore, QAGS, entailment contra spans). Mitigação mais barata e mais eficaz: **exigir que cada KC cite o trecho da fonte que o justifica**, e rejeitar KCs sem citação verificável.

**10. Grounding no texto-fonte melhora qualidade mas não melhora consistência.**
Achado direto de Esiason et al. (BEA 2026) com RAG. Precisamos de dois mecanismos separados: citação obrigatória para a qualidade, e corte estrutural de granularidade para a consistência. Não espere que RAG resolva os dois.

**11. Use um filtro de qualidade de item entre a geração e o agrupamento.**
SAQUET (Moore et al., AIED 2024) aplica automaticamente uma rubrica de 19 Item-Writing Flaws. Itens ruins vão poluir o espaço de agrupamento. E a literatura de AQG é clara sobre onde o erro entra: distratores de MCQ são o ponto fraco consistente dos LLMs genéricos (COLING 2025). Se a qualidade do distrator for problema, considere formatos de item que não dependam de distratores no estágio intermediário, já que estamos usando os itens como sinal de agrupamento e não como avaliação final.

**12. Condicione nossas expectativas de qualidade ao domínio.**
Moore et al.: 52-56% em Chemistry contra 35% em E-Learning, p = 0,007. Qualquer número que medirmos em um domínio popular é um teto, não uma média. Reporte resultados por domínio, sempre.

**13. Plano de avaliação concreto, na ausência de dados de aluno.**
Em ordem de custo crescente:
- Automático, sem gold: razão KC/item; distribuição de similaridade par a par entre rótulos; silhouette do agrupamento; conformidade de forma; cobertura da fonte; **discriminabilidade por re-classificação de itens** (gere n itens por KC, embaralhe, reatribua, olhe a diagonal); estabilidade entre seeds e entre modelos.
- Automático, com gold quando existir: ARI, AMI, Fowlkes-Mallows contra o KCM do especialista; top-k recall para diagnosticar geração vs seleção.
- Humano: trio interpretabilidade / precisão / cobertura do KCGen-KT, com Cohen's Kappa reportado; e preferência pareada contra o gold **com comprimento normalizado**. Não espere unanimidade: a literatura vê 29-35%.
- Reservado para quando houver alunos: Q-matrix -> AFM com item-blocked RMSE, AIC/BIC, e fit de curva de aprendizado. **Projete o formato de saída como Q-matrix desde já.**

**14. Modelo pequeno pode bastar em alguns estágios.**
KCluster usou Phi-2 (2,7B) e bateu o especialista. Wang/Lin/Koedinger usaram gpt-4o-mini. O estágio caro é a geração; medir similaridade e classificar item em grupo podem ser feitos barato. Vale segmentar o gasto por estágio.

**15. Posicione o output como primeiro passe para human-in-the-loop, não como produto final.**
É a recomendação unânime da literatura, inclusive dos trabalhos que bateram o especialista em números. Moore et al.: os rótulos do LLM "devem ser vistos como uma fundação a ser refinada com insights de especialista e dados de desempenho de aluno". O padrão de ACE (Aytekin e Saygın) é o mais econômico: gerar candidatos por método barato, ranquear, mandar só o topo para revisão humana, propagar o resto por inferência estrutural.

---

## 7. Lacunas da literatura (declaração honesta)

1. **Ninguém extrai KCs de texto de ensino corrido.** O input padrão é um item de avaliação ou uma solução de aluno. Moon et al. (EDM 2025) é a exceção parcial e mais próxima, e mesmo assim o material está atrelado a questões dentro de uma plataforma OLI.
2. **Nenhuma medida de faithfulness de KC contra a fonte.** Consequência direta do item 1.
3. **Nenhuma métrica de variância de granularidade** dentro de um conjunto extraído, apesar de granularidade ser universalmente apontada como o problema central.
4. **Nenhum trabalho que gere itens sintéticos como estágio intermediário para descoberta de KCs** em contexto educacional.
5. **O gold standard é frágil.** Concordância entre especialistas é baixa (unanimidade em 29-35%), e ao menos um paper argumenta que seu próprio gold é de má qualidade. Boa parte do que a literatura reporta como erro do LLM pode ser ruído do referencial.
6. **Domínios avaliados são muito estreitos:** química introdutória, e-learning de mestrado, física introdutória, programação Java e Python, e cinco cursos OLI. Praticamente tudo em inglês, praticamente tudo STEM ou meta-educacional. Zero evidência em português, humanidades, ou domínios profissionais aplicados.
7. **Datasets pequenos onde há dados de aluno.** Os cursos com student data usados no KCluster têm menos de 650 questões e menos de 45 alunos. Os intervalos de confiança implícitos são largos e as diferenças reportadas, embora significativas, são de terceira casa decimal em RMSE.
8. **Nenhum estudo mede impacto em aprendizagem real.** Todos os autores reconhecem isso. A validação é sempre predição de desempenho ou julgamento de especialista, nunca ganho de aprendizado em sala.

---

## 8. Referências consolidadas

**Fundacional**
- Kenneth R. Koedinger, Albert T. Corbett, Charles Perfetti (2012). *The Knowledge-Learning-Instruction Framework: Bridging the Science-Practice Chasm to Enhance Robust Student Learning*. Cognitive Science 36(5), 757-798.
- Hao Cen, Kenneth Koedinger, Brian Junker (2006). *Learning Factors Analysis: A General Method for Cognitive Model Evaluation and Improvement*. ITS 2006, 164-175.
- Tiffany Barnes (2005). *The Q-matrix Method: Mining Student Response Data for Knowledge*. AAAI 2005 EDM Workshop.

**Núcleo CMU (Moore, Stamper e colaboradores)**
- Steven Moore, Robin Schmucker, Tom Mitchell, John Stamper (2024). *Automated Generation and Tagging of Knowledge Components from Multiple-Choice Questions*. L@S '24. DOI 10.1145/3657604.3662030. https://arxiv.org/abs/2405.20526 Código e dados: https://github.com/StevenJamesMoore/LearningAtScale24
- Yumou Wei, Paulo F. Carvalho, John Stamper (2025). *KCluster: An LLM-based Clustering Approach to Knowledge Component Discovery*. EDM 2025. https://arxiv.org/abs/2505.06469
- Canwen Wang, Jionghao Lin, Kenneth R. Koedinger (2025). *Leveraging Large Language Models for Identifying Knowledge Components*. LAK Workshop "LLMs for Qualitative Analysis in Education". https://arxiv.org/abs/2511.09935
- Steven Moore, Huy A. Nguyen, John Stamper (2020). *Towards Crowdsourcing the Identification of Knowledge Components*. L@S '20.
- Steven Moore, Huy A. Nguyen, John Stamper (2020). *Evaluating Crowdsourcing and Topic Modeling in Generating Knowledge Components from Explanations*. AIED 2020.
- Steven Moore, Huy A. Nguyen, John Stamper (2022). *Leveraging Students to Generate Skill Tags that Inform Learning Analytics*. ISLS 2022.
- Steven Moore, Eamon Costello, Huy A. Nguyen, John Stamper (2024). *An Automatic Question Usability Evaluation Toolkit* (SAQUET). AIED 2024.
- Steven Moore, Huy A. Nguyen, Tianying Chen, John Stamper (2023). *Assessing the Quality of Multiple-Choice Questions Using GPT-4 and Rule-Based Methods*. EC-TEL 2023.
- Steven Moore, Norman Bier, John Stamper (2024). *Assessing Educational Quality: Comparative Analysis of Crowdsourced, Expert, and AI-Driven Rubric Applications*. AAAI HCOMP 2024.
- Huy A. Nguyen, Steven Moore, John Stamper et al. (2022). *Towards Generalized Methods for Automatic Question Generation in Educational Domains*. EC-TEL 2022.
- Hassan Khosravi, Paul Denny, Steven Moore, John Stamper (2023). *Learnersourcing in the Age of AI: Student, Educator and Machine Partnerships for Content Creation*. Computers and Education: AI.

**Pipelines multi-estágio e clustering**
- Zhangqi Duan, Nigel Fernandez, Arun Balajiee Lekshmi Narayanan, Mohammad Hassany, Rafaella Sampaio de Alencar, Peter Brusilovsky, Bita Akram, Andrew Lan. *Automated Knowledge Component Generation and Interpretable Knowledge Tracing in Coding Problems* (KCGen-KT). https://arxiv.org/abs/2502.18632
- Hyeongdon Moon, Richard Lee Davis, Seyed Parsa Neshaei, Pierre Dillenbourg (2025). *Using Large Multimodal Models to Extract Knowledge Components for Knowledge Tracing from Multimedia Question Information*. EDM 2025. https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.long-papers.170/index.html
- *Systematically Identifying, Defining and Organizing Knowledge Components for Data Science Problem Solving through Human-LLM Collaboration*. L@S 2025. DOI 10.1145/3698205.3733952
- Zhangqi Duan, Arnav Kankaria, Dhruv Kartik, Andrew Lan. *Using LLMs for Knowledge Component-level Correctness Labeling in Open-ended Coding Problems*. https://arxiv.org/abs/2602.17542
- Yang Shi, Robin Schmucker, Min Chi, Tiffany Barnes, Thomas Price (2023). *KC-Finder: Automated Knowledge Component Discovery for Programming Problems*. EDM 2023. https://eric.ed.gov/?id=ED630850
- Rafaella Sampaio de Alencar, Mehmet Arif Demirtas, Adittya Soukarjya Saha, Yang Shi, Peter Brusilovsky (2025). *Integrating Expert Knowledge With Automated Knowledge Component Extraction for Student Modeling*. UMAP 2025. Combina parsing automático de código com ontologia construída por especialista.
- K. M. Shahana, Chandrashekar Lakshmanarayanan (2023). *Unsupervised Concept Tagging of Mathematical Questions from Student Explanations*. AIED 2023, LNAI 13916, 627-638.

**Learning objectives e granularidade**
- Naiming Liu, Shashank Sonkar, Debshila Basu Mallick, Richard Baraniuk, Zhongzhou Chen (2025). *Atomic Learning Objectives and LLMs Labeling: A High-Resolution Approach for Physics Education*. LAK '25. DOI 10.1145/3706468.3706550. https://arxiv.org/abs/2412.09914
- Pragnya Sridhar, Aidan Doyle, Arav Agarwal, Christopher Bogart, Jaromir Savelka, Majd Sakr (2023). *Harnessing LLMs in Curricular Design: Using GPT-4 to Support Authoring of Learning Objectives*. https://arxiv.org/abs/2306.17459
- Christian Lohr et al. (2025). *Leveraging Large Language Models to Generate Course-Specific Semantically Annotated Learning Objects*. Journal of Computer Assisted Learning 41. DOI 10.1111/jcal.13101
- Tsvetomila Mihaylova, Jing Fan, Bita Akram, Narges Norouzi, Peter Brusilovsky, Juho Leinonen, Arto Hellas. *Analyzing the Difficulty of Programming Assignments with Interpretable Knowledge Component Metrics*. https://arxiv.org/abs/2607.03419

**Prerequisites e knowledge graphs educacionais**
- Mehmet Cem Aytekin, Yücel Saygın (2024). *ACE: AI-Assisted Construction of Educational Knowledge Graphs with Prerequisite Relations*. JEDM. https://jedm.educationaldatamining.org/index.php/JEDM/article/view/737
- Paulina Gacek, Weronika T. Adrian (2025). *Automated Curriculum Analysis Using Large Language Models and Knowledge Graphs*. DOI 10.1177/17248035251360196
- Rui Yang et al. (2024). *Leveraging Large Language Models for Concept Graph Recovery and Question Answering in NLP Education*. https://arxiv.org/abs/2402.14293
- *A Graph Neural Network Model for Concept Prerequisite Relation Extraction*. CIKM 2023. DOI 10.1145/3583780.3614761

**Automatic question generation**
- Sami Sarsa, Paul Denny, Arto Hellas, Juho Leinonen (2022). *Automatic Generation of Programming Exercises and Code Explanations Using Large Language Models*. ICER 2022, 27-43. https://arxiv.org/abs/2206.11861
- Jacob Doughty, Zipiao Wan et al. (2024). *A Comparative Study of AI-Generated (GPT-4) and Human-crafted MCQs in Programming Education*. ACE 2024. DOI 10.1145/3636243.3636256. https://arxiv.org/abs/2312.03173
- Nikahat Mulla et al. (2024). *Automated Educational Question Generation at Different Bloom's Skill Levels Using Large Language Models: Strategies and Evaluation*. AIED 2024. DOI 10.1007/978-3-031-64299-9_12. https://arxiv.org/abs/2408.04394
- *Automatic Multiple-Choice Question Generation and Evaluation Systems Based on LLM*. COLING 2025. https://aclanthology.org/2025.coling-main.154.pdf
- *Optimizing Automated Question Generation for Educational Assessments: A Semantic Analysis of LLMs with Structured and Unstructured Ontologies*. ETASR 2025. https://etasr.com/index.php/ETASR/article/view/10662

**Avaliação e consistência**
- Jordan Esiason, Priyanka Khare, Wookhee Min, Seung Lee, Gamze Ozogul, Xiaoying Zheng, Yeil Jeong (2026). *Assessing the Quality and Consistency of Automated Knowledge Component Generation using Instructor-generated Questions and LLMs*. BEA 2026. https://aclanthology.org/2026.bea-1.18/
- Survey de fact-checking e factuality em LLMs (2025). Artificial Intelligence Review. DOI 10.1007/s10462-025-11454-w

