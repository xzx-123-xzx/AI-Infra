<script setup>
import { onMounted, ref } from 'vue'
import { api, loadSettings } from '../api'

const settings = loadSettings()
const keys = ref([])
const error = ref('')
const newKey = ref('')
const form = ref({ name: '', tenant_id: 'default' })

async function load() {
  error.value = ''
  try {
    keys.value = await api.listKeys(settings)
  } catch (e) {
    error.value = e.message
  }
}

async function createKey() {
  try {
    const res = await api.createKey(settings, form.value)
    newKey.value = res.api_key
    form.value.name = ''
    await load()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div>
    <h2 style="margin: 0 0 16px">API Key 管理</h2>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="card">
      <h2>创建 Key</h2>
      <div class="row">
        <div>
          <label>名称</label>
          <input v-model="form.name" placeholder="my-app" />
        </div>
        <div>
          <label>租户 ID</label>
          <input v-model="form.tenant_id" />
        </div>
        <div style="flex: 0">
          <label>&nbsp;</label>
          <button @click="createKey">创建</button>
        </div>
      </div>
      <p v-if="newKey" class="mono" style="margin-top: 12px; color: var(--success)">
        新 Key（仅显示一次）：{{ newKey }}
      </p>
    </div>

    <div class="card">
      <h2>已有 Keys</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>名称</th>
            <th>租户</th>
            <th>前缀</th>
            <th>限流 RPM</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="k in keys" :key="k.id">
            <td>{{ k.id }}</td>
            <td>{{ k.name }}</td>
            <td>{{ k.tenant_id }}</td>
            <td class="mono">{{ k.key_prefix }}</td>
            <td>{{ k.rate_limit_rpm }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
