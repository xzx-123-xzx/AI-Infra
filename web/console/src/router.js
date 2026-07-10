import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import ApiKeys from './views/ApiKeys.vue'
import KnowledgeBases from './views/KnowledgeBases.vue'
import KbDetail from './views/KbDetail.vue'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/keys', component: ApiKeys },
  { path: '/knowledge-bases', component: KnowledgeBases },
  { path: '/knowledge-bases/:id', component: KbDetail, props: true },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
