import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import ApiKeys from './views/ApiKeys.vue'
import KnowledgeBases from './views/KnowledgeBases.vue'
import KbDetail from './views/KbDetail.vue'
import Prompts from './views/Prompts.vue'
import Tenants from './views/Tenants.vue'
import Mlops from './views/Mlops.vue'
import Eval from './views/Eval.vue'
import Federated from './views/Federated.vue'
import Workflows from './views/Workflows.vue'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/keys', component: ApiKeys },
  { path: '/knowledge-bases', component: KnowledgeBases },
  { path: '/knowledge-bases/:id', component: KbDetail, props: true },
  { path: '/prompts', component: Prompts },
  { path: '/tenants', component: Tenants },
  { path: '/mlops', component: Mlops },
  { path: '/eval', component: Eval },
  { path: '/federated', component: Federated },
  { path: '/workflows', component: Workflows },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
