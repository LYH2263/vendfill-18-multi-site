<script setup lang="ts">
import { ref, watch } from 'vue'
import { ApiError, api, qs } from '../api'
import { useLocation } from '../composables/useLocation'
import type { RefillLineDTO } from '../types'

const { currentLocationId } = useLocation()
const lanes = ref<RefillLineDTO[]>([])
const loading = ref(false)
const loadError = ref('')

watch(currentLocationId, async (id, _old, onCleanup) => {
  if (!id) { lanes.value = []; return }
  let stale = false
  onCleanup(() => { stale = true })
  loading.value = true
  loadError.value = ''
  try {
    const data = await api<{ lanes: RefillLineDTO[] }>('/refills/full' + qs({ location_id: id }))
    if (!stale) lanes.value = data.lanes
  } catch (e: any) {
    if (stale) return
    if (e instanceof ApiError && e.status === 404) {
      lanes.value = []  // 无单 = 空态，不是错误
    } else {
      loadError.value = e?.message || '加载失败'
      lanes.value = []
    }
  } finally {
    if (!stale) loading.value = false
  }
}, { immediate: true })
</script>
<template>
  <h1>满仓</h1>
  <p class="sub">当前点位最新有效补货单中缺口为 0 的货道（无需补货）</p>
  <div v-if="!currentLocationId" class="vf-empty">请先在「点位」页选择或新建一个点位。</div>
  <template v-else>
    <div v-if="loadError" class="vf-error">{{ loadError }}</div>
    <div v-if="loading" class="vf-loading">加载中…</div>
    <template v-else>
      <div v-if="lanes.length === 0" class="vf-empty">
        当前点位暂无补货单（或没有满仓货道），请先到「补货小票」生成。
      </div>
      <div v-else class="card">
        <table>
          <thead><tr><th>货道</th><th>商品</th><th>库存</th><th>在途</th><th>容量</th></tr></thead>
          <tbody>
            <tr v-for="l in lanes" :key="l.lane_id ?? l.slot_no">
              <td>{{ l.slot_no }}</td><td>{{ l.sku_name }}</td><td>{{ l.stock }}</td><td>{{ l.in_transit }}</td><td>{{ l.capacity }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </template>
</template>
