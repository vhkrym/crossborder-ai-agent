import {createApp} from 'vue'
import {createRouter,createWebHistory} from 'vue-router'
import App from './App.vue'
import './style.css'
const router=createRouter({history:createWebHistory(),routes:[{path:'/',redirect:'/overview'},{path:'/decisions',component:()=>import('./Decisions.vue')},{path:'/agent-tasks',component:()=>import('./AgentTasks.vue')},...['overview','profit','advertising','inventory'].map(path=>({path:'/'+path,component:()=>import('./Dashboard.vue')})),{path:'/:pathMatch(.*)*',redirect:'/overview'}]})
createApp(App).use(router).mount('#app')
