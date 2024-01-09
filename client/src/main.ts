import { createApp } from 'vue'
import App from './App.vue'
import './style.css'
import { getDirectoryInfo } from './api/rest.ts'

createApp(App).mount('#app')
getDirectoryInfo()
