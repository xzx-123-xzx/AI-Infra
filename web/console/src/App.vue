<script setup>
import { RouterLink, RouterView } from 'vue-router'
import SettingsPanel from './components/SettingsPanel.vue'
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <h1>AI-Infra</h1>
      <nav class="nav">
        <RouterLink to="/">概览</RouterLink>
        <RouterLink to="/keys">API Keys</RouterLink>
        <RouterLink to="/knowledge-bases">知识库</RouterLink>
        <RouterLink to="/prompts">Prompt</RouterLink>
        <RouterLink to="/tenants">租户</RouterLink>
        <RouterLink to="/mlops">MLOps</RouterLink>
        <RouterLink to="/eval">评测</RouterLink>
        <RouterLink to="/federated">联邦检索</RouterLink>
        <RouterLink to="/workflows">Agent 编排</RouterLink>
      </nav>
    </aside>
    <main class="main">
      <SettingsPanel />
      <RouterView />
    </main>
  </div>
</template>
