<script setup lang="ts">
import { ref, watch } from 'vue'
import { ApiError, api, qs } from '../api'
import { useLocation } from '../composables/useLocation'

const { currentLocationId } = useLocation()
const s = ref<Record<string, number> | null>(null)
const loading = ref(false)
const loadError = ref('')

watch(currentLocationId, async (id, _old, onCleanup) => {
  if (!id) { s.value = null; return }
  let stale = false
  onCleanup(() => { stale = true })
  loading.value = true
  loadError.value = ''
  try {
    const data = await api<Record<string, number>>('/refills/summary' + qs({ location_id: id }))
    if (!stale) s.value = data
  } catch (e: any) {
    if (stale) return
    if (e instanceof ApiError && e.status === 404) {
      s.value = null  // 无单空态
    } else {
      loadError.value = e?.message || '加载失败'
    }
  } finally {
    if (!stale) loading.value = false
  }
}, { immediate: true })
</script>
<template>
  <h1>汇总</h1>
  <p class="sub">当前点位最新有效补货单的合计</p>
  <div v-if="!currentLocationId" class="vf-empty">请先在「点位」页选择或新建一个点位。</div>
  <template v-else>
    <div v-if="loadError" class="vf-error">{{ loadError }}</div>
    <div v-if="loading" class="vf-loading">加载中…</div>
    <div v-else-if="!s" class="vf-empty">
      当前点位暂无补货单，请先到「补货小票」生成。
    </div>
    <div v-else class="card grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem">
      <div><div class="muted">建议补货总量</div><div class="stat">{{ s.total_fill }}</div></div>
      <div><div class="muted">待补货道</div><div class="stat">{{ s.need_fill_count }}</div></div>
      <div><div class="muted">满仓货道</div><div class="stat">{{ s.full_count }}</div></div>
      <div><div class="muted">超占货道</div><div class="stat">{{ s.overbooked_count }}</div></div>
    </div>
  </template>
</template>
