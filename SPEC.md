# Spec: Vendor Spend & Renewal Cockpit

Especificação técnica do projeto (em português), usada como fonte de verdade para o código. O código, os dados e a documentação estão em inglês. Todos os dados são sintéticos.

## Especificação para o Claude Code

O Claude Code entrega a camada de dados e lógica: dados sintéticos com padrões plantados, forecast, decomposição da variação e regras de recomendação. Tudo reprodutível com uma semente fixa e coberto por testes.

### Repositório

```
vendor-renewal-cockpit/
  README.md              problema, método, resultados, limitações
  docs/methodology.md    premissas do forecast e das regras
  config.yaml            semente, data-âncora, IPCA, limiares
  src/
    generate.py          dados sintéticos
    forecast.py          projeção até o fim do ano e 12 meses
    variance.py          preço, volume e fornecedor não orçado
    recommend.py         renovar, renegociar, ajustar, consolidar, encerrar
    contracts_pdf.py     3 contratos de exemplo em PDF
    export.py            CSVs para o Supabase
  sql/schema.sql         tabelas e views para o Supabase
  data/processed/        CSVs gerados
  tests/
```

### Esquema de dados

| Tabela | Colunas principais |
| --- | --- |
| vendors | vendor\_id, name (fictício), category, owner\_department, criticality, risk\_tier |
| contracts | contract\_id, vendor\_id, start\_date, end\_date, auto\_renew, notice\_days, billing\_model, unit\_price, seats\_contracted, annual\_value, price\_escalator\_pct, termination\_fee, status |
| monthly\_spend | month, vendor\_id, contract\_id, actual\_amount, seats\_active, units\_used |
| budget | month, vendor\_id, budget\_qty, budget\_unit\_price, budget\_amount |
| headcount | month, department, headcount |
| benchmarks | vendor\_id, list\_price\_per\_seat, source\_url, as\_of |
| savings | event\_id, vendor\_id, date, type, baseline\_price, negotiated\_price, annualized\_impact, note |

- **category:** SaaS, Cloud, Marketing, Professional services, Data and security.
- **billing\_model:** per\_seat, usage, fixed.
- **status:** onboarding, active, renewal\_window, renegotiating, terminated.
- **savings.type:** saving (contra o preço anterior) ou cost\_avoidance (contra a primeira cotação, para itens sem histórico).

### Regras do gerador

- 40 fornecedores, 18 meses (jun/2025 a nov/2026), moeda BRL, semente fixa.
- Data-âncora configurável ("hoje" do cenário), para que as renovações próximas existam sempre.
- Padrões plantados, para o produto ter o que encontrar:
  - 3 grupos de ferramentas sobrepostas (ex.: três de videoconferência, duas de assinatura eletrônica).
  - 5 contratos por licença com utilização abaixo de 60%.
  - 2 contratos com reajuste acima do IPCA configurado.
  - 6 renovações nos próximos 90 dias, 2 delas com renovação automática e aviso prévio já perto de vencer.
  - 1 fornecedor sem linha de orçamento surgindo no meio do ano.
  - Nuvem crescendo com o uso; marketing com picos sazonais.
- Benchmarks: preço de tabela público real, com URL e data, só para os fornecedores com preço publicado. Os demais ficam sem benchmark.
- Nomes de fornecedores fictícios.

### Forecast

| Modelo de cobrança | Regra |
| --- | --- |
| per\_seat | licenças = headcount do departamento × taxa de adoção observada; preço com reajuste aplicado na data de renovação |
| usage | tendência dos últimos 6 meses mais sazonalidade mensal |
| fixed | valor anual do contrato / 12 até o fim da vigência |

Saída: **landing do ano** = realizado acumulado + forecast do restante, comparado ao orçamento anual, por fornecedor e por categoria.

### Decomposição da variação

```latex
\text{Variação total} = \underbrace{(P_{real} - P_{orc}) \times Q_{real}}_{\text{preço}} + \underbrace{(Q_{real} - Q_{orc}) \times P_{orc}}_{\text{volume}} + \underbrace{\text{gasto sem orçamento}}_{\text{não orçado}}
```

O teste principal verifica que os três componentes somam exatamente a variação total.

### Regras de recomendação

Aplicadas a todo contrato a até 120 dias da renovação, nesta ordem de prioridade:

| Condição | Recomendação | Impacto estimado |
| --- | --- | --- |
| Criticidade baixa e utilização abaixo de 20% | Encerrar | Valor anual menos multa de rescisão |
| Fornecedor em grupo sobreposto | Consolidar no de maior utilização ou menor preço | Soma dos contratos eliminados |
| Utilização abaixo de 60% | Ajustar licenças ao pico de uso + 10% | Licenças cortadas × preço |
| Preço acima do benchmark ou reajuste acima do IPCA | Renegociar | Diferença até o benchmark ou até o IPCA |
| Nenhuma das anteriores | Renovar | Zero |

Cada recomendação traz o **prazo de decisão** = data de término menos aviso prévio. Todos os limiares ficam no config.yaml.

### Testes mínimos

- Mesma semente gera os mesmos dados.
- Componentes da variação somam a variação total.
- Forecast nunca negativo.
- Prazo de decisão sempre anterior à data de término.
- Cada padrão plantado é encontrado pela regra correspondente.
- Nenhum nome real de fornecedor fora da tabela de benchmarks.
