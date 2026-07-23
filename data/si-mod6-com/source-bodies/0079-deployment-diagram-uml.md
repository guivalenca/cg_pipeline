---
id: "79"
title: "Deployment Diagram UML"
source_url: "https://www.ibm.com/docs/pt-br/rsas/7.5.0?topic=topologies-deployment-diagrams"
fetch_url: "https://www.ibm.com/docs/pt-br/rsas/7.5.0?topic=topologies-deployment-diagrams"
resolved_url: "https://www.ibm.com/docs/pt-br/rsas/7.5.0?topic=topologies-deployment-diagrams"
firecrawl_title: "Diagramas de Implementação - Documentação da IBM"
description: "In UML, deployment diagrams model the physical architecture of a system. Deployment diagrams show the relationships between the software and hardware components in the system and the physical distribution of the processing."
fetched_at: "2026-05-12T03:59:52.961165Z"
provider: "firecrawl"
strategy: "app_ui"
cache_key: "fbcd7965970df9720e191be6307cb1228225b27d2673182570710a6e2964533b"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=utf-8"
word_count: 986
char_count: 6368
content_sha256: "c8d59b318234c49bde426026398e11e17706b2418163612af92ef59842392fdd"
image_count: 4
link_count: 105
warnings: []
gate_status: "passed"
gate_failures: []
route_notes:
  - "enterprise_docs_navigation_heavy"
---

# Diagramas de Implementação

Atualizado pela última vez: 2021-03-05

Na UML, os diagramas de implementação modelam a arquitetura física de um sistema. Os diagramas de implementação mostram os relacionamentos entre os componentes de software e hardware no sistema e a distribuição física do processamento.

Os diagramas de implementação, que normalmente são preparados durante a fase de desenvolvimento da implementação, mostram a organização física dos nós em um sistema distribuído, os artefatos que estão armazenados em cada nó e os componentes e outros elementos que os artefatos implementam. Os nós representam dispositivos de hardware como por exemplo servidores, sensores e impressoras, bem como outros dispositivos que suportam o ambiente de tempo de execução de um sistema. Caminhos de comunicação e relacionamentos de implementação modelam as conexões do sistema.

Image summary: Example UML deployment diagram showing four nodes: User’s Computer, Web services, Application Server, and Database server. The User’s Computer contains a Web browser artifact; Web services contains a Business Logic Service; the Application Server contains WebSphere with a Web Application and DB API; and the Database server contains reporting data. Dashed communication paths show an HTTP connection over the internet, SOAP over HTTPS, and a native database connection. [Original image: Um diagrama de implementação de exemplo](https://www.ibm.com/docs/pt-br/SS4JE2_7.5.5/com.ibm.xtools.modeler.doc/images/cdepd.gif)

Os diagramas de implementação são eficazes para visualizar, especificar e documentar os seguintes tipos de sistemas:

- Sistemas incorporados que utilizam hardware que é controlado por estímulo externo; por exemplo, um vídeo que é controlado pela alteração de temperatura
- Sistemas cliente/servidor que normalmente distinguem entre a interface com o usuário e os dados persistentes de um sistema
- Sistemas distribuídos que possuem vários servidores e podem hospedar diversas versões de artefatos de software, alguns dos quais podem até migrar de um nó para outro

Como os diagramas de implementação se concentram na configuração dos nós de processamento de tempo de execução e de seus componentes e artefatos, é possível utilizar esse tipo de diagrama para avaliar as implicações da distribuição e de alocações de recursos.

Nota: Os diagramas de implementação são distintos dos diagramas de componentes. Um diagrama de implementação mostra os componentes e artefatos em relação ao local em que eles são utilizados no sistema implementado. Um diagrama de componentes define a composição dos componentes e artefatos no sistema.

Nota: Os diagramas de implementação são distintos das topologias de implementação, um tipo de modelo diferente. Para obter informações sobre topologias de implementação, consulte [Implementação e Topologias de Modelagem](https://www.ibm.com/docs/pt-br/SS4JE2_7.5.5/com.ibm.ccl.soa.deploy.core.doc/topics/topo_overview_cpt.html "As ferramentas de arquitetura de implementação permitem criar topologias, um tipo de modelo que mostra os relacionamentos entre os recursos da tecnologia da informação e que permite planejar e validar cenários de implementação.").

Os seguintes tópicos descrevem elementos de modelos em diagramas de implementação:

- **[Nós nos Modelos UML](https://www.ibm.com/docs/pt-br/SS4JE2_7.5.5/com.ibm.xtools.modeler.doc/topics/cnode.html)**

  Nos modelos UML, os nós são elementos de modelo que representam os recursos computacionais de um sistema, como por exemplo computadores pessoais, sensores, dispositivos de impressão ou servidores. Os nós podem ser conectados por caminhos de comunicação, para descrever estruturas de rede.

- **[Instâncias do Nó](https://www.ibm.com/docs/pt-br/SS4JE2_7.5.5/com.ibm.xtools.modeler.doc/topics/cnodeinst.html)**

  Na modelagem UML, uma instância de nó é um elemento de modelo que representa uma instanciação, ou uma ocorrência real, de um nó. As instâncias de nó baseiam-se nos nós existentes.

- **[Ambientes de Execução](https://www.ibm.com/docs/pt-br/SS4JE2_7.5.5/com.ibm.xtools.modeler.doc/topics/cexecenviro.html)**

  Em modelagem UML, um ambiente de execução é um tipo de nó que representa uma plataforma de execução específica, como um sistema operacional ou um sistema de gerenciamento de banco de dados. É possível utilizar os ambientes de execução para descrever o contexto no qual a execução de um modelo ocorre.

- **[Artefatos](https://www.ibm.com/docs/pt-br/SS4JE2_7.5.5/com.ibm.xtools.modeler.doc/topics/cartifact.html)**

  Em modelos UML, artefatos são elementos de modelo que representam as entidades físicas em um sistema de software. Os artefatos representam unidades físicas de execução, como por exemplo arquivos executáveis, bibliotecas, componentes de software, documentos e bancos de dados.

- **[Instâncias do Artefato](https://www.ibm.com/docs/pt-br/SS4JE2_7.5.5/com.ibm.xtools.modeler.doc/topics/cartinst.html)**

  Em modelagem UML, uma instância do artefato é um elemento de modelo que representa uma instanciação ou uma ocorrência real de um artefato. As instâncias do artefato baseiam-se nos artefatos existentes.

- **[Dispositivos](https://www.ibm.com/docs/pt-br/SS4JE2_7.5.5/com.ibm.xtools.modeler.doc/topics/cdevice.html)**

  Em diagramas de implementação, um dispositivo é um tipo de nó que representa um recurso computacional físico em um sistema, como um servidor de aplicativos.

- **[Especificações de Implementação](https://www.ibm.com/docs/pt-br/SS4JE2_7.5.5/com.ibm.xtools.modeler.doc/topics/cdeployspec.html)**

  Uma especificação de implementação é basicamente um arquivo de configuração, como um documento XML ou um arquivo de texto, que define como um artefato é implementado em um nó.

- **[Relacionamentos em Diagramas de Implementação](https://www.ibm.com/docs/pt-br/SS4JE2_7.5.5/com.ibm.xtools.modeler.doc/topics/crelsme_depd.html)**

  Na UML, um relacionamento é uma conexão entre elementos de modelo. Um relacionamento UML é um tipo de elementos de modelo que inclui semântica em um modelo, definindo a estrutura e o comportamento entre os elementos de modelo.

**Tarefas relacionadas**

- [Modelando a Visualização de Implementação e Topologia de um Aplicativo](https://www.ibm.com/docs/pt-br/SS4JE2_7.5.5/com.ibm.xtools.modeler.doc/topics/twrkdepd.html "Você pode utilizar diagramas de implementação para modelar o layout físico ou topologia de um sistema. Os diagramas de implementação descrevem a configuração de nós de processamento do tempo de execução e os artefatos que são implementados neles.")

- [Especificando a Implementação de Artefatos em Nós](https://www.ibm.com/docs/pt-br/SS4JE2_7.5.5/com.ibm.xtools.modeler.doc/topics/tdeployart.html "Na modelagem UML, implemente artefatos em nós para indicar que o nó suporta a implementação de instâncias desses artefatos quando o sistema é executado.")
