<script setup>
import { ref } from 'vue'

const replayText = ref('')
const loading = ref(false)

const result = ref(null)

async function analyzeBattle() {
  if (!replayText.value.trim()) return

  loading.value = true

  try {
    const replayJson = JSON.parse(replayText.value)

    const response = await fetch('http://localhost:8000/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        log_text: replayJson.log,
        format_id: replayJson.formatid,
        winner: replayJson.players?.[0]
      })
    })

    result.value = await response.json()
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="container">
    <h1>Scope Lens</h1>
    <p>Insights para batalhas Pokémon</p>

    <textarea
      v-model="replayText"
      placeholder="Cole aqui o replay ou JSON"
    />

    <button
      @click="analyzeBattle"
      :disabled="loading"
    >
      {{ loading ? 'Analisando...' : 'Analisar' }}
    </button>

    <section v-if="result" class="results">
      <h2>Resultado</h2>

      <div class="cards">
        <div class="card">
          <h3>KOs</h3>
          <p>{{ result.total_kos }}</p>
        </div>

        <div class="card">
          <h3>Dano</h3>
          <p>{{ result.total_damage }}</p>
        </div>

        <div class="card">
          <h3>MVP</h3>
          <p>{{ result.mvp }}</p>
        </div>
      </div>

      <h2>Eventos</h2>

      <ul>
        <li
          v-for="(event, index) in result.events"
          :key="index"
        >
          Turno {{ event.turn }} -
          {{ event.source }}
          →
          {{ event.target }}
        </li>
      </ul>
    </section>
  </main>
</template>

<style scoped>
.container {
  max-width: 1000px;
  margin: auto;
  padding: 2rem;
  font-family: Arial, sans-serif;
}

textarea {
  width: 100%;
  min-height: 250px;
  margin-top: 1rem;
  padding: 1rem;
}

button {
  margin-top: 1rem;
  padding: 0.8rem 1.4rem;
  cursor: pointer;
}

.cards {
  display: flex;
  gap: 1rem;
  margin: 1rem 0;
}

.card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  min-width: 150px;
}

.results {
  margin-top: 2rem;
}
</style>