<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api, loadSettings } from '../api'

const settings = loadSettings()
const kbs = ref([])
const error = ref('')
const form = ref({ name: '', tenant_id: 'default', description: '' })

async function load() {
  error.value = ''
  try {
    kbs.value = await api.listKbs(settings)
  } catch (e) {
    error.value = e.message
  }
}

async function createKb() {
  try {
    await api.createKb(settings, form.value)
    form.value = { name: '', tenant_id: 'default', description: '' }
    await load()
  } catch (e) {
    error.value = e.message
  }
}

async function remove(id) {
  if (!confirm('确认删除该知识库？')) return
  try {
    await api.deleteKb(settings, id)
    await load()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div>
    <h2 style="margin: 0 0 16px">知识库</h2>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="card">
      <h2>新建知识库</h2>
      <div class="row">
        <div>
          <label>名称</label>
          <input v-model="form.name" />
        </div>
        <div>
          <label>租户 ID</label>
          <input v-model="form.tenant_id" />
        </div>
        <div>
          <label>描述</label>
          <input v-model="form.description" />
        </div>
        <div style="flex: 0">
          <label>&nbsp;</label>
          <button @click="createKb">创建</button>
        </div>
      </div>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>名称</th>
            <th>租户</th>
            <th>描述</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="kb in kbs" :key="kb.id">
            <td>{{ kb.id }}</td>
            <td><RouterLink :to="`/knowledge-bases/${kb.id}`">{{ kb.name }}</RouterLink></td>
            <td>{{ kb.tenant_id }}</td>
            <td>{{ kb.description || '-' }}</td>
            <td><button class="danger" @click="remove(kb.id)">删除</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
