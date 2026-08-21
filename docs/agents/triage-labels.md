# Triage Labels

Os skills falam em cinco papéis canônicos de triagem. Esta tabela mapeia cada papel para o
que existe de fato no Linear (time `DEV`).

| Papel nos skills  | No nosso tracker                | Significado                                           |
| ----------------- | ------------------------------- | ----------------------------------------------------- |
| `needs-triage`    | label `needs-triage`            | Ainda não avaliada. Toda issue nova entra aqui.       |
| `needs-info`      | label `needs-info`              | Parada esperando informação de quem reportou.         |
| `ready-for-agent` | label `ready-for-agent`         | Especificada o suficiente para um agente AFK tocar.   |
| `ready-for-human` | label `ready-for-human`         | Precisa de implementação ou decisão humana.           |
| `wontfix`         | **estado `Canceled`**           | Não será feita. Não existe label `wontfix`.           |

## O grupo `Triage` é seleção única

As quatro labels vivem no grupo `Triage` do time `DEV`. Grupo no Linear significa
**mutuamente exclusivas**: uma issue está em exatamente um estágio de triagem, e a
ferramenta impede o contrário. Isso é intencional — foi o motivo de usar grupo em vez de
labels soltas.

Consequência prática, porque `issueUpdate` **substitui** o conjunto inteiro de `labelIds`:
ao mover uma issue de estágio, monte o novo conjunto como *(labels atuais − qualquer label
do grupo `Triage`) + a nova*. Nunca mande duas do grupo na mesma lista, e nunca mande só a
nova — isso apagaria `Feature`, `Bug` e companhia.

## `wontfix` é estado, não label

Quando um skill disser "marque como wontfix": comente o porquê e mova a issue para
`Canceled`. O Linear já expressa isso nativamente; uma label seria uma segunda verdade
sobre a mesma coisa.

## Labels de tipo são outro eixo

`Feature`, `Bug`, `Improvement` e `Miscellaneous` existem nos dois times e continuam
valendo. Elas dizem **o que** a issue é; o grupo `Triage` diz **em que estágio** ela está.
São ortogonais — uma issue normalmente tem uma de cada. Não substitua uma pela outra.

## BISOPS não tem triagem

O time `BISOPS` tem só as labels de tipo (mais `Contabilidade`). Labels no Linear são por
time, então o grupo `Triage` não existe lá e nenhum skill roda no BISOPS. Se um dia isso
mudar, recrie o grupo e as quatro labels com `issueLabelCreate` usando o `teamId` do
BISOPS — não dá para compartilhar as do DEV.

## Histórico

O time `DEV` tinha um grupo `Next move` (External, Review, Shape, Agent, Founder) criado
às pressas. Foi apagado em 2026-08-21 ao adotar este vocabulário; as issues DEV-5, 6, 7,
8, 9 e 14 perderam a label `Founder` nesse processo.
