<script setup lang="ts">
import { ref, watch } from 'vue'
import { ApiError, api, qs } from '../api'
import { useLocation } from '../composables/useLocation'
import type { RefillOrderDTO } from '../types'

const { currentLocationId } = useLocation()
const orders = ref<RefillOrderDTO[]>([])
const loading = ref(false)
const loadError = ref('')
const generating = ref(false)
const generateError = ref('')

// 生成期间切换点位：abort 在途请求，且 tag 不符的响应绝不落到新点位视图。
let runController: AbortController | null = null

async function load(id: number) {
  loading.value = true
  loadError.value = ''
  try {
    orders.value = await api<RefillOrderDTO[]>('/refills' + qs({ location_id: id }))
  } catch (e: any) {
    loadError.value = e?.message || '补货单加载失败'
    orders.value = []
  } finally {
    loading.value = false
  }
}

watch(currentLocationId, (id) => {
  generateError.value = ''
  runController?.abort()  // 丢弃为旧点位发起的生成
  runController = null
  if (id) load(id)
  else orders.value = []
}, { immediate: true })

async function generate() {
  const id = currentLocationId.value
  if (!id || generating.value) return
  const tag = id  // 响应回来时点位必须仍是 tag
  generating.value = true
  generateError.value = ''
  runController?.abort()
  const controller = new AbortController()
  runController = controller
  try {
    await api('/refills/run' + qs({ location_id: id }), {
      method: 'POST',
      signal: controller.signal,
    })
    if (currentLocationId.value === tag) await load(tag)
  } catch (e: any) {
    if (e?.name === 'AbortError') return
    if (currentLocationId.value === tag) {
      generateError.value = e?.message || '生成失败'
    }
  } finally {
    if (runController === controller) { runController = null; generating.value = false }
  }
}

async function voidOrder(order: RefillOrderDTO) {
  const id = currentLocationId.value
  if (!id) return
  if (!window.confirm(`作废第 ${order.id} 号补货单？作废后该点位才可删除。`)) return
  try {
    await api(`/refills/${order.id}/void` + qs({ location_id: id }), { method: 'POST' })
    await load(id)
  } catch (e: any) {
    if (e instanceof ApiError && e.status === 409) {
      await load(id)  // 已作废，刷新状态即可
    } else {
      window.alert(e?.message || '作废失败')
    }
  }
}

const statusText = (s: string) => s === 'need_fill' ? '待补' : s === 'full' ? '满仓' : '超占'
</script>
<template>
  <h1>补货小票</h1>
  <p class="sub">仅为当前点位生成 · gap = 容量 − 库存 − 在途 · 头与明细单事务提交</p>

  <div v-if="!currentLocationId" class="vf-empty">请先在「点位」页选择或新建一个点位。</div>
  <template v-else>
    <button class="btn" :disabled="generating" @click="generate">
      {{ generating ? '生成中…' : '生成补货单' }}
    </button>
    <div v-if="generateError" class="vf-error" style="margin-top:0.6rem">{{ generateError }}</div>
    <div v-if="loadError" class="vf-error" style="margin-top:0.6rem">{{ loadError }}</div>
    <div v-if="loading" class="vf-loading" style="margin-top:0.8rem">加载中…</div>
    <div v-else-if="orders.length === 0" class="vf-empty" style="margin-top:0.8rem">
      当前点位暂无补货单，点击上方按钮生成。
    </div>

    <div style="display:flex;flex-direction:column;gap:0.9rem;margin-top:1rem;align-items:flex-start">
      <div v-for="o in orders" :key="o.id">
        <div class="vf-receipt" :class="{ 'vf-order-void': o.status === 'void' }">
          <h2>
            *** VendFill 补货单 #{{ o.id }} ***
            <span :class="o.status === 'void' ? 'badge badge-bad' : 'badge badge-ok'" style="margin-left:0.4rem">
              {{ o.status === 'void' ? '已作废' : '有效' }}
            </span>
          </h2>
          <div class="vf-receipt-line" style="font-weight:700;border-bottom:2px dashed #8a7e64">
            <span>货道 / 商品</span><span>补量</span>
          </div>
          <div class="vf-receipt-line" v-for="l in o.lines" :key="l.lane_id ?? (l.slot_no + l.sku_name)">
            <span>{{ l.slot_no }} {{ l.sku_name }}
              <small>({{ statusText(l.status) }})</small>
            </span>
            <span>{{ l.fill_qty }} / 缺{{ l.gap }}</span>
          </div>
          <p style="text-align:center;margin:0.8rem 0 0;font-size:0.72rem;color:#6a5e48">
            {{ o.created_at }} · 合计补 {{ o.total_fill }}
            <template v-if="o.status === 'void'"> · 作废于 {{ o.voided_at }}</template>
          </p>
        </div>
        <button
          v-if="o.status === 'active'"
          class="vf-btn-void"
          style="margin-top:0.45rem"
          @click="voidOrder(o)"
        >作废此单</button>
      </div>
    </div>
  </template>
</template>
