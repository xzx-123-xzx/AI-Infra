<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api, loadSettings } from '../api'

const route = useRoute()
const settings = loadSettings()
const kb = ref(null)
const docs = ref([])
const syncSources = ref([])
const error = ref('')
const query = ref('')
const answer = ref('')
const sources = ref([])
const uploading = ref(false)
const syncForm = ref({
  name: '',
  source_type: 'confluence',
  configJson: '{"base_url":"https://xxx.atlassian.net","page_id":"123","token":"xxx"}',
  cron_minutes: 0,
})
let pollTimer = null

async function load() {
  const id = Number(route.params.id)
  error.value = ''
  try {
    kb.value = await api.getKb(settings, id)
    docs.value = await api.listDocs(settings, id)
    syncSources.value = await api.listSyncSources(settings, id)
  } catch (e) {
    error.value = e.message
  }
}

function needsPoll() {
  return docs.value.some((d) => ['queued', 'processing', 'pending'].includes(d.status))
}

function startPoll() {
  stopPoll()
  if (!needsPoll()) return
  pollTimer = setInterval(async () => {
    if (!kb.value) return
    docs.value = await api.listDocs(settings, kb.value.id)
    if (!needsPoll()) stopPoll()
  }, 2000)
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function onUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  uploading.value = true
  try {
    await api.uploadDoc(settings, kb.value.id, file)
    await load()
    startPoll()
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

async function createSync() {
  try {
    const config = JSON.parse(syncForm.value.configJson)
    await api.createSyncSource(settings, kb.value.id, {
      name: syncForm.value.name,
      source_type: syncForm.value.source_type,
      config,
      cron_minutes: syncForm.value.cron_minutes,
    })
    await load()
  } catch (e) {
    error.value = e.message
  }
}

async function runSync(sourceId) {
  await api.runSync(settings, kb.value.id, sourceId)
  await load()
  startPoll()
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
onMounted(startPoll)
onUnmounted(stopPoll)
watch(docs, startPoll, { deep: true })
</script>

<template>
  <div v-if="kb">
    <h2 style="margin: 0 0 8px">{{ kb.name }}</h2>
    <p style="color: var(--muted); margin: 0 0 16px">ID {{ kb.id }} · {{ kb.tenant_id }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="card">
      <h2>文档</h2>
      <input type="file" accept=".txt,.md,.pdf,.png,.jpg,.jpeg,.mp3,.wav" @change="onUpload" />
      <p v-if="uploading" style="color: var(--muted)">上传中...</p>
      <table style="margin-top: 12px">
        <thead>
          <tr>
            <th>文件名</th>
            <th>状态</th>
            <th>进度</th>
            <th>分块数</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in docs" :key="d.id">
            <td>{{ d.filename }}</td>
            <td>{{ d.status }}</td>
            <td>
              <div style="background: var(--border); border-radius: 4px; height: 8px; width: 80px">
                <div
                  :style="{
                    width: (d.progress || 0) + '%',
                    background: d.status === 'failed' ? '#e55' : 'var(--accent)',
                    height: '8px',
                    borderRadius: '4px',
                  }"
                />
              </div>
              {{ d.progress || 0 }}%
            </td>
            <td>{{ d.chunk_count }}</td>
            <td><button class="danger" @click="removeDoc(d.id)">删除</button></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>外部同步（Confluence / 飞书）</h2>
      <div class="grid">
        <div>
          <label>名称</label>
          <input v-model="syncForm.name" />
        </div>
        <div>
          <label>类型</label>
          <select v-model="syncForm.source_type">
            <option value="confluence">Confluence</option>
            <option value="lark">飞书文档</option>
          </select>
        </div>
        <div>
          <label>定时（分钟，0=手动）</label>
          <input v-model.number="syncForm.cron_minutes" type="number" />
        </div>
      </div>
      <label style="margin-top: 8px; display: block">Config JSON</label>
      <textarea v-model="syncForm.configJson" rows="3" style="width: 100%" />
      <button style="margin-top: 8px" @click="createSync">添加同步源</button>
      <table v-if="syncSources.length" style="margin-top: 12px">
        <thead>
          <tr>
            <th>名称</th>
            <th>类型</th>
            <th>上次同步</th>
            <th>状态</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in syncSources" :key="s.id">
            <td>{{ s.name }}</td>
            <td>{{ s.source_type }}</td>
            <td>{{ s.last_sync_at || '-' }}</td>
            <td>{{ s.last_status || '-' }}</td>
            <td><button class="secondary" @click="runSync(s.id)">立即同步</button></td>
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
