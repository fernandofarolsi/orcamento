# 📝 Histórico de Implementações - Adore Móveis

Este arquivo registra as principais funcionalidades e melhorias implementadas no sistema.

---

## 📅 03/02/2026

### 🏠 Orçamentos & Ambientes (Abas)
- **Interface por Abas**: Agora é possível organizar os itens do orçamento por ambientes (Cozinha, Quarto, Banheiro, etc).
- **Campos Detalhados**: Cada ambiente possui Código do Item (.001, .002...), Descrição, Quantidade, Ambiente e Material.
- **Cálculos Automáticos**: O total do orçamento agora considera a quantidade de cada ambiente e seus respectivos insumos.

### � Correção Definitiva - Edição de Orçamentos
- **Debug Implementado**: Console.log para rastrear carregamento de dados e execução
- **Exibição Forçada**: Área de conteúdo (`tabContentArea`) agora é forçada a `display: block`
- **Timing Corrigido**: Chamadas das funções reorganizadas para garantir execução correta
- **Validação Melhorada**: Verificação de existência de elementos antes da manipulação
- **Resultado Final**: Edição de orçamentos funcionando 100% com exibição completa de itens e abas

### 🛠️ Correção Crítica - Templates de Propostas e Contratos
- **Erro Identificado**: `TypeError: 'builtin_function_or_method' object is not iterable`
- **Causa**: `items` é palavra reservada no Jinja2, conflitando com `group.items`
- **Solução**: Convertido `items` para `itens` em todo o fluxo:
  - Templates: `proposta_print.html` e `contrato_print.html`
  - Backend: Rotas `/proposta/<id>` e `/contrato/<id>`
- **Resultado**: Propostas e contratos funcionando sem erro 500

### 🔧 Correção Final - Templates de Propostas e Contratos
- **Referência Restante**: Encontrada e corrigida última ocorrência de `group.items` em `contrato_print.html`
- **Verificação Completa**: Todos os templates agora usam `group.itens` consistentemente
- **Resultado Final**: Propostas e contratos 100% funcionais sem erros

### 🎨 Correção Visual - Modal de Raspagem
- **Problema**: Modal de raspagem aparecia sem CSS adequado, podendo ficar visível indevidamente
- **Causa**: CSS `.modal` não estava definido no `estoque.html`, apenas no `financeiro.html`
- **Solução**: Adicionado CSS completo para modal no `estoque.html` com `display: none !important`
- **Resultado**: Modal agora fica corretamente oculto e só aparece quando acionado pelo botão

### 👥 Módulo de Clientes - Novo Funcionalidade
- **Cadastro Completo**: Sistema completo de gerenciamento de clientes com todos os dados necessários
- **Interface Profissional**: Formulário organizado em seções (Dados Pessoais, Contato, Endereço, Informações Adicionais)
- **Busca e Filtros**: Filtros por nome, CPF, email, status e cidade para localização rápida
- **Validações**: Formatação automática de CPF/CNPJ, telefone, WhatsApp e CEP
- **Busca de CEP**: Integração com ViaCEP para preenchimento automático do endereço
- **API Completa**: Rotas GET, POST, PUT, DELETE para gerenciamento via API
- **Integração**: Tabela clientes criada e vinculada aos orçamentos (client_id)
- **Menu Atualizado**: Link "Clientes" adicionado ao menu lateral
- **Manual Atualizado**: Seção completa de Clientes adicionada ao manual do usuário

### 🔗 Integração Clientes-Orçamentos
- **Seleção de Clientes**: Campo "Cliente" em orçamentos agora é um select com todos os clientes cadastrados
- **Link Rápido**: Botão "+ Cadastrar novo cliente" que abre em nova aba
- **Vínculo Automático**: Orçamentos salvos com client_id e nome do cliente
- **Edição Compatível**: Orçamentos existentes continuam funcionando e novos são vinculados
- **Backend Atualizado**: Rotas POST e PUT agora aceitam e salvam client_id
- **Carregamento Dinâmico**: Lista de clientes carregada automaticamente ao abrir orçamentos
- **Exibição Inteligente**: Select mostra "Nome (Cidade)" para fácil identificação

### ⚡ Cadastro Rápido de Cliente em Orçamentos
- **Modal Simplificado**: Cadastro rápido direto na página de orçamentos sem sair da tela
- **Campos Essenciais**: Apenas nome, telefone (obrigatórios) + email e observações (opcionais)
- **Fluxo Otimizado**: Cadastra e seleciona automaticamente o cliente no orçamento
- **Formatação Automática**: Telefone formatado automaticamente (00) 00000-0000
- **Integração Perfeita**: Cliente criado aparece imediatamente no select de clientes
- **Complemento Posterior**: Usuário pode completar cadastro completo depois em Clientes → Editar
- **Manual Atualizado**: Seção de cadastro rápido adicionada ao manual do usuário

### 📅 Calendário Integrado no Kanban
- **3 Meses Visíveis**: Mês anterior, atual e próximo mês lado a lado
- **Integração Automática**: Busca dados de orçamentos, contas a pagar e receber
- **Eventos Coloridos**: 🔵 Prazos de projetos, 🔴 Contas a pagar, 🟢 Contas a receber, 🟡 Instalações
- **Visual Interativo**: Clique em qualquer dia para ver detalhes dos eventos
- **Modal de Detalhes**: Exibe todos os eventos do dia com opção de editar data
- **Design Responsivo**: Calendários compactos com pontos indicadores de eventos
- **API Financeira**: Rotas para contas a receber/pagar e orçamentos com datas
- **Banco de Dados**: Tabelas contas_receber, contas_pagar e colunas de datas em orcamentos
- **Identificação Visual**: Dia atual destacado, dias com eventos bordados
- **Legenda Completa**: Cores e tipos de eventos claramente identificados

### 📋 IDEIAS FUTURAS - ROADMAP

#### 🗓️ Integração Google Calendar (Planejado)
- **Objetivo**: Sincronizar eventos com Google Calendar para notificações no celular
- **Funcionalidades**:
  - Autenticação OAuth2 com conta Google
  - Sincronização automática de prazos e contas
  - Notificações push no celular
  - Lembretes inteligentes (1 dia antes, 1 hora antes)
  - Multiplataforma (Android, iOS, Web)
- **Benefícios**:
  - Alertas automáticos no celular
  - Integração com calendário pessoal
  - Acesso offline via app Google Calendar
  - Backup automático de eventos
- **Complexidade**: Média (requer setup OAuth2 e Google Cloud Console)
- **Custo**: Gratuito (até 10.000 requisições/dia)
- **Status**: ✅ Planejado para implementação futura

### 🎨 CSS CONSOLIDADO - UNIFICAÇÃO COMPLETA
- **Arquivo Único**: `/static/css/consolidado.css` com todos os estilos do sistema
- **Templates Atualizadas**: Todas as 13 templates agora usam o CSS consolidado
- **Estilos Inline Removidos**: Limpeza completa de styles inline
- **Manutenção Facilitada**: CSS centralizado em um único arquivo
- **Consistência Garantida**: Mesmos estilos em todas as páginas

#### **📄 Templates Atualizadas:**
- ✅ **kanban.html**: CSS consolidado + classes utilitárias
- ✅ **orcamentos.html**: CSS consolidado + modal clientes
- ✅ **catalogo.html**: CSS consolidado + botões padrão
- ✅ **clientes.html**: CSS consolidado + filtros
- ✅ **estoque.html**: CSS consolidado + botão raspagem individual
- ✅ **financeiro.html**: CSS consolidado + abas
- ✅ **settings.html**: CSS consolidado + cards
- ✅ **relatorios.html**: CSS consolidado + exportação
- ✅ **login.html**: CSS consolidado + autenticação
- ✅ **dashboard_kpi.html**: CSS consolidado + KPI cards
- ✅ **proposta_print.html**: CSS consolidado + impressão
- ✅ **contrato_print.html**: CSS consolidado + impressão

#### **🎨 Seções CSS Adicionadas:**
- **Variáveis CSS**: Cores e espaçamentos padronizados
- **Estilos Gerais**: Botões, formulários, tabelas
- **Kanban**: Grid, cards, calendário integrado
- **Calendário**: Meses, dias, eventos, modais
- **Modais**: Geral e específicos (clientes, eventos)
- **Tooltips**: Explicativos e informativos
- **Abas e Tabs**: Navegação por abas
- **Autenticação**: Login e cards
- **KPI Dashboard**: Cards de métricas
- **Responsivo**: Media queries para mobile
- **Utilitários**: Classes helper (mb-, mt-, flex-, etc)

#### **🚀 Benefícios Alcançados:**
- ✅ **Performance**: Cache do CSS em arquivo único
- ✅ **Manutenção**: Alteração em um só lugar afeta todo sistema
- ✅ **Consistência**: Estilos unificados em todas páginas
- ✅ **Organização**: Código limpo e estruturado
- ✅ **Escalabilidade**: Fácil adicionar novos estilos
- ✅ **Profissionalismo**: Interface padronizada e coesa

---

### 💎 Proposta Comercial & Renders (Unidade: mm)
- Mudança de escala de metros (m) para milímetros (mm) em todo o sistema (Orçamentos, Catálogo, Proposta).
- Implementação de imagens por ambiente nos orçamentos e exibição na proposta comercial. Agora as fotos/renders são vinculadas a cada ambiente (aba) do orçamento, e não ao catálogo global. Isso permite usar desenhos específicos de cada projeto.
- **Carga de Dados**: Edição carrega abas, itens, valores e totais automaticamente
- **Margem de Segurança (Precificação)**: O sistema agora usa automaticamente o **maior preço** encontrado para cada material nos orçamentos, protegendo o lucro contra faltas de estoque. 
- **Relatório de Melhor Compra**: Novo relatório que identifica onde comprar cada material pelo menor preço, mostrando o potencial de economia.
- **Expansão do Kanban**: Kanban expandido para 7 etapas: Contato, Medição, Projeto, Orçamento, Produção, Instalação e Concluído.
- **Campos Editáveis**: Condições comerciais da proposta (prazo, garantia, etc) podem ser editadas na hora da impressão.
- **Layout Profissional**: Modelo de proposta com miniaturas de imagens, ideal para apresentação ao cliente.
- **Faturamento Detalhado**: No momento de faturar, é possível escolher o método de pagamento (Pix, Boleto, Cartão, etc), definir entrada e o número de parcelas.
- **Contas a Receber**: O faturamento gera automaticamente as contas a receber (Entrada e Parcelas) no Financeiro.
- **Refinamento de Estrutura**: Unificação do menu lateral no `base.html` com destaque dinâmico da página ativa.
- **Página de Configurações**: Nova página para centralizar Valor da Hora Fábrica e agenda de raspagem automática.
- **URLs de Fornecedores**: Suporte para salvar links específicos da Madeiranit, Leo Madeiras e Madeverde no estoque.
- **Automação de Preço**: Cálculo automático no catálogo usando margem de segurança e valor da hora.
- **Método Valci Goulart (Simplificado)**: Implementação do cálculo de orçamento por centro de custo com margens cascateadas (35% Lucro, 10% Negoc, 5% Imposto), integrado ao custo de produção global da fábrica.
- **Configuração Integrada**: Custos fixos e margens agora podem ser ajustados diretamente no momento do orçamento ou definidos como padrão nas configurações.
- **KPI de Margem**: Novo indicador no Dashboard mostrando a margem média projetada dos projetos.
- **Correção de Layout**: Resolvido conflito onde a sidebar aparecia na tela de login, quebrando o formulário.

---

## 📅 04/02/2026

### 🎨 Normalização da Interface do Catálogo
- **Formulários Padronizados**: Todos os inputs e selects do catálogo agora usam classes CSS consistentes (`form-input`).
- **Botões Normalizados**: Removido estilos inline e implementado classes padrão:
  - `btn-small` para botões compactos (botão "+")
  - `btn-success` para botões de sucesso (botão "Aplicar") 
  - `btn-secondary` para botões secundários (botão "Cancelar")
- **Interface Consistente**: Catálogo agora segue o mesmo padrão visual do resto do sistema.

### 🔧 Cálculo Proporcional em Orçamentos
- **Preview em Tempo Real**: Adicionada área de preview que mostra o valor do item enquanto ajusta as dimensões.
- **Cálculo Proporcional Corrigido**: Itens com componentes agora recalculam automaticamente ao alterar L, A, P ou complexidade.
- **Eventos Automáticos**: Campos de dimensão e complexidade agora possuem `oninput`/`onchange` para recálculo instantâneo.
- **Detalhamento do Valor**: Preview mostra separadamente: Material + Mão de Obra + Acessórios.

### 💰 Correção de Custos dos Materiais
- **Valores Corrigidos**: Ajustadas quantidades excessivas nos componentes dos itens:
  - Item "gh": Reduzido de 500 para 2 unidades de Sarrafo Pinus (R$ 10,00 total)
  - Item "ll": Reduzido de 1 para 0.5 unidades de MDF Branco (R$ 73,10 total)
- **Cálculo Proporcional**: Agora os valores recalculam corretamente ao alterar dimensões.

### 📐 Cálculo por Volume Corrigido
- **Tipo de Cálculo Ajustado**: Item "ll" alterado de "fixo" para "volume":
  - Agora a quantidade de MDF é proporcional ao volume (L × A × P)
  - Se o volume dobra, a quantidade de material dobra
  - Ex: 10cm³ → 0.5 unidades, 20cm³ → 1.0 unidades
- **Funcionamento**: O cálculo agora responde proporcionalmente às dimensões informadas no orçamento.

### 💬 Tooltips Explicativos no Estoque
- **Ajuda Visual**: Adicionados ícones ⓘ com tooltips ao passar o mouse nos campos confusos:
  - **Unidade**: Explica quando usar Unidade/Metro/Quilo com exemplos práticos
  - **Área da Unidade**: Detalha como calcular área para chapas, fitas, etc
  - **É Acessório?**: Esclarece o uso como opcional nos orçamentos
  - **Site Origem**: Explica a diferença entre raspagem automática e controle manual
- **Interface Intuitiva**: Tooltips aparecem com explicações detalhadas ao passar o mouse, facilitando o entendimento.

### 🎨 Padronização CSS no Catálogo de Produtos
- **CSS Unificado**: Seção de componentes/insumos agora usa `form-group` como o resto do formulário
- **Espaçamento Corrigido**: Ajustado gap entre campos para manter consistência visual
- **Tooltips Adicionados**: Ícones ⓘ explicativos nos campos de componentes:
  - **Insumo**: Explica que são materiais do estoque que compõem o produto
  - **Qtd**: Detalha como funciona a quantidade base para cada tipo de cálculo
  - **Cálculo**: Mostra exemplos de cada tipo (Fixo, Área, Volume, Perímetro)
- **Botão Alinhado**: Botão "+" agora dentro de um form-group para alinhamento perfeito.

### 🔢 Melhoria na Usabilidade das Margens
- **Valores Intuitivos**: Margens agora exibidas como porcentagens inteiras (35, 10, 5) em vez de decimais (0.35, 0.10, 0.05)
- **Interface Simplificada**: Mais fácil de entender e editar sem alterar a lógica de cálculo
- **Conversão Automática**: Backend converte automaticamente entre inteiro (interface) e decimal (cálculos)
- **Consistência Mantida**: Fórmulas e resultados permanecem exatamente os mesmos

### � Correções de Funcionalidades Críticas

### � Contratos Profissionais
- **Layout de Impressão**: Modelo de contrato limpo e profissional focado no cliente.
- **Subtotais por Item**: Exibição clara do valor total de cada ambiente.
- **Privacidade Técnica**: Detalhes internos (insumos/materiais) e ambientes aparecem no sistema mas não são impressos no contrato do cliente, focando no que foi contratado.

### 🛠️ Catálogo de Insumos (Multi-Insumos)
- **Composição de Produtos**: Agora um item do catálogo (ex: Armário) pode ter vários insumos vinculados (MDF, Dobradiça, Fita de Borda).
- **Tipos de Cálculo Dinâmico**:
    - **Fixo**: Quantidade fixa por peça.
    - **Área (m²)**: Proporcional à Largura x Altura.
    - **Vol (m³)**: Proporcional ao Volume.
    - **Perímetro**: Proporcional ao contorno (ideal para fitas de borda).

---

## 📅 05/02/2026

### 🛠️ Correções no Módulo de Clientes
- **Modal de Cadastro**: Corrigido bug onde o modal aparecia aberto ao carregar a página. Adicionado `display: none` explícito.
- **Botão Novo Cliente**: Resolvido problema onde o botão não abria o modal. Ajustada a lógica JS para forçar `display: flex`.
- **Padronização Visual**: O modal de Clientes foi refatorado para usar o mesmo estilo "inline" e comportamento do modal de Orçamentos, garantindo consistência visual e funcional.
- **Mapeamento de Campos**: Corrigido erro de referência a IDs inexistentes (`endereco` -> `logradouro`, etc), garantindo que a edição carregue todos os dados corretamente.
- **Botão Faturar**: Corrigido bug no módulo de Orçamentos onde o botão de faturar não abria o modal devido a erro na leitura da resposta da API.
- **Lista de Orçamentos**: Implementada filtragem automática para ocultar orçamentos "Faturados". Adicionado botão "Ver Histórico (Faturados)" para consultar negócios fechados.
- **Layout de Busca**: Filtros de busca e status agora alinhados perfeitamente em uma única linha.
- **Visualização**: Ajuste de espaçamento e alinhamento dos campos de filtro para melhor usabilidade.

---
*Este arquivo será atualizado conforme novas funcionalidades forem implementadas.*
