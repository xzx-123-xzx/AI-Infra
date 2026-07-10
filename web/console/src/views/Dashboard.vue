<script setup>
import { onMounted, ref } from 'vue'
import { api, loadSettings } from '../api'

const settings = loadSettings()
const gateway = ref(null)
const rag = ref(null)
const models = ref([])
const error = ref('')

onMounted(async () => {
  try {
    gateway.value = await api.gatewayHealth(settings)
    rag.value = await api.ragHealth(settings)
    models.value = (await api.listModels(settings)).data || []
  } catch (e) {
    error.value = e.message
  }
})
</script>

<template>
  <div>
    <h2 style="margin: 0 0 16px">系统概览</h2>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="grid">
      <div class="card">
        <h2>Gateway</h2>
        <p v-if="gateway" class="status-ok">● {{ gateway.status }} ({{ gateway.service }})</p>
        <p v-else class="status-fail">未连接</p>
      </div>
      <div class="card">
        <h2>RAG</h2>
        <template v-if="rag">
          <p class="status-ok">● {{ rag.status }}</p>
          <p style="color: var(--muted); font-size: 13px">
            Embedding: {{ rag.embedding_backend }} · Rerank: {{ rag.rerank_backend }} · Dim:
            {{ rag.embedding_dimension }}
          </p>
        </template>
        <p v-else class="status-fail">未连接</p>
      </div>
      <div class="card">
        <h2>可用模型</h2>
        <ul style="margin: 0; padding-left: 18px">
          <li v-for="m in models" :key="m.id">{{ m.id }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>
