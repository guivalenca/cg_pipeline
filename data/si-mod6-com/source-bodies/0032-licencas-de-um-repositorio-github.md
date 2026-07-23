---
id: "32"
title: "Licenças de um Repositório GitHub"
source_url: "https://docs.github.com/pt/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository"
fetch_url: "https://docs.github.com/pt/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository"
resolved_url: "https://docs.github.com/pt/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository"
firecrawl_title: "Licenciar um repositório - Documentos do GitHub"
description: "Repositórios públicos em GitHub geralmente são usados para compartilhar open source software. Para que seu repositório seja realmente open source, você precisará licenciar para que outras pessoas sejam livres para usar, alterar e distribuir o software."
fetched_at: "2026-05-12T03:59:51.593575Z"
provider: "firecrawl"
strategy: "app_ui"
cache_key: "82527eb2d8935d439b386c24a05b451fe3cf2a13a5509ac25415698c563699e1"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=utf-8"
word_count: 1357
char_count: 8919
content_sha256: "ddfc9fc74a485d7fd0fbb4f71d2dc374f753b15857ca2af54986bfbd5f91ff71"
image_count: 0
link_count: 17
warnings: []
gate_status: "passed"
gate_failures: []
route_notes:
  - "github_docs_navigation_heavy"
---

# Licenciar um repositório

Repositórios públicos em GitHub geralmente são usados para compartilhar open source software. Para que seu repositório seja realmente open source, você precisará licenciar para que outras pessoas sejam livres para usar, alterar e distribuir o software.

## Neste artigo

## [Escolher a licença ideal](https://docs.github.com/pt/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository#choosing-the-right-license)

Criamos [choosealicense.com](https://choosealicense.com/) para ajudar você a entender como licenciar seu código. Uma licença de software descreve o que pode e não pode ser feito com seu código-fonte, assim é importante tomar uma decisão fundamentada.

Você não tem qualquer obrigação de escolher uma licença. Entretanto, sem uma licença, são aplicadas as leis padrão de copyright, o que significa que você detém todos os direitos de seu código-fonte e ninguém poderá reproduzir, distribuir ou criar derivativos de seu trabalho. Se você estiver criando um projeto open source, recomendamos que você inclua uma licença de open source. O [Guia de Código Aberto](https://opensource.guide/legal/#which-open-source-license-is-appropriate-for-my-project) fornece diretrizes adicionais sobre como escolher a licença correta para seu projeto.

Observação

Se você publicar o código-fonte em um repositório público do GitHub, de acordo com os [Termos de Serviço](https://docs.github.com/pt/site-policy/github-terms/github-terms-of-service), outros usuários do GitHub.com terão o direito de ver seu repositório e criar forks dele. Se você já criou um repositório e não quer mais que os usuários tenham acesso a ele, você pode torná-lo privado. Ao alterar a visibilidade de um repositório para privado, as bifurcações existentes ou cópias locais criadas por outros usuários continuarão existindo. Para saber mais, confira [Definir a visibilidade do repositório](https://docs.github.com/pt/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).

## [Identificar a localização da sua licença](https://docs.github.com/pt/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository#determining-the-location-of-your-license)

A maioria das pessoas coloca o texto da licença em um arquivo chamado `LICENSE.txt` (`LICENSE.md` ou `LICENSE.rst`) na raiz do repositório. [Veja um exemplo do Hubot](https://github.com/hubotio/hubot/blob/main/LICENSE.md).

Alguns projetos incluem as informações sobre a licença no README. Por exemplo, um README de um projeto pode incluir uma observação declarando "Este projeto está licenciado nos termos da licença MIT."

Como uma prática recomendada, incentivamos que você inclua o arquivo da licença no seu projeto.

## [Pesquisando GitHub por tipo de licença](https://docs.github.com/pt/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository#searching-github-by-license-type)

É possível filtrar os repositórios com base nas licenças ou na família de licenças usando o qualificador `license` e a palavra-chave exata da licença.

| Licença | Palavra-chave da licença |
| --- | --- |
| Licença Academic Free v3.0 | `AFL-3.0` |
| Licença do Apache 2.0 | `Apache-2.0` |
| Licença artística 2.0 | `Artistic-2.0` |
| Licença Boost Software 1.0 | `BSL-1.0` |
| Licença BSD de 2 cláusulas "Simplificada" | `BSD-2-Clause` |
| Licença BSD de "3 cláusulas" "Nova" ou "Revisada" | `BSD-3-Clause` |
| Licença Completa de três cláusulas do BSD | `BSD-3-Clause-Clear` |
| Licença "original" ou "antiga" de quatro cláusulas do BSD | `BSD-4-Clause` |
| Licença de zero cláusula do BSD | `0BSD` |
| Família de licenças do Creative Commons | `CC` |
| Creative Commons Zero v1.0 Universal | `CC0-1.0` |
| Atribuição Creative Commons 4.0 | `CC-BY-4.0` |
| Creative Commons Attribution ShareAlike 4.0 | `CC-BY-SA-4.0` |
| Licença pública WTFPL | `WTFPL` |
| Licença da Comunidade Educacional v2.0 | `ECL-2.0` |
| Licença Pública do Eclipse 1.0 | `EPL-1.0` |
| Licença Pública do Eclipse 2.0 | `EPL-2.0` |
| Licença Pública da União Europeia 1.1 | `EUPL-1.1` |
| Licença Pública Geral do LGNU Affero v3.0 | `AGPL-3.0` |
| Família de Licenças Públicas Gerais do GNU | `GPL` |
| Licença Pública Geral do GNU v2.0 | `GPL-2.0` |
| Licença Pública Geral do GNU v3.0 | `GPL-3.0` |
| Família de Licenças Públicas Gerais Menores do GNU | `LGPL` |
| Licença Pública Geral Menor do GNU v2.1 | `LGPL-2.1` |
| Licença Pública Geral Menor do GNU v3.0 | `LGPL-3.0` |
| ISC | `ISC` |
| Licença Pública do LaTeX Project v1.3c | `LPPL-1.3c` |
| Licença Pública da Microsoft | `MS-PL` |
| MIT | `MIT` |
| Licença Pública Mozilla 2.0 | `MPL-2.0` |
| Licença de Software Livre 3.0 | `OSL-3.0` |
| Licença do PostgreSQL | `PostgreSQL` |
| Licença Sil Open Font 1.1 | `OFL-1.1` |
| Licença de Código Aberto da University of Illinois/NCSA | `NCSA` |
| A Unlicense | `Unlicense` |
| Licença zLib | `Zlib` |

Quando você pesquisar uma família de licenças, os resultados incluirão todas as licenças daquela família. Por exemplo, quando você usar a consulta `license:gpl`, os resultados incluirão os repositórios licenciados sob a Licença Pública Geral do GNU v2.0 e a Licença Pública Geral do GNU v3.0. Para saber mais, confira [Pesquisar repositórios](https://docs.github.com/pt/search-github/searching-on-github/searching-for-repositories#search-by-license).

## [Identificar uma licença](https://docs.github.com/pt/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository#detecting-a-license)

```
          [O arquivo open source Ruby gem Licensee](https://github.com/licensee/licensee) compara o arquivo _LICENSE_ do repositório a uma breve lista de licenças conhecidas. O Licensee também fornece a [API de Licenças](/rest/licenses) e [fornece informações sobre como os repositórios do GitHub são licenciados](https://github.com/blog/1964-open-source-license-usage-on-github-com). Se o repositório estiver usando uma licença que não está listada no [site Escolher uma Licença](https://choosealicense.com/appendix/), você poderá [solicitar a inclusão da licença](https://github.com/github/choosealicense.com/blob/gh-pages/CONTRIBUTING.md#adding-a-license).
```

Caso o seu repositório use uma licença listada no site Choose a License que não aparece na parte superior da página do repositório, ele pode conter licenças múltiplas ou outras complexidades. Para que sua licença seja identificada, simplifique o arquivo _LICENSE_ e anote a complexidade em algum outro local, como no arquivo _LEIAME_ do repositório.

## [Aplicar uma licença em um repositório com uma licença existente](https://docs.github.com/pt/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository#applying-a-license-to-a-repository-with-an-existing-license)

O seletor de licença só está disponível quando você cria um novo projeto no GitHub.

```
          [Unavailable image: Captura de tela da seção "Escolher uma licença" da nova página do repositório, incluindo um menu suspenso rotulado como "Licença."](/assets/images/help/repository/repository-license-picker.png)
```

Você pode adicionar uma licença manualmente usando o navegador. Para obter mais informações sobre como adicionar uma licença a um repositório, confira [Adicionar uma licença a um repositório](https://docs.github.com/pt/communities/setting-up-your-project-for-healthy-contributions/adding-a-license-to-a-repository).

## [Isenção de responsabilidade](https://docs.github.com/pt/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository#disclaimer)

O objetivo dos esforços de licenciamento open source da GitHub é fornecer um ponto de partida para ajudá-lo a fazer uma escolha informada. GitHub exibe informações de licença para ajudar os usuários a obter informações sobre licenças open source e os projetos que as usam. Esperamos que seja útil, mas esteja ciente de que não somos advogados e que cometemos erros como qualquer pessoa. Por esse motivo, GitHub fornece as informações em uma base "as-is" e não faz garantias sobre quaisquer informações ou licenças fornecidas sobre ou através dela, e se isenta de responsabilidade por danos resultantes do uso das informações de licença. Se você tiver quaisquer dúvidas com relação à licença ideal para seu código ou quaisquer outras questões legais relacionadas a ele, sempre é melhor consultar um profissional.

## [Leitura adicional](https://docs.github.com/pt/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository#further-reading)

- A seção Guias de Código Aberto [O Lado Legal do Código Aberto](https://opensource.guide/legal/)
- [GitHub Skills](https://skills.github.com/)
