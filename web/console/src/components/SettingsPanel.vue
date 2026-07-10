<script setup>
import { ref } from 'vue'
import { loadSettings, saveSettings } from './api'

const open = ref(false)
const settings = ref(loadSettings())
const saved = ref(false)

function toggle() {
  open.value = !open.value
  settings.value = loadSettings()
}

function submit() {
  saveSettings(settings.value)
  saved.value = true
  setTimeout(() => (saved.value = false), 2000)
}
</script>

<template>
  <div class="card">
    <div class="row" style="align-items: center">
      <h2 style="margin: 0; flex: 1">连接设置</h2>
      <button class="secondary" @click="toggle">{{ open ? '收起' : '编辑' }}</button>
    </div>
    <p v-if="!open" class="mono" style="color: var(--muted); margin: 12px 0 0">
      Gateway: {{ settings.gatewayBase }} · RAG: {{ settings.ragBase }}
    </p>
    <form v-if="open" @submit.prevent="submit" style="margin-top: 16px">
      <div class="grid">
        <div>
          <label>Admin Token</label>
          <input v-model="settings.adminToken" type="password" />
        </div>
        <div>
          <label>Gateway Base URL</label>
          <input v-model="settings.gatewayBase" placeholder="/api/gateway" />
        </div>
        <div>
          <label>RAG Base URL</label>
          <input v-model="settings.ragBase" placeholder="/api/rag" />
        </div>
      </div>
      <div style="margin-top: 12px">
        <button type="submit">保存</button>
        <span v-if="saved" style="margin-left: 12px; color: var(--success)">已保存</span>
      </div>
    </form>
  </div>
</template>
