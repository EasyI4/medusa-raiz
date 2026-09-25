# Design system · Autocenter IA

O frontend segue a linguagem visual do projeto `ExemploDeFrontend`, adaptada para Nuxt/Vue e para a marca Medusa Autocenter.

## Fundamentos

- **Marca:** verde `--color-brand-*`, com `--color-brand-500` como ação principal.
- **Superfícies:** canvas cinza-claro, cards brancos e sidebar neutra.
- **Estados:** `success`, `info`, `warning` e `danger` nunca dependem apenas da cor; os componentes também exibem texto.
- **Tipografia:** Manrope para interface e a pilha monoespaçada para códigos de peças.
- **Forma:** raios entre `--radius-sm` e `--radius-2xl`; botões circulares usam `--radius-round`.
- **Elevação:** três níveis (`--shadow-xs`, `--shadow-sm` e `--shadow-md`).
- **Movimento:** transições rápidas e desativação automática com `prefers-reduced-motion`.

Os tokens ficam em `assets/css/tokens.css`. Não use valores de marca diretamente em componentes quando já houver um token equivalente.

## Componentes-base

Os componentes reutilizáveis ficam em `components/ui`:

- `DsButton`: variantes `primary`, `secondary`, `ghost` e `danger`; tamanhos `sm`, `md` e `lg`.
- `DsIcon`: biblioteca de ícones lineares usada pela interface.
- `DsBrand`: assinatura de marca com subtítulo configurável.

Campos usam as classes `ds-field`, `ds-field__label` e `ds-input`. Indicadores curtos usam `ds-badge`.

## Organização do CSS

- `base.css`: reset, acessibilidade e comportamento global.
- `components.css`: primitivos do design system.
- `auth.css`: login e estados de configuração.
- `chat.css`: shell, sidebar, histórico, mensagens e compositor.
- `catalog.css`: resumo, compatibilidade, cards e aplicações de peças.

`main.css` é apenas o ponto de entrada desses módulos.

## Regras de uso

1. Priorize tokens e componentes-base antes de criar novos padrões.
2. Preserve contraste, foco visível e rótulos acessíveis em ações só com ícone.
3. Use verde para ação/êxito, azul para informação, âmbar para atenção e vermelho para erro.
4. Códigos de peça devem manter fonte monoespaçada e ação explícita de cópia.
5. Novos layouts devem funcionar nos breakpoints de 800 px e 520 px já adotados.
