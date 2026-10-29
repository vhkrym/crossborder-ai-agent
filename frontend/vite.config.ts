import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import AutoImport from 'unplugin-auto-import/vite'
import {ElementPlusResolver} from 'unplugin-vue-components/resolvers'
export default defineConfig(({ mode }) => { const env=loadEnv(mode,process.cwd(),''); return {plugins:[vue(),AutoImport({resolvers:[ElementPlusResolver()],dts:false}),Components({resolvers:[ElementPlusResolver()],dts:false})],build:{rollupOptions:{output:{manualChunks(id){if(id.includes('/node_modules/echarts/'))return 'charts';if(id.includes('/node_modules/zrender/'))return 'renderer';}}}},server:{proxy:{'/api':{target:env.BACKEND_URL || 'http://127.0.0.1:8000',changeOrigin:true}}}} })
