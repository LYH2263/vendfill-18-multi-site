<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ApiError, api, qs } from '../api'
import { useLocation } from '../composables/useLocation'
import type { LaneDTO } from '../types'

const { currentLocationId } = useLocation()
const rows = ref<LaneDTO[]>([])
const loading = ref(false)
const loadError = ref('')
const formError = ref('')
const saving = ref(false)

const form = reactive({ slot_no: '', sku_name: '', capacity: 20, stock: 0, in_transit: 0 })

async function load(id: number) {
  loading.value = true
  loadError.value = ''
  try {
    rows.value = await api<LaneDTO[]>('/lanes' + qs({ location_id: id }))
  } catch (e: any) {
    loadError.value = e?.message || '货道加载失败'
    rows.value = []
  } finally {
    loading.value = false
  }
}

watch(currentLocationId, (id) => {
  formError.value = ''
  if (id) load(id)
  else rows.value = []
}, { immediate: true })

async function createLane() {
  const id = currentLocationId.value
  if (!id) return
  formError.value = ''
  if (!form.slot_no.trim() || !form.sku_name.trim()) {
    formError.value = '货道编号与商品名必填'
    return
  }
  saving.value = true
  try {
    await api('/lanes', {
      method: 'POST',
      body: JSON.stringify({
        location_id: id,
        slot_no: form.slot_no.trim(),
        sku_name: form.sku_name.trim(),
        capacity: Number(form.capacity),
        stock: Number(form.stock),
        in_transit: Number(form.in_transit),
      }),
    })
    form.slot_no = form.sku_name = ''
    await load(id)
  } catch (e: any) {
    formError.value = e?.message || '新建货道失败'
  } finally {
    saving.value = false
  }
}

async function removeLane(lane: LaneDTO) {
  const id = currentLocationId.value
  if (!id) return
  if (!window.confirm(`删除货道 ${lane.slot_no}（${lane.sku_name}）？其销量记录将一并删除。`)) return
  try {
    await api(`/lanes/${lane.id}`, { method: 'DELETE' })
    await load(id)
  } catch (e: any) {
    if (e instanceof ApiError && e.status === 409) {
      window.alert(e.message)
    } else {
      window.alert(e?.message || '删除失败')
    }
  }
}
</script>
<template>
  <h1>货道格子</h1>
  <p class="sub">仅显示当前点位的货道 · 格内库存条 · 缺口按容量−库存−在途</p>

  <div v-if="!currentLocationId" class="vf-empty">请先在「点位」页选择或新建一个点位。</div>
  <template v-else>
    <form class="vf-form" @submit.prevent="createLane">
      <label>编号<input v-model="form.slot_no" placeholder="D1" maxlength="16" /></label>
      <label>商品<input v-model="form.sku_name" placeholder="苏打水" maxlength="64" /></label>
      <label>容量<input v-model.number="form.capacity" type="number" min="1" /></label>
      <label>库存<input v-model.number="form.stock" type="number" min="0" /></label>
      <label>在途<input v-model.number="form.in_transit" type="number" min="0" /></label>
      <button class="btn" type="submit" :disabled="saving">{{ saving ? '保存中…' : '添加货道' }}</button>
      <span v-if="formError" style="color:var(--vf-red);font-size:0.74rem">{{ formError }}</span>
    </form>

    <div v-if="loadError" class="vf-error">{{ loadError }}</div>
    <div v-if="loading" class="vf-loading">加载中…</div>
    <div v-else-if="rows.length === 0" class="vf-empty">当前点位还没有货道，请在上方添加。</div>
    <div v-else class="vf-slot-grid">
      <div v-for="r in rows" :key="r.id" class="vf-slot">
        <button class="vf-slot-del" title="删除货道" @click="removeLane(r)">×</button>
        <div class="vf-slot-no">{{ r.slot_no }}</div>
        <div class="vf-slot-sku">{{ r.sku_name }}</div>
        <div class="vf-slot-bar">
          <div
            class="vf-slot-fill"
            :class="{ 'vf-need': r.gap > 0 }"
            :style="{ width: Math.min(r.fill_pct, 100) + '%' }"
          />
        </div>
        <div class="vf-slot-meta">{{ r.stock }}/{{ r.capacity }} · 缺 {{ r.gap }}</div>
      </div>
    </div>
  </template>
</template>
