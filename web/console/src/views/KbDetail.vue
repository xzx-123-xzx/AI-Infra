<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api, loadSettings } from '../api'

const route = useRoute()
const settings = loadSettings()
const kb = ref(null)
const docs = ref([])
const error = ref('')
const query = ref('')
const answer = ref('')
const sources = ref([])
const uploading = ref(false)

async function load() {
  const id = Number(route.params.id)
  error.value = ''
  try {
    kb.value = await api.getKb(settings, id)
    docs.value = await api.listDocs(settings, id)
  } catch (e) {
    error.value = e.message
  }
}

async function onUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    await api.uploadDoc(settings, kb.value.id, file)
    await load()
  } catch (err) {
    error.value = err.message
  } finally {
    uploading.value = false
    e.target.value = ''
  }
}

async function removeDoc(docId) {
  if (!confirm('删除该文档？')) return
  await api.deleteDoc(settings, kb.value.id, docId)
  await load()
}

async function ask() {
  error.value = ''
  answer.value = ''
  sources.value = []
  try {
    const res = await api.chat(settings, kb.value.id, query.value)
    answer.value = res.answer
    sources.value = res.sources || []
  } catch (e) {
    error.value = e.message
  }
}

watch(() => route.params.id, load, { immediate: true })
onMounted(load)
</script>

<template>
  <div v-if="kb">
    <h2 style="margin: 0 0 8px">{{ kb.name }}</h2>
    <p style="color: var(--muted); margin: 0 0 16px">ID {{ kb.id }} · {{ kb.tenant_id }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="card">
      <h2>文档</h2>
      <input type="file" accept=".txt,.md,.pdf" @change="onUpload" />
      <p v-if="uploading" style="color: var(--muted)">上传处理中...</p>
      <table style="margin-top: 12px">
        <thead>
          <tr>
            <th>文件名</th>
            <th>状态</th>
            <th>分块数</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in docs" :key="d.id">
            <td>{{ d.filename }}</td>
            <td>{{ d.status }}</td>
            <td>{{ d.chunk_count }}</td>
            <td><button class="danger" @click="removeDoc(d.id)">删除</button></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>RAG 问答</h2>
      <div class="row">
        <div>
          <label>问题</label>
          <input v-model="query" placeholder="输入问题..." @keyup.enter="ask" />
        </div>
        <div style="flex: 0">
          <label>&nbsp;</label>
          <button @click="ask">提问</button>
        </div>
      </div>
      <div v-if="answer" style="margin-top: 16px">
        <label>回答</label>
        <div class="chat-box">{{ answer }}</div>
        <label style="margin-top: 12px">引用来源 ({{ sources.length }})</label>
        <div v-for="(s, i) in sources" :key="i" class="chat-box" style="margin-top: 8px; font-size: 13px">
          doc={{ s.doc_id }} chunk={{ s.chunk_index }} score={{ s.rerank_score ?? s.score }}
          <hr style="border-color: var(--border)" />
          {{ s.content }}
        </div>
      </div>
    </div>
  </div>
</template>
