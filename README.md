#  Scope Lens — Notas

O **Scope Lens** é uma ferramenta de "autópsia" para replays de Pokémon Showdown. O objetivo é transformar o log bruto do simulador em uma análise estratégica que identifique onde a partida foi ganha ou perdida.

---

## Stack e Setup
*   **Backend:** Python 3.10+ com FastAPI.
    *   `poke-env`: Biblioteca core. Ela reconstrói o estado da batalha (não vamos fazer parsing de texto na mão, não faz sentido).
    *   `httpx`: Para buscar os logs das URLs do Showdown.
    *   `usage-stats`: Pode ser útil, mas só mostra as estatisticas do servidor no geral
*   **Frontend:** Vue.js 3 + Tailwind + Pinia.
    *   **Pinia**: Essencial. Vai centralizar o JSON da análise para que todos os componentes (gráficos e listas) acessem o mesmo dado.
*   **Data Source:** Usar os arquivos `pokedex.json` e `moves.json` (do repositório do Showdown) como base de dados estática para tipos, base stats e efeitos.

---

## A Lógica
Para não ser só um contador de dano, o sistema precisa rodar uma **simulação fantasma** da batalha em memória:

1.  **Reconstituição de Estado (Shadow State):** O log diz apenas nomes. O backend precisa cruzar com a Pokedex para saber Tipagens, Abilities e Base Stats. Smogon oferece isso
2.  **Momentum Score:** Cada turno precisa de um peso. 
    *   Nocautes (KOs) = Pontuação alta.
    *   Setups (Trick Room, Tailwind, Weather) = Pontuação constante enquanto ativos.
    *   Erros (Misses, Protect duplo) = Pontuação negativa.
3.  **Turning Point:** O motor de análise deve varrer o gráfico de vantagem e marcar o turno exato onde a curva mudou de direção bruscamente.
4.  **Inferência de Build:** Baseado no dano causado/recebido, o sistema deve "chutar" se o Pokémon é ofensivo ou defensivo (útil para portfólio).

---

## Roadmap

### Fase 1: Ingestão e Processamento Básico (MVP)
*   [ ] **Ingestion:** Rota que aceita URL do Showdown e baixa o `.json` do replay.
*   [ ] **Parsing:** Integrar `poke-env` para extrair lista de turnos, Pokémon vivos e HP restante.
*   [ ] **Front Básico:** Campo de input para link e uma lista simples renderizando os turnos no Vue.

### Fase 2: Inteligência e Análise
*   [ ] **Gráfico de Momentum:** Plotar a oscilação de vantagem (quem estava ganhando em cada turno).
*   [ ] **MVP da Partida:** Algoritmo para definir o Pokémon de maior impacto (baseado em dano, KOs e suporte).
*   [ ] **Reveals:** Lista automática de Itens e Abilities revelados durante o jogo.

### Fase 3: Polimento e UX
*   [ ] **Insights Automáticos:** Gerar frases tipo: *"O Trick Room no turno X anulou a velocidade do oponente"* (Laughs in Mega Ampharos).
*   [ ] **Timeline Interativa:** Clicar no turno no gráfico e ver o estado do campo naquele momento.

---

## Notas de Integração

*   **API Contract:** O Python deve devolver um JSON processado, nunca o log bruto. O Vue só deve se preocupar em exibir os dados.
*   **CORS:** Configurar o middleware no FastAPI para liberar o `localhost:5173`.
*   **Estrutura de Pastas:**
```text
/backend
  /app
    /engine (lógica de análise e momentum)
    /parser (reconstituição via poke-env)
    main.py (endpoints do fastapi)
/frontend
  /src
    /stores (pinia store para os dados do replay)
    /components (gráficos e cards de pokémon)