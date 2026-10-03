<script setup lang="ts">
import { ref, watch } from 'vue'
import { api, qs } from '../api'
import { useLocation } from '../composables/useLocation'
import type { SaleDTO } from '../types'

const { currentLocationId } = useLocation()
const rows = ref<SaleDTO[]>([])
const loading = ref(false)
const loadError = ref('')

watch(currentLocationId, async (id, _old, onCleanup) => {
  if (!id) { rows.value = []; return }
  let stale = false
  onCleanup(() => { stale = true })
  loading.value = true
  loadError.value = ''
  try {
    const data = await api<SaleDTO[]>('/sales' + qs({ location_id: id }))
    if (!stale) rows.value = data
  } catch (e: any) {
    if (!stale) { loadError.value = e?.message || '销量加载失败'; rows.value = [] }
  } finally {
    if (!stale) loading.value = false
  }
}, { immediate: true })
</script>
<template>
  <h1>销量</h1>
  <p class="sub">当前点位的近期出货记录</p>
  <div v-if="!currentLocationId" class="vf-empty">请先在「点位」页选择或新建一个点位。</div>
  <template v-else>
    <div v-if="loadError" class="vf-error">{{ loadError }}</div>
    <div v-if="loading" class="vf-loading">加载中…</div>
    <div v-else-if="rows.length === 0" class="vf-empty">当前点位暂无销量记录。</div>
    <div v-else class="card">
      <table>
        <thead><tr><th>货道</th><th>商品</th><th>数量</th><th>时间</th></tr></thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.slot_no }}</td><td>{{ r.sku_name }}</td><td>{{ r.qty }}</td><td>{{ r.sold_at }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </template>
</template>
