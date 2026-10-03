<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ApiError, api } from '../api'
import { useLocation } from '../composables/useLocation'

const {
  locations, currentLocationId, loaded, initError, init,
  refreshLocations, setCurrentLocation,
} = useLocation()

const form = reactive({ code: '', name: '', address: '' })
const formError = ref('')
const creating = ref(false)
const actionError = ref('')

onMounted(init)

async function createLocation() {
  formError.value = ''
  if (!form.code.trim() || !form.name.trim()) {
    formError.value = '编码与名称必填'
    return
  }
  creating.value = true
  try {
    const row = await api('/locations', {
      method: 'POST',
      body: JSON.stringify({
        code: form.code.trim(), name: form.name.trim(), address: form.address.trim(),
      }),
    })
    form.code = form.name = form.address = ''
    await refreshLocations(row.id)  // 新建后自动切到新点位
  } catch (e: any) {
    formError.value = e?.message || '新建失败'
  } finally {
    creating.value = false
  }
}

async function removeLocation(id: number, code: string, activeCount: number) {
  actionError.value = ''
  if (!window.confirm(`确认删除点位 ${code}？该点位的货道、销量与已作废单据都会被删除。`)) return
  try {
    await api(`/locations/${id}`, { method: 'DELETE' })
    // refreshLocations 发现当前点位已消失时会自动回退到剩余第一个（或 null）。
    await refreshLocations()
  } catch (e: any) {
    if (e instanceof ApiError && e.status === 409) {
      actionError.value = `点位 ${code} 存在未作废补货单，不能删除；请先到「补货小票」页把该点位的单据作废。`
    } else {
      actionError.value = e?.message || '删除失败'
    }
  }
}
</script>
<template>
  <h1>点位 / 机位</h1>
  <p class="sub">点击卡片切换当前点位；五页列表与补货生成只作用于当前点位</p>

  <div v-if="initError" class="vf-error">{{ initError }}</div>
  <div v-if="actionError" class="vf-error">{{ actionError }}</div>

  <div
    class="vf-site-rail"
    style="flex-direction:row;flex-wrap:wrap;border:none;background:transparent;padding:0;gap:0.5rem;margin-bottom:1rem"
  >
    <div v-if="!loaded" class="vf-loading">加载点位中…</div>
    <div
      v-for="r in locations"
      :key="r.id"
      class="vf-site-btn vf-loc-card"
      :class="{ 'vf-current': r.id === currentLocationId }"
      @click="setCurrentLocation(r.id)"
    >
      <strong style="display:block;color:var(--vf-led)">{{ r.code }}
        <span v-if="r.id === currentLocationId" class="badge badge-ok" style="margin-left:0.3rem">当前</span>
      </strong>
      <span style="font-size:0.72rem">{{ r.name }}</span>
      <span class="vf-loc-meta">货道 {{ r.lane_count }} · 未作废单 {{ r.active_order_count }}</span>
      <div class="vf-card-actions">
        <button
          class="vf-btn-danger"
          @click.stop="removeLocation(r.id, r.code, r.active_order_count)"
        >删除</button>
      </div>
    </div>
    <div v-if="loaded && locations.length === 0" class="vf-empty" style="flex:1">
      还没有点位，请在下方新建第一个点位。
    </div>
  </div>

  <form class="vf-form" @submit.prevent="createLocation">
    <label>编码
      <input v-model="form.code" placeholder="VM-02" maxlength="32" />
    </label>
    <label>名称
      <input v-model="form.name" placeholder="地铁口 B 点位" maxlength="128" />
    </label>
    <label>地址
      <input v-model="form.address" placeholder="可选" maxlength="256" />
    </label>
    <button class="btn" :disabled="creating" type="submit">{{ creating ? '新建中…' : '新建点位' }}</button>
    <span v-if="formError" class="vf-error" style="margin:0;border:none;padding:0">{{ formError }}</span>
  </form>

  <div class="card">
    <table>
      <thead><tr><th>编码</th><th>名称</th><th>地址</th><th>货道数</th><th>未作废单</th></tr></thead>
      <tbody>
        <tr v-for="r in locations" :key="r.id">
          <td>{{ r.code }}</td><td>{{ r.name }}</td><td>{{ r.address }}</td>
          <td>{{ r.lane_count }}</td><td>{{ r.active_order_count }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
