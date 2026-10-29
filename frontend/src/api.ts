import axios from 'axios'
export type Money=string
export interface Store {id:number;name:string;marketplace:string;market:string;currency:string}
export interface Profit {sku:string;quantity:number;gross_sales:Money;refund_amount:Money;net_revenue:Money;purchase_cost:Money|null;logistics_cost:Money|null;platform_fees:Money|null;ad_spend:Money;contribution_profit:Money|null;profit_margin:Money|null;cost_increased:boolean;reasons:string[]}
export interface Advertising {sku:string;spend:Money;attributed_sales:Money;clicks:number;ad_orders:number;acos:Money|null;roas:Money|null;cpc:Money|null;conversion_rate:Money|null;reasons:string[]}
export interface Inventory {sku:string;snapshot_date:string|null;on_hand:number|null;reserved:number|null;available:number|null;inbound:number|null;lead_time_days:number|null;observed_days:number;average_daily_sales:Money|null;coverage_days:Money|null;risk:string;suggested_replenishment:number|null;reasons:string[]}
export interface Analysis {summary:{net_revenue:Money|null;contribution_profit:Money|null;acos:Money|null;inventory_risk_skus:number;inventory_unknown_skus:number;reasons:string[]}|null;store_id:number;currency:string;start_date:string;end_date:string;units:Record<string,string>;profit:Profit[];advertising:Advertising[];inventory:Inventory[];reasons:string[];window:number|null;safety_days:number|null}
export const api=axios.create({baseURL:import.meta.env.VITE_API_BASE_URL || '/api/v1',timeout:20000})
export function errorText(e:unknown):string {if(axios.isAxiosError(e)) return typeof e.response?.data?.detail==='string'?e.response.data.detail:`请求失败（${e.response?.status || e.code || '网络不可达'}），请检查后端及数据库配置`;return '请求失败，请重试'}
