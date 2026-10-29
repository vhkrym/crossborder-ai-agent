<script setup lang="ts">
import {ref,onMounted,onBeforeUnmount,watch} from 'vue'
import {init,use,type ECharts} from 'echarts/core'
import {BarChart} from 'echarts/charts'
import {GridComponent,TooltipComponent,LegendComponent} from 'echarts/components'
import {CanvasRenderer} from 'echarts/renderers'
use([BarChart,GridComponent,TooltipComponent,LegendComponent,CanvasRenderer])
const props=defineProps<{title:string;labels:string[];series:{name:string;values:(number|null)[]}[];unit:string;cap?:number}>()
const emit=defineEmits<{select:[sku:string]}>();const root=ref<HTMLElement>();let chart:ECharts|undefined;let observer:ResizeObserver|undefined
function draw(){chart?.setOption({animation:false,color:['#bc657b','#81a8b2'],grid:{left:100,right:55,top:50,bottom:40},legend:{top:0},tooltip:{trigger:'axis',confine:true,renderMode:'richText',formatter:(items:any)=>items.map((p:any)=>{const v=props.series[p.seriesIndex]?.values[p.dataIndex];return `${props.labels[p.dataIndex]} · ${p.seriesName}: ${v==null?'不可计算':v.toLocaleString('zh-CN',{maximumFractionDigits:2})+' '+props.unit}${props.cap&&v!=null&&v>props.cap?'（图示截断）':''}`}).join('\n')},xAxis:{type:'value',name:props.unit,axisLabel:{hideOverlap:true}},yAxis:{type:'category',inverse:true,data:props.labels,axisLabel:{fontSize:11}},series:props.series.map(s=>({type:'bar',name:s.name,barMaxWidth:18,data:s.values.map(v=>({value:v===null?null:props.cap?Math.min(v,props.cap):v,itemStyle:v!==null&&v<0?{color:'#c95660'}:undefined}))}))},true)}
onMounted(()=>{chart=init(root.value!);chart.on('click',p=>{if(p.name)emit('select',p.name)});observer=new ResizeObserver(()=>chart?.resize());observer.observe(root.value!);draw()});watch(()=>[props.labels,props.series,props.cap],draw,{deep:true});onBeforeUnmount(()=>{observer?.disconnect();chart?.dispose()})
</script>
<template><article class="chart-card"><h2>{{title}}</h2><p>点击条形联动 SKU 筛选<span v-if="cap"> · 图示上限 {{cap}} 天，悬浮查看真实值</span></p><p v-if="!labels.length">暂无可展示数据</p><div ref="root" role="img" :aria-label="title" :style="{height:Math.max(320,labels.length*31+90)+'px',display:labels.length?'block':'none'}"/></article></template>
